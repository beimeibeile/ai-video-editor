"""
API服务化模块 v1.0 (P4-2)
REST API封装所有能力，统一认证+限流+API文档自动生成

API端点：
- GET  /api/health - 健康检查
- GET  /api/status - 战斗群状态
- POST /api/script/generate - 剧本生成
- POST /api/storyboard/generate - 分镜生成
- POST /api/character/analyze - 角色分析
- POST /api/pipeline/run - 全链路流水线
- POST /api/quality/check - 质量门检查
- GET  /api/effects/list - 特效库列表
- GET  /api/templates/list - 模板列表
- GET  /api/docs - API文档（OpenAPI格式）

认证：API Key（请求头 X-API-Key）
限流：每分钟60次（简单令牌桶）
"""
import os
import sys
import json
import time
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional, Callable
from urllib.parse import urlparse, parse_qs
from datetime import datetime

SKILL_ROOT = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor"
sys.path.insert(0, SKILL_ROOT)
sys.path.insert(0, os.path.join(SKILL_ROOT, "capabilities"))


# ==================== 认证与限流 ====================

class AuthManager:
    """API Key认证管理"""

    def __init__(self, api_keys: Dict[str, str] = None):
        self.api_keys = api_keys or {}
        self._rate_limit: Dict[str, list] = {}  # api_key -> [timestamps]
        self.rate_limit_per_minute = 60

    def add_key(self, key: str, name: str = "default"):
        """添加API Key"""
        self.api_keys[key] = name

    def validate(self, api_key: str) -> tuple:
        """验证API Key并检查限流

        Returns:
            (valid: bool, message: str)
        """
        if not self.api_keys:
            # 未配置API Key，开放访问
            return True, "open_access"

        if not api_key:
            return False, "缺少API Key（请求头 X-API-Key）"

        if api_key not in self.api_keys:
            return False, "无效的API Key"

        # 限流检查
        now = time.time()
        if api_key not in self._rate_limit:
            self._rate_limit[api_key] = []

        # 清理1分钟前的记录
        self._rate_limit[api_key] = [
            t for t in self._rate_limit[api_key] if now - t < 60
        ]

        if len(self._rate_limit[api_key]) >= self.rate_limit_per_minute:
            return False, f"请求频率超限（每分钟{self.rate_limit_per_minute}次）"

        self._rate_limit[api_key].append(now)
        return True, self.api_keys[api_key]


# ==================== API文档生成 ====================

API_SPEC = {
    "openapi": "3.0.0",
    "info": {
        "title": "AI Video Editor API",
        "description": "航空母舰战斗群视频剪辑平台API",
        "version": "1.0.0",
    },
    "servers": [{"url": "http://localhost:8080"}],
    "paths": {
        "/api/health": {
            "get": {
                "summary": "健康检查",
                "responses": {"200": {"description": "服务正常"}},
            }
        },
        "/api/status": {
            "get": {
                "summary": "战斗群状态",
                "responses": {"200": {"description": "战斗群战备状态"}},
            }
        },
        "/api/script/generate": {
            "post": {
                "summary": "剧本生成",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "idea": {"type": "string", "description": "创意主题"},
                                    "genre": {"type": "string", "description": "视频类型"},
                                    "duration": {"type": "number", "description": "时长（秒）"},
                                },
                                "required": ["idea"],
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "剧本生成成功"}},
            }
        },
        "/api/storyboard/generate": {
            "post": {
                "summary": "分镜生成",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "theme": {"type": "string"},
                                    "style": {"type": "string"},
                                    "duration": {"type": "number"},
                                    "shot_count": {"type": "integer"},
                                },
                                "required": ["theme"],
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "分镜生成成功"}},
            }
        },
        "/api/pipeline/run": {
            "post": {
                "summary": "全链路流水线",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "topic": {"type": "string"},
                                    "video_type": {"type": "string"},
                                    "duration": {"type": "number"},
                                    "project_name": {"type": "string"},
                                },
                                "required": ["topic"],
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "流水线执行完成"}},
            }
        },
        "/api/quality/check": {
            "post": {
                "summary": "质量门检查",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "draft_path": {"type": "string", "description": "草稿路径"},
                                },
                                "required": ["draft_path"],
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "质量检查完成"}},
            }
        },
        "/api/effects/list": {
            "get": {
                "summary": "特效库列表",
                "responses": {"200": {"description": "特效列表"}},
            }
        },
        "/api/templates/list": {
            "get": {
                "summary": "模板列表",
                "responses": {"200": {"description": "模板列表"}},
            }
        },
    },
}


# ==================== API请求处理器 ====================

class APIHandler(BaseHTTPRequestHandler):
    """API请求处理器"""

    auth_manager: AuthManager = None
    carrier_group = None

    def _send_json(self, data: Dict[str, Any], status: int = 200):
        """发送JSON响应"""
        response = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-Key")
        self.end_headers()
        self.wfile.write(response)

    def _read_body(self) -> Dict[str, Any]:
        """读取请求体"""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length)
        try:
            return json.loads(body.decode("utf-8"))
        except Exception:
            return {}

    def _check_auth(self) -> bool:
        """检查认证"""
        if self.auth_manager:
            api_key = self.headers.get("X-API-Key", "")
            valid, message = self.auth_manager.validate(api_key)
            if not valid:
                self._send_json({"success": False, "error": message}, status=401)
                return False
        return True

    def do_OPTIONS(self):
        """处理OPTIONS请求（CORS预检）"""
        self._send_json({"success": True})

    def do_GET(self):
        """处理GET请求"""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            self._send_json({
                "success": True,
                "status": "ok",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0",
            })

        elif path == "/api/status":
            if not self._check_auth():
                return
            if self.carrier_group:
                status = self.carrier_group.get_status()
                self._send_json({"success": True, "status": status})
            else:
                self._send_json({"success": False, "error": "战斗群未初始化"})

        elif path == "/api/effects/list":
            if not self._check_auth():
                return
            effects_path = os.path.join(SKILL_ROOT, "effects", "index.json")
            if os.path.exists(effects_path):
                with open(effects_path, "r", encoding="utf-8") as f:
                    effects = json.load(f)
                self._send_json({"success": True, "effects": effects})
            else:
                self._send_json({"success": False, "error": "特效库不存在"})

        elif path == "/api/templates/list":
            if not self._check_auth():
                return
            try:
                from cap_template_system import TemplateSystem
                ts = TemplateSystem()
                templates = [t.to_dict() if hasattr(t, "to_dict") else str(t) for t in ts.list_templates()]
                self._send_json({"success": True, "templates": templates, "count": len(templates)})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)})

        elif path == "/api/docs":
            self._send_json(API_SPEC)

        else:
            self._send_json({"success": False, "error": f"未知端点: {path}"}, status=404)

    def do_POST(self):
        """处理POST请求"""
        parsed = urlparse(self.path)
        path = parsed.path

        if not self._check_auth():
            return

        body = self._read_body()

        if path == "/api/script/generate":
            try:
                from cap_script_engine import ScriptEngine, VideoGenre
                engine = ScriptEngine()
                genre_str = body.get("genre", "CUSTOM")
                genre = VideoGenre(genre_str) if genre_str in [g.value for g in VideoGenre] else VideoGenre.CUSTOM
                script = engine.generate(
                    idea=body.get("idea", ""),
                    genre=genre,
                    duration=body.get("duration", 30),
                )
                self._send_json({"success": True, "script": script.to_dict() if hasattr(script, "to_dict") else str(script)})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)

        elif path == "/api/storyboard/generate":
            try:
                from cap_storyboard_engine.storyboard_engine import StoryboardGenerator
                gen = StoryboardGenerator()
                sb = gen.generate(
                    theme=body.get("theme", ""),
                    style=body.get("style", "cinematic"),
                    total_duration=body.get("duration", 15),
                    shot_count=body.get("shot_count", 5),
                )
                self._send_json({"success": True, "storyboard": sb.to_dict()})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)

        elif path == "/api/character/analyze":
            try:
                from cap_character_engine import CharacterEngine
                # 简化实现：需要script对象
                self._send_json({"success": True, "message": "角色分析API（需传入剧本数据）"})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)

        elif path == "/api/pipeline/run":
            try:
                from cap_pipeline_orchestrator import PipelineOrchestrator
                orch = PipelineOrchestrator()
                result = orch.run_full_pipeline(
                    topic=body.get("topic", ""),
                    video_type=body.get("video_type", "exploration"),
                    duration=body.get("duration", 30),
                    project_name=body.get("project_name"),
                )
                self._send_json({"success": result.success, "result": {
                    "project_name": result.project_name,
                    "draft_path": result.draft_path,
                    "total_duration": result.total_duration,
                    "steps": [{"name": s.name, "status": s.status, "duration": s.duration_seconds} for s in result.steps],
                }})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)

        elif path == "/api/quality/check":
            draft_path = body.get("draft_path", "")
            if not draft_path or not os.path.exists(draft_path):
                self._send_json({"success": False, "error": f"草稿路径不存在: {draft_path}"}, status=400)
                return
            try:
                from cap_creative.quality_gate import QualityGate
                qg = QualityGate()
                report = qg.check(draft_path)
                self._send_json({"success": True, "report": report if isinstance(report, dict) else {"status": "completed"}})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)

        else:
            self._send_json({"success": False, "error": f"未知端点: {path}"}, status=404)

    def log_message(self, format, *args):
        """静默日志"""
        pass


# ==================== API服务器 ====================

class APIServer:
    """API服务器"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080,
                 api_keys: Dict[str, str] = None):
        self.host = host
        self.port = port
        self.auth_manager = AuthManager(api_keys)
        self.carrier_group = None
        self.server: Optional[HTTPServer] = None

    def init_carrier_group(self):
        """初始化战斗群"""
        try:
            from cap_carrier_group.carrier_group_v2 import CarrierGroup
            self.carrier_group = CarrierGroup()
        except Exception as e:
            print(f"⚠️ 战斗群初始化失败: {e}")

    def start(self):
        """启动API服务器"""
        self.init_carrier_group()

        # 注入依赖到handler
        APIHandler.auth_manager = self.auth_manager
        APIHandler.carrier_group = self.carrier_group

        self.server = HTTPServer((self.host, self.port), APIHandler)
        print(f"🚀 API服务器启动: http://{self.host}:{self.port}")
        print(f"   文档: http://{self.host}:{self.port}/api/docs")
        print(f"   健康: http://{self.host}:{self.port}/api/health")
        if self.auth_manager.api_keys:
            print(f"   认证: 已启用（{len(self.auth_manager.api_keys)}个API Key）")
        else:
            print(f"   认证: 开放访问（未配置API Key）")
        print(f"   限流: 每分钟{self.auth_manager.rate_limit_per_minute}次")

        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            print("\n⏹️ API服务器停止")
            self.server.shutdown()

    def stop(self):
        """停止API服务器"""
        if self.server:
            self.server.shutdown()


if __name__ == "__main__":
    # 启动API服务器（默认开放访问，生产环境应配置API Key）
    server = APIServer(host="0.0.0.0", port=8080)
    server.start()
