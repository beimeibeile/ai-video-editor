"""
通用质量门框架
参考 shuohao-skills 的质量门机制：14-18道确定性检查全部脚本化，不靠模型自觉。

设计原则：
1. 每道门是一个确定性函数，输入数据，返回 GateResult
2. 支持批量检查（run_all）和单门检查（run_single）
3. 每道门必须有击穿用例（negative test），证明它真的会拦
4. 门可注册、可扩展，不修改核心代码
5. 检查结果可序列化为 JSON，可渲染为报告

使用方法：
    from quality_gate import QualityGate, GateResult, GateRegistry

    # 定义一道门
    def check_duration(storyboard):
        if storyboard.get("total_duration", 0) > 180:
            return GateResult.fail("G001", "总时长超过180秒", detail=f"当前{storyboard['total_duration']}秒")
        return GateResult.pass("G001", "总时长合规")

    # 注册
    registry = GateRegistry()
    registry.register("storyboard", check_duration)

    # 批量检查
    results = registry.run_all("storyboard", storyboard_data)
    print(results.summary())
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Callable, List, Dict, Any, Optional
from enum import Enum


class GateStatus(Enum):
    """质量门状态"""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


@dataclass
class GateResult:
    """单道质量门的检查结果"""
    gate_id: str
    gate_name: str
    status: GateStatus
    message: str
    detail: str = ""
    severity: str = "error"  # error / warning / info
    data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def pass_(cls, gate_id: str, gate_name: str, message: str = "通过", **kwargs) -> "GateResult":
        return cls(gate_id=gate_id, gate_name=gate_name, status=GateStatus.PASS,
                   message=message, **kwargs)

    @classmethod
    def fail(cls, gate_id: str, gate_name: str, message: str, detail: str = "", **kwargs) -> "GateResult":
        return cls(gate_id=gate_id, gate_name=gate_name, status=GateStatus.FAIL,
                   message=message, detail=detail, severity="error", **kwargs)

    @classmethod
    def warn(cls, gate_id: str, gate_name: str, message: str, detail: str = "", **kwargs) -> "GateResult":
        return cls(gate_id=gate_id, gate_name=gate_name, status=GateStatus.WARN,
                   message=message, detail=detail, severity="warning", **kwargs)

    @classmethod
    def skip(cls, gate_id: str, gate_name: str, message: str = "跳过") -> "GateResult":
        return cls(gate_id=gate_id, gate_name=gate_name, status=GateStatus.SKIP,
                   message=message, severity="info")

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    def __str__(self) -> str:
        icon = {"pass": "✅", "fail": "❌", "warn": "⚠️", "skip": "⏭️"}[self.status.value]
        line = f"{icon} [{self.gate_id}] {self.gate_name}: {self.message}"
        if self.detail and self.status != GateStatus.PASS:
            line += f"\n   ↳ {self.detail}"
        return line


@dataclass
class GateReport:
    """批量质量门检查报告"""
    category: str
    results: List[GateResult] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    warned: int = 0
    skipped: int = 0

    def add(self, result: GateResult):
        self.results.append(result)
        if result.status == GateStatus.PASS:
            self.passed += 1
        elif result.status == GateStatus.FAIL:
            self.failed += 1
        elif result.status == GateStatus.WARN:
            self.warned += 1
        else:
            self.skipped += 1

    @property
    def all_passed(self) -> bool:
        return self.failed == 0

    @property
    def total(self) -> int:
        return len(self.results)

    def summary(self) -> str:
        lines = [
            f"{'='*60}",
            f"质量门报告: {self.category}",
            f"{'='*60}",
            f"总计: {self.total} | 通过: {self.passed} | 失败: {self.failed} | 警告: {self.warned} | 跳过: {self.skipped}",
            f"{'='*60}",
        ]
        for r in self.results:
            lines.append(str(r))
        lines.append(f"{'='*60}")
        if self.all_passed:
            lines.append("✅ 全部通过")
        else:
            lines.append(f"❌ {self.failed} 道门未通过，需修复后重跑")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "warned": self.warned,
            "skipped": self.skipped,
            "all_passed": self.all_passed,
            "results": [r.to_dict() for r in self.results],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


# 质量门函数类型
GateFunc = Callable[[Dict[str, Any]], GateResult]


class GateRegistry:
    """质量门注册表

    按类别组织质量门，支持注册、注销、批量运行。
    每个类别对应一个检查场景（storyboard / script / outline / edit 等）。
    """

    def __init__(self):
        self._gates: Dict[str, List[GateFunc]] = {}

    def register(self, category: str, gate_func: GateFunc) -> None:
        """注册一道质量门到指定类别"""
        if category not in self._gates:
            self._gates[category] = []
        self._gates[category].append(gate_func)

    def register_many(self, category: str, gate_funcs: List[GateFunc]) -> None:
        """批量注册"""
        for f in gate_funcs:
            self.register(category, f)

    def unregister(self, category: str, gate_func: GateFunc) -> bool:
        """注销一道门，返回是否成功"""
        if category in self._gates and gate_func in self._gates[category]:
            self._gates[category].remove(gate_func)
            return True
        return False

    def categories(self) -> List[str]:
        return list(self._gates.keys())

    def gate_count(self, category: str) -> int:
        return len(self._gates.get(category, []))

    def run_all(self, category: str, data: Dict[str, Any]) -> GateReport:
        """运行指定类别的所有质量门"""
        report = GateReport(category=category)
        gates = self._gates.get(category, [])
        for gate_func in gates:
            try:
                result = gate_func(data)
            except Exception as e:
                result = GateResult.fail(
                    gate_id="ERROR",
                    gate_name=getattr(gate_func, "__name__", "unknown"),
                    message=f"检查函数执行异常: {type(e).__name__}",
                    detail=str(e)
                )
            report.add(result)
        return report

    def run_single(self, category: str, gate_name: str, data: Dict[str, Any]) -> Optional[GateResult]:
        """运行单道质量门（按函数名匹配）"""
        for gate_func in self._gates.get(category, []):
            if gate_func.__name__ == gate_name:
                return gate_func(data)
        return None


# ──────────────────────────────────────────────
# 内置质量门：剪辑质量检查（阶段一立即可用）
# ──────────────────────────────────────────────

def gate_edit_total_duration(data: Dict[str, Any]) -> GateResult:
    """E001: 视频总时长合规（短视频≤180秒，可配置）"""
    max_dur = data.get("max_duration", 180)
    total = data.get("total_duration", 0)
    if total <= 0:
        return GateResult.fail("E001", "总时长", "总时长为0或未设置", f"当前值: {total}")
    if total > max_dur:
        return GateResult.fail("E001", "总时长", f"超过上限{max_dur}秒", f"当前{total}秒")
    return GateResult.pass_("E001", "总时长", f"{total}秒，合规")


def gate_edit_segment_count(data: Dict[str, Any]) -> GateResult:
    """E002: 片段数量合理（≥2，≤200）"""
    count = len(data.get("segments", []))
    if count < 2:
        return GateResult.fail("E002", "片段数量", "片段少于2个", f"当前{count}个")
    if count > 200:
        return GateResult.warn("E002", "片段数量", "片段超过200个，可能影响性能", f"当前{count}个")
    return GateResult.pass_("E002", "片段数量", f"{count}个，合理")


def gate_edit_transition_alignment(data: Dict[str, Any]) -> GateResult:
    """E003: 转场位置对齐（转场必须在片段边界，不重叠）"""
    transitions = data.get("transitions", [])
    segments = data.get("segments", [])
    if not transitions:
        return GateResult.skip("E003", "转场对齐", "无转场")
    misaligned = []
    for i, t in enumerate(transitions):
        t_start = t.get("start", 0)
        # 检查是否在某个片段边界
        on_boundary = any(
            abs(t_start - s.get("end", 0)) < 0.034  # 1帧容差(30fps)
            for s in segments
        )
        if not on_boundary:
            misaligned.append(f"转场#{i}@{t_start}s")
    if misaligned:
        return GateResult.fail("E003", "转场对齐", f"{len(misaligned)}个转场不在片段边界",
                               detail="; ".join(misaligned[:5]))
    return GateResult.pass_("E003", "转场对齐", f"{len(transitions)}个转场全部对齐")


def gate_edit_subtitle_coverage(data: Dict[str, Any]) -> GateResult:
    """E004: 字幕覆盖检查（有旁白的片段必须有字幕）"""
    segments = data.get("segments", [])
    no_subtitle = []
    for i, s in enumerate(segments):
        has_narration = s.get("narration") or s.get("has_audio")
        has_subtitle = s.get("subtitle") or s.get("has_subtitle")
        if has_narration and not has_subtitle:
            no_subtitle.append(f"片段#{i}")
    if no_subtitle:
        return GateResult.warn("E004", "字幕覆盖", f"{len(no_subtitle)}个有旁白片段缺少字幕",
                               detail="; ".join(no_subtitle[:5]))
    return GateResult.pass_("E004", "字幕覆盖", "所有有旁白片段均有字幕")


def gate_edit_aspect_ratio(data: Dict[str, Any]) -> GateResult:
    """E005: 画幅一致性（所有片段画幅与画布一致）"""
    canvas_ratio = data.get("canvas_ratio", 9/16)
    segments = data.get("segments", [])
    mismatched = []
    for i, s in enumerate(segments):
        seg_ratio = s.get("aspect_ratio")
        if seg_ratio and abs(seg_ratio - canvas_ratio) > 0.01:
            mismatched.append(f"片段#{i}({seg_ratio:.2f})")
    if mismatched:
        return GateResult.warn("E005", "画幅一致", f"{len(mismatched)}个片段画幅与画布不一致",
                               detail="; ".join(mismatched[:5]))
    return GateResult.pass_("E005", "画幅一致", "所有片段画幅一致")


def gate_edit_frame_precision(data: Dict[str, Any]) -> GateResult:
    """E006: 时间码帧对齐（所有时间点必须是1/30或1/60秒的整数倍）"""
    fps = data.get("fps", 30)
    frame_dur = 1.0 / fps
    tolerance = frame_dur * 0.1  # 10%容差
    timestamps = data.get("timestamps", [])
    misaligned = []
    for ts in timestamps:
        quotient = ts / frame_dur
        if abs(quotient - round(quotient)) > tolerance:
            misaligned.append(f"{ts}s")
    if misaligned:
        return GateResult.fail("E006", "帧对齐", f"{len(misaligned)}个时间点未帧对齐",
                               detail=f"帧率{fps}fps，帧间隔{frame_dur:.4f}s; 示例: {'; '.join(misaligned[:3])}")
    return GateResult.pass_("E006", "帧对齐", f"所有时间点已按{fps}fps对齐")


def gate_edit_black_frame(data: Dict[str, Any]) -> GateResult:
    """E007: 黑屏检测（片段首尾帧不能全黑超过0.5秒）"""
    segments = data.get("segments", [])
    black_segments = []
    for i, s in enumerate(segments):
        if s.get("is_black_frame"):
            dur = s.get("duration", 0)
            if dur > 0.5:
                black_segments.append(f"片段#{i}({dur}s)")
    if black_segments:
        return GateResult.warn("E007", "黑屏检测", f"{len(black_segments)}个黑屏片段超过0.5秒",
                               detail="; ".join(black_segments[:5]))
    return GateResult.pass_("E007", "黑屏检测", "无异常黑屏")


# ──────────────────────────────────────────────
# 内置质量门：分镜质量检查（阶段二预留，当前可用基础版）
# ──────────────────────────────────────────────

def gate_storyboard_shot_duration(data: Dict[str, Any]) -> GateResult:
    """S001: 单镜头时长（2-15秒，AI视频生成上限）"""
    shots = data.get("shots", [])
    if not shots:
        return GateResult.fail("S001", "镜头时长", "无镜头数据")
    invalid = []
    for i, shot in enumerate(shots):
        dur = shot.get("duration", 0)
        if dur < 2:
            invalid.append(f"镜头#{i}({dur}s<2s)")
        elif dur > 15:
            invalid.append(f"镜头#{i}({dur}s>15s)")
    if invalid:
        return GateResult.fail("S001", "镜头时长", f"{len(invalid)}个镜头时长超出2-15秒范围",
                               detail="; ".join(invalid[:5]))
    return GateResult.pass_("S001", "镜头时长", f"{len(shots)}个镜头全部在2-15秒范围内")


def gate_storyboard_hook_first(data: Dict[str, Any]) -> GateResult:
    """S002: 首集/首段有钩子（前3秒必须有钩子元素）"""
    hooks = data.get("hooks", [])
    if not hooks:
        return GateResult.fail("S002", "钩子检查", "未检测到钩子", "前3秒需要钩子元素")
    first_hook_time = min(h.get("time", 999) for h in hooks)
    if first_hook_time > 3:
        return GateResult.fail("S002", "钩子检查", f"首个钩子在{first_hook_time}秒，超过3秒阈值")
    return GateResult.pass_("S002", "钩子检查", f"首个钩子在{first_hook_time}秒")


def gate_storyboard_beat_coverage(data: Dict[str, Any]) -> GateResult:
    """S003: 节拍认领（每个节拍被恰好一个镜头认领，顺序不乱）"""
    shots = data.get("shots", [])
    beats = data.get("beats", [])
    if not beats:
        return GateResult.skip("S003", "节拍认领", "无节拍数据")
    claimed = set()
    for shot in shots:
        for b in shot.get("beats", []):
            if b in claimed:
                return GateResult.fail("S003", "节拍认领", f"节拍{b}被多个镜头认领")
            claimed.add(b)
    unclaimed = [b for b in range(len(beats)) if b not in claimed]
    if unclaimed:
        return GateResult.fail("S003", "节拍认领", f"{len(unclaimed)}个节拍未被认领",
                               detail=f"未认领: {unclaimed[:5]}")
    return GateResult.pass_("S003", "节拍认领", f"全部{len(beats)}个节拍已认领")


def gate_storyboard_shot_size_diversity(data: Dict[str, Any]) -> GateResult:
    """S004: 景别多样性（不能全是同一种景别，至少2种）"""
    shots = data.get("shots", [])
    if not shots:
        return GateResult.fail("S004", "景别多样性", "无镜头数据")
    sizes = set(s.get("shot_size", "") for s in shots if s.get("shot_size"))
    if len(sizes) < 2:
        return GateResult.warn("S004", "景别多样性", f"仅{len(sizes)}种景别，建议至少2种",
                               detail=f"当前景别: {', '.join(sizes) if sizes else '无'}")
    return GateResult.pass_("S004", "景别多样性", f"{len(sizes)}种景别: {', '.join(sizes)}")


def gate_storyboard_camera_move_diversity(data: Dict[str, Any]) -> GateResult:
    """S005: 运镜多样性（不能全是固定镜头，动态镜头占比≥30%）"""
    shots = data.get("shots", [])
    if not shots:
        return GateResult.fail("S005", "运镜多样性", "无镜头数据")
    static_moves = {"固定", "static", "fixed", ""}
    dynamic_count = sum(1 for s in shots if s.get("camera_move", "") not in static_moves)
    ratio = dynamic_count / len(shots)
    if ratio < 0.3:
        return GateResult.warn("S005", "运镜多样性", f"动态镜头仅{ratio:.0%}，建议≥30%",
                               detail=f"动态{dynamic_count}/{len(shots)}")
    return GateResult.pass_("S005", "运镜多样性", f"动态镜头{ratio:.0%} ({dynamic_count}/{len(shots)})")


def gate_storyboard_emotion_rhythm(data: Dict[str, Any]) -> GateResult:
    """S006: 情绪节奏（应包含钩子→展开→高潮→收束的节奏变化）"""
    shots = data.get("shots", [])
    if not shots:
        return GateResult.fail("S006", "情绪节奏", "无镜头数据")
    emotions = set(s.get("emotion", "") for s in shots if s.get("emotion"))
    required = {"钩子", "高潮", "收束"}
    missing = required - emotions
    if missing:
        return GateResult.warn("S006", "情绪节奏", f"缺少关键情绪: {', '.join(missing)}",
                               detail=f"当前情绪: {', '.join(emotions) if emotions else '无'}")
    return GateResult.pass_("S006", "情绪节奏", f"情绪完整: {', '.join(sorted(emotions))}")


def gate_storyboard_first_shot_closeup(data: Dict[str, Any]) -> GateResult:
    """S007: 首镜头景别（短视频首镜头建议特写/近景，增强代入感）"""
    shots = data.get("shots", [])
    if not shots:
        return GateResult.fail("S007", "首镜头景别", "无镜头数据")
    first_size = shots[0].get("shot_size", "")
    closeup_sizes = {"特写", "近景", "closeup", "close_up", "medium_close"}
    if first_size not in closeup_sizes:
        return GateResult.warn("S007", "首镜头景别", f"首镜头为'{first_size}'，建议特写/近景",
                               detail="短视频首镜头用近景可增强代入感")
    return GateResult.pass_("S007", "首镜头景别", f"首镜头为'{first_size}'，符合短视频习惯")


def gate_storyboard_duration_sum(data: Dict[str, Any]) -> GateResult:
    """S008: 时长合计一致（各镜头时长合计与总时长误差≤0.5秒）"""
    shots = data.get("shots", [])
    total = data.get("total_duration", 0)
    if not shots or total <= 0:
        return GateResult.skip("S008", "时长合计", "无总时长数据")
    shot_sum = sum(s.get("duration", 0) for s in shots)
    diff = abs(shot_sum - total)
    if diff > 0.5:
        return GateResult.fail("S008", "时长合计", f"镜头合计{shot_sum:.1f}s与总时长{total:.1f}s差{diff:.1f}s",
                               detail="误差超过0.5秒阈值")
    return GateResult.pass_("S008", "时长合计", f"合计{shot_sum:.1f}s≈总时长{total:.1f}s（差{diff:.2f}s）")


def gate_storyboard_subtitle_nonempty(data: Dict[str, Any]) -> GateResult:
    """S009: 字幕非空（每个镜头应有字幕，空字幕镜头≤20%）"""
    shots = data.get("shots", [])
    if not shots:
        return GateResult.fail("S009", "字幕覆盖", "无镜头数据")
    empty_count = sum(1 for s in shots if not s.get("subtitle", "").strip())
    ratio = empty_count / len(shots)
    if ratio > 0.2:
        return GateResult.warn("S009", "字幕覆盖", f"{empty_count}个镜头无字幕（{ratio:.0%}）",
                               detail="建议空字幕镜头≤20%")
    return GateResult.pass_("S009", "字幕覆盖", f"字幕完整{len(shots)-empty_count}/{len(shots)}")


def gate_storyboard_first_shot_no_transition(data: Dict[str, Any]) -> GateResult:
    """S010: 首镜头转场（首镜头不应有入场转场，因为前面没有画面）"""
    shots = data.get("shots", [])
    if not shots:
        return GateResult.fail("S010", "首镜头转场", "无镜头数据")
    first_trans = shots[0].get("transition_in", "无")
    if first_trans not in ("无", "", "none", "cut"):
        return GateResult.warn("S010", "首镜头转场", f"首镜头入场转场为'{first_trans}'，建议为'无'",
                               detail="首镜头前面没有画面，入场转场无意义")
    return GateResult.pass_("S010", "首镜头转场", "首镜头无入场转场，正确")


# ──────────────────────────────────────────────
# 全局注册表实例
# ──────────────────────────────────────────────

_global_registry = GateRegistry()

# 注册剪辑质量门
_global_registry.register_many("edit", [
    gate_edit_total_duration,
    gate_edit_segment_count,
    gate_edit_transition_alignment,
    gate_edit_subtitle_coverage,
    gate_edit_aspect_ratio,
    gate_edit_frame_precision,
    gate_edit_black_frame,
])

# 注册分镜质量门
_global_registry.register_many("storyboard", [
    gate_storyboard_shot_duration,
    gate_storyboard_hook_first,
    gate_storyboard_beat_coverage,
    gate_storyboard_shot_size_diversity,
    gate_storyboard_camera_move_diversity,
    gate_storyboard_emotion_rhythm,
    gate_storyboard_first_shot_closeup,
    gate_storyboard_duration_sum,
    gate_storyboard_subtitle_nonempty,
    gate_storyboard_first_shot_no_transition,
])


def get_registry() -> GateRegistry:
    """获取全局质量门注册表"""
    return _global_registry


def validate(category: str, data: Dict[str, Any]) -> GateReport:
    """便捷函数：运行指定类别的质量门检查"""
    return _global_registry.run_all(category, data)


if __name__ == "__main__":
    print("=" * 60)
    print("质量门框架自测")
    print("=" * 60)

    # 测试剪辑质量门
    print("\n--- 剪辑质量门（正常数据）---")
    edit_data = {
        "total_duration": 60,
        "max_duration": 180,
        "segments": [
            {"duration": 10, "narration": "你好", "subtitle": "你好", "aspect_ratio": 9/16, "end": 10},
            {"duration": 20, "narration": "世界", "subtitle": "世界", "aspect_ratio": 9/16, "end": 30},
            {"duration": 30, "aspect_ratio": 9/16, "end": 60},
        ],
        "transitions": [{"start": 10}, {"start": 30}],
        "timestamps": [0, 10, 30, 60],
        "fps": 30,
        "canvas_ratio": 9/16,
    }
    report = validate("edit", edit_data)
    print(report.summary())

    # 测试分镜质量门
    print("\n--- 分镜质量门（正常数据）---")
    sb_data = {
        "shots": [
            {"duration": 5, "beats": [0, 1]},
            {"duration": 8, "beats": [2]},
            {"duration": 3, "beats": [3]},
        ],
        "beats": [0, 1, 2, 3],
        "hooks": [{"time": 1.5, "type": "question"}],
    }
    report2 = validate("storyboard", sb_data)
    print(report2.summary())

    # 测试击穿用例
    print("\n--- 击穿用例（应失败）---")
    bad_data = {"total_duration": 200, "segments": [], "timestamps": [0.033, 0.066]}
    report3 = validate("edit", bad_data)
    print(report3.summary())
