"""
四姊妹项目同步管理器
确保 ai-video-editor / anysearch-skill / comfyui-controls-skill / blender-controls-skill
四个项目的版本、依赖、API约定保持同步

功能：
1. check() - 检查四项目同步状态（git commit/分支/未提交修改/版本号）
2. sync_version() - 同步版本号到四个项目
3. batch_commit() - 批量提交四个项目
4. batch_push() - 批量推送四个项目
5. report() - 生成同步状态报告（HTML/文本）

使用方法：
    python sync_manager.py check
    python sync_manager.py sync_version 1.2.0
    python sync_manager.py batch_commit "更新说明"
    python sync_manager.py batch_push
    python sync_manager.py report
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# 四姊妹项目路径（DoubaoWork）
BASE_DIR = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills"

PROJECTS = {
    "ai-video-editor": {
        "path": os.path.join(BASE_DIR, "ai-video-editor"),
        "role": "船（指挥中枢）",
        "repo": "https://github.com/beimeibeile/ai-video-editor",
    },
    "anysearch-skill": {
        "path": os.path.join(BASE_DIR, "anysearch-skill"),
        "role": "雷达（情报搜索）",
        "repo": "https://github.com/beimeibeile/anysearch-skill",
    },
    "comfyui-controls-skill": {
        "path": os.path.join(BASE_DIR, "comfyui-controls-skill"),
        "role": "战机（算力）",
        "repo": "https://github.com/beimeibeile/Comfyui-controls-skill",
    },
    "blender-controls-skill": {
        "path": os.path.join(BASE_DIR, "blender-controls-skill"),
        "role": "导弹（3D特效）",
        "repo": "https://github.com/beimeibeile/Blender-controls-skill",
    },
}

# 共享配置文件（需要同步的文件）
SHARED_FILES = [
    "VERSION",
    "requirements.txt",
]


def run_git(path: str, args: List[str]) -> Tuple[str, str, int]:
    """在指定目录运行git命令"""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=path,
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), -1


def get_git_info(path: str) -> Dict:
    """获取项目的git状态信息"""
    info = {
        "exists": os.path.exists(os.path.join(path, ".git")),
        "branch": "",
        "commit": "",
        "commit_msg": "",
        "ahead": 0,
        "behind": 0,
        "modified": [],
        "untracked": [],
        "last_commit_time": "",
    }

    if not info["exists"]:
        return info

    # 分支
    out, _, _ = run_git(path, ["rev-parse", "--abbrev-ref", "HEAD"])
    info["branch"] = out

    # commit
    out, _, _ = run_git(path, ["rev-parse", "HEAD"])
    info["commit"] = out[:7] if out else ""

    # commit message
    out, _, _ = run_git(path, ["log", "-1", "--pretty=%s"])
    info["commit_msg"] = out

    # 最后提交时间
    out, _, _ = run_git(path, ["log", "-1", "--pretty=%ci"])
    info["last_commit_time"] = out

    # 未提交修改
    out, _, _ = run_git(path, ["status", "--porcelain"])
    if out:
        for line in out.split("\n"):
            if line.strip():
                status = line[:2].strip()
                file = line[3:].strip()
                if status == "??":
                    info["untracked"].append(file)
                else:
                    info["modified"].append(f"{status} {file}")

    # 远程同步状态
    out, _, _ = run_git(path, ["rev-list", "--left-right", "--count", "HEAD...@{u}"])
    if out and "\t" in out:
        parts = out.split("\t")
        info["ahead"] = int(parts[0])
        info["behind"] = int(parts[1])

    return info


def get_version(path: str) -> str:
    """读取项目版本号"""
    version_file = os.path.join(path, "VERSION")
    if os.path.exists(version_file):
        with open(version_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    # 从SKILL.md读取
    skill_md = os.path.join(path, "SKILL.md")
    if os.path.exists(skill_md):
        with open(skill_md, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("version:"):
                    return line.split(":")[1].strip()
    return "unknown"


def check_sync() -> Dict:
    """检查四项目同步状态"""
    print("=" * 70)
    print("四姊妹项目同步状态检查")
    print("=" * 70)

    results = {}
    versions = {}
    commits = {}
    all_clean = True

    for name, cfg in PROJECTS.items():
        print(f"\n[{name}] {cfg['role']}")
        info = get_git_info(cfg["path"])
        version = get_version(cfg["path"])
        results[name] = {**info, "version": version, "role": cfg["role"]}
        versions[name] = version
        commits[name] = info["commit"]

        print(f"  路径: {cfg['path']}")
        print(f"  版本: {version}")
        print(f"  分支: {info['branch']}")
        print(f"  commit: {info['commit']} - {info['commit_msg'][:40]}")
        print(f"  最后提交: {info['last_commit_time']}")

        if info["ahead"] > 0:
            print(f"  ⚠️  领先远程 {info['ahead']} 个提交（需push）")
            all_clean = False
        if info["behind"] > 0:
            print(f"  ⚠️  落后远程 {info['behind']} 个提交（需pull）")
            all_clean = False
        if info["modified"]:
            print(f"  ⚠️  未提交修改 ({len(info['modified'])}个):")
            for m in info["modified"][:5]:
                print(f"      {m}")
            if len(info["modified"]) > 5:
                print(f"      ... 还有{len(info['modified'])-5}个")
            all_clean = False
        if info["untracked"]:
            print(f"  ⚠️  未跟踪文件 ({len(info['untracked'])}个):")
            for u in info["untracked"][:5]:
                print(f"      {u}")
            all_clean = False
        if not info["modified"] and not info["untracked"] and info["ahead"] == 0:
            print(f"  ✅ 工作区干净")

    # 版本一致性检查
    print("\n" + "=" * 70)
    print("版本一致性:")
    unique_versions = set(versions.values())
    if len(unique_versions) == 1:
        print(f"  ✅ 所有项目版本一致: {list(unique_versions)[0]}")
    else:
        print(f"  ❌ 版本不一致:")
        for name, ver in versions.items():
            print(f"      {name}: {ver}")
        all_clean = False

    # 分支一致性检查
    branches = {name: info["branch"] for name, info in results.items()}
    unique_branches = set(branches.values())
    if len(unique_branches) == 1:
        print(f"  ✅ 所有项目分支一致: {list(unique_branches)[0]}")
    else:
        print(f"  ⚠️  分支不一致:")
        for name, br in branches.items():
            print(f"      {name}: {br}")

    print("\n" + "=" * 70)
    if all_clean:
        print("✅ 四项目全部同步，工作区干净")
    else:
        print("⚠️  存在不同步项，详见上方")
    print("=" * 70)

    return {
        "projects": results,
        "versions": versions,
        "all_clean": all_clean,
        "check_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def sync_version(version: str) -> bool:
    """同步版本号到四个项目"""
    print(f"\n同步版本号到 {version}")
    success = True

    for name, cfg in PROJECTS.items():
        version_file = os.path.join(cfg["path"], "VERSION")
        try:
            with open(version_file, "w", encoding="utf-8") as f:
                f.write(version + "\n")
            print(f"  ✅ {name}: VERSION -> {version}")
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            success = False

        # 同步更新SKILL.md中的version
        skill_md = os.path.join(cfg["path"], "SKILL.md")
        if os.path.exists(skill_md):
            try:
                with open(skill_md, "r", encoding="utf-8") as f:
                    content = f.read()
                import re
                content = re.sub(r"^version:.*$", f"version: {version}", content, flags=re.MULTILINE)
                with open(skill_md, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"  ✅ {name}: SKILL.md version -> {version}")
            except Exception as e:
                print(f"  ⚠️  {name}: SKILL.md更新失败: {e}")

    return success


def batch_commit(message: str) -> Dict:
    """批量提交四个项目"""
    print(f"\n批量提交: {message}")
    results = {}

    for name, cfg in PROJECTS.items():
        print(f"\n[{name}]")
        # add all
        out, err, code = run_git(cfg["path"], ["add", "-A"])
        if code != 0:
            print(f"  ❌ add失败: {err}")
            results[name] = "add_failed"
            continue

        # 检查是否有变更
        out, _, _ = run_git(cfg["path"], ["status", "--porcelain"])
        if not out:
            print(f"  ⏭️  无变更，跳过")
            results[name] = "no_changes"
            continue

        # commit
        out, err, code = run_git(cfg["path"], ["commit", "-m", message])
        if code == 0:
            # 获取新commit
            commit_out, _, _ = run_git(cfg["path"], ["rev-parse", "--short", "HEAD"])
            print(f"  ✅ 提交成功: {commit_out}")
            results[name] = f"committed:{commit_out}"
        else:
            print(f"  ❌ 提交失败: {err[:100]}")
            results[name] = "commit_failed"

    return results


def batch_push() -> Dict:
    """批量推送四个项目"""
    print("\n批量推送到远程")
    results = {}

    for name, cfg in PROJECTS.items():
        print(f"\n[{name}]")
        out, err, code = run_git(cfg["path"], ["push", "origin", "HEAD"])
        if code == 0:
            print(f"  ✅ 推送成功")
            results[name] = "pushed"
        else:
            # 检查是否是"Everything up-to-date"
            if "up-to-date" in err or "up-to-date" in out:
                print(f"  ⏭️  已是最新")
                results[name] = "up_to_date"
            else:
                print(f"  ❌ 推送失败: {err[:150]}")
                results[name] = "push_failed"

    return results


def generate_report(output_path: str = None) -> str:
    """生成HTML同步状态报告"""
    data = check_sync()

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>四姊妹项目同步报告</title>
<style>
body {{ font-family: -apple-system, sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; }}
h1 {{ color: #58a6ff; }}
.card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin-bottom: 12px; }}
.card h2 {{ font-size: 15px; color: #58a6ff; margin-bottom: 8px; }}
.status-ok {{ color: #3fb950; }}
.status-warn {{ color: #d29922; }}
.status-err {{ color: #f85149; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #21262d; }}
th {{ color: #8b949e; }}
code {{ background: #21262d; padding: 2px 6px; border-radius: 3px; font-size: 12px; }}
</style>
</head>
<body>
<h1>航空母舰战斗群 - 同步状态报告</h1>
<p>检查时间: {data['check_time']}</p>
<p>总体状态: {'<span class="status-ok">✅ 全部同步</span>' if data['all_clean'] else '<span class="status-warn">⚠️ 存在不同步项</span>'}</p>
<table>
<tr><th>项目</th><th>角色</th><th>版本</th><th>分支</th><th>Commit</th><th>状态</th></tr>
"""

    for name, info in data["projects"].items():
        status = "✅ 干净" if (not info["modified"] and not info["untracked"] and info["ahead"] == 0) else f"⚠️ {len(info['modified'])}修改 {len(info['untracked'])}未跟踪"
        status_class = "status-ok" if "✅" in status else "status-warn"
        html += f"""<tr>
<td><b>{name}</b></td>
<td>{info['role']}</td>
<td><code>{info['version']}</code></td>
<td><code>{info['branch']}</code></td>
<td><code>{info['commit']}</code></td>
<td class="{status_class}">{status}</td>
</tr>"""

    html += """</table>
</body>
</html>"""

    if output_path is None:
        output_path = os.path.join(
            r"D:\DobaoWork_Project\Ai_Video_Editor",
            "sync_report.html"
        )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n报告已生成: {output_path}")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python sync_manager.py check          # 检查同步状态")
        print("  python sync_manager.py sync_version X  # 同步版本号")
        print("  python sync_manager.py batch_commit M # 批量提交")
        print("  python sync_manager.py batch_push     # 批量推送")
        print("  python sync_manager.py report         # 生成HTML报告")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "check":
        check_sync()
    elif cmd == "sync_version":
        if len(sys.argv) < 3:
            print("请指定版本号，如: python sync_manager.py sync_version 1.2.0")
        else:
            sync_version(sys.argv[2])
    elif cmd == "batch_commit":
        msg = sys.argv[2] if len(sys.argv) > 2 else "同步更新"
        batch_commit(msg)
    elif cmd == "batch_push":
        batch_push()
    elif cmd == "report":
        generate_report()
    else:
        print(f"未知命令: {cmd}")
