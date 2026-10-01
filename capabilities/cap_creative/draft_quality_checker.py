"""
剪映工程质量门检查器
从draft_content.json自动提取数据，运行edit类别质量门，输出文本+HTML报告

使用方法:
    from draft_quality_checker import DraftQualityChecker
    checker = DraftQualityChecker(r"D:\JianyingProDrafts\MyProject")
    report = checker.check()
    checker.save_html_report(report, "quality_report.html")
"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from quality_gate import validate, GateReport
    _QG_AVAILABLE = True
except ImportError:
    _QG_AVAILABLE = False


class DraftQualityChecker:
    """剪映工程质量门检查器"""

    def __init__(self, draft_dir: str, fps: int = 30):
        self.draft_dir = draft_dir
        self.fps = fps
        self.draft_data = None
        self._load()

    def _load(self):
        """加载draft_content.json"""
        content_file = os.path.join(self.draft_dir, "draft_content.json")
        info_file = os.path.join(self.draft_dir, "draft_info.json")

        target = content_file if os.path.exists(content_file) else info_file
        if not os.path.exists(target):
            raise FileNotFoundError(f"未找到草稿文件: {self.draft_dir}")

        with open(target, 'r', encoding='utf-8') as f:
            self.draft_data = json.load(f)

    def extract_edit_data(self) -> Dict[str, Any]:
        """从剪映工程提取edit类别质量门所需数据"""
        data = self.draft_data
        tracks = data.get("tracks", [])

        segments = []
        transitions = []
        timestamps = set()
        total_duration_us = 0

        for track in tracks:
            track_type = track.get("type", "")
            for seg in track.get("segments", []):
                start_us = seg.get("target_timerange", {}).get("start", 0)
                dur_us = seg.get("target_timerange", {}).get("duration", 0)
                start_s = start_us / 1_000_000
                dur_s = dur_us / 1_000_000
                end_s = start_s + dur_s

                seg_info = {
                    "start": start_s,
                    "duration": dur_s,
                    "end": end_s,
                    "track_type": track_type,
                    "has_subtitle": track_type == "text",
                    "has_audio": track_type in ("audio", "video"),
                    "material_id": seg.get("material_id", ""),
                }
                segments.append(seg_info)

                timestamps.add(round(start_s, 4))
                timestamps.add(round(end_s, 4))

                if end_s > total_duration_us / 1_000_000:
                    total_duration_us = int(end_s * 1_000_000)

                # 检查转场
                if seg.get("transitions"):
                    for trans in seg["transitions"]:
                        trans_start = trans.get("start", start_us) / 1_000_000
                        transitions.append({"start": trans_start})

        # 画布信息
        canvas = data.get("canvas_config", {})
        canvas_w = canvas.get("width", 1080)
        canvas_h = canvas.get("height", 1920)
        canvas_ratio = canvas_w / canvas_h if canvas_h > 0 else 9 / 16

        return {
            "total_duration": total_duration_us / 1_000_000,
            "max_duration": 180,
            "segments": segments,
            "transitions": transitions,
            "timestamps": sorted(timestamps),
            "fps": self.fps,
            "canvas_ratio": canvas_ratio,
            "canvas_width": canvas_w,
            "canvas_height": canvas_h,
        }

    def check(self) -> Optional[GateReport]:
        """运行质量门检查"""
        if not _QG_AVAILABLE:
            print("❌ quality_gate模块不可用")
            return None

        edit_data = self.extract_edit_data()
        report = validate("edit", edit_data)

        print(report.summary())
        print(f"\n📊 工程统计:")
        print(f"   总时长: {edit_data['total_duration']:.1f}秒")
        print(f"   片段数: {len(edit_data['segments'])}")
        print(f"   转场数: {len(edit_data['transitions'])}")
        print(f"   画布: {edit_data['canvas_width']}x{edit_data['canvas_height']}")

        return report

    def save_html_report(self, report: GateReport, output_path: str, project_name: str = ""):
        """保存HTML质量门报告（参考shuohao report模式）"""
        if not report:
            return

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status_color = {
            "pass": "#22c55e", "fail": "#ef4444", "warn": "#f59e0b", "skip": "#6b7280"
        }
        status_icon = {"pass": "✅", "fail": "❌", "warn": "⚠️", "skip": "⏭️"}

        rows_html = ""
        for r in report.results:
            color = status_color.get(r.status.value, "#6b7280")
            icon = status_icon.get(r.status.value, "?")
            detail_html = f'<div class="detail">{r.detail}</div>' if r.detail and r.status.value != "pass" else ""
            rows_html += f"""
            <tr>
                <td class="gate-id">{r.gate_id}</td>
                <td>{r.gate_name}</td>
                <td style="color:{color};font-weight:bold">{icon} {r.status.value.upper()}</td>
                <td>{r.message}{detail_html}</td>
            </tr>"""

        overall_color = "#22c55e" if report.all_passed else "#ef4444"
        overall_text = "全部通过" if report.all_passed else f"{report.failed} 项未通过"

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>质量门报告 - {project_name or self.draft_dir}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, 'Segoe UI', sans-serif; background:#0f172a; color:#e2e8f0; padding:24px; }}
.container {{ max-width:900px; margin:0 auto; }}
.header {{ background:linear-gradient(135deg,#1e293b,#334155); border-radius:12px; padding:24px; margin-bottom:20px; border:1px solid #334155; }}
.header h1 {{ font-size:22px; margin-bottom:8px; }}
.header .meta {{ color:#94a3b8; font-size:13px; }}
.stats {{ display:grid; grid-template-columns:repeat(5,1fr); gap:12px; margin:20px 0; }}
.stat {{ background:#1e293b; border-radius:8px; padding:16px; text-align:center; border:1px solid #334155; }}
.stat .num {{ font-size:28px; font-weight:bold; }}
.stat .label {{ font-size:12px; color:#94a3b8; margin-top:4px; }}
.overall {{ text-align:center; padding:16px; border-radius:8px; margin-bottom:20px; font-size:18px; font-weight:bold; background:{overall_color}22; border:1px solid {overall_color}; color:{overall_color}; }}
table {{ width:100%; border-collapse:collapse; background:#1e293b; border-radius:8px; overflow:hidden; border:1px solid #334155; }}
th {{ background:#334155; padding:12px; text-align:left; font-size:13px; color:#cbd5e1; }}
td {{ padding:10px 12px; border-bottom:1px solid #334155; font-size:13px; }}
tr:last-child td {{ border-bottom:none; }}
.gate-id {{ font-family:monospace; color:#60a5fa; }}
.detail {{ font-size:11px; color:#94a3b8; margin-top:4px; padding-left:8px; border-left:2px solid #475569; }}
.footer {{ text-align:center; color:#64748b; font-size:12px; margin-top:20px; }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🎬 剪辑质量门报告</h1>
        <div class="meta">工程: {project_name or os.path.basename(self.draft_dir)} | 检查时间: {now}</div>
    </div>
    <div class="overall">{overall_text}</div>
    <div class="stats">
        <div class="stat"><div class="num">{report.total}</div><div class="label">总检查项</div></div>
        <div class="stat"><div class="num" style="color:#22c55e">{report.passed}</div><div class="label">通过</div></div>
        <div class="stat"><div class="num" style="color:#ef4444">{report.failed}</div><div class="label">失败</div></div>
        <div class="stat"><div class="num" style="color:#f59e0b">{report.warned}</div><div class="label">警告</div></div>
        <div class="stat"><div class="num" style="color:#6b7280">{report.skipped}</div><div class="label">跳过</div></div>
    </div>
    <table>
        <thead><tr><th>编号</th><th>检查项</th><th>状态</th><th>说明</th></tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
    <div class="footer">ai-video-editor 质量门系统 | 参考 shuohao-skills report 模式</div>
</div>
</body>
</html>"""

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n📄 HTML报告已保存: {output_path}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        draft_dir = sys.argv[1]
    else:
        draft_dir = r"D:\JianyingProDrafts\JianyingPro Drafts\SubtitleBar_Demo"

    print(f"检查工程: {draft_dir}")
    checker = DraftQualityChecker(draft_dir)
    report = checker.check()
    if report:
        out = os.path.join(os.path.dirname(draft_dir), "quality_report.html")
        checker.save_html_report(report, out)
