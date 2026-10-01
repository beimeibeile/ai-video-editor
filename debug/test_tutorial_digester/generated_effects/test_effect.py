"""
这是一个测试教程
基于教程《测试教程》封装

制作手法：
1. 第一步
2. 第二步
"""
import os
import sys
from typing import Dict, Any, Optional

skill_root = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\jianying-editor"
sys.path.insert(0, os.path.join(skill_root, "scripts"))
from jy_wrapper import JyProject
import pyJianYingDraft as draft


def create_test_effect(
    project_name: str,
    text: str = "示例文字",
    duration: float = 3.0,
    width: int = 1080,
    height: int = 1920,
    **kwargs
) -> Dict[str, Any]:
    """
    创建test_effect特效工程

    Args:
        project_name: 工程名
        text: 文字内容
        duration: 时长（秒）
        width/height: 画布尺寸

    Returns:
        工程信息字典
    """
    print(f"\n[1/3] 创建工程: {project_name}")
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    print(f"[2/3] 添加文字: {text}")
    seg = project.add_text_simple(
        text=text,
        start_time="0s",
        duration=f"{duration}s",
        track_name="Text",
    )

    print(f"[3/3] 保存工程")
    result = project.save()

    return {
        "status": "success",
        "project_name": project_name,
        "draft_path": result.get("draft_path", ""),
    }


if __name__ == "__main__":
    create_test_effect("测试", text="测试文字")
