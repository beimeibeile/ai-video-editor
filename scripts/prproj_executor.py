#!/usr/bin/env python3
"""
Pr工程(.prproj)执行器
基于真实PR模板，程序化生成可导入剪映的.prproj工程文件

核心原理：
- .prproj = gzip压缩的XML
- 真实模板可被剪映正常导入（已验证）
- 通过替换媒体FilePath实现模板复用
- 关键帧动画、多轨道结构完整保留

用法:
    from prproj_executor import PrprojExecutor
    exe = PrprojExecutor()
    result = exe.create_project(
        template="real_template.prproj",
        output="out/my_project.prproj",
        media_map={"原视频.mov": "C:/path/to/new.mp4"},
    )
"""

import logging
logger = logging.getLogger(__name__)

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

try:
    from paths import PATHS
    PROJECT_ROOT = PATHS.get("project_root", "")
except ImportError:
    PROJECT_ROOT = str(Path(__file__).parent.parent.parent)

# 模板目录
TEMPLATE_DIR = os.path.join(PROJECT_ROOT, "prxml_test")
DEFAULT_TEMPLATE = os.path.join(TEMPLATE_DIR, "real_template.prproj")


class PrprojExecutor:
    """Pr工程执行器"""

    def __init__(self, template_dir: Optional[str] = None):
        self.template_dir = template_dir or TEMPLATE_DIR
        self._modifier = None

    def list_templates(self) -> List[Dict]:
        """列出可用模板"""
        templates = []
        if os.path.exists(self.template_dir):
            for f in Path(self.template_dir).glob("*.prproj"):
                templates.append({
                    "name": f.name,
                    "path": str(f),
                    "size": f.stat().st_size,
                })
        return templates

    def get_template_info(self, template_path: str) -> Dict:
        """获取模板信息（序列、媒体列表）"""
        from prproj_template_modifier import PrprojTemplateModifier
        modifier = PrprojTemplateModifier(template_path)
        return {
            "template": template_path,
            "xml_size": modifier.original_size,
            "sequences": modifier.sequences,
            "media_files": modifier.media_files,
        }

    def create_project(
        self,
        output: str,
        *,
        template: Optional[str] = None,
        media_map: Optional[Dict[str, str]] = None,
        replace_all: Optional[str] = None,
    ) -> Dict:
        """
        基于模板生成新的Pr工程

        Args:
            output: 输出.prproj文件路径
            template: 模板路径（默认用real_template.prproj）
            media_map: 媒体映射 {原文件名: 新路径}
            replace_all: 将所有媒体替换为同一个文件路径

        Returns:
            生成结果字典
        """
        from prproj_template_modifier import PrprojTemplateModifier

        template_path = template or DEFAULT_TEMPLATE

        if not os.path.exists(template_path):
            return {
                "success": False,
                "error": f"模板不存在: {template_path}",
            }

        try:
            modifier = PrprojTemplateModifier(template_path)

            replaced = 0
            if replace_all:
                replaced = modifier.replace_all_media(replace_all)
            elif media_map:
                replaced = modifier.replace_media(media_map)

            # 确保输出目录存在
            os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
            modifier.save(output)

            return {
                "success": True,
                "output": os.path.abspath(output),
                "template": template_path,
                "media_replaced": replaced,
                "sequences": len(modifier.sequences),
                "media_count": len(modifier.media_files),
                "file_size": os.path.getsize(output),
                "next_step": "在剪映中通过'导入PR或FCP工程'按钮导入",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "template": template_path,
            }

    def create_from_instructions(
        self,
        instructions: Dict,
        output_dir: str,
    ) -> Dict:
        """
        从指令字典创建Pr工程（供orchestrator调用）

        指令格式:
        {
            "template": "real_template.prproj",  # 可选
            "output_name": "my_project",          # 输出文件名（不含扩展名）
            "media_map": {"原视频.mov": "C:/path/to/new.mp4"},
            "replace_all": "C:/path/to/video.mp4",  # 二选一
        }
        """
        output_name = instructions.get("output_name", "prproj_project")
        output = os.path.join(output_dir, f"{output_name}.prproj")

        return self.create_project(
            output=output,
            template=instructions.get("template"),
            media_map=instructions.get("media_map"),
            replace_all=instructions.get("replace_all"),
        )


# 便捷函数
def create_prproj_project(
    output: str,
    media_map: Optional[Dict[str, str]] = None,
    template: Optional[str] = None,
) -> Dict:
    """便捷函数：创建Pr工程"""
    exe = PrprojExecutor()
    return exe.create_project(
        output=output,
        template=template,
        media_map=media_map,
    )


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Pr工程执行器")
    parser.add_argument("--list", action="store_true", help="列出可用模板")
    parser.add_argument("--info", help="查看模板信息")
    parser.add_argument("--create", help="创建工程（输出路径）")
    parser.add_argument("--template", help="模板路径")
    parser.add_argument("--media-map", help="媒体映射JSON")
    parser.add_argument("--replace-all", help="所有媒体替换为该文件")
    args = parser.parse_args()

    exe = PrprojExecutor()

    if args.list:
        templates = exe.list_templates()
        logger.info(json.dumps(templates, ensure_ascii=False, indent=2))
    elif args.info:
        info = exe.get_template_info(args.info)
        logger.info(json.dumps(info, ensure_ascii=False, indent=2))
    elif args.create:
        media_map = None
        if args.media_map:
            media_map = json.loads(args.media_map)
        result = exe.create_project(
            output=args.create,
            template=args.template,
            media_map=media_map,
            replace_all=args.replace_all,
        )
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        logger.info("用法: prproj_executor.py --list | --info <template> | --create <output>")
