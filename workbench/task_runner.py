"""
导演工作台 - 任务执行器
检测 workbench/tasks/ 目录下的 task.json，自动执行剪辑任务

使用方法：
1. 用户在工作台(index.html)配置参数，生成task.json
2. 将task.json放入 tasks/ 目录
3. 运行本脚本检测并执行
4. 执行结果写回 task_result.json
"""
import os
import sys
import json
import time
import glob
from datetime import datetime

# 路径配置
SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_DIR = os.path.join(SKILL_ROOT, "workbench", "tasks")
os.makedirs(TASKS_DIR, exist_ok=True)

# 添加脚本路径
sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))
sys.path.insert(0, os.path.join(SKILL_ROOT, "capabilities", "cap_e2e_pipeline"))

# jianying-editor路径
JY_SKILL = r"C:\Users\Administrator\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\jianying-editor"
sys.path.insert(0, os.path.join(JY_SKILL, "scripts"))


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")


def execute_task(task_path):
    """执行单个任务"""
    try:
        with open(task_path, "r", encoding="utf-8") as f:
            task = json.load(f)

        task_id = task.get("task_id", "unknown")
        config = task.get("config", {})
        log(f"开始执行任务: {task_id}")

        # 更新状态
        task["status"] = "running"
        task["started_at"] = datetime.now().isoformat()
        with open(task_path, "w", encoding="utf-8") as f:
            json.dump(task, f, ensure_ascii=False, indent=2)

        # 执行剪辑
        result = run_editing(config, task.get("materials", []))

        # 写回结果
        task["status"] = "completed"
        task["completed_at"] = datetime.now().isoformat()
        task["result"] = result
        with open(task_path.replace(".json", "_result.json"), "w", encoding="utf-8") as f:
            json.dump(task, f, ensure_ascii=False, indent=2)

        log(f"任务完成: {task_id} -> {result.get('project_name', '')}")
        return True

    except Exception as e:
        log(f"任务执行失败: {e}", "ERROR")
        task["status"] = "failed"
        task["error"] = str(e)
        with open(task_path, "w", encoding="utf-8") as f:
            json.dump(task, f, ensure_ascii=False, indent=2)
        return False


def run_editing(config, materials):
    """执行剪辑任务（调用pipeline或特效库）"""
    from jy_wrapper import JyProject
    import pyJianYingDraft as draft

    project_name = config.get("project_name", "工作台任务")
    width = config.get("width", 1080)
    height = config.get("height", 1920)
    intro_style = config.get("intro_style", "none")

    log(f"创建工程: {project_name} ({width}x{height})")
    project = JyProject(project_name, width=width, height=height, overwrite=True)

    # 1. 添加片头
    intro_offset = 0.0
    if intro_style != "none":
        try:
            from intro_builder import add_intro_to_project
            intro_offset = add_intro_to_project(
                project,
                template=intro_style,
                title=config.get("main_title", "精彩开始"),
                subtitle=config.get("sub_title"),
                start_time=0.0,
                width=width,
                height=height,
                output_dir=os.path.join(TASKS_DIR, "assets"),
            )
            log(f"片头已添加: {intro_style} ({intro_offset}s)")
        except Exception as e:
            log(f"片头添加失败: {e}", "WARN")

    # 2. 添加素材
    current_time = intro_offset
    segments = []
    for mat in materials:
        # 素材路径需要用户提供绝对路径，这里只做框架
        log(f"素材: {mat} (需提供绝对路径)")

    # 3. 转场
    transition = config.get("transition_style", "none")
    if transition != "none" and len(segments) > 1:
        for i in range(1, len(segments)):
            try:
                project.add_transition_simple(transition, video_segment=segments[i])
            except Exception as e:
                log(f"转场失败: {e}", "WARN")

    project.save()
    return {"project_name": project_name, "intro_duration": intro_offset}


def watch_and_execute(interval=5):
    """轮询检测新任务"""
    log(f"任务执行器启动，监控目录: {TASKS_DIR}")
    log(f"检测间隔: {interval}秒")

    processed = set()
    while True:
        tasks = glob.glob(os.path.join(TASKS_DIR, "task_*.json"))
        for task_path in tasks:
            if task_path in processed:
                continue
            if "_result" in task_path:
                continue
            processed.add(task_path)
            execute_task(task_path)

        time.sleep(interval)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="导演工作台任务执行器")
    parser.add_argument("--once", action="store_true", help="只执行一次，不轮询")
    parser.add_argument("--task", type=str, help="执行指定任务文件")
    parser.add_argument("--interval", type=int, default=5, help="轮询间隔秒数")
    args = parser.parse_args()

    if args.task:
        execute_task(args.task)
    elif args.once:
        tasks = glob.glob(os.path.join(TASKS_DIR, "task_*.json"))
        for t in tasks:
            if "_result" not in t:
                execute_task(t)
    else:
        watch_and_execute(args.interval)
