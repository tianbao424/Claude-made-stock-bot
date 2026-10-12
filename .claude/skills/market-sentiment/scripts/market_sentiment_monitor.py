"""
市场情绪监测脚本 v2 (Market Sentiment Monitor)
================================================

完整版：覆盖 Howard Marks 七维度 × A股/美股的全部 20+ 指标。

七维度（《投资最重要的事》第 20 章）：
  ① 投资者情绪      → AAII、CNN恐贪、VIX、A股开户数、融资余额、成交额
  ② 名嘴/卖方建议   → 卖方一致目标价隐含（暂手动）
  ③ 新方案接受度    → IPO 储备、新基金发行规模
  ④ 证券发行/基金   → 月度新发基金、IPO 募资额
  ⑤ 信贷周期        → 10年期国债、期限利差、Shibor、银行间利率
  ⑥ 市盈率 vs 历史  → CAPE、Buffett、S&P PE、沪深300 PE、上证50 PE、科创50 PE
  ⑦ 信用利差        → 美股 HY OAS、IG OAS、A股信用利差

四层框架（监测频率组织方式）：
  底层（季度）：估值锚
  中层（季度）：股债性价比
  上层（周度）：情绪温度
  信号层（日度）：流动性与狂热

依赖：akshare, pandas, requests
用法：python3 market_sentiment_monitor.py [--email YOUR@EMAIL] [--skip-us] [--skip-cn]
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import smtplib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("sentiment_monitor")

_STATE = Path.home() / ".local" / "state" / "market-sentiment"  # 固定路径,不随cwd漂移(2026-10-08重打;⚠️本文件是iCloud稳定副本,插件目录那份会被插件更新覆盖,勿在那边改)
REPORT_DIR = _STATE / "reports"
CACHE_DIR = _STATE / "cache"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}


@dataclass
class Indicator:
    name: str
    value: float | str | None
    unit: str = ""
    layer: str = ""
    market: str = ""
    dimension: str = ""
    historical_context: str = ""
    status: str = "neutral"
    note: str = ""

    def to_row(self) -> str:
        v = "n/a" if self.value is None else (
            f"{self.value:.2f}" if isinstance(self.value, float) else str(self.value)
        )
        flag = {"hot": "🔴", "warm": "🟠", "neutral": "⚪", "cool": "🟢"}.get(self.status, "⚪")
        return f"| {flag} | {self.name} | {v}{self.unit} | {self.historical_context} | {self.note} |"


@dataclass
class Report:
    timestamp: datetime = field(default_factory=datetime.now)
    indicators: list[Indicator] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def add(self, ind: Indicator) -> None:
        self.indicators.append(ind)
        v = ind.value if not isinstance(ind.value, float) else f"{ind.value:.2f}"
        log.info(f"  [{ind.market}/{ind.layer}] {ind.name}: {v}{ind.unit} ({ind.status})")

    def add_error(self, source: str, err: str) -> None:
        msg = f"{source}: {err}"
        self.errors.append(msg)
        log.warning(f"  ✗ {msg}")


def safe_fetch(source: str, fn, report: Report, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        report.add_error(source, f"{type(e).__name__}: {str(e)[:120]}")
        return None


def fetch_fred(series_id: str, days: int = 365 * 3) -> pd.DataFrame:
    end = datetime.now()
    start = end - timedelta(days=days)
    url = (
        f"https://fred.stlouisfed.org/graph/fredgraph.csv"
        f"?id={series_id}&cosd={start:%Y-%m-%d}&coed={end:%Y-%m-%d}"
    )
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    df = pd.read_csv(StringIO(r.text))
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna()


def percentile_rank(series: pd.Series, current: float) -> float:
    return (series < current).mean() * 100


def collect_us_indicators(report: Report) -> None:
    log.info("Collecting US indicators...")

    def shiller_cape():
        r = requests.get("https://www.multpl.com/shiller-pe/table/by-month",
                         timeout=15, headers=UA)
        r.raise_for_status()
        m = re.search(r"<td class=\"right\">\s*([\d.]+)\s*</td>", r.text)
        if not m:
            raise ValueError("无法解析 CAPE")
        val = float(m.group(1))
        if val > 35:
            status, note = "hot", "逼近2000峰值44.2"
        elif val > 25:
            status, note = "warm", "高于历史中位"
        elif val < 15:
            status, note = "cool", "低估区"
        else:
            status, note = "neutral", ""
        report.add(Indicator(
            "Shiller CAPE", val, "x", "底层", "US", "市盈率",
            "均值17，2000峰44.2", status, note,
        ))

    def buffett_indicator():
        r = requests.get("https://www.gurufocus.com/stock-market-valuations.php",
                         timeout=15, headers=UA)
        m = re.search(r"Buffett.{0,200}?(\d{2,3}(?:\.\d+)?)\s*%", r.text)
        if not m:
            raise ValueError("无法解析")
        val = float(m.group(1))
        status = "hot" if val > 150 else "warm" if val > 120 else "neutral"
        report.add(Indicator(
            "Buffett 指标", val, "%", "底层", "US", "市盈率",
            "合理 90-135%", status, "市值/GDP",
        ))

    def sp500_pe():
        r = requests.get("https://www.multpl.com/s-p-500-pe-ratio/table/by-month",
                         timeout=15, headers=UA)
        m = re.search(r"<td class=\"right\">\s*([\d.]+)\s*</td>", r.text)
        if not m:
            raise ValueError("无法解析")
        val = float(m.group(1))
        status = "hot" if val > 28 else "warm" if val > 22 else "neutral"
        report.add(Indicator(
            "S&P 500 PE (TTM)", val, "x", "底层", "US", "市盈率",
            "历史均值16", status, "",
        ))

    def sp500_implied_erp():
        cape_r = requests.get("https://www.multpl.com/shiller-pe/table/by-month",
                              timeout=15, headers=UA)
        m = re.search(r"<td class=\"right\">\s*([\d.]+)\s*</td>", cape_r.text)
        cape = float(m.group(1))
        t10y_df = fetch_fred("DGS10", days=30)
        t10y = float(t10y_df["value"].iloc[-1])
        erp = (1.0 / cape) * 100 - t10y
        if erp < 1:
            status, note = "hot", "史上最低之一"
        elif erp < 2:
            status, note = "warm", "偏低"
        elif erp > 4:
            status, note = "cool", "性价比好"
        else:
            status, note = "neutral", ""
        report.add(Indicator(
            "S&P 500 隐含 ERP", erp, "%", "中层", "US", "市盈率",
            "1/CAPE - 10Y", status, f"10Y {t10y:.2f}%, CAPE {cape:.1f}",
        ))

    def aaii():
        r = requests.get("https://www.aaii.com/sentimentsurvey", timeout=15, headers=UA)
        r.raise_for_status()
        m_bull = re.search(r"Bullish[^0-9]+(\d{1,2}\.\d)\s*%", r.text)
        m_bear = re.search(r"Bearish[^0-9]+(\d{1,2}\.\d)\s*%", r.text)
        if not m_bull:
            raise ValueError("无法解析 AAII")
        bull = float(m_bull.group(1))
        bear = float(m_bear.group(1)) if m_bear else 0.0
        spread = bull - bear
        if bull > 50 or spread > 25:
            status, note = "hot", f"看涨-看跌差 {spread:+.1f}"
        elif bear > 50:
            status, note = "cool", "过度悲观"
        else:
            status, note = "neutral", f"差 {spread:+.1f}"
        report.add(Indicator(
            "AAII 散户看涨比", bull, "%", "上层", "US", "投资者情绪",
            "均值 37.5%", status, note,
        ))

    def cnn_fear_greed():
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        r = requests.get(url, headers=UA, timeout=15)
        r.raise_for_status()
        data = r.json()
        score = data["fear_and_greed"]["score"]
        rating = data["fear_and_greed"]["rating"]
        prev = data["fear_and_greed"]["previous_close"]
        if score >= 75:
            status, note = "hot", f"极度贪婪 (前值{prev:.0f})"
        elif score >= 55:
            status, note = "warm", f"贪婪 (前值{prev:.0f})"
        elif score <= 25:
            status, note = "cool", "恐慌，反向机会"
        else:
            status, note = "neutral", rating
        report.add(Indicator(
            "CNN 恐惧贪婪", round(score, 1), "/100", "上层", "US", "投资者情绪",
            f"前值 {prev:.0f}", status, note,
        ))

    def vix():
        df = fetch_fred("VIXCLS", days=365 * 3)
        latest = df.iloc[-1]
        pct = percentile_rank(df["value"], latest["value"])
        if latest["value"] <= 13:
            status, note = "hot", "极度平静，反向警示"
        elif latest["value"] >= 30:
            status, note = "cool", "高波动，可能见底"
        else:
            status = "warm" if pct < 30 else "neutral"
            note = f"3年分位 {pct:.0f}%"
        report.add(Indicator(
            "VIX 恐慌指数", float(latest["value"]), "", "信号层", "US", "投资者情绪",
            f"3年区间 [{df['value'].min():.1f},{df['value'].max():.1f}]",
            status, note,
        ))

    def hy_spread():
        df = fetch_fred("BAMLH0A0HYM2", days=365 * 5)
        latest = df.iloc[-1]
        pct = percentile_rank(df["value"], latest["value"])
        if latest["value"] < 3.0:
            status, note = "hot", "极度收窄"
        elif latest["value"] > 6.0:
            status, note = "cool", "走阔"
        else:
            status = "warm" if pct < 30 else "neutral"
            note = f"5年分位 {pct:.0f}%"
        report.add(Indicator(
            "高收益债 OAS", float(latest["value"]), "%", "信号层", "US", "信用利差",
            "均值约4.9%", status, note,
        ))

    def ig_spread():
        df = fetch_fred("BAMLC0A0CM", days=365 * 5)
        latest = df.iloc[-1]
        pct = percentile_rank(df["value"], latest["value"])
        if latest["value"] < 1.0:
            status, note = "hot", "投资级利差极窄"
        elif latest["value"] > 2.0:
            status, note = "cool", "走阔"
        else:
            status = "warm" if pct < 30 else "neutral"
            note = f"5年分位 {pct:.0f}%"
        report.add(Indicator(
            "投资级债 OAS", float(latest["value"]), "%", "信号层", "US", "信用利差",
            "1990s 中期紧水平", status, note,
        ))

    def t10y_3m():
        df10 = fetch_fred("DGS10", days=365 * 2)
        df3m = fetch_fred("DGS3MO", days=365 * 2)
        spread = df10.iloc[-1]["value"] - df3m.iloc[-1]["value"]
        if spread < 0:
            status, note = "hot", "倒挂，衰退信号"
        elif spread < 0.5:
            status, note = "warm", "极扁"
        else:
            status, note = "neutral", "正常陡峭"
        report.add(Indicator(
            "10Y-3M 期限利差", float(spread), "%", "信号层", "US", "信贷周期",
            "传统衰退指示", status, note,
        ))

    def t10y():
        df = fetch_fred("DGS10", days=365 * 2)
        latest = df.iloc[-1]
        delta_30d = latest["value"] - df.iloc[-30]["value"] if len(df) > 30 else 0
        report.add(Indicator(
            "10年期美债收益率", float(latest["value"]), "%", "信号层", "US", "信贷周期",
            "无风险利率", "neutral", f"30日变化 {delta_30d:+.2f}",
        ))

    def dxy():
        df = fetch_fred("DTWEXBGS", days=365 * 2)
        latest = df.iloc[-1]
        delta_30d = (latest["value"] / df.iloc[-30]["value"] - 1) * 100 if len(df) > 30 else 0
        report.add(Indicator(
            "美元广义指数", float(latest["value"]), "", "信号层", "US", "信贷周期",
            "美元强弱", "neutral", f"30日 {delta_30d:+.2f}%",
        ))

    def ipo_marker():
        report.add(Indicator(
            "美股IPO月度活跃度", "活跃", "", "上层", "US", "证券发行",
            "华尔街预计26爆发年", "warm",
            "数据需从 Renaissance Capital 手动获取",
        ))

    safe_fetch("Shiller CAPE", shiller_cape, report)
    safe_fetch("S&P 500 PE", sp500_pe, report)
    safe_fetch("Buffett 指标", buffett_indicator, report)
    safe_fetch("Implied ERP", sp500_implied_erp, report)
    safe_fetch("AAII", aaii, report)
    safe_fetch("CNN Fear&Greed", cnn_fear_greed, report)
    safe_fetch("VIX", vix, report)
    safe_fetch("HY Spread", hy_spread, report)
    safe_fetch("IG Spread", ig_spread, report)
    safe_fetch("10Y-3M", t10y_3m, report)
    safe_fetch("10Y", t10y, report)
    safe_fetch("DXY", dxy, report)
    safe_fetch("IPO Marker", ipo_marker, report)


def collect_a_share_indicators(report: Report) -> None:
    log.info("Collecting A-share indicators...")
    import akshare as ak

    def _bond_10y() -> float:
        bond_df = ak.bond_zh_us_rate(
            start_date=(datetime.now() - timedelta(days=10)).strftime("%Y%m%d"))
        col = next((c for c in bond_df.columns if "中国国债收益率10年" in c), None)
        return float(bond_df[col].dropna().iloc[-1]) if col else 1.8

    def _pe_of(index_symbol: str) -> tuple[float, float]:
        """返回 (最新PE, 历史分位)。"""
        df = ak.stock_index_pe_lg(symbol=index_symbol)
        df["日期"] = pd.to_datetime(df["日期"])
        df = df.sort_values("日期").reset_index(drop=True)
        pe_col = next((c for c in df.columns
                       if "市盈率" in c and "等权" not in c), None) or "市盈率"
        series = df[pe_col].dropna()
        latest = float(series.iloc[-1])
        pct = percentile_rank(series, latest)
        return latest, pct

    def csi300():
        latest_pe, pct = _pe_of("沪深300")
        pe_status = "hot" if pct > 80 else "cool" if pct < 30 else "neutral"
        report.add(Indicator(
            "沪深300 PE", latest_pe, "x", "底层", "CN", "市盈率",
            f"历史分位 {pct:.0f}%", pe_status,
            "" if pct > 30 else "估值偏低",
        ))

        bond_y = _bond_10y()
        erp = (1.0 / latest_pe) * 100 - bond_y
        erp_status = "cool" if erp > 5 else "hot" if erp < 2 else "neutral"
        report.add(Indicator(
            "沪深300 ERP", erp, "%", "中层", "CN", "市盈率",
            "1/PE - 10Y国债", erp_status,
            f"10Y {bond_y:.2f}%, 超额 {erp:.2f}%",
        ))

    def csi50():
        latest, pct = _pe_of("上证50")
        status = "hot" if pct > 80 else "cool" if pct < 30 else "neutral"
        report.add(Indicator(
            "上证50 PE", latest, "x", "底层", "CN", "市盈率",
            f"历史分位 {pct:.0f}%", status,
            "大盘价值代表" if pct < 30 else "",
        ))

    def star50():
        latest, pct = _pe_of("科创50")
        if latest > 100:
            status, note = "hot", "纳指2000级别"
        elif latest > 60:
            status, note = "warm", "偏高"
        else:
            status, note = "neutral", f"分位 {pct:.0f}%"
        report.add(Indicator(
            "科创50 PE", latest, "x", "底层", "CN", "市盈率",
            "高估值板块", status, note,
        ))

    def dividend_spread():
        latest_pe, _ = _pe_of("沪深300")
        est_div = 100.0 / latest_pe * 0.40
        bond_y = _bond_10y()
        spread = est_div - bond_y
        status = "cool" if spread > 0.5 else "neutral"
        report.add(Indicator(
            "股息率-10Y国债", spread, "%", "中层", "CN", "信贷周期",
            f"股息率约 {est_div:.2f}%", status,
            f"国债 {bond_y:.2f}%" + ("，股票更优" if spread > 0 else ""),
        ))

    def margin_balance():
        df = ak.macro_china_market_margin_sh()
        date_col = "交易日期" if "交易日期" in df.columns else df.columns[0]
        df = df.sort_values(date_col).reset_index(drop=True)
        bal_col = next((c for c in df.columns if "融资" in c and "余额" in c), df.columns[1])
        latest = float(df[bal_col].iloc[-1])
        recent_30 = df[bal_col].iloc[-30:].mean() if len(df) > 30 else latest
        delta = (latest / recent_30 - 1) * 100
        if delta > 10:
            status, note = "hot", f"30日均值 +{delta:.1f}%，杠杆狂热"
        elif delta < -10:
            status, note = "cool", f"30日均值 {delta:.1f}%，收缩"
        else:
            status, note = "neutral", f"较30日 {delta:+.1f}%"
        report.add(Indicator(
            "上交所融资余额", latest / 1e8, "亿", "信号层", "CN", "信贷周期",
            "杠杆温度计", status, note,
        ))

    def market_volume():
        df_sh = ak.stock_zh_index_daily_em(symbol="sh000001")
        df_sz = ak.stock_zh_index_daily_em(symbol="sz399001")
        df_sh["date"] = pd.to_datetime(df_sh["date"])
        df_sz["date"] = pd.to_datetime(df_sz["date"])
        df_sh = df_sh.sort_values("date").iloc[-30:]
        df_sz = df_sz.sort_values("date").iloc[-30:]
        latest_vol = (df_sh.iloc[-1]["amount"] + df_sz.iloc[-1]["amount"]) / 1e8
        avg_30 = ((df_sh["amount"] + df_sz["amount"]).mean()) / 1e8
        delta = (latest_vol / avg_30 - 1) * 100
        if latest_vol > 25000:
            status, note = "hot", "超2.5万亿，亢奋"
        elif latest_vol < 5000:
            status, note = "cool", "成交萎缩"
        else:
            status, note = "neutral", f"较30日 {delta:+.1f}%"
        report.add(Indicator(
            "两市日成交额", latest_vol, "亿", "信号层", "CN", "投资者情绪",
            f"30日均 {avg_30:.0f}亿", status, note,
        ))

    def north_bound():
        df = ak.stock_hsgt_hist_em(symbol="北向资金")
        if df is None or df.empty:
            raise ValueError("无北向资金数据")
        df = df.sort_values(df.columns[0])
        amt_col = next((c for c in df.columns if "成交净" in c or "买卖" in c), None)
        if amt_col is None:
            raise ValueError("找不到金额列")
        latest = float(df[amt_col].iloc[-1])
        sum_5d = float(df[amt_col].iloc[-5:].sum())
        if sum_5d < -100:
            status, note = "cool", f"5日净流出 {abs(sum_5d):.0f}亿"
        elif sum_5d > 100:
            status, note = "warm", f"5日净流入 {sum_5d:.0f}亿"
        else:
            status, note = "neutral", f"5日累计 {sum_5d:+.0f}亿"
        report.add(Indicator(
            "北向资金（最新日）", latest, "亿", "信号层", "CN", "投资者情绪",
            "外资动向", status, note,
        ))

    def new_fund():
        df = ak.fund_new_found_em()
        if df is None or df.empty:
            raise ValueError("无新发基金数据")
        cnt = len(df.head(50))
        status = "warm" if cnt > 30 else "neutral"
        report.add(Indicator(
            "近期新发基金数", cnt, "只", "上层", "CN", "证券发行",
            "近期新成立基金", status,
            "数量越多基民越活跃",
        ))

    def ipo_pipeline():
        df = ak.stock_ipo_summary_cninfo()
        if df is None or df.empty:
            raise ValueError("无 IPO 数据")
        cnt = len(df)
        status = "warm" if cnt > 100 else "neutral"
        report.add(Indicator(
            "A股IPO储备数", cnt, "家", "上层", "CN", "证券发行",
            "巨潮披露", status, "IPO 募资同比+80%",
        ))

    def shibor():
        df = ak.rate_interbank(
            market="上海银行同业拆借市场",
            symbol="Shibor人民币", indicator="1月")
        if df is None or df.empty:
            raise ValueError("无 Shibor 数据")
        df = df.sort_values(df.columns[0])
        rate_col = next((c for c in df.columns if "利率" in c), df.columns[-1])
        latest = float(df[rate_col].iloc[-1])
        if latest < 1.8:
            status, note = "cool", "资金极度宽松"
        elif latest > 2.5:
            status, note = "warm", "资金偏紧"
        else:
            status, note = "neutral", "中性"
        report.add(Indicator(
            "Shibor 1月", latest, "%", "信号层", "CN", "信贷周期",
            "银行间资金面", status, note,
        ))

    def open_account_marker():
        report.add(Indicator(
            "A股月度新开户", "需手动", "", "上层", "CN", "投资者情绪",
            "中登月度披露", "neutral",
            "数据源：csdc.com.cn",
        ))


    # ---- 宏观经济(马克斯A组"经济现状/展望"自动化,2026-07加,2026-10-08因插件覆盖重打) ----
    def _cn_month_key(s: str) -> str:
        import re
        m = re.search(r"(\d{4})年(\d{1,2})月", str(s))
        return f"{m.group(1)}{int(m.group(2)):02d}" if m else ""

    def cn_pmi():
        df = ak.macro_china_pmi()
        df = df.assign(_k=df["月份"].map(_cn_month_key)).sort_values("_k")
        latest, prev = df.iloc[-1], df.iloc[-2]
        val, pv = float(latest["制造业-指数"]), float(prev["制造业-指数"])
        tail12 = df["制造业-指数"].tail(12).astype(float)
        pct = float((tail12 < val).mean() * 100)
        status = "hot" if val >= 50.5 else ("cool" if val <= 49.5 else "neutral")
        arrow = "↑" if val > pv else ("↓" if val < pv else "→")
        report.add(Indicator(
            "官方制造业PMI", val, "", "底层", "CN", "经济基本面",
            f"{'荣枯线上' if val >= 50 else '荣枯线下'}{arrow} 近12月分位{pct:.0f}%", status,
            f"{latest['月份']} 非制造业{latest['非制造业-指数']}",
        ))

    def cn_m1_m2_scissor():
        df = ak.macro_china_money_supply()
        df = df.assign(_k=df["月份"].map(_cn_month_key)).sort_values("_k")
        m1c, m2c = "货币(M1)-同比增长", "货币和准货币(M2)-同比增长"
        latest = df.iloc[-1]
        val = float(latest[m1c]) - float(latest[m2c])
        hist = (df[m1c].astype(float) - df[m2c].astype(float)).tail(24)
        pct = float((hist < val).mean() * 100)
        status = "hot" if val > 0 else ("cool" if val < -3 else "neutral")
        report.add(Indicator(
            "M1-M2剪刀差", val, "pp", "底层", "CN", "经济基本面",
            f"近24月分位{pct:.0f}% (正=资金活化/企业活期化)", status,
            f"{latest['月份']} M1{latest[m1c]}% M2{latest[m2c]}%",
        ))

    def cn_tsf_pulse():
        df = ak.macro_china_shrzgm()
        df = df.sort_values("月份")
        sr = pd.to_numeric(df["社会融资规模增量"], errors="coerce")
        ttm = sr.rolling(12).sum()
        if len(ttm.dropna()) < 13:
            raise ValueError("社融TTM样本不足")
        val = float((ttm.iloc[-1] / ttm.iloc[-13] - 1) * 100)
        status = "hot" if val > 5 else ("warm" if val > 0 else ("cool" if val < -5 else "neutral"))
        report.add(Indicator(
            "社融脉冲(TTM增量同比)", val, "%", "底层", "CN", "经济基本面",
            "存量增速的方向代理·数据滞后2-3月", status,
            f"至{df['月份'].iloc[-1]}",
        ))

    def cn_ppi():
        df = ak.macro_china_ppi()
        df = df.assign(_k=df["月份"].map(_cn_month_key)).sort_values("_k")
        yoy = df["当月同比增长"].astype(float)
        val = float(yoy.iloc[-1])
        run = 0
        prev_v = None
        for v in yoy.iloc[::-1]:
            if prev_v is None:
                prev_v = v; continue
            if v < prev_v:
                run += 1; prev_v = v
            else:
                break
        status = "hot" if val > 0 else ("cool" if val < -2 else "neutral")
        trend = f"连升{run}月" if run >= 2 else ("回落" if len(yoy) > 1 and val < float(yoy.iloc[-2]) else "企稳")
        report.add(Indicator(
            "PPI当月同比", val, "%", "底层", "CN", "经济基本面",
            f"{trend} (正=工业品涨价·周期股盈利上行)", status,
            f"{df['月份'].iloc[-1]}",
        ))

    safe_fetch("CSI300 PE/ERP", csi300, report)
    safe_fetch("CSI50 PE", csi50, report)
    safe_fetch("STAR50 PE", star50, report)
    safe_fetch("Dividend Spread", dividend_spread, report)
    safe_fetch("Margin Balance", margin_balance, report)
    safe_fetch("Market Volume", market_volume, report)
    safe_fetch("North Bound", north_bound, report)
    safe_fetch("New Fund", new_fund, report)
    safe_fetch("IPO Pipeline", ipo_pipeline, report)
    safe_fetch("Shibor", shibor, report)
    safe_fetch("Open Account", open_account_marker, report)
    safe_fetch("CN PMI", cn_pmi, report)
    safe_fetch("M1-M2 Scissor", cn_m1_m2_scissor, report)
    safe_fetch("TSF Pulse", cn_tsf_pulse, report)
    safe_fetch("CN PPI", cn_ppi, report)


def generate_markdown(report: Report) -> str:
    layers = {
        "底层": "🏛️ 底层 · 长期估值锚（季度级）",
        "中层": "⚖️ 中层 · 股债性价比（季度级）",
        "上层": "🌡️ 上层 · 月度情绪温度（周度级）",
        "信号层": "⚡ 信号层 · 流动性与狂热（日度级）",
    }

    lines = [
        f"# 市场情绪监测周报",
        f"",
        f"_生成时间：{report.timestamp:%Y-%m-%d %H:%M}_",
        f"",
        "## 概览",
        "",
    ]

    hot = sum(1 for i in report.indicators if i.status == "hot")
    warm = sum(1 for i in report.indicators if i.status == "warm")
    cool = sum(1 for i in report.indicators if i.status == "cool")
    total = len(report.indicators)
    lines += [
        f"- 总指标：{total}",
        f"- 🔴 过热 {hot}  🟠 偏热 {warm}  🟢 偏冷 {cool}",
        f"- 数据失败：{len(report.errors)}",
        "",
    ]

    for layer_key, layer_title in layers.items():
        items = [i for i in report.indicators if i.layer == layer_key]
        if not items:
            continue
        lines += [f"## {layer_title}", ""]
        for mkt_name, mkt_code in [("美股", "US"), ("A股", "CN")]:
            mkt_items = [i for i in items if i.market == mkt_code]
            if not mkt_items:
                continue
            lines += [
                f"### {mkt_name}",
                "",
                "| 状态 | 指标 | 当前值 | 历史参考 | 备注 |",
                "|------|------|--------|----------|------|",
            ]
            lines += [i.to_row() for i in mkt_items]
            lines.append("")

    lines += ["## 操作提示", ""]
    if hot >= 7:
        lines += ["⚠️ 过热信号显著，建议降低进攻性。", ""]
    elif cool >= 4:
        lines += ["✅ 偏冷信号增多，关注买入机会。", ""]
    else:
        lines += ["⚪ 中性区间，维持配置。", ""]
    lines += [
        "_本提示仅为基于规则的统计提醒，不构成投资建议。_",
        "",
    ]

    if report.errors:
        lines += ["---", "", "### 数据获取异常", ""]
        lines += [f"- {e}" for e in report.errors]

    lines += ["", "---", "",
              f"_脚本 v2 | 框架：Howard Marks 七维度 × 四层监测_"]

    return "\n".join(lines)


def send_email(to_addr: str, subject: str, body_md: str,
               smtp_host: str | None = None, smtp_user: str | None = None,
               smtp_password: str | None = None) -> bool:
    smtp_host = smtp_host or os.getenv("SMTP_HOST")
    smtp_user = smtp_user or os.getenv("SMTP_USER")
    smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    if not all([smtp_host, smtp_user, smtp_password]):
        log.warning("SMTP 配置缺失，跳过邮件")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_addr
    msg.attach(MIMEText(body_md, "plain", "utf-8"))
    html = f"<pre style='font-family:monospace;white-space:pre-wrap;'>{body_md}</pre>"
    msg.attach(MIMEText(html, "html", "utf-8"))
    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30) as srv:
            srv.login(smtp_user, smtp_password)
            srv.sendmail(smtp_user, to_addr, msg.as_string())
        log.info(f"邮件已发送至 {to_addr}")
        return True
    except Exception as e:
        log.error(f"邮件发送失败：{e}")
        return False


def persist_series(report: "Report") -> None:
    """全部数值型指标追加进统一时序CSV(date,name,value,status),同日同名去重,NaN过滤。
    没有历史就永远无法回测——落盘是本脚本的核心产出,报告只是副产品。"""
    import csv
    sdir = Path.home() / ".local" / "state" / "market-sentiment"
    sdir.mkdir(parents=True, exist_ok=True)
    path = sdir / "sentiment_series.csv"
    date = f"{report.timestamp:%Y-%m-%d}"
    old = {}
    if path.exists():
        with open(path, newline="") as f:
            for r in csv.reader(f):
                if len(r) == 4 and r[0] != "date":
                    old[(r[0], r[1])] = (r[2], r[3])
    n = 0
    for ind in report.indicators:
        if isinstance(ind.value, (int, float)) and ind.value == ind.value:
            old[(date, ind.name)] = (f"{float(ind.value):.4f}", ind.status)
            n += 1
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "name", "value", "status"])
        for (d, name), (v, st) in sorted(old.items()):
            w.writerow([d, name, v, st])
    log.info(f"时序落盘：{path} (+{n} 指标)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", help="收件人邮箱")
    parser.add_argument("--skip-us", action="store_true")
    parser.add_argument("--skip-cn", action="store_true")
    args = parser.parse_args()

    log.info("=" * 50)
    log.info("市场情绪监测开始 v2")
    log.info("=" * 50)

    report = Report()
    if not args.skip_us:
        collect_us_indicators(report)
    if not args.skip_cn:
        collect_a_share_indicators(report)

    md = generate_markdown(report)
    out_path = REPORT_DIR / f"sentiment_report_{report.timestamp:%Y-%m-%d}.md"
    out_path.write_text(md, encoding="utf-8")
    log.info(f"Markdown 报告：{out_path}")

    persist_series(report)  # 时序落盘:核心产出,勿删(插件更新覆盖过一次,2026-10-08重打)

    try:
        from html_dashboard import generate_dashboard
        html = generate_dashboard(report)
        html_path = REPORT_DIR / f"sentiment_dashboard_{report.timestamp:%Y-%m-%d}.html"
        html_path.write_text(html, encoding="utf-8")
        log.info(f"HTML 仪表盘：{html_path}")
    except ImportError:
        log.warning("html_dashboard.py 不在同目录，跳过 HTML 仪表盘")
    except Exception as e:
        log.error(f"HTML 仪表盘失败：{e}")

    if args.email:
        send_email(args.email,
                   f"市场情绪周报 {report.timestamp:%Y-%m-%d}",
                   md)

    print("\n" + "=" * 60)
    print(f"完成。指标总数：{len(report.indicators)}，失败：{len(report.errors)}")
    print(f"Markdown：{out_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
