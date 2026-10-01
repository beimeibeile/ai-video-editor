"""
端到端视频生成流程 (E2E Pipeline)
整合：分镜引擎 → 素材加工(LTX-2.5/ffmpeg) → 剪映合成

流程：
1. 创意文案生成（cap_creative_engine）
2. 分镜生成（cap_storyboard_engine）
3. 素材加工（LTX-2.5 I2V / ffmpeg Ken Burns）
4. 剪映合成（转场+字幕+音效+BGM）
"""
import os
import sys
import json
from typing import List, Dict, Optional, Any

# 模块路径
SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SKILL_ROOT)

from cap_storyboard_engine import generate_storyboard, Storyboard
from cap_asset_library import get_library

# 环境检测（首次运行时检查依赖）
try:
    from cap_env_checker import check_environment as _check_env
    _ENV_CHECKER_AVAILABLE = True
except ImportError:
    _ENV_CHECKER_AVAILABLE = False

# 创意引擎（可选，用于自动生成创意字幕）
try:
    from cap_creative_engine import CreativeEngine
    _CREATIVE_ENGINE_AVAILABLE = True
except ImportError:
    _CREATIVE_ENGINE_AVAILABLE = False

# 片头生成器（特效库集成）
try:
    _scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts")
    sys.path.insert(0, _scripts_dir)
    from intro_builder import add_intro_to_project as _add_intro_effect
    _INTRO_BUILDER_AVAILABLE = True
except ImportError:
    _INTRO_BUILDER_AVAILABLE = False

# 半透明字幕条（特效库集成）
try:
    from subtitle_bar import add_subtitle_bar as _add_subtitle_bar_effect
    _SUBTITLE_BAR_AVAILABLE = True
except ImportError:
    _SUBTITLE_BAR_AVAILABLE = False

# 蒙版展开快闪（特效库集成）—— v4/v5双轴向展开
try:
    from mask_flash_transition import create_solid_color_image, add_rect_mask_to_segment as _add_rect_mask
    from mask_keyframe import apply_mask_expand as _apply_mask_kf, save_with_mask_keyframes as _save_with_mask_kf
    _MASK_FLASH_AVAILABLE = True
    _MASK_KF_AVAILABLE = True
except ImportError:
    _MASK_FLASH_AVAILABLE = False
    _MASK_KF_AVAILABLE = False

# 人物介绍卡片（特效库集成）
try:
    from character_intro import add_character_intro_to_project as _add_char_intro
    _CHARACTER_INTRO_AVAILABLE = True
except ImportError:
    _CHARACTER_INTRO_AVAILABLE = False

# 文字排版预设（特效库集成）
try:
    from text_layout import add_text_layout as _add_text_layout
    _TEXT_LAYOUT_AVAILABLE = True
except ImportError:
    _TEXT_LAYOUT_AVAILABLE = False

# 拍立得照片墙（特效库集成）
try:
    from polaroid_wall import add_polaroid_photos_to_project as _add_polaroid_photos
    _POLAROID_WALL_AVAILABLE = True
except ImportError:
    _POLAROID_WALL_AVAILABLE = False

# 发光轮廓效果（特效库集成）
try:
    from glow_outline import add_glow_outline_to_project as _add_glow_outline
    _GLOW_OUTLINE_AVAILABLE = True
except ImportError:
    _GLOW_OUTLINE_AVAILABLE = False

# 混合模式工具（保存时自动注入）
try:
    from mix_mode import save_with_mix_modes
    _MIX_MODE_AVAILABLE = True
except ImportError:
    _MIX_MODE_AVAILABLE = False

# 质量门框架（cap_creative）
try:
    from cap_creative import validate as qg_validate, GateReport
    _QUALITY_GATE_AVAILABLE = True
except ImportError:
    _QUALITY_GATE_AVAILABLE = False

# Blender扩展特效库（转场遮罩/粒子背景/光线扫描）
try:
    from blender_effects import create_transition as _blender_create_transition
    _BLENDER_EFFECTS_AVAILABLE = True
except ImportError:
    _BLENDER_EFFECTS_AVAILABLE = False

# 片头风格→模板映射
_INTRO_STYLE_MAP = {
    "impact": "flash_title",
    "cute": "warm_intro",
    "funny": "tag_intro",
    "minimal": "minimal_title",
    "suspense": "cyber_intro",
}

# 字幕风格→字幕条样式映射
_SUBTITLE_BAR_STYLE_MAP = {
    "cinema": "rect_dark",
    "vlog": "pill_warm",
    "news": "pill_cool",
    "tech": "pill_cyber",
    "bar_cyber": "pill_cyber",
    "bar_warm": "pill_warm",
    "bar_cool": "pill_cool",
    "bar_dark": "rect_dark",
    "bar_minimal": "rect_minimal",
}

# 蒙版快闪配色预设
_MASK_FLASH_PRESETS = {
    "cyberpunk": [(0, 200, 255), (255, 0, 200), (200, 255, 0)],
    "warm": [(255, 100, 50), (255, 200, 50), (255, 50, 100)],
    "cool": [(50, 100, 255), (50, 200, 255), (100, 255, 200)],
    "neon": [(255, 0, 100), (0, 255, 200), (255, 255, 0)],
}


class E2EPipeline:
    """端到端视频生成流程"""

    def __init__(self,
                 project_dir: str = None,
                 jianying_skill_path: str = None,
                 ffmpeg_path: str = None,
                 comfyui_addr: str = "http://127.0.0.1:8188"):
        # 项目目录
        if project_dir is None:
            project_dir = os.path.join(os.path.expanduser("~"), "Videos", "剪映导出", "Doubao_Jianying-editor")
        self.project_dir = project_dir
        self.work_dir = os.path.join(project_dir, "debug", "e2e_pipeline")
        os.makedirs(os.path.join(self.work_dir, "input"), exist_ok=True)
        os.makedirs(os.path.join(self.work_dir, "output"), exist_ok=True)

        # 剪映
        if jianying_skill_path is None:
            jianying_skill_path = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
        self.jy_skill = jianying_skill_path

        # ffmpeg
        self.ffmpeg = ffmpeg_path or r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"

        # ComfyUI
        self.comfyui_addr = comfyui_addr

        # 素材库
        self.asset_lib = get_library()

    def run(self,
            theme: str,
            style: str = "cinematic",
            duration: float = 15.0,
            shot_count: int = 5,
            project_name: str = None,
            width: int = 1080,
            height: int = 1920,
            hook_text: str = "",
            ending_text: str = "",
            custom_subtitles: List[str] = None,
            input_images: List[str] = None,
            use_ltx: bool = True,
            ltx_shots: List[int] = None,
            use_flf2v: bool = False,
            flf2v_shots: List[int] = None,
            use_hunyuan: bool = False,
            hunyuan_shots: List[int] = None,
            add_bgm: bool = True,
            add_intro: bool = False,
            use_blender_intro: bool = False,
            blender_intro_style: str = "cinematic",
            use_blender_transitions: bool = False,
            blender_transition_style: str = "fade",
            pip_config: List[Dict] = None,
            auto_beat: bool = False,
            beat_threshold: float = 0.5,
            character_intros: List[Dict] = None,
            text_layout_style: str = None,
            photo_wall: List[str] = None,
            glow_outline_shots: List[int] = None) -> Dict[str, Any]:
        """
        执行端到端流程

        Args:
            theme: 视频主题
            style: 风格 cinematic/vlog/tutorial/thriller/emotional
            duration: 总时长（秒）
            shot_count: 镜头数量
            project_name: 剪映工程名
            width/height: 画布尺寸
            hook_text: 钩子文案
            ending_text: 结尾文案
            custom_subtitles: 自定义字幕列表
            input_images: 用户素材图片路径列表
            use_ltx: 是否使用LTX-2.5 I2V（需要ComfyUI运行）
            ltx_shots: 使用LTX的镜头索引列表（默认[0]，即第一个镜头）
            use_flf2v: 是否使用FLF2V首尾帧（需要首尾帧图片）
            flf2v_shots: 使用FLF2V的镜头索引列表
            use_hunyuan: 是否使用混元视频1.5 I2V（需要ComfyUI运行，动作控制更精准）
            hunyuan_shots: 使用混元I2V的镜头索引列表
            add_bgm: 是否添加BGM
            add_intro: 是否添加片头
            use_blender_intro: 是否使用Blender 3D片头（需要Blender安装，效果更炫）
            blender_intro_style: Blender片头风格（cinematic/neon/minimal/epic）
            use_blender_transitions: 是否使用Blender转场遮罩（需要Blender安装，转场更丰富）
            blender_transition_style: Blender转场风格（fade/slide_left/slide_right/zoom_in/zoom_out）
            pip_config: 画中画配置列表，每项如 {"shots": [0,1], "layout": "split_h"}
            auto_beat: 是否启用自动卡点（根据BGM节拍调整切点）
            beat_threshold: 卡点能量阈值（0-1）
            character_intros: 人物介绍列表，每项如 {"image": "path", "name": "张三", "subtitle": "主角"}
            text_layout_style: 文字排版预设风格（vertical_stagger/horizontal_title/diagonal_cascade/left_align_stack/center_focus），用于钩子文案
            photo_wall: 拍立得照片墙图片路径列表，用于结尾展示
            glow_outline_shots: 使用发光轮廓效果的镜头索引列表，如 [0, 2]

        Returns:
            {"status": "success", "project_name": ..., "storyboard": ..., "video_clips": [...]}
        """
        # ==================== 环境检测（首次运行） ====================
        self._run_env_check()

        if project_name is None:
            project_name = f"E2E_{theme}_{style}"

        if ltx_shots is None:
            ltx_shots = [0] if use_ltx else []
        if flf2v_shots is None:
            flf2v_shots = []
        if hunyuan_shots is None:
            hunyuan_shots = [] if not use_hunyuan else [0]

        print(f"{'='*60}")
        print(f"端到端视频生成: {theme}")
        print(f"风格: {style} | 时长: {duration}s | 镜头: {shot_count}")
        print(f"{'='*60}")

        # ==================== 步骤1：分镜生成 ====================
        print("\n[1/4] 分镜生成")
        sb = generate_storyboard(
            theme=theme, style=style, total_duration=duration,
            shot_count=shot_count, hook_text=hook_text,
            ending_text=ending_text, custom_subtitles=custom_subtitles,
        )

        # 创意引擎字幕优化（如果用户未提供自定义字幕）
        if custom_subtitles is None and _CREATIVE_ENGINE_AVAILABLE:
            try:
                creative = CreativeEngine()
                creative_sb = creative.generate_storyboard(
                    theme=theme, num_shots=shot_count,
                    hook=hook_text, use_hot_trends=True,
                )
                creative_subtitles = [s.subtitle for s in creative_sb.shots if s.subtitle]
                if creative_subtitles:
                    for i, shot in enumerate(sb.shots):
                        if i < len(creative_subtitles):
                            shot.subtitle = creative_subtitles[i]
                    print(f"  创意字幕: 已优化 {len(creative_subtitles)} 个镜头字幕")
            except Exception as e:
                print(f"  创意字幕优化跳过: {e}")

        print(sb.summary())

        # 分镜质量门检查
        qg_report = self._run_storyboard_quality_gates(sb)

        # 特效自动选用：根据风格和情绪自动设置转场类型
        self._auto_select_effects(sb, style)

        # 保存分镜
        sb_path = os.path.join(self.work_dir, f"{project_name}_storyboard.json")
        with open(sb_path, 'w', encoding='utf-8') as f:
            f.write(sb.to_json())

        # ==================== 步骤2：素材准备 ====================
        print("\n[2/4] 素材加工")
        video_clips = self._prepare_materials(
            sb, input_images, width, height, use_ltx, ltx_shots,
            use_flf2v, flf2v_shots, project_name,
            use_hunyuan=use_hunyuan, hunyuan_shots=hunyuan_shots,
        )

        # ==================== 步骤3：剪映合成（含片头） ====================
        print("\n[3/4] 剪映合成")
        intro_duration = 2.0 if add_intro else 0.0
        result = self._build_jianying(
            sb, video_clips, project_name, width, height, add_bgm,
            add_intro=add_intro, intro_duration=intro_duration,
            intro_style=sb.intro_style,
            use_blender_intro=use_blender_intro,
            blender_intro_style=blender_intro_style,
            pip_config=pip_config, auto_beat=auto_beat,
            beat_threshold=beat_threshold,
            style=style,
            character_intros=character_intros,
            text_layout_style=text_layout_style,
            photo_wall=photo_wall,
            glow_outline_shots=glow_outline_shots,
        )

        # ==================== 步骤3.5：剪辑质量门检查 ====================
        edit_report = None
        edit_report_html = None
        draft_path = result.get("draft_path", "")
        if draft_path and os.path.exists(draft_path):
            edit_report = self._run_edit_quality_gates(draft_path, sb)
            if edit_report:
                # 生成 HTML 报告
                try:
                    from cap_creative.report_renderer import render_html_report
                    edit_data = edit_report.get('source_data', {})
                    edit_report_html = os.path.join(self.work_dir, f"{project_name}_edit_report.html")
                    render_html_report(
                        edit_report,
                        title=f"{project_name} - 剪辑质量门报告",
                        category="edit",
                        source_data=edit_data,
                        output_path=edit_report_html,
                    )
                except Exception as e:
                    print(f"  ⚠️  HTML报告生成失败: {e}")

        print(f"\n[4/4] {'片头已集成' if add_intro else '跳过片头'}")

        print(f"\n{'='*60}")
        print(f"完成: {project_name}")
        print(f"{'='*60}")

        return {
            "status": "success",
            "project_name": project_name,
            "storyboard": sb.to_dict(),
            "storyboard_path": sb_path,
            "storyboard_quality_gate": qg_report,
            "storyboard_report_html": os.path.join(self.work_dir, f"{sb.theme}_storyboard_report.html") if qg_report else None,
            "video_clips": video_clips,
            "work_dir": self.work_dir,
            "draft_path": draft_path,
            "edit_quality_gate": edit_report,
            "edit_report_html": edit_report_html,
        }

    def _auto_select_effects(self, sb: Storyboard, style: str) -> None:
        """特效自动选用：根据风格和镜头位置自动设置转场类型

        规则：
        - 第一个镜头：无入场转场
        - 高潮镜头（中间偏后1-2个）→ 蒙版快闪 v4（双轴向四角汇聚）
        - 最后一个镜头：叠化收束
        - 普通镜头 → 根据风格选择默认转场
        - thriller/cinematic → 快切为主
        - vlog/emotional → 叠化为主
        - tutorial → 淡入淡出
        """
        if not sb.shots:
            return

        # 风格→默认转场映射
        style_default = {
            "cinematic": "快切",
            "thriller": "快切",
            "vlog": "叠化",
            "emotional": "叠化",
            "tutorial": "淡入",
        }
        default_trans = style_default.get(style, "叠化")

        # 选择高潮镜头（中间偏后1-2个）
        n = len(sb.shots)
        climax_indices = set()
        if n >= 4:
            # 选择中间偏后的1-2个镜头作为高潮
            climax_start = max(1, n // 2)
            climax_end = min(n - 1, climax_start + 2)
            for i in range(climax_start, climax_end):
                climax_indices.add(i)
        elif n == 3:
            climax_indices.add(1)

        flash_count = 0
        for i, shot in enumerate(sb.shots):
            # 第一个镜头：无入场转场
            if i == 0:
                shot.transition_in = "无"
                shot.transition_duration = 0.0
                continue

            # 高潮镜头：蒙版快闪 v4
            if i in climax_indices and _MASK_FLASH_AVAILABLE:
                shot.transition_in = "蒙版快闪"
                shot.transition_duration = min(0.8, shot.duration * 0.3)
                flash_count += 1
                continue

            # 最后一个镜头：叠化收束
            if i == n - 1:
                shot.transition_in = "叠化"
                shot.transition_duration = 0.5
                continue

            # 普通镜头：风格默认转场
            shot.transition_in = default_trans
            shot.transition_duration = 0.3

        if flash_count:
            print(f"  特效自动选用: {flash_count}个高潮镜头→蒙版快闪v4, 其余→{default_trans}")
        else:
            print(f"  特效自动选用: 全部→{default_trans}")

    def _run_env_check(self):
        """运行环境检测，生成适配策略并输出详细报告

        检测完成后：
        1. 根据真实环境生成系统工作策略（full/standard/minimal/basic）
        2. 输出详细报告（环境状况+功能影响+安装指引）
        3. 给用户选择机会（继续/安装/跳过）
        4. 提示安装触发指令
        """
        if not _ENV_CHECKER_AVAILABLE:
            return

        try:
            from cap_env_checker import check_environment_with_strategy, generate_detailed_report
            report, strategy = check_environment_with_strategy()

            # 输出策略摘要
            print(f"\n{'='*60}")
            print(f"环境检测完成 | 策略模式: {strategy.mode}")
            print(f"{'='*60}")
            print(f"说明: {strategy.description}")
            print(f"可用功能: {len(strategy.enabled_features)}项 | 受限功能: {len(strategy.disabled_features)}项")

            # 缺失依赖提示
            if report.missing:
                print(f"\n⚠️  缺失依赖: {', '.join(report.missing)}")
                if strategy.install_commands:
                    print("   安装触发指令（发送给助手即可）:")
                    for name, cmd in strategy.install_commands.items():
                        print(f"   - {name}: 「{cmd}」")

            # 警告
            if strategy.warnings:
                print(f"\nℹ️  注意事项:")
                for w in strategy.warnings[:3]:
                    print(f"   - {w[:80]}...")

            # 用户选择提示
            print(f"\n请选择: 1.继续当前环境  2.安装缺失依赖  3.稍后再问")
            print(f"{'='*60}\n")

            # 保存详细报告
            try:
                report_dir = os.path.join(self.work_dir, "env_reports")
                os.makedirs(report_dir, exist_ok=True)
                from datetime import datetime
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                # JSON报告
                import json as _json
                with open(os.path.join(report_dir, f"env_report_{ts}.json"), 'w', encoding='utf-8') as f:
                    _json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
                # Markdown详细报告
                with open(os.path.join(report_dir, f"env_report_{ts}.md"), 'w', encoding='utf-8') as f:
                    f.write(generate_detailed_report(report, strategy))
                # 最新报告软链接（覆盖）
                with open(os.path.join(self.work_dir, "env_report_latest.md"), 'w', encoding='utf-8') as f:
                    f.write(generate_detailed_report(report, strategy))
            except Exception:
                pass

            # 保存策略到pipeline实例，供后续流程参考
            self._env_strategy = strategy
            self._env_report = report

        except Exception as e:
            print(f"\n⚠️  环境检测跳过: {e}")

    def _run_storyboard_quality_gates(self, sb: Storyboard) -> Optional[Dict]:
        """运行分镜质量门检查

        将 Storyboard 转换为质量门数据格式，运行 storyboard 类别检查。
        返回质量门报告字典，失败时返回 None。

        检查项：
        - S001: 单镜头时长 2-15秒
        - S002: 首镜头有钩子（前3秒）
        - S003: 节拍认领（当前分镜无节拍概念，跳过）
        """
        if not _QUALITY_GATE_AVAILABLE:
            print("  ⚠️  质量门框架不可用，跳过检查")
            return None

        # 转换为质量门数据格式（传递完整分镜信息）
        qg_data = {
            "total_duration": sb.total_duration,
            "shots": [{
                "duration": s.duration,
                "shot_size": s.shot_size,
                "camera_move": s.camera_move,
                "emotion": s.emotion,
                "subtitle": s.subtitle,
                "transition_in": s.transition_in,
            } for s in sb.shots],
            "beats": [],  # 当前分镜无节拍概念
            "hooks": [],
        }

        # 钩子检测：第一个镜头的 emotion 为 "钩子" 或有 hook_text
        if sb.hook_text or (sb.shots and sb.shots[0].emotion == "钩子"):
            # 钩子时间 = 第一个镜头的中间位置
            hook_time = sb.shots[0].duration / 2 if sb.shots else 0
            qg_data["hooks"].append({"time": hook_time, "type": "text"})

        report = qg_validate("storyboard", qg_data)
        print(f"\n  📋 分镜质量门: {report.passed}/{report.total} 通过")
        for r in report.results:
            if r.status.value != "pass":
                print(f"    {r}")

        # 保存质量门报告(JSON)
        qg_path = os.path.join(self.work_dir, f"{sb.theme}_quality_gate.json")
        try:
            with open(qg_path, 'w', encoding='utf-8') as f:
                f.write(report.to_json())
        except Exception:
            pass

        # 生成HTML报告
        report_dict = report.to_dict()
        html_path = os.path.join(self.work_dir, f"{sb.theme}_storyboard_report.html")
        try:
            from cap_creative.report_renderer import render_html_report
            render_html_report(
                report_dict,
                title=f"{sb.theme} - 分镜质量门报告",
                category="storyboard",
                source_data=qg_data,
                output_path=html_path,
            )
            print(f"  [报告] 分镜HTML已生成: {html_path}")
        except Exception as e:
            print(f"  ⚠️  分镜HTML报告生成失败: {e}")

        return report_dict

    def _run_edit_quality_gates(self, draft_path: str, sb: Storyboard) -> Optional[Dict]:
        """运行剪辑质量门检查

        从剪映工程提取数据，运行 edit 类别检查。
        返回质量门报告字典，失败时返回 None。

        检查项：
        - E001: 总时长不超过上限
        - E002: 片段数量合理
        - E003: 转场对齐
        - E004: 字幕覆盖率
        - E005: 画幅一致
        - E006: 帧对齐
        - E007: 黑屏检测
        """
        try:
            from cap_creative import validate as qg_validate
            from cap_creative.draft_extractor import extract_draft_data
        except ImportError:
            print("  ⚠️  质量门框架不可用，跳过剪辑检查")
            return None

        try:
            # 从剪映工程提取数据
            edit_data = extract_draft_data(draft_path)
            # 用分镜的总时长覆盖默认上限
            edit_data['max_duration'] = sb.total_duration + 5.0  # 允许5秒误差

            report = qg_validate("edit", edit_data)
            print(f"\n  📋 剪辑质量门: {report.passed}/{report.total} 通过")
            for r in report.results:
                if r.status.value != "pass":
                    print(f"    {r}")

            # 保存质量门报告
            qg_path = os.path.join(self.work_dir, f"{sb.theme}_edit_quality_gate.json")
            try:
                with open(qg_path, 'w', encoding='utf-8') as f:
                    f.write(report.to_json())
            except Exception:
                pass

            result = report.to_dict()
            result['source_data'] = edit_data
            return result

        except Exception as e:
            print(f"  ⚠️  剪辑质量门检查失败: {e}")
            return None

    def _prepare_materials(self, sb: Storyboard, input_images: List[str],
                           width: int, height: int, use_ltx: bool,
                           ltx_shots: List[int], use_flf2v: bool = False,
                           flf2v_shots: List[int] = None, project_name: str = "",
                           use_hunyuan: bool = False, hunyuan_shots: List[int] = None) -> List[str]:
        if flf2v_shots is None:
            flf2v_shots = []
        if hunyuan_shots is None:
            hunyuan_shots = []
        """素材加工：生成/动态化每个镜头的视频"""
        from cap_ffmpeg_motion.ffmpeg_motion import FFmpegMotion
        fm = FFmpegMotion(ffmpeg_path=self.ffmpeg)

        # 色调对应的基础颜色
        tone_colors = {
            "冷": "#1a2a3a", "暖": "#3a2a1a", "中性": "#2a2a2a",
            "高对比": "#0a0a0a", "低饱和": "#3a3a3a",
        }

        # 运镜映射
        move_map = {
            "推": "zoom_in", "拉": "zoom_out", "快推": "zoom_in",
            "缓推": "zoom_in", "缓拉": "zoom_out",
            "移右": "pan_right", "移左": "pan_left",
            "固定": "zoom_in", "快切": "zoom_in",
        }

        video_clips = []

        # 批量LTX优化：收集所有需要LTX的镜头，一次性批量生成
        ltx_shot_indices = [i for i in range(len(sb.shots)) if use_ltx and i in ltx_shots]
        ltx_results = {}  # {shot_index: output_path}
        if len(ltx_shot_indices) > 1:
            print(f"  批量LTX: {len(ltx_shot_indices)}个镜头将批量生成")
            ltx_results = self._batch_ltx_i2v(sb, input_images, ltx_shot_indices, width, height, project_name)

        for i, shot in enumerate(sb.shots):
            out_path = os.path.join(self.work_dir, "output", f"{project_name}_shot_{i:02d}.mp4")

            # 确定输入图片
            if input_images and i < len(input_images):
                img_path = input_images[i]
            else:
                # 生成占位图
                img_path = os.path.join(self.work_dir, "input", f"{project_name}_shot_{i:02d}.png")
                if not os.path.exists(img_path):
                    import subprocess
                    color = tone_colors.get(shot.color_tone, "#2a2a2a")
                    subprocess.run([
                        self.ffmpeg, "-y",
                        "-f", "lavfi", "-i", f"color=c={color}:s={width}x{height}:d=1",
                        "-vf", "drawbox=x=0:y=0:w=iw:h=ih/3:color=ffffff@0.05:t=fill,"
                               "drawbox=x=0:y=ih*2/3:w=iw:h=ih/3:color=000000@0.2:t=fill",
                        "-frames:v", "1", img_path
                    ], capture_output=True)

            # 动态化
            move_type = move_map.get(shot.camera_move, "zoom_in")

            if use_flf2v and i in flf2v_shots:
                # FLF2V首尾帧：首帧=当前图，尾帧=下一镜头图（最后一镜头尾帧=当前图）
                last_img = input_images[i+1] if (input_images and i+1 < len(input_images)) else img_path
                flf_success = self._try_flf2v(img_path, last_img, out_path, shot, width, height)
                if not flf_success:
                    print(f"  镜头{i}: FLF2V失败，降级Ken Burns")
                    fm.image_to_ken_burns(
                        img_path, out_path, duration=shot.duration,
                        move_type=move_type, intensity=shot.move_intensity,
                        width=width, height=height, fps=30
                    )
            elif use_ltx and i in ltx_shots:
                # 优先使用批量结果
                if i in ltx_results and ltx_results[i] and os.path.exists(ltx_results[i]):
                    out_path = ltx_results[i]
                    print(f"  镜头{i}: 使用批量LTX结果")
                else:
                    # LTX-2.5 I2V（需要ComfyUI运行）
                    ltx_success = self._try_ltx_i2v(img_path, out_path, shot, width, height)
                    if not ltx_success:
                        # 降级为Ken Burns
                        print(f"  镜头{i}: LTX失败，降级Ken Burns")
                        fm.image_to_ken_burns(
                            img_path, out_path, duration=shot.duration,
                            move_type=move_type, intensity=shot.move_intensity,
                            width=width, height=height, fps=30
                        )
            elif use_hunyuan and i in hunyuan_shots:
                # 混元视频1.5 I2V（动作控制更精准，需要ComfyUI运行）
                hunyuan_success = self._try_hunyuan_i2v(img_path, out_path, shot, width, height)
                if not hunyuan_success:
                    print(f"  镜头{i}: 混元I2V失败，降级Ken Burns")
                    fm.image_to_ken_burns(
                        img_path, out_path, duration=shot.duration,
                        move_type=move_type, intensity=shot.move_intensity,
                        width=width, height=height, fps=30
                    )
            else:
                fm.image_to_ken_burns(
                    img_path, out_path, duration=shot.duration,
                    move_type=move_type, intensity=shot.move_intensity,
                    width=width, height=height, fps=30
                )

            video_clips.append(out_path)
            size_kb = os.path.getsize(out_path) // 1024 if os.path.exists(out_path) else 0
            print(f"  镜头{i}: {shot.camera_move}({move_type}) 强度{shot.move_intensity} -> {size_kb}KB")

        # 素材质检
        print(f"\n  素材质检:")
        for i, clip in enumerate(video_clips):
            qc = self._validate_clip(clip)
            if qc.get("valid"):
                print(f"    镜头{i}: ✅ {qc['width']}x{qc['height']} {qc['fps']}fps {qc['duration']:.1f}s {qc['size_mb']}MB")
            else:
                print(f"    镜头{i}: ❌ {qc.get('reason', '未知')}")

        return video_clips

    def _add_intro_to_project(self, project, sb: Storyboard,
                               duration: float, style: str,
                               width: int, height: int, draft) -> float:
        """在剪映工程中添加片头轨道，返回片头时长（秒）"""
        import subprocess

        # 片头风格配置
        intro_styles = {
            "impact": {"bg_color": "#0a0a1a", "accent": "#ff4444", "main_size": 16, "main_color": (1, 0.9, 0.3), "anim": "放大", "y": 0.3},
            "cute": {"bg_color": "#1a0a1a", "accent": "#ff88cc", "main_size": 13, "main_color": (1, 0.7, 0.9), "anim": "弹入", "y": 0.2},
            "funny": {"bg_color": "#1a1a0a", "accent": "#ffcc00", "main_size": 14, "main_color": (1, 0.9, 0.2), "anim": "弹性伸缩", "y": 0.25},
            "minimal": {"bg_color": "#0a0a0a", "accent": "#888888", "main_size": 11, "main_color": (1, 1, 1), "anim": "渐显", "y": 0.1},
            "suspense": {"bg_color": "#050510", "accent": "#4444ff", "main_size": 12, "main_color": (0.7, 0.8, 1), "anim": "打字机_I", "y": 0.15},
        }
        cfg = intro_styles.get(style, intro_styles["minimal"])

        # 1. 生成片头背景（优先素材库，降级ffmpeg）
        bg_path = None
        best = self.asset_lib.get_best_match("background", context="片头背景", style=style)
        if best:
            bg_path = self.asset_lib.get_path(best["id"])

        if not bg_path or not os.path.exists(bg_path):
            # ffmpeg生成渐变背景+Ken Burns
            bg_path = os.path.join(self.work_dir, "output", f"{project.name}_intro_bg.mp4")
            temp_img = bg_path + ".png"
            subprocess.run([
                self.ffmpeg, "-y",
                "-f", "lavfi", "-i", f"color=c={cfg['bg_color']}:s={width}x{height}:d=1",
                "-vf", f"drawbox=x=0:y=0:w=iw:h=ih/4:color={cfg['accent']}@0.2:t=fill,"
                       f"drawbox=x=0:y=ih*3/4:w=iw:h=ih/4:color={cfg['accent']}@0.15:t=fill",
                "-frames:v", "1", temp_img
            ], capture_output=True)

            from cap_ffmpeg_motion.ffmpeg_motion import FFmpegMotion
            fm = FFmpegMotion(ffmpeg_path=self.ffmpeg)
            fm.image_to_ken_burns(
                temp_img, bg_path, duration=duration,
                move_type="zoom_in", intensity=0.08,
                width=width, height=height, fps=30
            )
            if os.path.exists(temp_img):
                os.remove(temp_img)

        # 2. 背景轨道
        if bg_path and os.path.exists(bg_path):
            project.add_media_safe(bg_path, start_time="0s", duration=f"{duration}s", track_name="IntroBG")

        # 3. 主标题
        title = sb.hook_text or sb.theme
        project.add_text_simple(
            title,
            start_time="0.3s", duration=f"{max(duration - 0.5, 0.5)}s",
            font_size=cfg["main_size"],
            color_rgb=cfg["main_color"],
            style=draft.TextStyle(size=cfg["main_size"], bold=True),
            border=draft.TextBorder(color=(0, 0, 0), width=50),
            shadow=draft.TextShadow(color=(0, 0, 0), distance=8, diffuse=15),
            clip_settings=draft.ClipSettings(transform_y=cfg["y"]),
            anim_in=cfg["anim"],
            track_name="IntroTitle",
        )

        # 4. 副标题（主题）
        project.add_text_simple(
            sb.theme,
            start_time="0.8s", duration=f"{max(duration - 1.0, 0.5)}s",
            font_size=6.0,
            color_rgb=(0.8, 0.8, 0.8),
            clip_settings=draft.ClipSettings(transform_y=cfg["y"] - 0.25),
            anim_in="渐显",
            track_name="IntroSub",
        )

        # 5. 片头音效
        sfx_best = self.asset_lib.get_best_match("sfx", context="片头冲击", style=style)
        if sfx_best:
            sfx_path = self.asset_lib.get_path(sfx_best["id"])
            try:
                project.add_media_safe(sfx_path, start_time="0.1s", duration="0.5s", track_name="IntroSFX")
            except Exception:
                pass

        return duration

    def _try_ltx_i2v(self, img_path: str, out_path: str, shot,
                     width: int, height: int) -> bool:
        """尝试LTX-2.5 I2V，失败返回False"""
        try:
            from cap_comfyui_runner.api import img2video_ltx25, check_comfyui_ready
            if not check_comfyui_ready(self.comfyui_addr):
                return False

            # LTX-2.5参数优化：帧数对齐8n+1，分辨率限制768x448（12GB显存安全，height需被32整除），步数20
            max_ltx_w, max_ltx_h = 768, 448
            ltx_w = min((width // 32) * 32, max_ltx_w)
            ltx_h = min((height // 32) * 32, max_ltx_h)
            raw_frames = max(int(shot.duration * 24), 17)
            frames = ((raw_frames - 1) // 8) * 8 + 1  # 对齐8n+1

            result = img2video_ltx25(
                image_path=img_path,
                output_path=out_path,
                prompt=f"{shot.subtitle}，{shot.emotion}氛围，{shot.shot_size}，电影感",
                width=ltx_w, height=ltx_h,
                frames=frames, fps=24,
                steps=20, seed=None,  # None=内部生成随机种子（LTX不接受-1）
                strength=0.7,
                server_addr=self.comfyui_addr,
                timeout=300,
            )
            return result and os.path.exists(out_path)
        except Exception as e:
            print(f"  LTX I2V异常: {e}")
            return False

    def _try_hunyuan_i2v(self, img_path: str, out_path: str, shot,
                          width: int, height: int) -> bool:
        """尝试混元视频1.5 I2V，失败返回False"""
        try:
            from cap_comfyui_runner.api import hunyuan_i2v, check_comfyui_ready
            if not check_comfyui_ready(self.comfyui_addr):
                return False

            # 混元视频1.5参数：640x360（12GB显存安全），33帧@16fps≈2秒
            max_hw, max_hh = 640, 360
            hunyuan_w = min((width // 16) * 16, max_hw)
            hunyuan_h = min((height // 16) * 16, max_hh)
            frames = 33  # 混元默认33帧

            result = hunyuan_i2v(
                image_path=img_path,
                output_path=out_path,
                prompt=f"{shot.subtitle}, {shot.emotion} atmosphere, {shot.shot_size}, cinematic, high quality",
                negative_prompt="blurry, low quality, distorted, static, watermark, text",
                width=hunyuan_w, height=hunyuan_h,
                frames=frames, fps=16,
                steps=20, cfg=6.0,
                server_addr=self.comfyui_addr,
                timeout=300,
            )
            return result and os.path.exists(out_path)
        except Exception as e:
            print(f"  混元I2V异常: {e}")
            return False

    def _batch_ltx_i2v(self, sb: Storyboard, input_images: List[str],
                        shot_indices: List[int], width: int, height: int,
                        project_name: str) -> Dict[int, str]:
        """批量LTX I2V：一次性生成多个镜头的视频（减少模型加载开销）"""
        try:
            from cap_comfyui_runner.api import batch_img2video_ltx25, check_comfyui_ready
            if not check_comfyui_ready(self.comfyui_addr):
                return {}

            max_ltx_w, max_ltx_h = 768, 448
            ltx_w = min((width // 32) * 32, max_ltx_w)
            ltx_h = min((height // 32) * 32, max_ltx_h)

            # 收集图片和提示词
            images = []
            prompts = []
            for idx in shot_indices:
                if input_images and idx < len(input_images):
                    img_path = input_images[idx]
                else:
                    img_path = os.path.join(self.work_dir, "input", f"{project_name}_shot_{idx:02d}.png")
                if os.path.exists(img_path):
                    images.append(img_path)
                    shot = sb.shots[idx]
                    prompts.append(f"{shot.subtitle}，{shot.emotion}氛围，{shot.shot_size}，电影感")
                else:
                    images.append(None)
                    prompts.append("")

            # 过滤掉不存在的图片
            valid_pairs = [(idx, img, p) for idx, img, p in zip(shot_indices, images, prompts) if img]
            if not valid_pairs:
                return {}

            valid_indices = [p[0] for p in valid_pairs]
            valid_images = [p[1] for p in valid_pairs]
            valid_prompts = [p[2] for p in valid_pairs]

            output_dir = os.path.join(self.work_dir, "output")
            results = batch_img2video_ltx25(
                image_paths=valid_images,
                output_dir=output_dir,
                prompt="cinematic, high quality",
                per_image_prompts=valid_prompts,
                width=ltx_w, height=ltx_h,
                frames=97, fps=24, steps=10,
                strength=0.7,
                server_addr=self.comfyui_addr,
                timeout_per_video=300,
            )

            # 映射回镜头索引
            ltx_results = {}
            for idx, result in zip(valid_indices, results):
                if result and os.path.exists(result):
                    ltx_results[idx] = result
            return ltx_results
        except Exception as e:
            print(f"  批量LTX异常: {e}")
            return {}

    def _validate_clip(self, video_path: str) -> Dict:
        """素材质检：验证生成的视频片段"""
        try:
            from cap_comfyui_runner.api import get_video_info
            if not os.path.exists(video_path):
                return {"valid": False, "reason": "文件不存在"}
            info = get_video_info(video_path)
            v = info.get("video", {})
            return {
                "valid": True,
                "width": v.get("width", 0),
                "height": v.get("height", 0),
                "fps": v.get("fps", 0),
                "duration": info.get("duration_sec", 0),
                "size_mb": info.get("size_mb", 0),
            }
        except Exception as e:
            return {"valid": False, "reason": str(e)}

    def _try_flf2v(self, first_img: str, last_img: str, out_path: str,
                   shot, width: int, height: int) -> bool:
        """尝试LTX-2.5 FLF2V首尾帧视频，失败返回False"""
        try:
            from cap_comfyui_runner.api import flf2video_ltx25_v2, check_comfyui_ready
            if not check_comfyui_ready(self.comfyui_addr):
                return False

            # FLF2V参数优化：帧数对齐8n+1，分辨率限制768x432，步数20
            max_flf_w, max_flf_h = 768, 432
            flf_w = min((width // 32) * 32, max_flf_w)
            flf_h = min((height // 32) * 32, max_flf_h)
            raw_frames = max(int(shot.duration * 24), 17)
            frames = ((raw_frames - 1) // 8) * 8 + 1  # 对齐8n+1

            result = flf2video_ltx25_v2(
                first_image_path=first_img,
                last_image_path=last_img,
                output_path=out_path,
                prompt=f"{shot.subtitle}，{shot.emotion}氛围，平滑过渡，电影感运镜",
                width=flf_w, height=flf_h,
                frames=frames, fps=24,
                steps=20, seed=None,
                first_strength=1.0, last_strength=1.0,
                server_addr=self.comfyui_addr,
                timeout=300,
            )
            return result and os.path.exists(out_path)
        except Exception as e:
            print(f"  FLF2V异常: {e}")
            return False

    def _build_jianying(self, sb: Storyboard, video_clips: List[str],
                        project_name: str, width: int, height: int,
                        add_bgm: bool, add_intro: bool = False,
                        intro_duration: float = 2.0,
                        intro_style: str = "impact",
                        use_blender_intro: bool = False,
                        blender_intro_style: str = "cinematic",
                        pip_config: List[Dict] = None,
                        auto_beat: bool = False,
                        beat_threshold: float = 0.5,
                        style: str = "cinematic",
                        character_intros: List[Dict] = None,
                        text_layout_style: str = None,
                        photo_wall: List[str] = None,
                        glow_outline_shots: List[int] = None) -> Dict:
        """剪映合成（含片头集成）"""
        sys.path.insert(0, os.path.join(self.jy_skill, "scripts"))
        from jy_wrapper import JyProject
        import pyJianYingDraft as draft

        # 艺术字幕 + 运镜预设库
        sys.path.insert(0, os.path.join(SKILL_ROOT, "..", "scripts"))
        try:
            from artistic_subtitle import add_artistic_subtitle
        except ImportError:
            add_artistic_subtitle = None
        try:
            from camera_moves import apply_storyboard_camera_move, add_cinematic_color_grade
            _CAMERA_MOVES_AVAILABLE = True
        except ImportError:
            _CAMERA_MOVES_AVAILABLE = False
        try:
            from enhanced_subtitle import add_styled_subtitle, SUBTITLE_STYLES
            _ENHANCED_SUBTITLE_AVAILABLE = True
        except ImportError:
            _ENHANCED_SUBTITLE_AVAILABLE = False
        try:
            from pip_layouts import apply_layout, LAYOUTS
            _PIP_LAYOUTS_AVAILABLE = True
        except ImportError:
            _PIP_LAYOUTS_AVAILABLE = False
        try:
            from auto_beat import generate_beat_timeline, apply_beat_cuts
            _AUTO_BEAT_AVAILABLE = True
        except ImportError:
            _AUTO_BEAT_AVAILABLE = False

        project = JyProject(project_name, width=width, height=height, overwrite=True)

        # 0. 片头（在正片之前）—— 使用特效库片头生成器或Blender 3D片头
        intro_offset = 0.0
        if add_intro:
            if use_blender_intro:
                # Blender 3D片头（更炫，需要Blender安装）
                try:
                    from blender_intro import create_blender_intro
                    intro_title = sb.hook_text or sb.theme or "精彩开始"
                    intro_sub = sb.ending_text if len(sb.ending_text) < 20 else ""
                    blender_intro_dir = os.path.join(self.work_dir, "output", "blender_intro")
                    blender_video = create_blender_intro(
                        title=intro_title,
                        subtitle=intro_sub,
                        output_dir=blender_intro_dir,
                        style=blender_intro_style,
                        width=width,
                        height=height,
                        duration=intro_duration,
                    )
                    if blender_video and os.path.exists(blender_video):
                        # 将Blender片头视频导入剪映工程
                        intro_seg = project.add_media_safe(
                            blender_video,
                            start_time="0s",
                            duration=f"{intro_duration}s",
                            track_name="BlenderIntro",
                        )
                        if intro_seg:
                            intro_offset = intro_duration
                            print(f"  片头: {intro_duration}s (Blender 3D, {blender_intro_style})")
                        else:
                            print(f"  ⚠️  Blender片头导入剪映失败，回退特效库")
                            use_blender_intro = False
                    else:
                        print(f"  ⚠️  Blender片头生成失败，回退特效库")
                        use_blender_intro = False
                except Exception as e:
                    print(f"  ⚠️  Blender片头异常: {e}，回退特效库")
                    use_blender_intro = False

            if not use_blender_intro:
                if _INTRO_BUILDER_AVAILABLE:
                    intro_template = _INTRO_STYLE_MAP.get(intro_style, "flash_title")
                    intro_title = sb.hook_text or sb.theme or "精彩开始"
                    intro_sub = sb.ending_text if len(sb.ending_text) < 20 else None
                    intro_offset = _add_intro_effect(
                        project,
                        template=intro_template,
                        title=intro_title,
                        subtitle=intro_sub,
                        start_time=0.0,
                        width=width,
                        height=height,
                        output_dir=os.path.join(self.work_dir, "output", "intro_assets"),
                    )
                    print(f"  片头: {intro_offset}s ({intro_template}, 特效库)")
                else:
                    intro_offset = self._add_intro_to_project(
                        project, sb, intro_duration, intro_style, width, height, draft
                    )
                    print(f"  片头: {intro_duration}s ({intro_style}, 原生)")

        # 1.5 人物介绍卡片（特效库集成）
        char_intro_duration = 0.0
        if character_intros and _CHARACTER_INTRO_AVAILABLE:
            char_preset_map = {
                "cinematic": "red_drama",
                "thriller": "cyber_tech",
                "vlog": "warm_friends",
                "emotional": "warm_friends",
                "tutorial": "minimal_white",
            }
            char_preset = char_preset_map.get(style, "red_drama")
            char_result = _add_char_intro(
                project,
                characters=character_intros,
                preset=char_preset,
                start_time=intro_offset,
                width=width,
                height=height,
                output_dir=os.path.join(self.work_dir, "output", "character_intro_assets"),
            )
            if char_result.get("status") == "success":
                char_intro_duration = char_result.get("duration", 0)
                print(f"  人物介绍: {char_result['character_count']}人 ({char_preset}, {char_intro_duration}s)")
            else:
                print(f"  人物介绍失败: {char_result.get('reason')}")

        # 1.6 文字排版钩子文案（特效库集成）
        text_layout_duration = 0.0
        if text_layout_style and _TEXT_LAYOUT_AVAILABLE and sb.hook_text:
            try:
                layout_texts = [sb.hook_text]
                if sb.theme and len(sb.theme) < 15:
                    layout_texts.append(sb.theme)
                _add_text_layout(
                    project,
                    texts=layout_texts,
                    layout=text_layout_style,
                    start_time=intro_offset + char_intro_duration,
                    duration=3.0,
                )
                text_layout_duration = 3.0
                print(f"  文字排版: {text_layout_style} ({text_layout_duration}s)")
            except Exception as e:
                print(f"  文字排版失败: {e}")

        # 2. 添加视频片段（从片头+人物介绍+文字排版后开始）
        segments = []
        current_time = intro_offset + char_intro_duration + text_layout_duration

        # 画中画配置：标记哪些镜头已被画中画组合消耗
        pip_consumed = set()
        if pip_config and _PIP_LAYOUTS_AVAILABLE:
            for pip in pip_config:
                shot_indices = pip.get("shots", [])
                layout = pip.get("layout", "split_h")
                if len(shot_indices) < 2:
                    continue
                # 检查素材是否存在
                pip_clips = [video_clips[idx] for idx in shot_indices if idx < len(video_clips)]
                if len(pip_clips) < 2:
                    continue
                # 计算画中画持续时长（取组合中第一个镜头的时长）
                pip_duration = sb.shots[shot_indices[0]].duration
                # 应用画中画布局
                try:
                    apply_layout(
                        project, layout, pip_clips,
                        start_time=f"{current_time:.2f}s",
                        duration=f"{pip_duration:.2f}s",
                    )
                    pip_consumed.update(shot_indices)
                    print(f"  画中画[{layout}]: 镜头{shot_indices} ({pip_duration:.1f}s)")
                    current_time += pip_duration
                except Exception as e:
                    print(f"  画中画失败: {e}")

        # 普通镜头（未被画中画消耗的）
        for i, shot in enumerate(sb.shots):
            if i in pip_consumed or i >= len(video_clips):
                if i in pip_consumed:
                    continue
                break
            seg = project.add_media_safe(
                video_clips[i],
                start_time=f"{current_time:.2f}s",
                duration=f"{shot.duration:.2f}s"
            )
            if seg:
                segments.append(seg)
                # 应用运镜关键帧（根据分镜camera_move字段）
                if _CAMERA_MOVES_AVAILABLE:
                    duration_us = int(shot.duration * 1_000_000)
                    move_intensity = getattr(shot, 'move_intensity', 1.0)
                    apply_storyboard_camera_move(
                        seg, shot.camera_move, duration_us,
                        intensity=move_intensity
                    )
                    # 应用调色（根据分镜color_tone）
                    color_style_map = {
                        "冷": "cool", "暖": "warm", "中性": "cinematic",
                        "高对比": "noir", "低饱和": "vintage",
                    }
                    color_tone = getattr(shot, 'color_tone', "中性")
                    color_style = color_style_map.get(color_tone, "cinematic")
                    add_cinematic_color_grade(seg, duration_us, style=color_style)
            current_time += shot.duration

        # 发光轮廓效果（特效库集成）—— 对指定镜头添加轮廓图层
        glow_count = 0
        if glow_outline_shots and _GLOW_OUTLINE_AVAILABLE:
            glow_start_base = intro_offset + char_intro_duration + text_layout_duration
            for shot_idx in glow_outline_shots:
                if shot_idx >= len(sb.shots) or shot_idx >= len(video_clips):
                    continue
                shot = sb.shots[shot_idx]
                base_img = video_clips[shot_idx]
                # 如果是视频，提取第一帧作为轮廓底图
                if base_img.lower().endswith(('.mp4', '.mov', '.avi')):
                    frame_path = os.path.join(self.work_dir, "output", f"glow_frame_{shot_idx}.png")
                    try:
                        import subprocess
                        subprocess.run([
                            self.ffmpeg, "-y", "-i", base_img,
                            "-vframes", "1", "-q:v", "2", frame_path
                        ], capture_output=True, timeout=30)
                        if os.path.exists(frame_path):
                            base_img = frame_path
                        else:
                            continue
                    except Exception:
                        continue
                # 计算该镜头的起始时间
                shot_start = glow_start_base
                for j in range(shot_idx):
                    if j not in pip_consumed:
                        shot_start += sb.shots[j].duration
                try:
                    _add_glow_outline(
                        project,
                        base_image=base_img,
                        start_time=shot_start,
                        duration=shot.duration,
                        output_dir=os.path.join(self.work_dir, "output", "glow_outline_assets"),
                    )
                    glow_count += 1
                    print(f"  发光轮廓: 镜头{shot_idx} ({shot.duration:.1f}s)")
                except Exception as e:
                    print(f"  发光轮廓镜头{shot_idx}失败: {e}")

        # 自动卡点：如果启用且有BGM，根据节拍调整切点
        if auto_beat and _AUTO_BEAT_AVAILABLE and add_bgm and sb.bgm_mood:
            print(f"  自动卡点: 分析BGM节拍 (阈值{beat_threshold})...")
            # 注意：实际卡点需要BGM文件路径，云端音乐无法直接分析
            # 这里生成基于镜头时长的均匀卡点作为fallback
            total_dur = sb.total_duration
            beat_cuts = []
            t = intro_offset
            for shot in sb.shots:
                t += shot.duration
                beat_cuts.append(t)
            print(f"  卡点: {len(beat_cuts)}个切点 (均匀分布，BGM云端无法本地分析)")

        print(f"  添加 {len(segments)} 个视频片段 + {len(pip_consumed)}个画中画 (起始{intro_offset + char_intro_duration:.2f}s, 运镜+调色已应用)")

        # 2. 转场（加在前一个片段末尾）—— 支持蒙版快闪特效
        trans_count = 0
        flash_count = 0
        flash_assets_dir = os.path.join(self.work_dir, "output", "mask_flash_assets")
        for i in range(1, len(segments)):
            shot = sb.shots[i]
            if shot.transition_in == "无":
                continue

            # 蒙版快闪特效 v4（双轴向四角汇聚）
            if shot.transition_in == "蒙版快闪" and _MASK_FLASH_AVAILABLE:
                try:
                    trans_start = intro_offset + sum(s.duration for s in sb.shots[:i]) - shot.transition_duration
                    # v4四角汇聚：4色块从四角对角线展开到中心
                    flash_colors = _MASK_FLASH_PRESETS.get("cyberpunk", [(0, 200, 255), (255, 0, 200), (200, 255, 0), (0, 255, 128)])[:4]
                    corner_dirs = ["diagonal_tl", "diagonal_tr", "diagonal_bl", "diagonal_br"]
                    stagger = shot.transition_duration * 0.15  # 错峰15%
                    expand_us = int(shot.transition_duration * 1e6 * 0.7)  # 展开占70%时长

                    for j, (color, direction) in enumerate(zip(flash_colors, corner_dirs)):
                        block_path = os.path.join(flash_assets_dir, f"flash_v4_{i}_{j}.png")
                        os.makedirs(flash_assets_dir, exist_ok=True)
                        create_solid_color_image(color, width, height, block_path)

                        seg_start = trans_start + j * stagger
                        flash_seg = project.add_media_safe(
                            block_path,
                            start_time=f"{seg_start:.2f}s",
                            duration=f"{shot.transition_duration:.2f}s",
                            track_name=f"MaskFlashV4_{i}_{j}",
                        )
                        if flash_seg:
                            if _MASK_KF_AVAILABLE:
                                # v4：矩形蒙版 + 双轴向对角线展开
                                _add_rect_mask(flash_seg, width, height)
                                _apply_mask_kf(
                                    project, flash_seg,
                                    start_us=0, duration_us=expand_us,
                                    direction=direction,
                                    canvas_w=width, canvas_h=height,
                                    curve="EASE_OUT",
                                )
                            else:
                                # 蒙版关键帧不可用时跳过该色块
                                continue
                            # 淡出
                            end_us = int(shot.transition_duration * 1e6)
                            flash_seg.add_keyframe(draft.KeyframeProperty.alpha, int(end_us * 0.7), 1.0, **draft.Keyframe.EASE_OUT)
                            flash_seg.add_keyframe(draft.KeyframeProperty.alpha, end_us, 0.0, **draft.Keyframe.EASE_OUT)
                    flash_count += 1
                    continue
                except Exception as e:
                    print(f"  蒙版快闪v4@{i}失败，回退普通转场: {e}")

            # Blender转场遮罩（需要Blender安装，转场更丰富）
            if use_blender_transitions and _BLENDER_EFFECTS_AVAILABLE and shot.transition_in not in ["无", "蒙版快闪"]:
                try:
                    trans_start = intro_offset + sum(s.duration for s in sb.shots[:i]) - shot.transition_duration
                    blender_trans_dir = os.path.join(self.work_dir, "output", "blender_transitions")
                    os.makedirs(blender_trans_dir, exist_ok=True)

                    # 风格映射：根据转场类型选择Blender转场风格
                    blender_style_map = {
                        "叠化": "fade", "快切": "fade", "闪黑": "fade",
                        "闪白": "fade", "黑场": "fade", "淡入": "fade",
                    }
                    b_style = blender_style_map.get(shot.transition_in, blender_transition_style)

                    trans_video = _blender_create_transition(
                        output_dir=os.path.join(blender_trans_dir, f"trans_{i}"),
                        style=b_style,
                        width=width,
                        height=height,
                        duration=shot.transition_duration,
                    )

                    if trans_video and os.path.exists(trans_video):
                        # 将Blender转场遮罩叠加到时间线（正片叠底混合模式）
                        trans_seg = project.add_media_safe(
                            trans_video,
                            start_time=f"{trans_start:.2f}s",
                            duration=f"{shot.transition_duration:.2f}s",
                            track_name=f"BlenderTrans_{i}",
                        )
                        if trans_seg and _MIX_MODE_AVAILABLE:
                            from mix_mode import apply_mix_mode
                            apply_mix_mode(project, trans_seg, mode="multiply", intensity=1.0)
                        trans_count += 1
                        print(f"  Blender转场@{i}: {b_style} ({shot.transition_duration}s)")
                        continue
                except Exception as e:
                    print(f"  Blender转场@{i}失败，回退普通转场: {e}")

            # 普通转场
            try:
                trans_map = {
                    "叠化": "叠化", "快切": "闪黑", "闪白": "闪白",
                    "黑场": "渐黑", "淡入": "淡入淡出",
                }
                trans_type = trans_map.get(shot.transition_in, "叠化")
                segments[i-1].add_transition(
                    getattr(draft.TransitionType, trans_type, draft.TransitionType.叠化),
                    duration=int(shot.transition_duration * 1_000_000)
                )
                trans_count += 1
            except Exception as e:
                print(f"  转场{i}失败: {e}")
        print(f"  添加 {trans_count} 个普通转场 + {flash_count} 个蒙版快闪")

        # 3. 字幕（从片头后开始）—— 优先使用特效库字幕条
        sub_count = 0
        current_time = intro_offset
        # 分镜风格→字幕风格映射
        style_map = {
            "cinematic": "cinema", "vlog": "vlog", "tutorial": "news",
            "thriller": "tech", "emotional": "vlog",
        }
        sub_style = style_map.get(style, "cinema")
        # 检查是否使用特效库字幕条
        use_bar = _SUBTITLE_BAR_AVAILABLE and sub_style in _SUBTITLE_BAR_STYLE_MAP
        bar_style = _SUBTITLE_BAR_STYLE_MAP.get(sub_style, "rect_dark") if use_bar else None

        for i, shot in enumerate(sb.shots):
            if shot.subtitle:
                if use_bar:
                    # 特效库半透明字幕条
                    _add_subtitle_bar_effect(
                        project,
                        text=shot.subtitle,
                        start_time=f"{current_time + 0.2:.2f}s",
                        duration=f"{max(shot.duration - 0.4, 0.5):.2f}s",
                        style=bar_style,
                        position_y=0.6,
                        anim_in="pop",
                        output_dir=os.path.join(self.work_dir, "output", "subtitle_bar_assets"),
                    )
                elif _ENHANCED_SUBTITLE_AVAILABLE:
                    add_styled_subtitle(
                        project,
                        text=shot.subtitle,
                        start_time=f"{current_time + 0.2:.2f}s",
                        duration=f"{max(shot.duration - 0.4, 0.5):.2f}s",
                        style=sub_style,
                    )
                elif add_artistic_subtitle:
                    add_artistic_subtitle(
                        project,
                        main_text=shot.subtitle,
                        start_time=f"{current_time + 0.2:.2f}s",
                        duration=f"{max(shot.duration - 0.4, 0.5):.2f}s",
                        style=shot.subtitle_style,
                    )
                sub_count += 1
            current_time += shot.duration
        print(f"  添加 {sub_count} 个字幕 ({'字幕条:'+bar_style if use_bar else sub_style+'风格'})")

        # 4. 音效（从片头后开始）
        sfx_count = 0
        current_time = intro_offset
        for i, shot in enumerate(sb.shots):
            if shot.sfx_hint:
                best = self.asset_lib.get_best_match(
                    "sfx", context=shot.sfx_hint, style=sb.intro_style
                )
                if best:
                    sfx_path = self.asset_lib.get_path(best["id"])
                    try:
                        project.add_media_safe(
                            sfx_path, start_time=f"{current_time:.2f}s",
                            duration="0.5s", track_name="SFX"
                        )
                        sfx_count += 1
                    except Exception:
                        pass
            current_time += shot.duration
        print(f"  添加 {sfx_count} 个音效")

        # 5. BGM（覆盖片头+正片）
        if add_bgm and sb.bgm_mood:
            total_dur = intro_offset + sb.total_duration
            try:
                project.add_cloud_music(
                    sb.bgm_mood, start_time="0s",
                    duration=f"{total_dur}s", track_name="BGM"
                )
                print(f"  BGM: {sb.bgm_mood} ({total_dur:.1f}s)")
            except Exception as e:
                print(f"  BGM失败: {e}")

        # 6. 拍立得照片墙结尾（特效库集成）
        if photo_wall and _POLAROID_WALL_AVAILABLE:
            try:
                wall_start = intro_offset + char_intro_duration + text_layout_duration + sb.total_duration
                _add_polaroid_photos(
                    project,
                    photos=photo_wall,
                    start_time=wall_start,
                    duration=4.0,
                    stagger=0.6,
                    output_dir=os.path.join(self.work_dir, "output", "polaroid_assets"),
                )
                print(f"  拍立得照片墙: {len(photo_wall)}张 (起始{wall_start:.1f}s)")
            except Exception as e:
                print(f"  拍立得照片墙失败: {e}")

        # 保存（自动注入蒙版关键帧+混合模式）
        has_mask_kf = _MASK_KF_AVAILABLE and getattr(project, '_mask_kf_patches', None)
        has_mix = _MIX_MODE_AVAILABLE and getattr(project, '_mix_mode_patches', None)

        if has_mask_kf and has_mix:
            # 先保存基础工程，再分别注入两种补丁
            result = project.save()
            draft_path = os.path.join(getattr(project, 'root', ''), getattr(project, 'name', project_name))
            from mask_keyframe import inject_mask_keyframes_to_draft
            from mix_mode import inject_mix_modes_to_draft
            inject_mask_keyframes_to_draft(draft_path, project._mask_kf_patches, canvas_h=height)
            inject_mix_modes_to_draft(draft_path, project._mix_mode_patches)
            print(f"  保存: 已注入蒙版关键帧+混合模式")
        elif has_mask_kf:
            result = _save_with_mask_kf(project, canvas_h=height)
            print(f"  保存: 已注入蒙版关键帧")
        elif has_mix:
            result = save_with_mix_modes(project)
            print(f"  保存: 已注入混合模式")
        else:
            result = project.save()
        draft_path = os.path.join(getattr(project, 'root', ''), getattr(project, 'name', project_name))
        return {"status": "success", "segments": len(segments), "transitions": trans_count, "draft_path": draft_path}


# ==================== 便捷函数 ====================

def create_video(theme: str, style: str = "cinematic",
                 duration: float = 15.0, shot_count: int = 5,
                 **kwargs) -> Dict[str, Any]:
    """一键生成视频"""
    pipeline = E2EPipeline()
    return pipeline.run(theme, style, duration, shot_count, **kwargs)
