"""
用户工作台 v2.0 后端API
面向普通用户的视频创建服务

端点：
- GET /api/projects - 历史项目列表
- POST /api/create - 创建视频（快速模式）
- GET /api/status/<id> - 查询生成状态
- GET /api/templates - 可用模板/风格列表
- POST /api/promo - 快速宣传视频生成
"""
import os
import sys
import json
import uuid
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# 技能路径
SKILL_ROOT = r"C:\Users\Administrator\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\ai-video-editor"
WORKBENCH_DIR = os.path.join(SKILL_ROOT, "user_workbench")
PROJECTS_DB = os.path.join(WORKBENCH_DIR, "projects.json")

sys.path.insert(0, os.path.join(SKILL_ROOT, "capabilities"))
sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))

# 可用风格
STYLES = [
    {"id": "sunset", "name": "日落橙", "color": "#ff6262", "desc": "温暖活力，适合vlog/旅行"},
    {"id": "ocean", "name": "海洋蓝", "color": "#0077b6", "desc": "科技冷静，适合产品/科普"},
    {"id": "forest", "name": "森林绿", "color": "#388e3c", "desc": "自然清新，适合美食/生活"},
    {"id": "purple", "name": "梦幻紫", "color": "#7b1fa2", "desc": "神秘高级，适合剧情/艺术"},
    {"id": "dark", "name": "暗夜黑", "color": "#28283c", "desc": "电影感，适合短片/预告"},
    {"id": "gold", "name": "黄金色", "color": "#daa520", "desc": "奢华大气，适合颁奖/庆典"},
    {"id": "warm", "name": "暖橙红", "color": "#dc5028", "desc": "热情奔放，适合运动/活动"},
    {"id": "cool", "name": "冷调蓝", "color": "#3264b4", "desc": "理性专业，适合商务/教育"},
]

# 视频类型
VIDEO_TYPES = [
    {"id": "promo", "name": "产品宣传", "icon": "📢", "desc": "产品介绍/品牌宣传/活动推广"},
    {"id": "vlog", "name": "旅行Vlog", "icon": "✈️", "desc": "旅行记录/生活日常/美食探店"},
    {"id": "tutorial", "name": "知识科普", "icon": "📚", "desc": "教程讲解/知识科普/技能分享"},
    {"id": "story", "name": "剧情短片", "icon": "🎬", "desc": "故事短片/微电影/情感剧情"},
    {"id": "intro", "name": "片头片尾", "icon": "🎞️", "desc": "频道片头/视频结尾/转场动画"},
]


def load_projects():
    """加载历史项目"""
    if os.path.exists(PROJECTS_DB):
        with open(PROJECTS_DB, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_projects(projects):
    """保存项目列表"""
    os.makedirs(WORKBENCH_DIR, exist_ok=True)
    with open(PROJECTS_DB, 'w', encoding='utf-8') as f:
        json.dump(projects, f, ensure_ascii=False, indent=2)


def add_project(project):
    """添加项目"""
    projects = load_projects()
    projects.insert(0, project)
    save_projects(projects)


def update_project(project_id, updates):
    """更新项目状态"""
    projects = load_projects()
    for p in projects:
        if p.get('id') == project_id:
            p.update(updates)
            break
    save_projects(projects)


class UserWorkbenchHandler(BaseHTTPRequestHandler):
    """用户工作台HTTP请求处理器"""

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, path):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                body = f.read().encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/' or path == '/index.html':
            self._send_html(os.path.join(WORKBENCH_DIR, 'index.html'))
        elif path == '/api/projects':
            projects = load_projects()
            self._send_json({"projects": projects, "count": len(projects)})
        elif path == '/api/styles':
            self._send_json({"styles": STYLES})
        elif path == '/api/types':
            self._send_json({"types": VIDEO_TYPES})
        elif path.startswith('/api/status/'):
            project_id = path.split('/')[-1]
            projects = load_projects()
            project = next((p for p in projects if p.get('id') == project_id), None)
            if project:
                self._send_json(project)
            else:
                self._send_json({"error": "项目不存在"}, 404)
        else:
            self._send_json({"error": "未知端点"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length else b'{}'
        try:
            data = json.loads(body.decode('utf-8'))
        except:
            data = {}

        if path == '/api/create':
            # 创建视频（快速宣传视频模式）
            title = data.get('title', '未命名视频')
            points = data.get('points', [])
            style = data.get('style', 'ocean')
            duration = float(data.get('duration', 4.0))

            project_id = uuid.uuid4().hex[:8]
            project = {
                "id": project_id,
                "title": title,
                "type": "promo",
                "style": style,
                "status": "running",
                "progress": 0,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "draft_path": "",
            }
            add_project(project)

            # 后台生成
            def generate():
                try:
                    from cap_promo_generator import PromoVideoGenerator
                    gen = PromoVideoGenerator()
                    update_project(project_id, {"progress": 10, "status": "generating"})

                    result = gen.quick_promo(
                        title=title,
                        points=points if points else ["精彩内容", "敬请期待"],
                        duration_per_point=duration,
                        bg_style=style,
                        project_name=f"User_{project_id}",
                    )
                    update_project(project_id, {
                        "progress": 100,
                        "status": "completed",
                        "draft_path": result.get('draft_path', ''),
                        "duration": result.get('total_duration', 0),
                        "scene_count": result.get('scene_count', 0),
                    })
                except Exception as e:
                    update_project(project_id, {"status": "failed", "error": str(e)})

            threading.Thread(target=generate, daemon=True).start()
            self._send_json({"project_id": project_id, "status": "started"})

        elif path == '/api/promo':
            # 快速宣传视频（同步）
            title = data.get('title', '宣传视频')
            points = data.get('points', [])
            style = data.get('style', 'ocean')

            from cap_promo_generator import PromoVideoGenerator
            gen = PromoVideoGenerator()
            result = gen.quick_promo(
                title=title,
                points=points if points else ["内容1", "内容2", "内容3"],
                bg_style=style,
                project_name=f"Promo_{uuid.uuid4().hex[:6]}",
            )
            self._send_json(result)
        else:
            self._send_json({"error": "未知端点"}, 404)

    def log_message(self, format, *args):
        pass  # 静默日志


def start_server(port=8080):
    """启动用户工作台服务"""
    os.makedirs(WORKBENCH_DIR, exist_ok=True)
    server = HTTPServer(('0.0.0.0', port), UserWorkbenchHandler)
    print(f"🎬 用户工作台 v2.0 已启动: http://localhost:{port}")
    print(f"   项目目录: {WORKBENCH_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n用户工作台已停止")
        server.server_close()


if __name__ == "__main__":
    start_server(8080)
