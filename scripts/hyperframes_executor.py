#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P28-3 HyperFramesExecutor封装
将HyperFrames CLI封装为P25执行器，支持输入HTML字符串或文件路径，输出MP4

依赖: Node.js 22+, hyperframes CLI (npm install -g hyperframes)
"""

import os
import sys
import json
import shutil
import subprocess
import tempfile
import logging
from typing import Dict, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class HyperFramesExecutor:
    """HyperFrames渲染执行器

    支持:
    - 从HTML文件渲染MP4
    - 从HTML字符串渲染MP4（自动创建临时项目）
    - 自定义分辨率/时长/FPS
    - 渲染进度回调
    """

    def __init__(self, work_dir: str = None, node_path: str = None):
        """
        Args:
            work_dir: 工作目录，默认在项目下创建p28_hyperframes_work
            node_path: Node.js路径，默认使用系统PATH
        """
        self.work_dir = work_dir or os.path.join(
            r"D:\DobaoWork_Project\Ai_Video_Editor",
            "p28_hyperframes_work"
        )
        self.node_path = node_path
        os.makedirs(self.work_dir, exist_ok=True)

        # 验证hyperframes CLI
        self._verify_cli()

    def _verify_cli(self):
        """验证hyperframes CLI可用"""
        # Windows上hyperframes是.cmd文件，需要用shell=True
        try:
            result = subprocess.run(
                "hyperframes --version",
                capture_output=True, text=True, timeout=10,
                shell=True
            )
            self.cli_version = result.stdout.strip()
            if not self.cli_version:
                self.cli_version = "0.8.140"  # fallback
        except (FileNotFoundError, subprocess.TimeoutExpired):
            raise RuntimeError(
                "hyperframes CLI未安装，请运行: npm install -g hyperframes"
            )

    def _scaffold_project(self, project_name: str, html_content: str,
                          width: int = 1920, height: int = 1080,
                          duration: float = 10.0, fps: int = 30) -> str:
        """创建HyperFrames项目结构

        Args:
            project_name: 项目名称
            html_content: HTML内容
            width/height: 分辨率
            duration: 时长(秒)
            fps: 帧率

        Returns:
            项目目录路径
        """
        project_dir = os.path.join(self.work_dir, project_name)
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)
        os.makedirs(project_dir)

        # 替换HTML中的duration和分辨率
        html = html_content
        html = html.replace('data-duration="10"', f'data-duration="{duration}"')
        html = html.replace('content="width=1920, height=1080"',
                           f'content="width={width}, height={height}"')
        html = html.replace('width: 1920px', f'width: {width}px')
        html = html.replace('height: 1080px', f'height: {height}px')

        # 写入index.html
        with open(os.path.join(project_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)

        # 写入hyperframes.json
        config = {
            "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
            "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
            "paths": {
                "blocks": "compositions",
                "components": "compositions/components",
                "assets": "assets"
            },
            "media": {"autoProxy": True}
        }
        with open(os.path.join(project_dir, "hyperframes.json"), "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        # 写入meta.json
        meta = {
            "id": project_name,
            "name": project_name,
            "createdAt": datetime.utcnow().isoformat() + "Z"
        }
        with open(os.path.join(project_dir, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        # 写入package.json
        pkg = {
            "name": project_name,
            "private": True,
            "type": "module",
            "scripts": {
                "dev": f"npx --yes hyperframes@{self.cli_version} preview",
                "check": f"npx --yes hyperframes@{self.cli_version} check",
                "render": f"npx --yes hyperframes@{self.cli_version} render"
            }
        }
        with open(os.path.join(project_dir, "package.json"), "w", encoding="utf-8") as f:
            json.dump(pkg, f, indent=2)

        return project_dir

    def render(self, html_input: str, output_path: str = None,
               width: int = 1920, height: int = 1080,
               duration: float = 10.0, fps: int = 30,
               project_name: str = None,
               progress_callback=None) -> Dict[str, Any]:
        """渲染HTML为MP4

        Args:
            html_input: HTML文件路径或HTML字符串
            output_path: 输出MP4路径，默认在项目renders目录
            width/height: 分辨率
            duration: 时长(秒)
            fps: 帧率
            project_name: 项目名称，默认自动生成
            progress_callback: 进度回调函数(percent: int, message: str)

        Returns:
            渲染结果字典: {success, output_path, duration, render_time, error}
        """
        # 判断是文件路径还是字符串
        if os.path.isfile(html_input):
            with open(html_input, "r", encoding="utf-8") as f:
                html_content = f.read()
        else:
            html_content = html_input

        # 生成项目名
        if not project_name:
            project_name = f"hf_render_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 创建项目
        project_dir = self._scaffold_project(
            project_name, html_content, width, height, duration, fps
        )

        # 执行渲染
        start_time = datetime.now()
        try:
            cmd = "hyperframes render"
            if fps != 30:
                cmd += f" --fps {fps}"

            process = subprocess.Popen(
                cmd,
                cwd=project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                shell=True
            )

            # 实时读取输出
            for line in process.stdout:
                line = line.strip()
                if progress_callback and "@hf-progress" in line:
                    try:
                        # 解析进度: @hf-progress {"code":"capture","done":1,"total":300,"pct":25}
                        json_str = line.split("@hf-progress", 1)[1].strip()
                        prog = json.loads(json_str)
                        pct = prog.get("pct", 0)
                        code = prog.get("code", "")
                        progress_callback(pct, f"{code}: {prog.get('done',0)}/{prog.get('total',0)}")
                    except (json.JSONDecodeError, ValueError):
                        pass

            process.wait()
            render_time = (datetime.now() - start_time).total_seconds()

            if process.returncode != 0:
                return {
                    "success": False,
                    "error": f"渲染失败，返回码{process.returncode}",
                    "render_time": render_time
                }

            # 查找输出文件
            renders_dir = os.path.join(project_dir, "renders")
            if not os.path.isdir(renders_dir):
                return {
                    "success": False,
                    "error": "renders目录不存在",
                    "render_time": render_time
                }

            mp4_files = sorted(
                [f for f in os.listdir(renders_dir) if f.endswith(".mp4")],
                key=lambda f: os.path.getmtime(os.path.join(renders_dir, f)),
                reverse=True
            )
            if not mp4_files:
                return {
                    "success": False,
                    "error": "未找到输出MP4文件",
                    "render_time": render_time
                }

            src_path = os.path.join(renders_dir, mp4_files[0])

            # 复制到目标路径
            if output_path:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                shutil.copy2(src_path, output_path)
                final_path = output_path
            else:
                final_path = src_path

            return {
                "success": True,
                "output_path": final_path,
                "project_dir": project_dir,
                "render_time": render_time,
                "width": width,
                "height": height,
                "duration": duration,
                "fps": fps
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "render_time": (datetime.now() - start_time).total_seconds()
            }

    def render_from_template(self, template_name: str, variables: Dict[str, str],
                             output_path: str = None, **kwargs) -> Dict[str, Any]:
        """从模板渲染（模板中的{{key}}替换为variables值）

        Args:
            template_name: 模板名称（在templates目录下）
            variables: 模板变量字典
            output_path: 输出路径
            **kwargs: 传递给render()的其他参数

        Returns:
            渲染结果
        """
        template_dir = os.path.join(os.path.dirname(__file__), "..", "p28_templates")
        template_file = os.path.join(template_dir, f"{template_name}.html")

        if not os.path.isfile(template_file):
            return {"success": False, "error": f"模板不存在: {template_file}"}

        with open(template_file, "r", encoding="utf-8") as f:
            html = f.read()

        for key, value in variables.items():
            html = html.replace(f"{{{{{key}}}}}", str(value))

        return self.render(html, output_path, **kwargs)


# ============ 内置模板 ============

TEMPLATES = {
    "title_card": """<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1920, height=1080" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
html,body { margin:0; width:1920px; height:1080px; overflow:hidden; background:{{bg_color}}; }
#root { width:100%; height:100%; display:flex; align-items:center; justify-content:center;
        font-family:Inter,ui-sans-serif,system-ui,sans-serif; }
#title { color:{{text_color}}; font-size:{{font_size}}px; font-weight:700;
         letter-spacing:-0.03em; text-align:center; }
#subtitle { color:{{sub_color}}; font-size:{{sub_size}}px; margin-top:24px;
            font-weight:400; opacity:0.8; }
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="10"
     data-width="1920" data-height="1080">
  <div style="text-align:center">
    <h1 id="title" class="clip" data-start="0" data-duration="10" data-track-index="0">{{title}}</h1>
    <p id="subtitle" class="clip" data-start="0.5" data-duration="9.5" data-track-index="1">{{subtitle}}</p>
  </div>
</div>
<script>
const tl = gsap.timeline({paused:true});
tl.fromTo("#title",{opacity:0,y:60},{opacity:1,y:0,duration:0.8,ease:"power3.out"},0);
tl.fromTo("#subtitle",{opacity:0,y:30},{opacity:1,y:0,duration:0.6,ease:"power2.out"},0.3);
tl.to("#title",{opacity:0,y:-30,duration:0.5},8.5);
tl.to("#subtitle",{opacity:0,duration:0.5},8.7);
window.__timelines["main"]=tl; tl.seek(0);
</script>
</body>
</html>""",
}


def create_template_file(template_name: str, output_dir: str = None):
    """将内置模板写入文件

    Args:
        template_name: 模板名称
        output_dir: 输出目录，默认p28_templates
    """
    if template_name not in TEMPLATES:
        raise ValueError(f"未知模板: {template_name}，可用: {list(TEMPLATES.keys())}")

    output_dir = output_dir or os.path.join(
        r"D:\DobaoWork_Project\Ai_Video_Editor", "p28_templates"
    )
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, f"{template_name}.html")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(TEMPLATES[template_name])
    return output_file


# ============ 测试 ============

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("=== HyperFramesExecutor 测试 ===")
    logger.info(f"CLI版本: {HyperFramesExecutor().cli_version}")

    # 创建title_card模板
    template_file = create_template_file("title_card")
    logger.info(f"模板已创建: {template_file}")

    # 渲染测试
    executor = HyperFramesExecutor()

    def on_progress(pct, msg):
        logger.info(f"  进度: {pct}% - {msg}")

    result = executor.render_from_template(
        "title_card",
        variables={
            "title": "AI Video Editor",
            "subtitle": "HyperFrames 渲染测试",
            "bg_color": "#0a0a0a",
            "text_color": "#f4f4f5",
            "sub_color": "#a1a1aa",
            "font_size": "96",
            "sub_size": "36",
        },
        output_path=r"D:\DobaoWork_Project\Ai_Video_Editor\p28_hyperframes_test\title_card_test.mp4",
        duration=5.0,
        progress_callback=on_progress
    )

    if result["success"]:
        logger.info(f"\n渲染成功!")
        logger.info(f"  输出: {result['output_path']}")
        logger.info(f"  耗时: {result['render_time']:.1f}s")
        logger.info(f"  分辨率: {result['width']}x{result['height']}")
    else:
        logger.error(f"\n渲染失败: {result.get('error')}")
