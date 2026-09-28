"""
知识管理器 — 自学习核心
任务开始前检索已知问题/验证模式，任务结束后沉淀经验
"""
import os

KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "..", "knowledge")
LESSONS_DIR = os.path.join(KNOWLEDGE_DIR, "lessons")

def check_known_issues(keyword=None):
    """
    检索已知问题
    
    Args:
        keyword: 关键词过滤，None则返回全部
    
    Returns:
        list of issue strings
    """
    path = os.path.join(LESSONS_DIR, "known_issues.md")
    if not os.path.exists(path):
        return []
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if keyword:
        # 简单关键词匹配
        lines = content.split('\n')
        matches = []
        for i, line in enumerate(lines):
            if keyword.lower() in line.lower():
                # 返回上下文（前后3行）
                start = max(0, i-2)
                end = min(len(lines), i+3)
                matches.append('\n'.join(lines[start:end]))
        return matches
    return [content]


def check_verified_patterns(keyword=None):
    """检索验证过的模式"""
    path = os.path.join(LESSONS_DIR, "verified_patterns.md")
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if keyword:
        lines = content.split('\n')
        matches = []
        for i, line in enumerate(lines):
            if keyword.lower() in line.lower():
                start = max(0, i-2)
                end = min(len(lines), i+5)
                matches.append('\n'.join(lines[start:end]))
        return matches
    return [content]


def check_reusable_assets(asset_type=None):
    """
    检查可复用素材库
    
    Args:
        asset_type: placeholders / textures / outlines / backgrounds
    
    Returns:
        dict of {filename: fullpath}
    """
    assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "reusable")
    result = {}
    
    if asset_type:
        types = [asset_type]
    else:
        types = ["placeholders", "textures", "outlines", "backgrounds"]
    
    for t in types:
        tdir = os.path.join(assets_dir, t)
        if os.path.exists(tdir):
            for f in os.listdir(tdir):
                if f.endswith(('.png', '.jpg', '.jpeg')):
                    result[f] = os.path.join(tdir, f)
    return result


def log_experience(category, title, content, status="verified"):
    """
    记录经验到知识库
    
    Args:
        category: verified_patterns / known_issues / decision_log
        title: 标题
        content: 内容（markdown格式）
        status: verified / pending / rejected
    """
    import time
    path = os.path.join(LESSONS_DIR, f"{category}.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    entry = f"\n## {time.strftime('%Y-%m-%d')} {title} [{status}]\n\n{content}\n"
    
    with open(path, 'a', encoding='utf-8') as f:
        f.write(entry)
    
    return True


def pre_task_check(task_description):
    """
    任务开始前的知识检索
    返回相关的已知问题和验证模式
    """
    issues = []
    patterns = []
    
    # 关键词提取
    keywords = ["混合模式", "blend", "转场", "关键帧", "字幕", "BGM", "5.9", "特效", "占位图"]
    for kw in keywords:
        if kw in task_description:
            issues.extend(check_known_issues(kw))
            patterns.extend(check_verified_patterns(kw))
    
    return {
        "known_issues": issues[:5],  # 最多返回5条
        "verified_patterns": patterns[:3],
    }
