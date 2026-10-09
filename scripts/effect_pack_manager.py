#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P29 特效包版本管理系统
- P29-1: 特效包格式标准化（registry-item.json + index.html + assets）
- P29-2: 版本化管理（semver，支持版本查询和升级）
- P29-3: 本地注册表（搜索/安装/更新/列表CLI）

特效包格式（对齐hyperframes:block）:
effect_pack/
├── registry-item.json    # 包元数据（名称/版本/描述/作者/依赖）
├── index.html            # 特效预览/演示页面（可选）
├── assets/               # 特效资源文件
│   ├── effect.json       # 剪映特效参数定义
│   ├── preview.png       # 预览图
│   └── ...
└── README.md             # 使用说明
"""

import os
import json
import shutil
import hashlib
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


# ============ 特效包元数据 ============

@dataclass
class EffectPackMeta:
    """特效包元数据（registry-item.json）"""
    name: str                    # 包名（唯一标识）
    version: str                 # semver版本，如 "1.0.0"
    description: str             # 描述
    author: str = "ai-video-editor"
    category: str = "general"    # 分类: scene/filter/character/transition/text
    tags: List[str] = field(default_factory=list)
    effects: List[str] = field(default_factory=list)  # 包含的特效名称
    dependencies: Dict[str, str] = field(default_factory=dict)  # 依赖包 {name: version_range}
    min_engine_version: str = "1.0.0"  # 最低引擎版本
    created_at: str = ""
    updated_at: str = ""
    checksum: str = ""           # 内容校验和

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat() + "Z"
        if not self.updated_at:
            self.updated_at = self.created_at


# ============ 版本工具 ============

def parse_version(version: str) -> Tuple[int, int, int]:
    """解析semver版本号"""
    parts = version.lstrip("v").split(".")
    if len(parts) != 3:
        raise ValueError(f"无效版本号: {version}（应为 major.minor.patch）")
    return tuple(int(p) for p in parts)


def compare_versions(v1: str, v2: str) -> int:
    """比较版本号: -1(v1<v2), 0(相等), 1(v1>v2)"""
    p1, p2 = parse_version(v1), parse_version(v2)
    if p1 < p2: return -1
    if p1 > p2: return 1
    return 0


def bump_version(version: str, level: str = "patch") -> str:
    """升级版本号: major/minor/patch"""
    major, minor, patch = parse_version(version)
    if level == "major":
        return f"{major+1}.0.0"
    elif level == "minor":
        return f"{major}.{minor+1}.0"
    else:
        return f"{major}.{minor}.{patch+1}"


def check_version_range(version: str, range_spec: str) -> bool:
    """检查版本是否满足范围约束
    支持: ^1.0.0, ~1.0.0, >=1.0.0, <=2.0.0, 1.0.0-2.0.0, *
    """
    if range_spec == "*" or range_spec == "":
        return True

    if range_spec.startswith("^"):
        base = range_spec[1:]
        b_major, _, _ = parse_version(base)
        return (compare_versions(version, base) >= 0 and
                parse_version(version)[0] == b_major)

    if range_spec.startswith("~"):
        base = range_spec[1:]
        b_major, b_minor, _ = parse_version(base)
        v_major, v_minor, _ = parse_version(version)
        return (compare_versions(version, base) >= 0 and
                v_major == b_major and v_minor == b_minor)

    if range_spec.startswith(">="):
        return compare_versions(version, range_spec[2:]) >= 0
    if range_spec.startswith("<="):
        return compare_versions(version, range_spec[2:]) <= 0
    if range_spec.startswith(">"):
        return compare_versions(version, range_spec[1:]) > 0
    if range_spec.startswith("<"):
        return compare_versions(version, range_spec[1:]) < 0

    if "-" in range_spec:
        low, high = range_spec.split("-", 1)
        return compare_versions(version, low.strip()) >= 0 and compare_versions(version, high.strip()) <= 0

    return compare_versions(version, range_spec) == 0


# ============ 特效包管理器 ============

class EffectPackManager:
    """特效包管理器：创建/安装/更新/搜索/列表"""

    def __init__(self, registry_dir: str = None):
        self.registry_dir = registry_dir or os.path.join(
            r"D:\DobaoWork_Project\Ai_Video_Editor", "effect_packs"
        )
        self.installed_dir = os.path.join(self.registry_dir, "installed")
        self.index_file = os.path.join(self.registry_dir, "index.json")
        os.makedirs(self.installed_dir, exist_ok=True)

        # 加载或创建索引
        self.index = self._load_index()

    def _load_index(self) -> Dict[str, Any]:
        """加载本地注册表索引"""
        if os.path.exists(self.index_file):
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"packs": {}, "updated_at": ""}

    def _save_index(self):
        """保存索引"""
        self.index["updated_at"] = datetime.now(timezone.utc).isoformat() + "Z"
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)

    def _compute_checksum(self, pack_dir: str) -> str:
        """计算包内容校验和（排除registry-item.json本身）"""
        hasher = hashlib.sha256()
        for root, dirs, files in os.walk(pack_dir):
            for fname in sorted(files):
                if fname == "registry-item.json":
                    continue
                fpath = os.path.join(root, fname)
                hasher.update(os.path.relpath(fpath, pack_dir).encode())
                with open(fpath, "rb") as f:
                    while chunk := f.read(8192):
                        hasher.update(chunk)
        return hasher.hexdigest()[:16]

    def create_pack(self, name: str, version: str = "0.1.0",
                    description: str = "", category: str = "general",
                    effects: List[str] = None,
                    output_dir: str = None) -> str:
        """创建新特效包

        Args:
            name: 包名
            version: 初始版本
            description: 描述
            category: 分类
            effects: 包含的特效名称列表
            output_dir: 输出目录，默认在registry_dir下

        Returns:
            包目录路径
        """
        pack_dir = os.path.join(output_dir or self.registry_dir, f"{name}@{version}")
        if os.path.exists(pack_dir):
            raise ValueError(f"包已存在: {pack_dir}")

        os.makedirs(os.path.join(pack_dir, "assets"), exist_ok=True)

        # 创建元数据
        meta = EffectPackMeta(
            name=name, version=version, description=description,
            category=category, effects=effects or [],
        )
        meta.checksum = self._compute_checksum(pack_dir)

        with open(os.path.join(pack_dir, "registry-item.json"), "w", encoding="utf-8") as f:
            json.dump(asdict(meta), f, indent=2, ensure_ascii=False)

        # 创建README
        readme = f"""# {name} v{version}

{description}

## 分类
{category}

## 包含特效
{chr(10).join(f'- {e}' for e in (effects or []))}

## 安装
```bash
python effect_pack_manager.py install {name}@{version}
```
"""
        with open(os.path.join(pack_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write(readme)

        # 创建默认effect.json
        effect_def = {
            "pack_name": name,
            "version": version,
            "effects": [
                {"name": e, "type": category, "params": {}}
                for e in (effects or [])
            ]
        }
        with open(os.path.join(pack_dir, "assets", "effect.json"), "w", encoding="utf-8") as f:
            json.dump(effect_def, f, indent=2, ensure_ascii=False)

        return pack_dir

    def install_pack(self, pack_path: str) -> Dict[str, Any]:
        """安装特效包到本地注册表

        Args:
            pack_path: 包目录路径或包名@版本

        Returns:
            安装结果
        """
        # 解析包路径
        if "@" in pack_path and not os.path.exists(pack_path):
            name, version = pack_path.rsplit("@", 1)
            pack_path = os.path.join(self.registry_dir, f"{name}@{version}")

        if not os.path.isdir(pack_path):
            return {"success": False, "error": f"包不存在: {pack_path}"}

        # 读取元数据
        meta_file = os.path.join(pack_path, "registry-item.json")
        if not os.path.exists(meta_file):
            return {"success": False, "error": "缺少registry-item.json"}

        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        name = meta["name"]
        version = meta["version"]

        # 检查依赖
        for dep_name, dep_range in meta.get("dependencies", {}).items():
            if dep_name not in self.index["packs"]:
                return {"success": False, "error": f"缺少依赖: {dep_name} ({dep_range})"}
            installed_ver = self.index["packs"][dep_name]["version"]
            if not check_version_range(installed_ver, dep_range):
                return {"success": False,
                        "error": f"依赖版本不满足: {dep_name} 需要{dep_range}, 当前{installed_ver}"}

        # 复制到installed目录
        target_dir = os.path.join(self.installed_dir, f"{name}@{version}")
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        shutil.copytree(pack_path, target_dir)

        # 更新索引
        self.index["packs"][name] = {
            "version": version,
            "path": target_dir,
            "category": meta.get("category", "general"),
            "effects": meta.get("effects", []),
            "installed_at": datetime.now(timezone.utc).isoformat() + "Z",
        }
        self._save_index()

        return {"success": True, "name": name, "version": version, "path": target_dir}

    def uninstall_pack(self, name: str) -> Dict[str, Any]:
        """卸载特效包"""
        if name not in self.index["packs"]:
            return {"success": False, "error": f"包未安装: {name}"}

        pack_info = self.index["packs"].pop(name)
        if os.path.exists(pack_info["path"]):
            shutil.rmtree(pack_info["path"])
        self._save_index()
        return {"success": True, "name": name}

    def update_pack(self, name: str, new_pack_path: str = None) -> Dict[str, Any]:
        """更新特效包到新版本"""
        if name not in self.index["packs"]:
            return {"success": False, "error": f"包未安装: {name}"}

        current_ver = self.index["packs"][name]["version"]

        if new_pack_path:
            return self.install_pack(new_pack_path)

        # 搜索可用更新
        available = self.search_packs(name)
        newer = [p for p in available if compare_versions(p["version"], current_ver) > 0]
        if not newer:
            return {"success": False, "error": f"没有可用更新（当前版本{current_ver}）"}

        latest = max(newer, key=lambda p: parse_version(p["version"]))
        return self.install_pack(latest["path"])

    def search_packs(self, query: str = "", category: str = "") -> List[Dict[str, Any]]:
        """搜索可用特效包"""
        results = []
        if not os.path.isdir(self.registry_dir):
            return results

        for entry in os.listdir(self.registry_dir):
            entry_path = os.path.join(self.registry_dir, entry)
            if not os.path.isdir(entry_path):
                continue
            meta_file = os.path.join(entry_path, "registry-item.json")
            if not os.path.exists(meta_file):
                continue
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)

            # 过滤
            if query and query.lower() not in meta["name"].lower() and \
               query.lower() not in meta.get("description", "").lower():
                continue
            if category and meta.get("category") != category:
                continue

            results.append({
                "name": meta["name"],
                "version": meta["version"],
                "description": meta.get("description", ""),
                "category": meta.get("category", "general"),
                "effects": meta.get("effects", []),
                "path": entry_path,
                "installed": meta["name"] in self.index["packs"],
            })

        return sorted(results, key=lambda p: (p["name"], parse_version(p["version"])))

    def list_installed(self) -> List[Dict[str, Any]]:
        """列出已安装的特效包"""
        return [
            {"name": name, **info}
            for name, info in self.index["packs"].items()
        ]

    def get_pack(self, name: str) -> Optional[Dict[str, Any]]:
        """获取已安装包的信息"""
        if name not in self.index["packs"]:
            return None
        info = self.index["packs"][name]
        meta_file = os.path.join(info["path"], "registry-item.json")
        if os.path.exists(meta_file):
            with open(meta_file, "r", encoding="utf-8") as f:
                info["meta"] = json.load(f)
        return info

    def get_effect(self, pack_name: str, effect_name: str) -> Optional[Dict[str, Any]]:
        """获取包中某个特效的定义"""
        pack = self.get_pack(pack_name)
        if not pack:
            return None
        effect_file = os.path.join(pack["path"], "assets", "effect.json")
        if not os.path.exists(effect_file):
            return None
        with open(effect_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        for effect in data.get("effects", []):
            if effect["name"] == effect_name:
                return effect
        return None


# ============ CLI ============

def main():
    import argparse
    parser = argparse.ArgumentParser(description="特效包版本管理CLI")
    sub = parser.add_subparsers(dest="command")

    # create
    p_create = sub.add_parser("create", help="创建新特效包")
    p_create.add_argument("name")
    p_create.add_argument("--version", default="0.1.0")
    p_create.add_argument("--description", default="")
    p_create.add_argument("--category", default="general")
    p_create.add_argument("--effects", nargs="*", default=[])

    # install
    p_install = sub.add_parser("install", help="安装特效包")
    p_install.add_argument("pack_path")

    # uninstall
    p_uninstall = sub.add_parser("uninstall", help="卸载特效包")
    p_uninstall.add_argument("name")

    # update
    p_update = sub.add_parser("update", help="更新特效包")
    p_update.add_argument("name")
    p_update.add_argument("--path", default=None)

    # search
    p_search = sub.add_parser("search", help="搜索特效包")
    p_search.add_argument("query", nargs="?", default="")
    p_search.add_argument("--category", default="")

    # list
    sub.add_parser("list", help="列出已安装特效包")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    mgr = EffectPackManager()

    if args.command == "create":
        path = mgr.create_pack(args.name, args.version, args.description,
                               args.category, args.effects)
        logger.info(f"创建成功: {path}")

    elif args.command == "install":
        result = mgr.install_pack(args.pack_path)
        logger.info(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "uninstall":
        result = mgr.uninstall_pack(args.name)
        logger.info(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "update":
        result = mgr.update_pack(args.name, args.path)
        logger.info(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "search":
        results = mgr.search_packs(args.query, args.category)
        logger.info(f"找到 {len(results)} 个包:")
        for p in results:
            status = "✓已安装" if p["installed"] else " "
            logger.info(f"  {status} {p['name']}@{p['version']} [{p['category']}] - {p['description']}")

    elif args.command == "list":
        installed = mgr.list_installed()
        logger.info(f"已安装 {len(installed)} 个包:")
        for p in installed:
            logger.info(f"  {p['name']}@{p['version']} [{p['category']}] - {len(p.get('effects',[]))}个特效")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
