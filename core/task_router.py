"""
任务路由器 — 模式识别 + 能力调度
根据用户输入判断模式，调度对应能力模块
"""
import re

# 模式触发词
MODE_TRIGGERS = {
    "mode_a": [
        "制作视频", "给图剪视频", "用剪映剪辑", "百万剪辑师",
        "卡点变装", "氛围感短片", "旗袍视频", "剪辑视频"
    ],
    "quick_cut": [
        "快剪视频", "快速剪辑", "直接剪", "不用确认", "快剪"
    ],
    "mode_b": [
        "仿制模板", "复刻视频", "照着这个做", "模仿这个视频",
        "模板替换", "剪映模板", "仿制"
    ],
    "material_creator": [
        "制作素材", "生成轮廓图", "生成纹理", "生成占位图",
        "做背景图", "发光轮廓素材"
    ],
    "comfy_runner": [
        "超分", "图片超分", "批量超分", "提升画质", "画质增强",
        "ComfyUI", "跑ComfyUI", "用ComfyUI", "comfyui",
        "人脸统一", "批量抠图", "图生视频", "风格迁移",
    ],
}

def detect_mode(user_input):
    """
    识别用户意图，返回模式名称
    
    Returns:
        mode: mode_a / quick_cut / mode_b / material_creator / unknown
    """
    text = user_input.lower()
    
    # 优先级：极速模式 > 仿制模板 > ComfyUI > 制作素材 > 模式A
    for keyword in MODE_TRIGGERS["quick_cut"]:
        if keyword in user_input:
            return "quick_cut"
    
    for keyword in MODE_TRIGGERS["mode_b"]:
        if keyword in user_input:
            return "mode_b"
    
    for keyword in MODE_TRIGGERS["comfy_runner"]:
        if keyword in user_input:
            return "comfy_runner"
    
    for keyword in MODE_TRIGGERS["material_creator"]:
        if keyword in user_input:
            return "material_creator"
    
    for keyword in MODE_TRIGGERS["mode_a"]:
        if keyword in user_input:
            return "mode_a"
    
    # 模糊匹配：上传了素材+视频相关词汇
    video_words = ["视频", "剪辑", "剪映", "成片", "短片"]
    if any(w in user_input for w in video_words):
        return "mode_a"
    
    return "unknown"


def get_capabilities_for_mode(mode):
    """
    返回该模式需要调用的能力模块列表
    
    Returns:
        list of capability module names
    """
    mapping = {
        "mode_a": [
            "cap_material_creator",   # 按需生成素材
            "cap_subtitle_designer",  # 字幕设计
            "cap_keyframe_engine",    # 关键帧
            "cap_audio_designer",     # 音频
        ],
        "quick_cut": [
            "cap_material_creator",
            "cap_subtitle_designer",
            "cap_keyframe_engine",
            "cap_audio_designer",
        ],
        "mode_b": [
            "cap_video_analyzer",     # 视频分析
            "cap_material_creator",   # 占位素材
            "cap_effect_library",     # 特效库
        ],
        "material_creator": [
            "cap_material_creator",
        ],
        "comfy_runner": [
            "cap_comfyui_runner",
        ],
    }
    return mapping.get(mode, [])


def route(user_input, has_attachments=False):
    """
    主路由函数
    
    Returns:
        dict: {mode, capabilities, need_confirmation, description}
    """
    mode = detect_mode(user_input)
    
    if mode == "unknown":
        if has_attachments:
            # 有素材但无明确触发词，默认模式A
            mode = "mode_a"
        else:
            return {
                "mode": "unknown",
                "capabilities": [],
                "need_confirmation": True,
                "description": "未识别到明确意图，请说明要做什么（制作视频/快剪视频/仿制模板/制作素材）"
            }
    
    descriptions = {
        "mode_a": "模式A：制作视频（需方案确认）",
        "quick_cut": "⚡ 极速模式：快剪视频（免确认，直接开工）",
        "mode_b": "模式B：仿制模板（需方案确认）",
        "material_creator": "制作素材（直接生成）",
        "comfy_runner": "ComfyUI算力任务（超分/人脸统一/抠图/图生视频）",
    }
    
    confirmations = {
        "mode_a": True,
        "quick_cut": False,
        "mode_b": True,
        "material_creator": False,
        "comfy_runner": False,
    }
    
    return {
        "mode": mode,
        "capabilities": get_capabilities_for_mode(mode),
        "need_confirmation": confirmations.get(mode, True),
        "description": descriptions.get(mode, ""),
    }
