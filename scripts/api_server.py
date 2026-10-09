"""
AI Video Editor API 服务
零依赖REST API服务（Python标准库http.server），提供视频生成、剪映工程、任务管理等能力

启动方式：
    python api_server.py --port 8000

API端点：
    GET  /api/health          - 健康检查
    GET  /api/capabilities    - 能力列表
    POST /api/video/generate  - 视频生成（T2V/I2V/FL2V/Ref2V）
    POST /api/draft/create    - 创建剪映工程
    GET  /api/task/{id}       - 查询任务状态
    GET  /api/tasks           - 任务列表
    POST /api/task/{id}/cancel - 取消任务
"""

import os
import sys
import json
import time
import uuid
import threading
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# 路径配置
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_SKILL_ROOT = os.path.dirname(_THIS_DIR)
sys.path.insert(0, _THIS_DIR)

# 模板市场
try:
    from template_market import get_market
    _template_market = get_market()
except Exception as e:
    logger.warning(f"模板市场初始化失败: {e}")
    _template_market = None

# 插件管理器
try:
    from plugin_sdk import get_plugin_manager
    _plugin_manager = get_plugin_manager()
    _plugin_manager.load_all()
    logger.info(f"插件管理器初始化完成，已加载 {len(_plugin_manager.list_plugins())} 个插件")
except Exception as e:
    logger.warning(f"插件管理器初始化失败: {e}")
    _plugin_manager = None

# 音频增强模块（BGM+音效+TTS）
try:
    from audio_enhancer import get_bgm_selector, get_sfx_manager, get_tts_enhancer
    _bgm_selector = get_bgm_selector()
    _sfx_manager = get_sfx_manager()
    _tts_enhancer = get_tts_enhancer()
    logger.info("音频增强模块初始化完成")
except Exception as e:
    logger.warning(f"音频增强模块初始化失败: {e}")
    _bgm_selector = None
    _sfx_manager = None
    _tts_enhancer = None

# 智能增强模块（导演决策+素材管理+自然语言）
try:
    from intelligence_enhancer import get_director_v3, get_asset_manager, get_nl_enhancer
    _director_v3 = get_director_v3()
    _asset_manager = get_asset_manager()
    _nl_enhancer = get_nl_enhancer()
    logger.info("智能增强模块初始化完成")
except Exception as e:
    logger.warning(f"智能增强模块初始化失败: {e}")
    _director_v3 = None
    _asset_manager = None
    _nl_enhancer = None

# 全自动流水线
try:
    from auto_pipeline import AutoPipeline
    _auto_pipeline = AutoPipeline()
    logger.info("全自动流水线初始化完成")
except Exception as e:
    logger.warning(f"全自动流水线初始化失败: {e}")
    _auto_pipeline = None

# 任务状态
TASK_PENDING = "pending"
TASK_RUNNING = "running"
TASK_COMPLETED = "completed"
TASK_FAILED = "failed"
TASK_CANCELLED = "cancelled"


class TaskManager:
    """任务管理器"""

    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_task(self, task_type: str, params: Dict[str, Any]) -> str:
        """创建任务"""
        task_id = str(uuid.uuid4())[:8]
        with self._lock:
            self.tasks[task_id] = {
                "id": task_id,
                "type": task_type,
                "status": TASK_PENDING,
                "params": params,
                "result": None,
                "error": None,
                "created_at": time.time(),
                "started_at": None,
                "completed_at": None,
            }
        return task_id

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务"""
        with self._lock:
            return self.tasks.get(task_id)

    def list_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出任务"""
        with self._lock:
            tasks = sorted(self.tasks.values(), key=lambda x: x["created_at"], reverse=True)
            return tasks[:limit]

    def update_task(self, task_id: str, **kwargs):
        """更新任务状态"""
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id].update(kwargs)

    def run_task_async(self, task_id: str, func, *args, **kwargs):
        """异步执行任务"""
        def wrapper():
            self.update_task(task_id, status=TASK_RUNNING, started_at=time.time())
            try:
                result = func(*args, **kwargs)
                self.update_task(task_id, status=TASK_COMPLETED, result=result, completed_at=time.time())
            except Exception as e:
                logger.error(f"任务{task_id}失败: {e}", exc_info=True)
                self.update_task(task_id, status=TASK_FAILED, error=str(e), completed_at=time.time())

        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()
        return thread


# 全局任务管理器
task_manager = TaskManager()


def get_capabilities() -> Dict[str, Any]:
    """获取系统能力列表"""
    return {
        "video_generation": {
            "models": ["ltx-2.5", "hunyuan-i2v", "minimax-h3"],
            "minimax_h3_variants": ["fl2va", "ref2va", "hybrid"],
            "modes": ["t2v", "i2v", "fl2v", "ref2v"],
            "max_resolution": "2560x1440",
            "max_frames": 361,
            "native_audio": True,
        },
        "jianying": {
            "effects": "25+特效",
            "animations": "入场/出场/循环动画",
            "transitions": "多种转场",
            "filters": "多种滤镜",
        },
        "audio": {
            "tts": "多音色语音合成",
            "bgm": "55首BGM库",
            "mixing": "多轨混音",
        },
        "comfyui": {
            "workflows": "35+工作流模板",
            "models": "文生图/图生图/视频生成/超分/抠图",
        },
    }


def generate_video_task(params: Dict[str, Any]) -> Dict[str, Any]:
    """视频生成任务执行函数"""
    model = params.get("model", "minimax-h3")
    mode = params.get("mode", "t2v")
    prompt = params.get("prompt", "")
    width = params.get("width", 1344)
    height = params.get("height", 768)
    frames = params.get("frames", 81)
    output_dir = params.get("output_dir", os.path.join(_SKILL_ROOT, "..", "api_output"))
    os.makedirs(output_dir, exist_ok=True)

    if model == "minimax-h3":
        # 添加comfyui-controls-skill的scripts目录到路径
        _comfyui_scripts = os.path.join(_SKILL_ROOT, "..", "comfyui-controls-skill", "scripts")
        if os.path.exists(_comfyui_scripts) and _comfyui_scripts not in sys.path:
            sys.path.insert(0, _comfyui_scripts)
        from minimax_h3_runner import MiniMaxH3Runner, PRESETS, MODEL_FL2VA, MODEL_REF2VA
        variant = params.get("variant", "fl2va")
        preset = params.get("preset", "turbo_768p")

        # 根据版本选择预设
        if variant == "ref2va" and preset not in ["ref2va_turbo", "ref2va_standard"]:
            preset = "ref2va_turbo"

        runner = MiniMaxH3Runner(
            server_addr="127.0.0.1:8188",
            output_dir=output_dir,
            preset=preset,
        )

        if mode == "t2v":
            output = runner.text_to_video(prompt, width, height, frames)
        elif mode == "i2v":
            image_path = params.get("image_path", "")
            if not image_path:
                raise ValueError("i2v模式需要image_path参数")
            output = runner.image_to_video(prompt, image_path, width, height, frames)
        elif mode == "fl2v":
            first_frame = params.get("first_frame_path", "")
            last_frame = params.get("last_frame_path", "")
            if not first_frame or not last_frame:
                raise ValueError("fl2v模式需要first_frame_path和last_frame_path参数")
            output = runner.first_last_to_video(prompt, first_frame, last_frame, width, height, frames)
        elif mode == "ref2v":
            ref_images = params.get("reference_images", [])
            ref_videos = params.get("reference_videos", [])
            ref_audios = params.get("reference_audios", [])
            output = runner.reference_to_video(
                prompt, ref_images, ref_videos, ref_audios, width, height, frames
            )
        else:
            raise ValueError(f"不支持的模式: {mode}")

        if not output:
            raise RuntimeError("视频生成失败：工作流执行返回空结果，请检查ComfyUI日志和模型文件是否存在")

        return {"output_path": output, "model": model, "variant": variant, "mode": mode}

    else:
        # LTX-2.5 / 混元I2V 使用video_generation_integrator
        from video_generation_integrator import VideoGenerationIntegrator, VideoGenConfig
        integrator = VideoGenerationIntegrator()
        config = VideoGenConfig(
            model=model,
            mode=mode,
            prompt=prompt,
            width=width,
            height=height,
            duration=frames,
        )
        if mode == "i2v":
            config.image_path = params.get("image_path", "")
        result = integrator.generate_video(config, output_dir)
        if not result.success:
            raise ValueError(f"生成失败: {result.errors}")
        return {"output_path": result.output_path, "model": model, "mode": mode}


def create_template_task(params: Dict[str, Any]) -> Dict[str, Any]:
    """模板风格复刻任务执行函数"""
    video_path = params.get("video_path", "")
    if not video_path:
        raise ValueError("缺少video_path参数")
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在: {video_path}")

    project_name = params.get("project_name", None)

    # 动态导入template_creator
    _this_dir = os.path.dirname(os.path.abspath(__file__))
    if _this_dir not in sys.path:
        sys.path.insert(0, _this_dir)
    from template_creator import create_template_from_video

    result = create_template_from_video(video_path, project_name)
    if result.get("status") != "success":
        raise ValueError(f"模板创建失败: {result.get('error', '未知错误')}")

    return {
        "draft_path": result["draft_path"],
        "project_name": result["project_name"],
        "segment_count": result["segment_count"],
        "style": result.get("style", {}),
    }


class APIHandler(BaseHTTPRequestHandler):
    """API请求处理器"""

    def _send_json(self, data: Dict[str, Any], status: int = 200):
        """发送JSON响应"""
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html_path: str, status: int = 200):
        """发送HTML响应"""
        try:
            with open(html_path, "r", encoding="utf-8") as f:
                body = f.read().encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self._send_json({"error": "页面文件不存在", "path": html_path}, 404)

    def _template_to_dict(self, template, detail: bool = False) -> Dict[str, Any]:
        """模板对象转字典"""
        from dataclasses import asdict
        data = asdict(template)
        if not detail:
            # 列表视图不返回评论
            data.pop("comments", None)
        return data

    def _read_body(self) -> Dict[str, Any]:
        """读取请求体"""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length)
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def _handle_upload(self):
        """处理文件上传（multipart/form-data）"""
        try:
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in content_type:
                self._send_json({"error": "需要multipart/form-data格式"}, 400)
                return

            # 解析boundary
            boundary = None
            for part in content_type.split(";"):
                part = part.strip()
                if part.startswith("boundary="):
                    boundary = part[9:].strip('"')
                    break

            if not boundary:
                self._send_json({"error": "无法解析boundary"}, 400)
                return

            content_length = int(self.headers.get("Content-Length", 0))
            raw_data = self.rfile.read(content_length)

            # 解析multipart
            boundary_bytes = ("--" + boundary).encode("utf-8")
            parts = raw_data.split(boundary_bytes)

            upload_dir = os.path.join(_SKILL_ROOT, "..", "uploads")
            os.makedirs(upload_dir, exist_ok=True)

            saved_path = None
            for part in parts:
                if not part or part == b"--\r\n" or part == b"--":
                    continue
                # 分离header和content
                if b"\r\n\r\n" in part:
                    header_bytes, content = part.split(b"\r\n\r\n", 1)
                    header_text = header_bytes.decode("utf-8", errors="ignore")
                    # 提取文件名
                    filename = None
                    for line in header_text.split("\r\n"):
                        if "filename=" in line:
                            for segment in line.split(";"):
                                segment = segment.strip()
                                if segment.startswith("filename="):
                                    filename = segment[9:].strip('"')
                                    break
                            break
                    if filename and content:
                        # 去除末尾的\r\n
                        if content.endswith(b"\r\n"):
                            content = content[:-2]
                        # 生成唯一文件名
                        ext = os.path.splitext(filename)[1]
                        unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
                        save_path = os.path.join(upload_dir, unique_name)
                        with open(save_path, "wb") as f:
                            f.write(content)
                        saved_path = os.path.abspath(save_path)
                        logger.info(f"文件上传成功: {filename} -> {saved_path} ({len(content)} bytes)")
                        break

            if saved_path:
                self._send_json({"path": saved_path, "filename": filename, "size": len(content)})
            else:
                self._send_json({"error": "未找到文件"}, 400)

        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            import traceback
            traceback.print_exc()
            self._send_json({"error": f"上传失败: {str(e)}"}, 500)

    def do_OPTIONS(self):
        """处理OPTIONS请求（CORS预检）"""
        self._send_json({"status": "ok"}, 200)

    def do_GET(self):
        """处理GET请求"""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        # 根路径返回用户工作台
        if path == "":
            web_index = os.path.join(_SKILL_ROOT, "web", "index.html")
            self._send_html(web_index)
            return

        if path == "/api/health":
            self._send_json({
                "status": "healthy",
                "service": "ai-video-editor-api",
                "version": "1.0.0",
                "timestamp": time.time(),
                "tasks_total": len(task_manager.tasks),
            })

        elif path == "/api/capabilities":
            self._send_json(get_capabilities())

        elif path == "/api/tasks":
            tasks = task_manager.list_tasks()
            self._send_json({"tasks": tasks, "total": len(tasks)})

        elif path.startswith("/api/task/"):
            task_id = path.split("/")[-1]
            task = task_manager.get_task(task_id)
            if task:
                self._send_json(task)
            else:
                self._send_json({"error": "任务不存在", "task_id": task_id}, 404)

        # 模板市场端点
        elif path == "/api/templates":
            if not _template_market:
                self._send_json({"error": "模板市场未初始化"}, 500)
                return
            query = parse_qs(parsed.query)
            keyword = query.get("keyword", [""])[0]
            category = query.get("category", [""])[0]
            style = query.get("style", [""])[0]
            scene = query.get("scene", [""])[0]
            difficulty = query.get("difficulty", [""])[0]
            sort_by = query.get("sort", ["rating"])[0]
            limit = int(query.get("limit", ["20"])[0])
            offset = int(query.get("offset", ["0"])[0])
            results = _template_market.search_templates(
                keyword=keyword, category=category, style=style,
                scene=scene, difficulty=difficulty,
                sort_by=sort_by, limit=limit, offset=offset
            )
            self._send_json({
                "templates": [self._template_to_dict(t) for t in results],
                "total": len(results),
            })

        elif path == "/api/templates/featured":
            if not _template_market:
                self._send_json({"error": "模板市场未初始化"}, 500)
                return
            limit = int(parse_qs(parsed.query).get("limit", ["6"])[0])
            results = _template_market.get_featured(limit)
            self._send_json({"templates": [self._template_to_dict(t) for t in results]})

        elif path == "/api/templates/hot":
            if not _template_market:
                self._send_json({"error": "模板市场未初始化"}, 500)
                return
            limit = int(parse_qs(parsed.query).get("limit", ["10"])[0])
            results = _template_market.get_hot(limit)
            self._send_json({"templates": [self._template_to_dict(t) for t in results]})

        elif path == "/api/templates/newest":
            if not _template_market:
                self._send_json({"error": "模板市场未初始化"}, 500)
                return
            limit = int(parse_qs(parsed.query).get("limit", ["10"])[0])
            results = _template_market.get_newest(limit)
            self._send_json({"templates": [self._template_to_dict(t) for t in results]})

        elif path == "/api/templates/categories":
            if not _template_market:
                self._send_json({"error": "模板市场未初始化"}, 500)
                return
            self._send_json(_template_market.get_categories())

        elif path == "/api/templates/stats":
            if not _template_market:
                self._send_json({"error": "模板市场未初始化"}, 500)
                return
            self._send_json(_template_market.get_stats())

        elif path.startswith("/api/templates/") and not path.startswith("/api/templates/"):
            pass  # 占位，避免匹配冲突

        elif path.startswith("/api/template/"):
            if not _template_market:
                self._send_json({"error": "模板市场未初始化"}, 500)
                return
            template_id = path.split("/")[-1]
            template = _template_market.get_template(template_id)
            if template:
                self._send_json(self._template_to_dict(template, detail=True))
            else:
                self._send_json({"error": "模板不存在", "template_id": template_id}, 404)

        # 插件管理端点
        elif path == "/api/plugins":
            if not _plugin_manager:
                self._send_json({"error": "插件管理器未初始化"}, 500)
                return
            self._send_json({
                "plugins": _plugin_manager.list_plugins(),
                "total": len(_plugin_manager.list_plugins()),
            })

        elif path == "/api/plugins/stats":
            if not _plugin_manager:
                self._send_json({"error": "插件管理器未初始化"}, 500)
                return
            self._send_json(_plugin_manager.get_stats())

        elif path == "/api/plugins/capabilities":
            if not _plugin_manager:
                self._send_json({"error": "插件管理器未初始化"}, 500)
                return
            self._send_json({
                "capabilities": _plugin_manager.list_capabilities(),
                "total": len(_plugin_manager.list_capabilities()),
            })

        elif path.startswith("/api/plugin/"):
            if not _plugin_manager:
                self._send_json({"error": "插件管理器未初始化"}, 500)
                return
            parts = path.split("/")
            # /api/plugin/{id}
            if len(parts) == 4:
                plugin_id = parts[3]
                plugin = _plugin_manager.get_plugin(plugin_id)
                if plugin:
                    self._send_json(plugin.get_info())
                else:
                    self._send_json({"error": "插件不存在", "plugin_id": plugin_id}, 404)
            # /api/plugin/{id}/capabilities
            elif len(parts) == 5 and parts[4] == "capabilities":
                plugin_id = parts[3]
                caps = [c for c in _plugin_manager.list_capabilities()
                        if c.get("plugin_id") == plugin_id]
                self._send_json({"capabilities": caps, "total": len(caps)})
            else:
                self._send_json({"error": "端点不存在", "path": path}, 404)

        # BGM搜索
        elif path == "/api/bgm/search":
            if not _bgm_selector:
                self._send_json({"error": "BGM选择器未初始化"}, 500)
                return
            query = parse_qs(parsed.query)
            emotion = query.get("emotion", [""])[0]
            style = query.get("style", [""])[0]
            tempo = query.get("tempo", [""])[0]
            limit = int(query.get("limit", ["10"])[0])
            results = _bgm_selector.select(emotion=emotion or None, style=style or None,
                                            tempo=tempo or None, limit=limit)
            self._send_json({"bgms": results, "total": len(results)})

        elif path == "/api/bgm/stats":
            if not _bgm_selector:
                self._send_json({"error": "BGM选择器未初始化"}, 500)
                return
            self._send_json(_bgm_selector.get_stats())

        # 音效搜索
        elif path == "/api/sfx/search":
            if not _sfx_manager:
                self._send_json({"error": "音效管理器未初始化"}, 500)
                return
            query = parse_qs(parsed.query)
            keyword = query.get("keyword", [""])[0]
            category = query.get("category", [""])[0]
            limit = int(query.get("limit", ["20"])[0])
            results = _sfx_manager.search(keyword=keyword or None, category=category or None, limit=limit)
            self._send_json({"sfxs": results, "total": len(results)})

        elif path == "/api/sfx/categories":
            if not _sfx_manager:
                self._send_json({"error": "音效管理器未初始化"}, 500)
                return
            self._send_json({"categories": _sfx_manager.list_categories()})

        # 素材管理
        elif path == "/api/assets":
            if not _asset_manager:
                self._send_json({"error": "素材管理器未初始化"}, 500)
                return
            query = parse_qs(parsed.query)
            keyword = query.get("keyword", [""])[0]
            asset_type = query.get("type", [""])[0]
            limit = int(query.get("limit", ["20"])[0])
            results = _asset_manager.search(keyword=keyword or None, asset_type=asset_type or None, limit=limit)
            self._send_json({"assets": results, "total": len(results)})

        elif path == "/api/assets/stats":
            if not _asset_manager:
                self._send_json({"error": "素材管理器未初始化"}, 500)
                return
            self._send_json(_asset_manager.get_stats())

        # 智能导演能力列表
        elif path == "/api/director/skills":
            if not _director_v3:
                self._send_json({"error": "导演决策引擎未初始化"}, 500)
                return
            self._send_json({"skills": _director_v3.list_skills()})

        # 自然语言意图列表
        elif path == "/api/nl/intents":
            if not _nl_enhancer:
                self._send_json({"error": "自然语言增强模块未初始化"}, 500)
                return
            self._send_json({"intents": _nl_enhancer.list_intents()})

        # TTS情绪/角色列表
        elif path == "/api/tts/emotions":
            if not _tts_enhancer:
                self._send_json({"error": "TTS增强模块未初始化"}, 500)
                return
            self._send_json({"emotions": _tts_enhancer.list_emotions()})

        elif path == "/api/tts/characters":
            if not _tts_enhancer:
                self._send_json({"error": "TTS增强模块未初始化"}, 500)
                return
            self._send_json({"characters": _tts_enhancer.list_characters()})

        else:
            self._send_json({"error": "端点不存在", "path": path}, 404)

    def do_POST(self):
        """处理POST请求"""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        # 文件上传端点（multipart/form-data）
        if path == "/api/upload":
            self._handle_upload()
            return

        body = self._read_body()

        if path == "/api/video/generate":
            # 验证必要参数
            if "prompt" not in body:
                self._send_json({"error": "缺少prompt参数"}, 400)
                return

            task_id = task_manager.create_task("video_generation", body)
            task_manager.run_task_async(task_id, generate_video_task, body)
            self._send_json({
                "task_id": task_id,
                "status": TASK_PENDING,
                "message": "视频生成任务已创建",
            }, 202)

        elif path == "/api/draft/create":
            # 创建剪映工程（简化版，后续完善）
            if "project_name" not in body:
                self._send_json({"error": "缺少project_name参数"}, 400)
                return
            task_id = task_manager.create_task("draft_create", body)
            self._send_json({
                "task_id": task_id,
                "status": TASK_PENDING,
                "message": "剪映工程创建任务已创建（功能开发中）",
            }, 202)

        elif path == "/api/create/template":
            # 模板风格复刻：从教学视频创建类似风格的剪映模板
            if "video_path" not in body:
                self._send_json({"error": "缺少video_path参数"}, 400)
                return
            video_path = body["video_path"]
            if not os.path.exists(video_path):
                self._send_json({"error": f"视频文件不存在: {video_path}"}, 400)
                return
            task_id = task_manager.create_task("template_create", body)
            task_manager.run_task_async(task_id, create_template_task, body)
            self._send_json({
                "task_id": task_id,
                "status": TASK_PENDING,
                "message": "模板风格复刻任务已创建",
            }, 202)

        elif path.startswith("/api/task/") and path.endswith("/cancel"):
            task_id = path.split("/")[-2]
            task = task_manager.get_task(task_id)
            if task and task["status"] in [TASK_PENDING, TASK_RUNNING]:
                task_manager.update_task(task_id, status=TASK_CANCELLED)
                self._send_json({"task_id": task_id, "status": TASK_CANCELLED, "message": "任务已取消"})
            else:
                self._send_json({"error": "任务不存在或无法取消"}, 404)

        # 模板市场POST端点
        elif path.startswith("/api/template/") and path.endswith("/rate"):
            if not _template_market:
                self._send_json({"error": "模板市场未初始化"}, 500)
                return
            template_id = path.split("/")[-2]
            rating = body.get("rating", 0)
            comment = body.get("comment", "")
            user = body.get("user", "anonymous")
            if not rating or rating < 1 or rating > 5:
                self._send_json({"error": "评分必须在1-5之间"}, 400)
                return
            success = _template_market.rate_template(template_id, rating, comment, user)
            if success:
                self._send_json({"message": "评分成功", "template_id": template_id})
            else:
                self._send_json({"error": "模板不存在"}, 404)

        elif path.startswith("/api/template/") and path.endswith("/use"):
            if not _template_market:
                self._send_json({"error": "模板市场未初始化"}, 500)
                return
            template_id = path.split("/")[-2]
            success = _template_market.increment_use(template_id)
            if success:
                self._send_json({"message": "使用计数已更新", "template_id": template_id})
            else:
                self._send_json({"error": "模板不存在"}, 404)

        elif path == "/api/templates":
            if not _template_market:
                self._send_json({"error": "模板市场未初始化"}, 500)
                return
            name = body.get("name", "")
            if not name:
                self._send_json({"error": "缺少name参数"}, 400)
                return
            template = _template_market.add_template(
                name=name,
                description=body.get("description", ""),
                category=body.get("category", ""),
                tags=body.get("tags", []),
                file_path=body.get("file_path", ""),
                author=body.get("author", "user"),
                style=body.get("style", ""),
                scene=body.get("scene", ""),
                duration=body.get("duration", ""),
                difficulty=body.get("difficulty", "简单"),
                aspect_ratio=body.get("aspect_ratio", "9:16竖屏"),
            )
            self._send_json({"message": "模板创建成功", "template_id": template.template_id}, 201)

        # 插件管理POST端点
        elif path.startswith("/api/plugin/") and path.endswith("/enable"):
            if not _plugin_manager:
                self._send_json({"error": "插件管理器未初始化"}, 500)
                return
            plugin_id = path.split("/")[-2]
            success = _plugin_manager.enable_plugin(plugin_id)
            if success:
                self._send_json({"message": "插件已启用", "plugin_id": plugin_id})
            else:
                self._send_json({"error": "启用插件失败"}, 500)

        elif path.startswith("/api/plugin/") and path.endswith("/disable"):
            if not _plugin_manager:
                self._send_json({"error": "插件管理器未初始化"}, 500)
                return
            plugin_id = path.split("/")[-2]
            success = _plugin_manager.disable_plugin(plugin_id)
            if success:
                self._send_json({"message": "插件已禁用", "plugin_id": plugin_id})
            else:
                self._send_json({"error": "禁用插件失败"}, 500)

        elif path.startswith("/api/plugin/") and path.endswith("/reload"):
            if not _plugin_manager:
                self._send_json({"error": "插件管理器未初始化"}, 500)
                return
            plugin_id = path.split("/")[-2]
            _plugin_manager.unload_plugin(plugin_id)
            plugin = _plugin_manager.load_plugin(plugin_id)
            if plugin:
                self._send_json({"message": "插件已重新加载", "plugin_id": plugin_id})
            else:
                self._send_json({"error": "重新加载插件失败"}, 500)

        elif path.startswith("/api/capability/") and path.endswith("/call"):
            if not _plugin_manager:
                self._send_json({"error": "插件管理器未初始化"}, 500)
                return
            capability_id = path.split("/")[-2]
            try:
                result = _plugin_manager.call_capability(capability_id, body)
                self._send_json({"status": "success", "result": result})
            except ValueError as e:
                self._send_json({"error": str(e)}, 404)
            except Exception as e:
                self._send_json({"error": f"调用能力失败: {e}"}, 500)

        # TTS品质增强
        elif path == "/api/tts/enhance":
            if not _tts_enhancer:
                self._send_json({"error": "TTS增强模块未初始化"}, 500)
                return
            text = body.get("text", "")
            if not text:
                self._send_json({"error": "缺少text参数"}, 400)
                return
            emotion = body.get("emotion", "平静")
            character = body.get("character", "narrator")
            config = _tts_enhancer.enhance_tts_config(text, emotion=emotion, character=character)
            self._send_json(config)

        # TTS字幕时间轴生成
        elif path == "/api/tts/subtitle-timeline":
            if not _tts_enhancer:
                self._send_json({"error": "TTS增强模块未初始化"}, 500)
                return
            configs = body.get("configs", [])
            start_time = body.get("start_time", 0.0)
            if not configs:
                self._send_json({"error": "缺少configs参数"}, 400)
                return
            timeline = _tts_enhancer.generate_subtitle_timeline(configs, start_time=start_time)
            self._send_json({"timeline": timeline, "total": len(timeline)})

        # 智能路由决策
        elif path == "/api/director/route":
            if not _director_v3:
                self._send_json({"error": "导演决策引擎未初始化"}, 500)
                return
            task_type = body.get("task_type", "")
            if not task_type:
                self._send_json({"error": "缺少task_type参数"}, 400)
                return
            requirements = body.get("requirements", {})
            result = _director_v3.route_task(task_type, requirements=requirements)
            self._send_json(result)

        # 镜头语言决策
        elif path == "/api/director/shot":
            if not _director_v3:
                self._send_json({"error": "导演决策引擎未初始化"}, 500)
                return
            emotion = body.get("emotion", "平静")
            purpose = body.get("purpose")
            duration_hint = body.get("duration_hint")
            result = _director_v3.decide_shot(emotion=emotion, purpose=purpose, duration_hint=duration_hint)
            self._send_json(result)

        # 情绪曲线生成
        elif path == "/api/director/emotion-curve":
            if not _director_v3:
                self._send_json({"error": "导演决策引擎未初始化"}, 500)
                return
            duration = body.get("duration", 30.0)
            structure = body.get("structure", "classic")
            result = _director_v3.generate_emotion_curve(duration=duration, structure=structure)
            self._send_json({"curve": result, "segments": len(result)})

        # 全自动流水线
        elif path == "/api/pipeline/run":
            if not _auto_pipeline:
                self._send_json({"error": "全自动流水线未初始化"}, 500)
                return
            topic = body.get("topic", "")
            if not topic:
                self._send_json({"error": "缺少topic参数"}, 400)
                return
            template = body.get("template", "vlog")
            style = body.get("style", "cinematic")
            resolution = body.get("resolution", "portrait_768")
            generate_assets = body.get("generate_assets", True)
            generate_audio = body.get("generate_audio", True)
            build_draft = body.get("build_draft", True)
            enhance_quality = body.get("enhance_quality", True)

            # 异步执行流水线
            task_id = task_manager.create_task("auto_pipeline", body)
            def run_pipeline(task_id, params):
                try:
                    task_manager.update_task(task_id, status=TASK_RUNNING, started_at=time.time())
                    result = _auto_pipeline.run(
                        topic=params.get("topic", ""),
                        template=params.get("template", "vlog"),
                        style=params.get("style", "cinematic"),
                        resolution=params.get("resolution", "portrait_768"),
                        generate_assets=params.get("generate_assets", True),
                        generate_audio=params.get("generate_audio", True),
                        build_draft=params.get("build_draft", True),
                        enhance_quality=params.get("enhance_quality", True),
                    )
                    task_manager.update_task(task_id, status=TASK_COMPLETED, result=result.__dict__, completed_at=time.time())
                except Exception as e:
                    task_manager.update_task(task_id, status=TASK_FAILED, error=str(e), completed_at=time.time())

            task_manager.run_task_async(task_id, run_pipeline, body)
            self._send_json({
                "task_id": task_id,
                "status": TASK_PENDING,
                "message": "全自动流水线任务已创建",
            }, 202)

        # 添加素材
        elif path == "/api/assets/add":
            if not _asset_manager:
                self._send_json({"error": "素材管理器未初始化"}, 500)
                return
            file_path = body.get("file_path", "")
            if not file_path or not os.path.exists(file_path):
                self._send_json({"error": "文件不存在或缺少file_path参数"}, 400)
                return
            asset_type = body.get("asset_type", "image")
            tags = body.get("tags", [])
            metadata = body.get("metadata", {})
            result = _asset_manager.add_asset(file_path, asset_type=asset_type, tags=tags, metadata=metadata)
            self._send_json(result)

        # 素材智能推荐
        elif path == "/api/assets/recommend":
            if not _asset_manager:
                self._send_json({"error": "素材管理器未初始化"}, 500)
                return
            context = body.get("context", "")
            asset_type = body.get("asset_type", "image")
            count = body.get("count", 5)
            results = _asset_manager.recommend(context=context, asset_type=asset_type, count=count)
            self._send_json({"recommendations": results, "total": len(results)})

        # 自然语言解析
        elif path == "/api/nl/parse":
            if not _nl_enhancer:
                self._send_json({"error": "自然语言增强模块未初始化"}, 500)
                return
            instruction = body.get("instruction", "")
            if not instruction:
                self._send_json({"error": "缺少instruction参数"}, 400)
                return
            result = _nl_enhancer.parse_instruction(instruction)
            self._send_json(result)

        # 创意扩展
        elif path == "/api/nl/expand":
            if not _nl_enhancer:
                self._send_json({"error": "自然语言增强模块未初始化"}, 500)
                return
            base_idea = body.get("base_idea", "")
            if not base_idea:
                self._send_json({"error": "缺少base_idea参数"}, 400)
                return
            direction = body.get("direction", "general")
            results = _nl_enhancer.expand_creative(base_idea, direction=direction)
            self._send_json({"expansions": results, "total": len(results)})

        else:
            self._send_json({"error": "端点不存在", "path": path}, 404)

    def log_message(self, format, *args):
        """简化日志输出"""
        logger.info(f"{self.address_string()} - {format % args}")


def main():
    """启动API服务"""
    import argparse
    parser = argparse.ArgumentParser(description="AI Video Editor API服务")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    server = HTTPServer((args.host, args.port), APIHandler)
    logger.info(f"=" * 60)
    logger.info(f"AI Video Editor API 服务启动")
    logger.info(f"地址: http://{args.host}:{args.port}")
    logger.info(f"健康检查: http://{args.host}:{args.port}/api/health")
    logger.info(f"能力列表: http://{args.host}:{args.port}/api/capabilities")
    logger.info(f"=" * 60)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("服务停止")
        server.shutdown()


if __name__ == "__main__":
    main()
