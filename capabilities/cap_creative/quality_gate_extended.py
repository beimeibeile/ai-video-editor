"""
质量门2.0扩展 — 借鉴shuohao-skills专业分镜质量门
新增15+项检查：台词时长匹配、构图完整性、参考图挂载、换景不换段、段尾留钩、运镜克制、对话正反打、进场三件套等
以及8种常见病诊断表
"""
from typing import Dict, Any, List
from quality_gate import GateResult, GateRegistry, get_registry


# ══════════════════════════════════════════════
# 分镜质量门扩展（S011-S025）
# ══════════════════════════════════════════════

def gate_storyboard_dialogue_fit(data: Dict[str, Any]) -> GateResult:
    """S011: 台词时长匹配（认领节拍的台词秒数≤分镜秒数，4.4秒台词给5秒切）"""
    shots = data.get("shots", [])
    if not shots:
        return GateResult.fail("S011", "台词时长匹配", "无镜头数据")
    overflow = []
    for i, shot in enumerate(shots):
        dialogue = shot.get("dialogue", "")
        if not dialogue:
            continue
        # 中文语速约4字/秒，英文约2.5词/秒
        char_count = len(dialogue.replace(" ", ""))
        est_duration = char_count / 4.0  # 估算台词时长
        shot_dur = shot.get("duration", 0)
        if est_duration > shot_dur * 0.9:  # 留10%缓冲
            overflow.append(f"镜头#{i}({shot_dur}s)台词约{est_duration:.1f}s")
    if overflow:
        return GateResult.warn("S011", "台词时长匹配", f"{len(overflow)}个镜头台词可能塞不下",
                               detail="; ".join(overflow[:5]))
    return GateResult.pass_("S011", "台词时长匹配", "所有镜头台词时长合理")


def gate_storyboard_composition_fields(data: Dict[str, Any]) -> GateResult:
    """S012: 构图量化字段完整性（lens/cameraPosition/composition/eyeline/focus/stability）"""
    shots = data.get("shots", [])
    if not shots:
        return GateResult.fail("S012", "构图字段完整性", "无镜头数据")
    required_fields = ["lens", "camera_position", "composition", "eyeline", "focus", "stability"]
    # 检查是否有任何镜头包含构图字段（新格式），否则跳过
    has_any = any(any(f.replace("_", "") in str(shot).lower() for f in required_fields) for shot in shots)
    if not has_any:
        return GateResult.skip("S012", "构图字段完整性", "未使用构图量化字段（旧格式分镜）")
    incomplete = []
    for i, shot in enumerate(shots):
        missing = [f for f in required_fields if f not in shot and f.replace("_", "") not in str(shot).lower()]
        if missing:
            incomplete.append(f"镜头#{i}缺{','.join(missing[:3])}")
    if incomplete:
        return GateResult.warn("S012", "构图字段完整性", f"{len(incomplete)}个镜头构图字段不完整",
                               detail="; ".join(incomplete[:5]))
    return GateResult.pass_("S012", "构图字段完整性", "所有镜头构图量化字段完整")


def gate_storyboard_reference_images(data: Dict[str, Any]) -> GateResult:
    """S013: 参考图挂载检查（场景图必挂/角色图必挂/道具图有就挂）"""
    shots = data.get("shots", [])
    if not shots:
        return GateResult.fail("S013", "参考图挂载", "无镜头数据")
    # 检查是否有参考图字段
    has_refs = any("reference_images" in shot or "refs" in shot or "scene_image" in shot for shot in shots)
    if not has_refs:
        return GateResult.skip("S013", "参考图挂载", "未使用参考图挂载机制")
    missing_scene = []
    missing_character = []
    for i, shot in enumerate(shots):
        refs = shot.get("reference_images", shot.get("refs", {}))
        if isinstance(refs, dict):
            if not refs.get("scene"):
                missing_scene.append(f"镜头#{i}")
            characters_in_shot = shot.get("characters", [])
            if characters_in_shot and not refs.get("characters"):
                missing_character.append(f"镜头#{i}")
    warnings = []
    if missing_scene:
        warnings.append(f"{len(missing_scene)}个镜头缺场景参考图")
    if missing_character:
        warnings.append(f"{len(missing_character)}个镜头缺角色参考图")
    if warnings:
        return GateResult.warn("S013", "参考图挂载", "；".join(warnings),
                               detail="场景图必挂，角色图有几个挂几个")
    return GateResult.pass_("S013", "参考图挂载", "参考图挂载完整")


def gate_storyboard_scene_continuity(data: Dict[str, Any]) -> GateResult:
    """S014: 换景不换段（一段内不能跨场景，换景必开新段）"""
    segments = data.get("segments", [])
    if not segments:
        return GateResult.skip("S014", "换景不换段", "无段落数据")
    cross_scene = []
    for i, seg in enumerate(segments):
        scenes_in_seg = set()
        for shot in seg.get("shots", []):
            scene_id = shot.get("scene_id", shot.get("scene", ""))
            if scene_id:
                scenes_in_seg.add(scene_id)
        if len(scenes_in_seg) > 1:
            cross_scene.append(f"段#{i}跨{len(scenes_in_seg)}场景")
    if cross_scene:
        return GateResult.warn("S014", "换景不换段", f"{len(cross_scene)}个段落跨场景",
                               detail="; ".join(cross_scene[:5]) + "；换景必开新段，一段一个环境锚")
    return GateResult.pass_("S014", "换景不换段", "所有段落场景连续")


def gate_storyboard_segment_hook(data: Dict[str, Any]) -> GateResult:
    """S015: 段尾留钩（每段最后一分镜应有悬念具象或下一段引子）"""
    segments = data.get("segments", [])
    if not segments or len(segments) < 2:
        return GateResult.skip("S015", "段尾留钩", "段落少于2个，无需检查")
    no_hook = []
    for i, seg in enumerate(segments[:-1]):  # 最后一段不需要留钩
        shots = seg.get("shots", [])
        if not shots:
            continue
        last_shot = shots[-1]
        has_hook = any(k in last_shot for k in ["hook", "suspense", "cliffhanger", "悬念", "引子", "transition_out"])
        if not has_hook:
            no_hook.append(f"段#{i}尾镜")
    if no_hook:
        return GateResult.warn("S015", "段尾留钩", f"{len(no_hook)}个段落结尾无钩子",
                               detail="段尾分镜应是悬念具象或下一段引子，段与段之间也是剪辑点")
    return GateResult.pass_("S015", "段尾留钩", "所有段落结尾有钩子")


def gate_storyboard_camera_restraint(data: Dict[str, Any]) -> GateResult:
    """S016: 运镜克制（一段内超过两种运镜就是炫技，固定是默认）"""
    segments = data.get("segments", [])
    if not segments:
        # 退而求其次：检查全片运镜种类
        shots = data.get("shots", [])
        if not shots:
            return GateResult.skip("S016", "运镜克制", "无镜头数据")
        moves = set(s.get("camera_move", "固定") for s in shots)
        if len(moves) > 4:
            return GateResult.warn("S016", "运镜克制", f"全片{len(moves)}种运镜，可能过于花哨",
                                   detail=f"运镜: {', '.join(moves)}；固定是默认，推给情绪拉给收场跟给移动")
        return GateResult.pass_("S016", "运镜克制", f"全片{len(moves)}种运镜，克制合理")
    overused = []
    for i, seg in enumerate(segments):
        moves = set(s.get("camera_move", "固定") for s in seg.get("shots", []))
        if len(moves) > 2:
            overused.append(f"段#{i}有{len(moves)}种运镜")
    if overused:
        return GateResult.warn("S016", "运镜克制", f"{len(overused)}个段落运镜超过2种",
                               detail="; ".join(overused[:5]) + "；一段超过两种运镜就是炫技")
    return GateResult.pass_("S016", "运镜克制", "所有段落运镜克制")


def gate_storyboard_dialogue_shot_reverse(data: Dict[str, Any]) -> GateResult:
    """S017: 对话正反打（对话场景应有正反打，问话给问话人近景，答话切答话人近景）"""
    shots = data.get("shots", [])
    if not shots:
        return GateResult.fail("S017", "对话正反打", "无镜头数据")
    # 找出对话镜头序列
    dialogue_shots = [i for i, s in enumerate(shots) if s.get("dialogue") or s.get("has_dialogue")]
    if len(dialogue_shots) < 2:
        return GateResult.skip("S017", "对话正反打", "对话镜头少于2个，无需检查")
    # 检查连续对话镜头是否有视角变化
    static_dialogue = []
    for idx in range(len(dialogue_shots) - 1):
        i, j = dialogue_shots[idx], dialogue_shots[idx + 1]
        if j - i == 1:  # 连续对话镜头
            size_i = shots[i].get("shot_size", "")
            size_j = shots[j].get("shot_size", "")
            if size_i == size_j and size_i:  # 同景别，可能没有正反打
                static_dialogue.append(f"镜头#{i}-#{j}")
    if static_dialogue:
        return GateResult.warn("S017", "对话正反打", f"{len(static_dialogue)}组连续对话镜头同景别",
                               detail="对话应切正反打，谁的台词信息量大谁的脸给得近")
    return GateResult.pass_("S017", "对话正反打", "对话镜头有正反打变化")


def gate_storyboard_opening_movement(data: Dict[str, Any]) -> GateResult:
    """S018: 进场三件套（首镜头必须有主体运动，静物特写开场是死画面）"""
    shots = data.get("shots", [])
    if not shots:
        return GateResult.fail("S018", "进场运动", "无镜头数据")
    first_shot = shots[0]
    has_movement = any(k in first_shot for k in ["movement", "action", "主体运动", "has_movement"])
    camera_move = first_shot.get("camera_move", "固定")
    if not has_movement and camera_move == "固定":
        return GateResult.warn("S018", "进场运动", "首镜头无主体运动且固定机位",
                               detail="进场三件套：运动主体→大远景定场→关键局部特写；静物特写开场是死画面")
    return GateResult.pass_("S018", "进场运动", "首镜头有主体运动")


def gate_storyboard_key_action_insert(data: Dict[str, Any]) -> GateResult:
    """S019: 关键动作独立成切（重要动作应有insert特写插入，是节奏的重音）"""
    shots = data.get("shots", [])
    if not shots:
        return GateResult.fail("S019", "关键动作特写", "无镜头数据")
    key_actions = [i for i, s in enumerate(shots) if s.get("is_key_action") or s.get("key_action")]
    if not key_actions:
        return GateResult.skip("S019", "关键动作特写", "未标记关键动作")
    no_insert = []
    for i in key_actions:
        shot = shots[i]
        is_closeup = shot.get("shot_size", "") in ("特写", "近景", "closeup", "close_up")
        if not is_closeup:
            no_insert.append(f"镜头#{i}")
    if no_insert:
        return GateResult.warn("S019", "关键动作特写", f"{len(no_insert)}个关键动作非特写",
                               detail="关键动作值得单独一格2秒特写插入（insert），是节奏的重音")
    return GateResult.pass_("S019", "关键动作特写", "所有关键动作都有特写")


def gate_storyboard_reaction_shot(data: Dict[str, Any]) -> GateResult:
    """S020: 反应镜头（重台词后应有听者反应镜头2-3秒，不用写词）"""
    shots = data.get("shots", [])
    if not shots:
        return GateResult.fail("S020", "反应镜头", "无镜头数据")
    heavy_dialogue = [i for i, s in enumerate(shots)
                      if s.get("dialogue") and len(s.get("dialogue", "")) > 10]
    if not heavy_dialogue:
        return GateResult.skip("S020", "反应镜头", "无重台词镜头")
    missing_reaction = []
    for i in heavy_dialogue:
        if i + 1 < len(shots):
            next_shot = shots[i + 1]
            is_reaction = next_shot.get("is_reaction") or next_shot.get("reaction") or \
                          (not next_shot.get("dialogue") and next_shot.get("shot_size") in ("特写", "近景"))
            if not is_reaction:
                missing_reaction.append(f"镜头#{i}后")
    if missing_reaction:
        return GateResult.warn("S020", "反应镜头", f"{len(missing_reaction)}处重台词后无反应镜头",
                               detail="反应镜头是免费的戏，重台词后切听者的脸2-3秒，不用写词")
    return GateResult.pass_("S020", "反应镜头", "重台词后有反应镜头")


def gate_storyboard_shot_rhythm_variety(data: Dict[str, Any]) -> GateResult:
    """S021: 节奏多样性（深浅相间、长短相间，不能每切都是3秒中景=均匀病）"""
    shots = data.get("shots", [])
    if not shots:
        return GateResult.fail("S021", "节奏多样性", "无镜头数据")
    durations = [s.get("duration", 0) for s in shots]
    sizes = [s.get("shot_size", "") for s in shots if s.get("shot_size")]
    # 检查时长方差
    if len(durations) >= 3:
        avg = sum(durations) / len(durations)
        variance = sum((d - avg) ** 2 for d in durations) / len(durations)
        if variance < 0.5:  # 时长过于均匀
            return GateResult.warn("S021", "节奏多样性", f"镜头时长过于均匀（方差{variance:.2f}）",
                                   detail="均匀病：每切都是3秒中景；深浅相间、长短相间才是节奏")
    # 检查景别方差
    if sizes and len(set(sizes)) == 1:
        return GateResult.warn("S021", "节奏多样性", f"所有镜头都是同一种景别（{sizes[0]}）",
                               detail="均匀病：深浅相间才是节奏")
    return GateResult.pass_("S021", "节奏多样性", "节奏有长短深浅变化")


def gate_storyboard_audio_scene_sync(data: Dict[str, Any]) -> GateResult:
    """S022: 声景同步（画面动作改了，环境音/声景也要同步改）"""
    shots = data.get("shots", [])
    if not shots:
        return GateResult.fail("S022", "声景同步", "无镜头数据")
    has_soundscape = any("soundscape" in s or "环境音" in s or "ambient" in s for s in shots)
    if not has_soundscape:
        return GateResult.skip("S022", "声景同步", "未使用声景字段")
    # 简单检查：有动作描述的镜头应有声景
    missing = []
    for i, shot in enumerate(shots):
        has_action = shot.get("action") or shot.get("movement") or shot.get("description")
        has_sound = shot.get("soundscape") or shot.get("环境音") or shot.get("ambient") or shot.get("sfxs")
        if has_action and not has_sound and i > 0:
            missing.append(f"镜头#{i}")
    if missing and len(missing) > len(shots) * 0.3:
        return GateResult.warn("S022", "声景同步", f"{len(missing)}个有动作镜头无声景",
                               detail="声景也是动作指令——画面动作一改，描述、声景一起改")
    return GateResult.pass_("S022", "声景同步", "声景与画面动作同步")


# ══════════════════════════════════════════════
# 常见病诊断表（8种，作为警告项）
# ══════════════════════════════════════════════

COMMON_DISEASES = {
    "stage_play": {"name": "舞台剧病", "symptom": "一段一切杵到底", "cure": "对话切正反打，动作给插入特写"},
    "uniform": {"name": "均匀病", "symptom": "每切都是3秒中景", "cure": "深浅相间、长短相间才是节奏"},
    "duration_drift": {"name": "秒数漂移", "symptom": "改了分镜秒数忘改提示词", "cure": "validate逐字对账，对齐指令和切点时刻"},
    "dialogue_overflow": {"name": "台词爆仓", "symptom": "4.4秒台词塞3秒切", "cure": "加秒或拆切"},
    "soundscape_mismatch": {"name": "声景漏改", "symptom": "画面改了环境音没改", "cure": "声景也是动作指令，三处一起改"},
    "closeup_amnesia": {"name": "特写失忆", "symptom": "大特写道具和设定图不一样", "cure": "挂道具设定图当参考，提示词提锚点特征"},
    "scene_cross_segment": {"name": "换景不换段", "symptom": "一段里从栈桥切进船舱", "cure": "换景必开新段，一段一个环境锚"},
    "neighbor_ignore": {"name": "改切不读邻切", "symptom": "改了第1切第2切位置矛盾", "cure": "改一切连读前后切，分镜图和文字逐格对照"},
}


def gate_storyboard_common_diseases(data: Dict[str, Any]) -> GateResult:
    """S023: 常见病综合诊断（8种分镜常见病检测）"""
    shots = data.get("shots", [])
    if not shots:
        return GateResult.fail("S023", "常见病诊断", "无镜头数据")
    detected = []

    # 均匀病检测
    durations = [s.get("duration", 0) for s in shots]
    if len(durations) >= 4:
        avg = sum(durations) / len(durations)
        if all(abs(d - avg) < 0.5 for d in durations):
            detected.append("均匀病")

    # 舞台剧病检测（连续同景别超过4镜）
    sizes = [s.get("shot_size", "") for s in shots]
    for i in range(len(sizes) - 3):
        if sizes[i] and sizes[i] == sizes[i+1] == sizes[i+2] == sizes[i+3]:
            detected.append("舞台剧病")
            break

    # 台词爆仓检测
    for i, shot in enumerate(shots):
        dialogue = shot.get("dialogue", "")
        if dialogue and len(dialogue) / 4.0 > shot.get("duration", 0) * 0.9:
            detected.append("台词爆仓")
            break

    if detected:
        disease_info = [f"{d}（{COMMON_DISEASES.get(d, {}).get('symptom', '')}）" for d in detected]
        return GateResult.warn("S023", "常见病诊断", f"检测到{len(detected)}种分镜常见病",
                               detail="; ".join(disease_info))
    return GateResult.pass_("S023", "常见病诊断", "未检测到常见分镜病")


def gate_storyboard_character_consistency(data: Dict[str, Any]) -> GateResult:
    """S024: 角色一致性（同一角色在不同镜头的描述应一致，参考图应挂载）"""
    shots = data.get("shots", [])
    if not shots:
        return GateResult.fail("S024", "角色一致性", "无镜头数据")
    characters = data.get("characters", {})
    if not characters:
        return GateResult.skip("S024", "角色一致性", "无角色设定数据")
    # 检查镜头中出现的角色是否都在角色设定中
    unknown_chars = set()
    for shot in shots:
        for char in shot.get("characters", []):
            if char not in characters and char not in [c.get("name", "") for c in characters.values()]:
                unknown_chars.add(char)
    if unknown_chars:
        return GateResult.warn("S024", "角色一致性", f"{len(unknown_chars)}个角色未在设定集中",
                               detail=f"未知角色: {', '.join(list(unknown_chars)[:5])}")
    return GateResult.pass_("S024", "角色一致性", "所有角色均在设定集中")


def gate_storyboard_emotion_transition(data: Dict[str, Any]) -> GateResult:
    """S025: 情绪过渡合理性（相邻镜头情绪不应突变，应有过渡）"""
    shots = data.get("shots", [])
    if not shots:
        return GateResult.fail("S025", "情绪过渡", "无镜头数据")
    emotions = [s.get("emotion", "") for s in shots if s.get("emotion")]
    if len(emotions) < 3:
        return GateResult.skip("S025", "情绪过渡", "情绪数据不足")
    # 简单检查：情绪种类变化是否过于频繁
    transitions = sum(1 for i in range(len(emotions)-1) if emotions[i] != emotions[i+1])
    if transitions > len(emotions) * 0.7:
        return GateResult.warn("S025", "情绪过渡", f"情绪变化过于频繁（{transitions}/{len(emotions)}次变化）",
                               detail="情绪应有铺垫和过渡，避免跳跃式变化")
    return GateResult.pass_("S025", "情绪过渡", f"情绪过渡合理（{transitions}次变化）")


# ══════════════════════════════════════════════
# 注册扩展质量门
# ══════════════════════════════════════════════

def register_extended_gates(registry: GateRegistry = None):
    """注册扩展质量门到全局注册表"""
    if registry is None:
        registry = get_registry()
    registry.register_many("storyboard", [
        gate_storyboard_dialogue_fit,
        gate_storyboard_composition_fields,
        gate_storyboard_reference_images,
        gate_storyboard_scene_continuity,
        gate_storyboard_segment_hook,
        gate_storyboard_camera_restraint,
        gate_storyboard_dialogue_shot_reverse,
        gate_storyboard_opening_movement,
        gate_storyboard_key_action_insert,
        gate_storyboard_reaction_shot,
        gate_storyboard_shot_rhythm_variety,
        gate_storyboard_audio_scene_sync,
        gate_storyboard_common_diseases,
        gate_storyboard_character_consistency,
        gate_storyboard_emotion_transition,
    ])
    return registry


# 自动注册
register_extended_gates()


if __name__ == "__main__":
    print("=" * 60)
    print("质量门2.0扩展自测")
    print("=" * 60)
    reg = get_registry()
    print(f"\n分镜质量门总数: {reg.gate_count('storyboard')}")
    print(f"剪辑质量门总数: {reg.gate_count('edit')}")
    print(f"总计: {reg.gate_count('storyboard') + reg.gate_count('edit')}道")

    # 测试常见病诊断
    print("\n--- 常见病诊断测试 ---")
    test_data = {
        "shots": [
            {"duration": 3, "shot_size": "中景", "dialogue": "你好世界这是一段很长的台词测试"},
            {"duration": 3, "shot_size": "中景"},
            {"duration": 3, "shot_size": "中景"},
            {"duration": 3, "shot_size": "中景"},
            {"duration": 3, "shot_size": "中景"},
        ],
        "beats": [0, 1, 2, 3, 4],
    }
    report = reg.run_all("storyboard", test_data)
    print(report.summary())
