"""
通用工具函数
"""
import os, time, json, shutil

def ensure_dir(path):
    """确保目录存在"""
    os.makedirs(path, exist_ok=True)
    return path

def timestamp():
    """当前时间戳字符串"""
    return time.strftime("%Y%m%d_%H%M%S")

def safe_name(name):
    """生成安全的文件名"""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)

def read_json(path):
    """读取JSON文件"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json(path, data):
    """写入JSON文件"""
    ensure_dir(os.path.dirname(path))
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def copy_to_59_drafts(project_name, source_root=None):
    """
    将工程从C盘11.6目录复制到D盘5.9草稿目录
    
    Args:
        project_name: 工程名称
        source_root: 源根目录，默认11.6草稿目录
    """
    if source_root is None:
        source_root = r"C:\Users\Administrator\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft"
    target_root = r"D:\JianyingProDrafts\JianyingPro Drafts"
    
    src = os.path.join(source_root, project_name)
    dst = os.path.join(target_root, project_name)
    
    if not os.path.exists(src):
        return False, f"源工程不存在: {src}"
    
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return True, f"已复制到: {dst}"

def log_lesson(category, title, content, status="verified"):
    """
    记录经验到知识库
    
    Args:
        category: verified_patterns / known_issues / decision_log
        title: 标题
        content: 内容
        status: verified / pending / rejected
    """
    lesson_dir = os.path.join(os.path.dirname(__file__), "..", "knowledge", "lessons")
    ensure_dir(lesson_dir)
    
    log_file = os.path.join(lesson_dir, f"{category}.md")
    entry = f"\n## {time.strftime('%Y-%m-%d')} {title} [{status}]\n{content}\n"
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(entry)
    
    return True
