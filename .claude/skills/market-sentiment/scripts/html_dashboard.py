"""
HTML 仪表盘生成器 v3
====================

严格复刻"两列大卡片"布局：
- A股左列 / 美股右列，对齐排列
- 按四层（底层/中层/上层/信号层）垂直分组
- 每个分组顶部一根色条 + 标题
- 卡片三段式：指标名（小字）/ 数值（大字）/ 一句话注释（小字）

设计上和最早那张参考截图严格一致。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


STATUS_STYLE = {
    "hot": {
        "bg": "#FBEAF0",
        "title": "#993556",
        "value": "#4B1528",
        "note": "#72243E",
    },
    "warm": {
        "bg": "#FAEEDA",
        "title": "#854F0B",
        "value": "#633806",
        "note": "#854F0B",
    },
    "neutral": {
        "bg": "#F1EFE8",
        "title": "#5F5E5A",
        "value": "#2C2C2A",
        "note": "#5F5E5A",
    },
    "cool": {
        "bg": "#E1F5EE",
        "title": "#0F6E56",
        "value": "#04342C",
        "note": "#085041",
    },
}

LAYER_META = {
    "底层": {"color": "#534AB7", "title": "底层 · 长期估值锚"},
    "中层": {"color": "#1D9E75", "title": "中层 · 股债性价比"},
    "上层": {"color": "#BA7517", "title": "上层 · 月度情绪温度"},
    "信号层": {"color": "#D85A30", "title": "信号层 · 流动性与狂热"},
}

MARKET_NAMES = {"US": "美股", "CN": "A股"}


def _escape(s: Any) -> str:
    if s is None:
        return ""
    s = str(s)
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def _format_value(ind) -> tuple[str, str]:
    if ind.value is None:
        return "n/a", ""
    if isinstance(ind.value, float):
        body = f"{ind.value:.2f}"
    else:
        body = str(ind.value)
    return body, ind.unit or ""


def render_card(ind) -> str:
    """单张大卡片，复刻截图样式。"""
    style = STATUS_STYLE.get(ind.status, STATUS_STYLE["neutral"])
    value_body, unit = _format_value(ind)
    market_label = MARKET_NAMES.get(ind.market, ind.market)
    title = f"{market_label} · {ind.name}"
    note = ind.note or ind.historical_context or ""

    return f"""
    <div class="card" style="
        background: {style['bg']};
        border-radius: 10px;
        padding: 18px 20px;
        min-height: 110px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    ">
      <div style="font-size: 13px; color: {style['title']}; font-weight: 500;">
        {_escape(title)}
      </div>
      <div style="font-size: 28px; font-weight: 500; color: {style['value']};
                  line-height: 1.2; margin: 6px 0;">
        {_escape(value_body)}<span style="font-size: 16px; font-weight: 400;
                                          margin-left: 2px;">{_escape(unit)}</span>
      </div>
      <div style="font-size: 12px; color: {style['note']}; line-height: 1.5;">
        {_escape(note)}
      </div>
    </div>"""


def render_layer_section(layer_key: str, indicators: list) -> str:
    """渲染一个层级：标题 + 两列卡片网格。"""
    meta = LAYER_META.get(layer_key, {"color": "#888", "title": layer_key})

    cn_inds = [i for i in indicators if i.market == "CN"]
    us_inds = [i for i in indicators if i.market == "US"]

    max_rows = max(len(cn_inds), len(us_inds))
    if max_rows == 0:
        return ""

    cells = []
    for row_idx in range(max_rows):
        cn = cn_inds[row_idx] if row_idx < len(cn_inds) else None
        us = us_inds[row_idx] if row_idx < len(us_inds) else None
        cells.append(render_card(cn) if cn else '<div></div>')
        cells.append(render_card(us) if us else '<div></div>')

    grid_html = "\n".join(cells)

    return f"""
    <section style="margin-bottom: 2rem;">
      <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 14px;">
        <span style="display: inline-block; width: 4px; height: 16px;
                     background: {meta['color']}; border-radius: 2px;"></span>
        <span style="font-size: 15px; font-weight: 500;">{meta['title']}</span>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
        {grid_html}
      </div>
    </section>"""


def render_summary(report) -> str:
    hot = sum(1 for i in report.indicators if i.status == "hot")
    warm = sum(1 for i in report.indicators if i.status == "warm")
    neutral = sum(1 for i in report.indicators if i.status == "neutral")
    cool = sum(1 for i in report.indicators if i.status == "cool")

    if hot >= 7:
        verdict = "过热信号显著，建议降低进攻性"
        verdict_color = "#993556"
    elif cool >= 4:
        verdict = "偏冷信号增多，关注买入机会"
        verdict_color = "#0F6E56"
    else:
        verdict = "市场处于中性区间，维持原配置"
        verdict_color = "#5F5E5A"

    return f"""
    <div style="margin-bottom: 1.5rem; padding: 20px 24px; background: var(--surface);
                border-radius: 12px; border: 0.5px solid var(--border);">
      <div style="display: flex; justify-content: space-between; align-items: baseline;
                  margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
        <div>
          <div style="font-size: 22px; font-weight: 500;">市场情绪监测周报</div>
          <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">
            生成于 {report.timestamp:%Y-%m-%d %H:%M} · 共 {len(report.indicators)} 个指标
          </div>
        </div>
        <div style="text-align: right;">
          <div style="font-size: 13px; color: {verdict_color}; font-weight: 500;">{verdict}</div>
        </div>
      </div>
      <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;">
        <div style="padding: 12px; background: #FBEAF0; border-radius: 8px; text-align: center;">
          <div style="font-size: 22px; font-weight: 500; color: #4B1528;">{hot}</div>
          <div style="font-size: 12px; color: #72243E; margin-top: 2px;">过热</div>
        </div>
        <div style="padding: 12px; background: #FAEEDA; border-radius: 8px; text-align: center;">
          <div style="font-size: 22px; font-weight: 500; color: #633806;">{warm}</div>
          <div style="font-size: 12px; color: #854F0B; margin-top: 2px;">偏热</div>
        </div>
        <div style="padding: 12px; background: #F1EFE8; border-radius: 8px; text-align: center;">
          <div style="font-size: 22px; font-weight: 500; color: #444441;">{neutral}</div>
          <div style="font-size: 12px; color: #5F5E5A; margin-top: 2px;">中性</div>
        </div>
        <div style="padding: 12px; background: #E1F5EE; border-radius: 8px; text-align: center;">
          <div style="font-size: 22px; font-weight: 500; color: #04342C;">{cool}</div>
          <div style="font-size: 12px; color: #085041; margin-top: 2px;">偏冷</div>
        </div>
      </div>
    </div>"""


def render_legend() -> str:
    return """
    <div style="margin-top: 2rem; padding: 12px 16px; background: var(--surface);
                border-radius: 8px; border: 0.5px solid var(--border);
                display: flex; gap: 20px; font-size: 12px; color: var(--text-secondary);
                flex-wrap: wrap; align-items: center;">
      <span style="font-weight: 500;">图例：</span>
      <span><span style="display: inline-block; width: 12px; height: 12px;
            background: #E1F5EE; border-radius: 2px; vertical-align: middle;
            margin-right: 4px;"></span>有安全边际</span>
      <span><span style="display: inline-block; width: 12px; height: 12px;
            background: #F1EFE8; border-radius: 2px; vertical-align: middle;
            margin-right: 4px;"></span>中性</span>
      <span><span style="display: inline-block; width: 12px; height: 12px;
            background: #FAEEDA; border-radius: 2px; vertical-align: middle;
            margin-right: 4px;"></span>偏热</span>
      <span><span style="display: inline-block; width: 12px; height: 12px;
            background: #FBEAF0; border-radius: 2px; vertical-align: middle;
            margin-right: 4px;"></span>过热/警示</span>
    </div>"""


def generate_dashboard(report) -> str:
    by_layer = {}
    for ind in report.indicators:
        by_layer.setdefault(ind.layer, []).append(ind)

    layers_html = "\n".join(
        render_layer_section(layer_key, by_layer.get(layer_key, []))
        for layer_key in LAYER_META.keys()
    )

    summary_html = render_summary(report)
    legend_html = render_legend()

    errors_html = ""
    if report.errors:
        err_items = "\n".join(f"<li>{_escape(e)}</li>" for e in report.errors)
        errors_html = f"""
        <details style="margin-top: 1.5rem; padding: 12px 16px; background: var(--surface);
                        border-radius: 8px; border: 0.5px solid var(--border);">
          <summary style="cursor: pointer; font-size: 13px; color: var(--text-secondary);">
            数据获取异常 ({len(report.errors)} 项)
          </summary>
          <ul style="margin-top: 8px; font-size: 12px; color: var(--text-secondary);">
            {err_items}
          </ul>
        </details>"""

    return _HTML_TEMPLATE.format(
        title=f"市场情绪监测 {report.timestamp:%Y-%m-%d}",
        timestamp=report.timestamp.strftime("%Y-%m-%d %H:%M"),
        summary=summary_html,
        layers=layers_html,
        legend=legend_html,
        errors=errors_html,
    )


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  :root {{
    --bg: #FAFAF7;
    --surface: #FFFFFF;
    --border: rgba(0,0,0,0.08);
    --text-primary: #1F1F1E;
    --text-secondary: #73726C;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #1A1A18;
      --surface: #232321;
      --border: rgba(255,255,255,0.08);
      --text-primary: #F1EFE8;
      --text-secondary: #9C9A92;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                 "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    background: var(--bg);
    color: var(--text-primary);
    line-height: 1.5;
  }}
  .container {{
    max-width: 920px;
    margin: 0 auto;
    padding: 32px 24px;
  }}
  .card {{
    transition: transform 0.15s ease;
  }}
  .card:hover {{
    transform: translateY(-1px);
  }}
  details summary::-webkit-details-marker {{ display: none; }}
  details summary::before {{
    content: "▸ ";
    transition: transform 0.2s;
    display: inline-block;
  }}
  details[open] summary::before {{
    transform: rotate(90deg);
  }}
  @media (max-width: 600px) {{
    .container {{ padding: 16px 12px; }}
    section > div[style*="grid-template-columns: 1fr 1fr"] {{
      grid-template-columns: 1fr !important;
    }}
  }}
</style>
</head>
<body>
<div class="container">
  {summary}
  {layers}
  {legend}
  {errors}
  <footer style="margin-top: 2rem; padding-top: 16px; border-top: 0.5px solid var(--border);
                 font-size: 11px; color: var(--text-secondary); text-align: center;">
    生成于 {timestamp} · Howard Marks 四层情绪诊断框架 ·
    本报告仅为基于规则的统计提醒，不构成投资建议
  </footer>
</div>
</body>
</html>"""


if __name__ == "__main__":
    from dataclasses import dataclass, field

    @dataclass
    class MockIndicator:
        name: str
        value: Any
        unit: str = ""
        layer: str = ""
        market: str = ""
        dimension: str = ""
        historical_context: str = ""
        status: str = "neutral"
        note: str = ""

    @dataclass
    class MockReport:
        timestamp: datetime = field(default_factory=datetime.now)
        indicators: list = field(default_factory=list)
        errors: list = field(default_factory=list)

    # 严格复刻截图的指标集
    report = MockReport()
    report.indicators = [
        MockIndicator("沪深300 PE", "14.4", "x", "底层", "CN", "市盈率",
                      "", "neutral", "历史中枢偏下，安全边际充足"),
        MockIndicator("Shiller CAPE", "~40-42", "x", "底层", "US", "市盈率",
                      "", "hot", "逼近2000年峰值44.2x"),
        MockIndicator("科创100 PE", "170-220", "x", "底层", "CN", "市盈率",
                      "", "hot", "日经90/纳指00级别"),
        MockIndicator("巴菲特指标", "~220", "%", "底层", "US", "市盈率",
                      "", "hot", "远超90-135%合理区间"),
        MockIndicator("沪深300 ERP", "~5.2", "%", "中层", "CN", "市盈率",
                      "", "cool", "股票相对债券仍有吸引力"),
        MockIndicator("隐含 ERP", "~0.02", "%", "中层", "US", "市盈率",
                      "", "hot", "史上最低之一"),
        MockIndicator("月度新开户", "492", "万", "上层", "CN", "投资者情绪",
                      "", "warm", "近十年第五高，散户进场"),
        MockIndicator("AAII 看涨比", "38.3", "%", "上层", "US", "投资者情绪",
                      "", "neutral", "略高于历史均值37.5%"),
        MockIndicator("宽基ETF 18日", "-2625", "亿", "上层", "CN", "投资者情绪",
                      "", "hot", "机构在高位减仓"),
        MockIndicator("恐惧贪婪指数", "贪婪", "", "上层", "US", "投资者情绪",
                      "", "hot", "一个月内从极度恐慌切换"),
        MockIndicator("IPO 募资同比", "+80", "%", "信号层", "CN", "证券发行",
                      "", "hot", "基金狂热阶段特征"),
        MockIndicator("HY 债利差", "~280", "bp", "信号层", "US", "信用利差",
                      "", "hot", "远低于20年均值490bp"),
        MockIndicator("热门赛道 PE", "欣快期", "", "信号层", "CN", "投资者情绪",
                      "", "hot", "AI/机器人/算力一致看多"),
        MockIndicator("AI capex", "FCF的90", "%", "信号层", "US", "信贷周期",
                      "", "hot", "单一叙事吞噬现金流"),
    ]

    from pathlib import Path
    html = generate_dashboard(report)
    out = Path("dashboard_sample.html")
    out.write_text(html, encoding="utf-8")
    print(f"示例已生成：{out.resolve()}")
    print(f"指标数：{len(report.indicators)}")
    print(f"文件大小：{out.stat().st_size:,} 字节")
