"""
P25: 中央调度器（Central Orchestrator）
导演引擎的第三模块：按依赖关系执行指令序列，调度各工具协同工作

核心能力：
1. 任务依赖图（DAG）：先生成素材→再做动画→最后合成
2. 执行队列：并行/串行调度
3. 失败重试：工具失败自动降级或重试
4. 音画同步：对白对齐口型，音效对齐动作
5. 资源管理：显存清理、临时文件管理

输入：P24输出的指令序列JSON
输出：执行结果报告（成功/失败/耗时/产物路径）
"""

import json
import os
import time
import uuid
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskType(Enum):
    TTS = "tts"                    # 语音合成
    KEYFRAME = "keyframe"          # 剪映关键帧
    EFFECT = "effect"              # 特效/转场
    AUDIO = "audio"                # 音轨处理
    SFX = "sfx"                    # 音效生成
    TEXT = "text"                  # 文字排版
    COMFYUI = "comfyui"            # ComfyUI视频生成
    BLENDER = "blender"            # Blender动画
    MEDIA = "media"                # 素材准备
    ASSET = "asset"                # 素材生成（角色图/场景图/道具图）
    COMPOSE = "compose"            # 最终合成


@dataclass
class Task:
    """调度任务单元"""
    id: str
    type: TaskType
    name: str
    params: Dict = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = ""
    start_time: float = 0
    end_time: float = 0
    retry_count: int = 0
    max_retries: int = 2


@dataclass
class ExecutionReport:
    """执行结果报告"""
    total_tasks: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    total_duration: float = 0
    tasks: List[Dict] = field(default_factory=list)
    output_path: str = ""


class CentralOrchestrator:
    """中央调度器"""

    def __init__(self, work_dir: str = None):
        self.work_dir = work_dir or os.path.join(
            os.path.expanduser("~"), "Videos", "ai-video-editor-output",
            "director_engine_output"
        )
        os.makedirs(self.work_dir, exist_ok=True)

        self.tasks: List[Task] = []
        self.task_map: Dict[str, Task] = {}
        self.report = ExecutionReport()

        # 工具执行器注册
        self.executors: Dict[TaskType, Callable] = {}
        self._register_default_executors()

    def _register_default_executors(self):
        """注册默认执行器（占位，实际执行由外部注入）"""
        self.executors[TaskType.TTS] = self._execute_tts
        self.executors[TaskType.KEYFRAME] = self._execute_keyframe
        self.executors[TaskType.EFFECT] = self._execute_effect
        self.executors[TaskType.AUDIO] = self._execute_audio
        self.executors[TaskType.SFX] = self._execute_sfx
        self.executors[TaskType.TEXT] = self._execute_text
        self.executors[TaskType.COMFYUI] = self._execute_comfyui
        self.executors[TaskType.BLENDER] = self._execute_blender
        self.executors[TaskType.MEDIA] = self._execute_media
        self.executors[TaskType.ASSET] = self._execute_asset
        self.executors[TaskType.COMPOSE] = self._execute_compose

    def build_tasks_from_instructions(self, instruction_sequence: Dict[str, Any],
                                       deep_analysis: Dict[str, Any] = None) -> List[Task]:
        """
        从P24指令序列构建任务DAG

        Args:
            instruction_sequence: P24输出的指令序列
            deep_analysis: P23深度语义分析结果（用于智能混音）

        依赖关系：
        - MEDIA（素材准备）→ 所有其他任务
        - COMFYUI/BLENDER（素材生成）→ COMPOSE
        - TTS → COMPOSE
        - AUDIO → COMPOSE
        - KEYFRAME/EFFECT/TEXT → COMPOSE
        - COMPOSE 最后执行
        """
        self.tasks = []
        self.task_map = {}

        project = instruction_sequence.get("project", {})
        project_name = project.get("title", "未命名项目")

        # 1. 素材准备任务（最先执行）
        media_task = Task(
            id=f"media_{uuid.uuid4().hex[:8]}",
            type=TaskType.MEDIA,
            name=f"素材准备: {project_name}",
            params={"project": project},
        )
        self._add_task(media_task)

        # 1.5 素材生成任务（角色图/场景图，依赖MEDIA）
        asset_task_ids = []
        characters = project.get("characters", [])
        scenes = project.get("scenes", [])

        for i, char in enumerate(characters):
            char_name = char.get("name", f"角色{i}")
            char_desc = char.get("description", "")
            task = Task(
                id=f"asset_char_{i:03d}",
                type=TaskType.ASSET,
                name=f"角色图: {char_name}",
                params={
                    "asset_type": "character",
                    "name": char_name,
                    "description": char_desc,
                    "character": char,
                },
                dependencies=[media_task.id],
            )
            self._add_task(task)
            asset_task_ids.append(task.id)

        for i, scene in enumerate(scenes):
            scene_loc = scene.get("location", f"场景{i}")
            scene_atm = scene.get("atmosphere", "")
            task = Task(
                id=f"asset_scene_{i:03d}",
                type=TaskType.ASSET,
                name=f"场景图: {scene_loc}",
                params={
                    "asset_type": "scene",
                    "name": scene_loc,
                    "description": f"{scene_loc}, {scene_atm}",
                    "scene": scene,
                },
                dependencies=[media_task.id],
            )
            self._add_task(task)
            asset_task_ids.append(task.id)

        # 2. TTS任务
        for i, tts in enumerate(instruction_sequence.get("tts_instructions", [])):
            task = Task(
                id=f"tts_{i:03d}",
                type=TaskType.TTS,
                name=f"TTS: {tts.get('character', '')} - {tts.get('text', '')[:20]}",
                params=tts,
                dependencies=[media_task.id],
            )
            self._add_task(task)

        # 3. 音轨任务
        for i, audio in enumerate(instruction_sequence.get("audio_instructions", [])):
            task = Task(
                id=f"audio_{i:03d}",
                type=TaskType.AUDIO,
                name=f"音轨: {audio.get('name', '')}",
                params=audio,
                dependencies=[media_task.id],
            )
            self._add_task(task)

        # 3.5 音效任务（SFX）
        for i, sfx in enumerate(instruction_sequence.get("sfx_instructions", [])):
            task = Task(
                id=f"sfx_{i:03d}",
                type=TaskType.SFX,
                name=f"音效: {sfx.get('type', '')}",
                params=sfx,
                dependencies=[media_task.id],
            )
            self._add_task(task)

        # 4. 剪映工程构建已合并到最终合成任务（避免重复构建）
        # KEYFRAME/EFFECT/TEXT指令由COMPOSE任务统一处理

        # 5. 最终合成任务（最后执行，包含角色+关键帧+特效+文字+音频）
        compose_deps = [t.id for t in self.tasks if t.type != TaskType.COMPOSE]
        compose_task = Task(
            id=f"compose_{uuid.uuid4().hex[:8]}",
            type=TaskType.COMPOSE,
            name=f"最终合成: {project_name}",
            params={
                "instruction_sequence": instruction_sequence,
                "project": project,
                "project_name": project_name,
                "output_dir": self.work_dir,
                "deep_analysis": deep_analysis,
            },
            dependencies=compose_deps,
        )
        self._add_task(compose_task)

        return self.tasks

    def _add_task(self, task: Task):
        """添加任务到调度器"""
        self.tasks.append(task)
        self.task_map[task.id] = task

    def execute(self, dry_run: bool = False) -> ExecutionReport:
        """
        执行任务DAG

        Args:
            dry_run: 只打印执行计划，不实际执行

        Returns:
            ExecutionReport 执行报告
        """
        print(f"\n{'='*60}")
        print(f"中央调度器启动")
        print(f"{'='*60}")
        print(f"任务总数: {len(self.tasks)}")
        print(f"工作目录: {self.work_dir}")
        print(f"模式: {'模拟执行' if dry_run else '实际执行'}")

        start_time = time.time()
        self.report = ExecutionReport(total_tasks=len(self.tasks))

        # 拓扑排序执行
        executed = set()
        while len(executed) < len(self.tasks):
            # 找到所有依赖已满足的待执行任务
            ready = [
                t for t in self.tasks
                if t.status == TaskStatus.PENDING
                and all(d in executed for d in t.dependencies)
            ]

            if not ready:
                # 检查是否有死锁
                pending = [t for t in self.tasks if t.status == TaskStatus.PENDING]
                if pending:
                    print(f"⚠️ 检测到死锁，{len(pending)}个任务无法执行")
                    for t in pending:
                        t.status = TaskStatus.FAILED
                        t.error = "依赖死锁"
                        self.report.failed_count += 1
                        self.report.tasks.append(self._task_to_report(t))
                break

            # 执行就绪任务（可并行，这里串行执行）
            for task in ready:
                self._execute_task(task, dry_run)
                executed.add(task.id)

        self.report.total_duration = time.time() - start_time

        # 打印报告
        self._print_report()

        return self.report

    def _execute_task(self, task: Task, dry_run: bool = False):
        """执行单个任务"""
        task.status = TaskStatus.RUNNING
        task.start_time = time.time()

        print(f"\n▶ [{task.type.value}] {task.name}")
        if task.dependencies:
            print(f"  依赖: {len(task.dependencies)}个任务")

        if dry_run:
            # 模拟执行
            time.sleep(0.1)
            task.status = TaskStatus.SUCCESS
            task.result = {"dry_run": True, "output": f"模拟输出_{task.id}"}
            print(f"  ✅ 模拟完成")
        else:
            # 实际执行
            executor = self.executors.get(task.type)
            if executor:
                try:
                    result = executor(task)
                    task.status = TaskStatus.SUCCESS
                    task.result = result
                    print(f"  ✅ 完成")
                except Exception as e:
                    if task.retry_count < task.max_retries:
                        task.retry_count += 1
                        print(f"  ⚠️ 失败，重试 {task.retry_count}/{task.max_retries}: {e}")
                        task.status = TaskStatus.PENDING  # 重新排队
                        return
                    else:
                        task.status = TaskStatus.FAILED
                        task.error = str(e)
                        print(f"  ❌ 失败（已重试{task.max_retries}次）: {e}")
            else:
                task.status = TaskStatus.SKIPPED
                task.error = "无执行器"
                print(f"  ⏭️ 跳过（无执行器）")

        task.end_time = time.time()

        # 记录报告
        if task.status == TaskStatus.SUCCESS:
            self.report.success_count += 1
        elif task.status == TaskStatus.FAILED:
            self.report.failed_count += 1
        elif task.status == TaskStatus.SKIPPED:
            self.report.skipped_count += 1

        self.report.tasks.append(self._task_to_report(task))

    def _task_to_report(self, task: Task) -> Dict:
        """任务转报告格式"""
        return {
            "id": task.id,
            "type": task.type.value,
            "name": task.name,
            "status": task.status.value,
            "duration": round(task.end_time - task.start_time, 2) if task.end_time else 0,
            "error": task.error,
            "retry_count": task.retry_count,
        }

    def _print_report(self):
        """打印执行报告"""
        print(f"\n{'='*60}")
        print(f"执行报告")
        print(f"{'='*60}")
        print(f"总任务: {self.report.total_tasks}")
        print(f"✅ 成功: {self.report.success_count}")
        print(f"❌ 失败: {self.report.failed_count}")
        print(f"⏭️ 跳过: {self.report.skipped_count}")
        print(f"总耗时: {self.report.total_duration:.2f}秒")
        print(f"{'='*60}\n")

    def save_report(self, output_path: str = None):
        """保存执行报告"""
        if not output_path:
            output_path = os.path.join(self.work_dir, "execution_report.json")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(asdict(self.report), f, ensure_ascii=False, indent=2)
        print(f"✅ 执行报告已保存: {output_path}")
        return output_path

    # ============ 默认执行器（占位实现） ============

    def _execute_tts(self, task: Task) -> Dict:
        """TTS执行器（优先使用适配层，回退到直连tts_executor）"""
        text = task.params.get("text", "")
        if not text:
            return {"output_path": None, "skipped": True}
        # 情绪优先级：voice_style（P24自动检测）> emotion（P23指定）> normal
        emotion = task.params.get("voice_style") or task.params.get("emotion") or "normal"
        character = task.params.get("character", "默认")

        # 优先使用适配层TTS适配器
        try:
            import sys
            adapters_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "adapters"
            )
            if adapters_path not in sys.path:
                sys.path.insert(0, adapters_path)
            from tts_adapter import TTSAdapter
            adapter = TTSAdapter()
            if adapter.is_available:
                response = adapter.generate(text=text, voice=character, emotion=emotion)
                if response and response.success:
                    return {
                        "output_path": response.audio_path,
                        "character": character,
                        "emotion": emotion,
                        "duration": response.duration_sec,
                        "provider": response.provider,
                        "via_adapter": True,
                    }
                else:
                    print(f"  ⚠️  适配层TTS失败: {getattr(response, 'error', '未知')}，回退到直连")
        except Exception as e:
            print(f"  ⚠️  适配层TTS初始化失败: {e}，回退到直连")

        # 回退到直连TTSExecutor
        try:
            from tts_executor import TTSExecutor
        except ImportError:
            return {"output_path": f"{self.work_dir}/tts/{task.id}.wav", "placeholder": True}

        executor = TTSExecutor(output_dir=os.path.join(self.work_dir, "tts"))
        result = executor.synthesize(text=text, character=character, emotion=emotion)
        return {"output_path": result, "character": character, "emotion": emotion}

    def _execute_keyframe(self, task: Task) -> Dict:
        """剪映工程构建执行器（调用实际的jianying_executor）"""
        try:
            from jianying_executor import JianyingExecutor
        except ImportError:
            # 占位实现
            return {"draft_path": f"{self.work_dir}/drafts/{task.id}", "placeholder": True}

        instructions = task.params.get("instruction_sequence", {})
        project = task.params.get("project", {})
        project_name = project.get("title", task.id)
        duration = project.get("duration", 20)

        executor = JianyingExecutor(work_dir=self.work_dir)
        result = executor.execute(
            instructions,
            project_name=project_name,
            duration=duration,
        )
        return result

    def _execute_effect(self, task: Task) -> Dict:
        """特效执行器（占位）"""
        return {"applied": len(task.params.get("effects", []))}

    def _execute_audio(self, task: Task) -> Dict:
        """音轨执行器（调用实际的audio_executor）"""
        try:
            from audio_executor import AudioExecutor
        except ImportError:
            return {"audio_path": f"{self.work_dir}/audio/{task.id}.wav", "placeholder": True}

        # 兼容两种格式：单个指令字典 或 包含audio_instructions列表的字典
        audio_instructions = task.params.get("audio_instructions")
        if not audio_instructions:
            # build_tasks_from_instructions中每个audio指令创建一个任务，params就是单个指令
            audio_instructions = [task.params]

        if not audio_instructions:
            return {"audio_path": None, "skipped": True}

        executor = AudioExecutor(output_dir=os.path.join(self.work_dir, "audio"))
        result = executor.execute(audio_instructions)

        # 提取实际生成的音频文件路径列表
        generated_files = []
        for r in result.get("results", []):
            if r.get("output_path") and os.path.exists(r["output_path"]):
                generated_files.append({
                    "output_path": r["output_path"],
                    "name": r.get("name", ""),
                    "type": r.get("type", ""),
                    "duration": r.get("duration", 0),
                    "volume": r.get("volume", 1.0),
                    "start_time": task.params.get("start_time", 0),
                })

        return {
            "audio_path": result.get("output_dir"),
            "success_count": result.get("success", 0),
            "generated_files": generated_files,
        }

    def _execute_sfx(self, task: Task) -> Dict:
        """音效执行器（优先使用适配层，回退到直连sfx_executor）"""
        sfx_type = task.params.get("type", "ding")
        emotion = task.params.get("emotion", "normal")
        duration = task.params.get("duration", 1.0)

        # 优先使用适配层SFX适配器
        try:
            import sys
            adapters_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "adapters"
            )
            if adapters_path not in sys.path:
                sys.path.insert(0, adapters_path)
            from sfx_adapter import SFXAdapter
            adapter = SFXAdapter()
            if adapter.is_available:
                response = adapter.generate(
                    description=sfx_type,
                    duration_sec=duration,
                    category=emotion,
                )
                if response and response.success:
                    return {
                        "sfx_path": response.audio_path,
                        "name": sfx_type,
                        "rating": response.quality_rating,
                        "source": "adapter",
                        "duration": response.duration_sec,
                        "from_cache": False,
                        "via_adapter": True,
                    }
                else:
                    print(f"  ⚠️  适配层SFX失败: {getattr(response, 'error', '未知')}，回退到直连")
        except Exception as e:
            print(f"  ⚠️  适配层SFX初始化失败: {e}，回退到直连")

        # 回退到直连SFXExecutor
        try:
            from sfx_executor import SFXExecutor
        except ImportError:
            return {"sfx_path": None, "placeholder": True}

        executor = SFXExecutor(work_dir=os.path.join(self.work_dir, "sfx"))
        result = executor.generate(sfx_type, emotion, duration)
        if result:
            return {
                "sfx_path": result["path"],
                "name": result["name"],
                "rating": result["rating"],
                "source": result["source"],
                "duration": result["duration"],
                "from_cache": result["from_cache"],
            }
        return {"sfx_path": None, "skipped": True}

    def _execute_text(self, task: Task) -> Dict:
        """文字排版执行器（调用实际的text_executor）"""
        try:
            from text_executor import TextExecutor
        except ImportError:
            return {"text_count": len(task.params.get("texts", [])), "placeholder": True}
        text_instructions = task.params.get("text_instructions", [])
        if not text_instructions:
            return {"text_count": 0, "skipped": True}
        executor = TextExecutor(output_dir=os.path.join(self.work_dir, "text"))
        result = executor.execute(text_instructions)
        return {"text_count": result.get("success", 0), "output_dir": result.get("output_dir")}

    def _execute_comfyui(self, task: Task) -> Dict:
        """ComfyUI素材生成执行器（调用实际的comfyui_executor）"""
        try:
            from comfyui_executor import ComfyUIAssetExecutor
        except ImportError:
            return {"success": False, "error": "comfyui_executor不可用", "assets": []}

        try:
            executor = ComfyUIAssetExecutor(work_dir=self.work_dir)

            if not executor.is_available():
                return {"success": False, "error": "ComfyUI未运行", "assets": []}

            params = task.params
            assets = params.get("assets", [])

            # 支持单个素材生成
            if not assets and "description" in params:
                assets = [{
                    "type": params.get("type", "character"),
                    "name": params.get("name", task.id),
                    "description": params.get("description", ""),
                }]

            if not assets:
                return {"success": True, "assets": [], "message": "无素材需要生成"}

            print(f"\n[ComfyUI] 任务: {task.name}, 生成{len(assets)}个素材")

            results = executor.generate_batch(assets)

            success_count = sum(1 for r in results if r["success"])
            output_paths = [r["output_path"] for r in results if r["success"]]

            return {
                "success": success_count == len(assets),
                "total": len(assets),
                "success_count": success_count,
                "failed_count": len(assets) - success_count,
                "assets": results,
                "output_paths": output_paths,
            }

        except Exception as e:
            print(f"  ❌ ComfyUI执行器失败: {e}")
            return {"success": False, "error": str(e), "assets": []}

    def _execute_blender(self, task: Task) -> Dict:
        """Blender执行器（占位）"""
        return {"animation_path": f"{self.work_dir}/animations/{task.id}.mp4"}

    def _execute_media(self, task: Task) -> Dict:
        """素材准备执行器（占位）"""
        return {"media_ready": True}

    def _execute_asset(self, task: Task) -> Dict:
        """素材生成执行器（调用ComfyUI生成角色图/场景图/道具图）"""
        try:
            from comfyui_executor import ComfyUIAssetExecutor
        except ImportError:
            return {"output_path": None, "placeholder": True, "error": "comfyui_executor不可用"}

        asset_type = task.params.get("asset_type", "character")
        name = task.params.get("name", "asset")
        description = task.params.get("description", "")

        # 检查是否已有缓存素材
        asset_dir = os.path.join(self.work_dir, "assets")
        os.makedirs(asset_dir, exist_ok=True)
        cached_path = os.path.join(asset_dir, f"{asset_type}_{name}.png")
        if os.path.exists(cached_path):
            print(f"  ⏭️ 素材已存在，跳过: {os.path.basename(cached_path)}")
            return {"output_path": cached_path, "asset_type": asset_type, "name": name, "from_cache": True}

        try:
            executor = ComfyUIAssetExecutor(work_dir=asset_dir)
            if not executor.is_available():
                print(f"  ⚠️ ComfyUI不可用，使用占位图")
                return {"output_path": None, "asset_type": asset_type, "name": name, "placeholder": True}

            if asset_type == "character":
                result = executor.generate_character(name=name, description=description)
            elif asset_type == "scene":
                result = executor.generate_scene(name=name, description=description)
            else:
                result = executor.generate_prop(name=name, description=description)

            if result.get("success"):
                return {
                    "output_path": result["output_path"],
                    "asset_type": asset_type,
                    "name": name,
                    "description": description,
                    "width": result.get("width"),
                    "height": result.get("height"),
                }
            else:
                print(f"  ⚠️ 素材生成失败: {result.get('error', '未知错误')}")
                return {"output_path": None, "asset_type": asset_type, "name": name, "placeholder": True}
        except Exception as e:
            print(f"  ⚠️ 素材生成异常: {e}")
            return {"output_path": None, "asset_type": asset_type, "name": name, "placeholder": True, "error": str(e)}

    def _execute_compose(self, task: Task) -> Dict:
        """最终合成执行器（调用实际的compose_executor）"""
        try:
            from compose_executor import ComposeExecutor
        except ImportError:
            output = f"{self.work_dir}/output/{task.params.get('project', {}).get('title', 'output')}.mp4"
            return {"output_path": output, "placeholder": True}

        instruction_sequence = task.params.get("instruction_sequence", {})
        project_name = task.params.get("project_name", "最终合成")
        width = task.params.get("width", 1080)
        height = task.params.get("height", 1920)
        duration = task.params.get("duration", 20.0)
        deep_analysis = task.params.get("deep_analysis", None)

        # 收集之前任务的结果
        tts_results = []
        audio_results = []
        sfx_results = []
        asset_results = []
        for t in self.tasks:
            if t.type == TaskType.TTS and t.result:
                tts_results.append(t.result)
            elif t.type == TaskType.AUDIO and t.result:
                # 兼容两种格式：generated_files（新）或 results（旧）
                gen_files = t.result.get("generated_files", [])
                if gen_files:
                    audio_results.extend(gen_files)
                else:
                    audio_results.extend(t.result.get("results", []))
            elif t.type == TaskType.SFX and t.result:
                sfx_results.append(t.result)
            elif t.type == TaskType.ASSET and t.result:
                asset_results.append(t.result)

        executor = ComposeExecutor(work_dir=self.work_dir)
        result = executor.execute(
            instruction_sequence=instruction_sequence,
            project_name=project_name,
            width=width,
            height=height,
            duration=duration,
            tts_results=tts_results if tts_results else None,
            audio_results=audio_results if audio_results else None,
            sfx_results=sfx_results if sfx_results else None,
            asset_results=asset_results if asset_results else None,
            deep_analysis=deep_analysis,
        )
        return result


if __name__ == "__main__":
    # 测试：用P24输出的指令序列做调度
    instr_path = r"D:\DobaoWork_Project\Ai_Video_Editor\director_engine_test\instruction_sequence.json"

    if os.path.exists(instr_path):
        with open(instr_path, "r", encoding="utf-8") as f:
            instructions = json.load(f)

        orchestrator = CentralOrchestrator()
        tasks = orchestrator.build_tasks_from_instructions(instructions)

        print(f"\n构建任务DAG: {len(tasks)}个任务")
        for t in tasks:
            deps = f" (依赖:{len(t.dependencies)})" if t.dependencies else ""
            print(f"  [{t.type.value}] {t.name}{deps}")

        # 模拟执行
        report = orchestrator.execute(dry_run=True)
        orchestrator.save_report()
    else:
        print(f"❌ 指令序列文件不存在: {instr_path}")
