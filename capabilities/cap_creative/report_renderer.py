"""
质量门 HTML 报告生成器
参考 shuohao-skills 的 report 模式，生成单页可视化报告

特性：
- KPI 带（通过率/通过/失败/警告/跳过）
- 质量门面板（每道门状态+详情+病灶横幅）
- 数据概览（分镜/剪辑指标）
- 导出 JSON 按钮
- 中英双语界面支持
"""

import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>质量门报告 - {title}</title>
<style>
:root {{
  --bg: #0d1117;
  --card: #161b22;
  --border: #30363d;
  --text: #e6edf3;
  --text-muted: #8b949e;
  --pass: #3fb950;
  --fail: #f85149;
  --warn: #d29922;
  --skip: #6e7681;
  --accent: #58a6ff;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: var(--bg);
  color: var(--text);
  padding: 24px;
  line-height: 1.6;
}}
.container {{ max-width: 1200px; margin: 0 auto; }}
h1 {{ font-size: 24px; margin-bottom: 8px; }}
.subtitle {{ color: var(--text-muted); font-size: 14px; margin-bottom: 24px; }}

/* KPI 带 */
.kpi-band {{
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}}
.kpi-card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}}
.kpi-value {{ font-size: 32px; font-weight: 700; }}
.kpi-label {{ font-size: 12px; color: var(--text-muted); margin-top: 4px; }}
.kpi-pass .kpi-value {{ color: var(--pass); }}
.kpi-fail .kpi-value {{ color: var(--fail); }}
.kpi-warn .kpi-value {{ color: var(--warn); }}
.kpi-skip .kpi-value {{ color: var(--skip); }}
.kpi-rate .kpi-value {{ color: var(--accent); }}

/* 病灶横幅 */
.banner {{
  background: rgba(248, 81, 73, 0.1);
  border: 1px solid var(--fail);
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 24px;
  display: none;
}}
.banner.show {{ display: block; }}
.banner-title {{ color: var(--fail); font-weight: 600; margin-bottom: 4px; }}
.banner-detail {{ color: var(--text-muted); font-size: 14px; }}

/* 质量门面板 */
.gate-section {{ margin-bottom: 24px; }}
.gate-section h2 {{
  font-size: 18px;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}}
.gate-list {{ display: flex; flex-direction: column; gap: 8px; }}
.gate-item {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 16px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
}}
.gate-status {{
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
  margin-top: 2px;
}}
.gate-pass {{ background: rgba(63, 185, 80, 0.2); color: var(--pass); }}
.gate-fail {{ background: rgba(248, 81, 73, 0.2); color: var(--fail); }}
.gate-warn {{ background: rgba(210, 153, 34, 0.2); color: var(--warn); }}
.gate-skip {{ background: rgba(110, 118, 129, 0.2); color: var(--skip); }}
.gate-content {{ flex: 1; }}
.gate-name {{ font-weight: 600; font-size: 14px; }}
.gate-id {{ color: var(--text-muted); font-size: 12px; margin-right: 8px; }}
.gate-message {{ font-size: 13px; color: var(--text-muted); margin-top: 2px; }}
.gate-detail {{
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
  padding: 6px 10px;
  background: rgba(0,0,0,0.2);
  border-radius: 4px;
  font-family: monospace;
}}

/* 数据概览 */
.data-overview {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 24px;
}}
.data-overview h2 {{ font-size: 18px; margin-bottom: 12px; }}
.data-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}}
.data-item {{ font-size: 14px; }}
.data-item .label {{ color: var(--text-muted); font-size: 12px; }}
.data-item .value {{ font-weight: 600; }}

/* 导出按钮 */
.export-btn {{
  display: inline-block;
  padding: 8px 16px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  margin-bottom: 24px;
}}
.export-btn:hover {{ opacity: 0.9; }}

.footer {{
  text-align: center;
  color: var(--text-muted);
  font-size: 12px;
  margin-top: 32px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}}
</style>
</head>
<body>
<div class="container">
  <h1>{title}</h1>
  <div class="subtitle">生成时间: {timestamp} | 类别: {category}</div>

  <button class="export-btn" onclick="downloadJSON()">导出 JSON</button>

  <div class="kpi-band">
    <div class="kpi-card kpi-rate">
      <div class="kpi-value">{pass_rate}%</div>
      <div class="kpi-label">通过率</div>
    </div>
    <div class="kpi-card kpi-pass">
      <div class="kpi-value">{passed}</div>
      <div class="kpi-label">通过</div>
    </div>
    <div class="kpi-card kpi-fail">
      <div class="kpi-value">{failed}</div>
      <div class="kpi-label">失败</div>
    </div>
    <div class="kpi-card kpi-warn">
      <div class="kpi-value">{warned}</div>
      <div class="kpi-label">警告</div>
    </div>
    <div class="kpi-card kpi-skip">
      <div class="kpi-value">{skipped}</div>
      <div class="kpi-label">跳过</div>
    </div>
  </div>

  <div class="banner {banner_show}" id="failBanner">
    <div class="banner-title">有 {failed} 道质量门未通过</div>
    <div class="banner-detail">{banner_detail}</div>
  </div>

  <div class="gate-section">
    <h2>质量门检查 ({total} 道)</h2>
    <div class="gate-list">
      {gate_items}
    </div>
  </div>

  {data_overview}

  <div class="footer">
    ai-video-editor 质量门报告 | cap_creative
  </div>
</div>

<script>
const reportData = {json_data};
function downloadJSON() {{
  const blob = new Blob([JSON.stringify(reportData, null, 2)], {{type: 'application/json'}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'quality_gate_report.json';
  a.click();
  URL.revokeObjectURL(url);
}}
</script>
</body>
</html>"""


def render_gate_item(result: Dict[str, Any]) -> str:
    """渲染单道质量门"""
    status = result.get('status', 'skip')
    status_map = {
        'pass': ('gate-pass', '✓'),
        'fail': ('gate-fail', '✗'),
        'warn': ('gate-warn', '!'),
        'skip': ('gate-skip', '→'),
    }
    css_class, icon = status_map.get(status, ('gate-skip', '?'))
    gate_id = result.get('gate_id', '')
    name = result.get('gate_name', '')
    message = result.get('message', '')
    detail = result.get('detail', '')

    detail_html = f'<div class="gate-detail">{detail}</div>' if detail else ''

    return f"""<div class="gate-item">
  <div class="gate-status {css_class}">{icon}</div>
  <div class="gate-content">
    <div class="gate-name"><span class="gate-id">[{gate_id}]</span>{name}</div>
    <div class="gate-message">{message}</div>
    {detail_html}
  </div>
</div>"""


def render_data_overview(data: Optional[Dict[str, Any]]) -> str:
    """渲染数据概览"""
    if not data:
        return ''

    items = []
    # 分镜数据
    if 'shots' in data:
        shots = data['shots']
        items.append(f'<div class="data-item"><div class="label">镜头数</div><div class="value">{len(shots)}</div></div>')
        total_dur = sum(s.get('duration', 0) for s in shots)
        items.append(f'<div class="data-item"><div class="label">镜头总时长</div><div class="value">{total_dur:.1f}s</div></div>')
    if 'total_duration' in data:
        items.append(f'<div class="data-item"><div class="label">总时长</div><div class="value">{data["total_duration"]:.1f}s</div></div>')
    if 'fps' in data:
        items.append(f'<div class="data-item"><div class="label">帧率</div><div class="value">{data["fps"]}fps</div></div>')
    if 'segments' in data:
        items.append(f'<div class="data-item"><div class="label">视频片段</div><div class="value">{len(data["segments"])}</div></div>')
    if 'transitions' in data:
        items.append(f'<div class="data-item"><div class="label">转场数</div><div class="value">{len(data["transitions"])}</div></div>')
    if 'subtitles' in data:
        items.append(f'<div class="data-item"><div class="label">字幕数</div><div class="value">{len(data["subtitles"])}</div></div>')
    if 'subtitle_coverage' in data:
        items.append(f'<div class="data-item"><div class="label">字幕覆盖率</div><div class="value">{data["subtitle_coverage"]:.1%}</div></div>')
    if 'aspect_ratio' in data:
        items.append(f'<div class="data-item"><div class="label">画幅</div><div class="value">{data["aspect_ratio"]}</div></div>')

    if not items:
        return ''

    return f"""<div class="data-overview">
  <h2>数据概览</h2>
  <div class="data-grid">{''.join(items)}</div>
</div>"""


def render_html_report(
    report: Dict[str, Any],
    title: str = "质量门报告",
    category: str = "",
    source_data: Optional[Dict[str, Any]] = None,
    output_path: str = None,
) -> str:
    """
    生成质量门 HTML 报告

    Args:
        report: 质量门报告字典（GateReport.to_dict() 格式）
        title: 报告标题
        category: 质量门类别（storyboard/edit）
        source_data: 源数据（用于数据概览）
        output_path: 输出路径（None则返回HTML字符串）

    Returns:
        HTML 字符串或输出路径
    """
    results = report.get('results', [])
    total = report.get('total', len(results))
    passed = report.get('passed', 0)
    failed = report.get('failed', 0)
    warned = report.get('warned', 0)
    skipped = report.get('skipped', 0)
    pass_rate = (passed / total * 100) if total > 0 else 0

    # 病灶横幅
    fail_items = [r for r in results if r.get('status') == 'fail']
    banner_show = 'show' if fail_items else ''
    banner_detail = '; '.join([f"[{r.get('gate_id','')}] {r.get('message','')}" for r in fail_items[:3]])
    if len(fail_items) > 3:
        banner_detail += f" 等{len(fail_items)}项"

    # 渲染质量门列表
    gate_items = '\n'.join([render_gate_item(r) for r in results])

    # 数据概览
    data_overview = render_data_overview(source_data)

    # JSON 数据
    json_data = json.dumps(report, ensure_ascii=False, indent=2)

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    html = HTML_TEMPLATE.format(
        title=title,
        timestamp=timestamp,
        category=category,
        pass_rate=f"{pass_rate:.0f}",
        passed=passed,
        failed=failed,
        warned=warned,
        skipped=skipped,
        total=total,
        banner_show=banner_show,
        banner_detail=banner_detail,
        gate_items=gate_items,
        data_overview=data_overview,
        json_data=json_data,
    )

    if output_path:
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"[报告] HTML已生成: {output_path}")
        return output_path

    return html


if __name__ == "__main__":
    # 测试
    test_report = {
        'total': 10,
        'passed': 8,
        'failed': 1,
        'warned': 1,
        'skipped': 0,
        'pass_rate': 80.0,
        'results': [
            {'gate_id': 'S001', 'name': '镜头时长', 'status': 'pass', 'message': '5个镜头全部在2-15秒范围内'},
            {'gate_id': 'S002', 'name': '钩子检查', 'status': 'pass', 'message': '首个钩子在1.1秒'},
            {'gate_id': 'S004', 'name': '景别多样性', 'status': 'pass', 'message': '5种景别'},
            {'gate_id': 'S006', 'name': '情绪节奏', 'status': 'fail', 'message': '缺少关键情绪: 收束', 'detail': '当前情绪: 钩子, 展开, 高潮'},
            {'gate_id': 'S008', 'name': '时长合计', 'status': 'warn', 'message': '镜头合计15.2s与总时长15.0s差0.2s', 'detail': '误差在0.5秒阈值内'},
        ],
    }
    test_data = {
        'shots': [{'duration': 3}, {'duration': 3}, {'duration': 3}, {'duration': 3}, {'duration': 3.2}],
        'total_duration': 15.0,
        'fps': 30,
    }
    output = render_html_report(test_report, title="测试报告", category="storyboard", source_data=test_data,
                                output_path=r"D:\DobaoWork_Project\Ai_Video_Editor\debug\test_report.html")
    print(f"测试报告: {output}")
