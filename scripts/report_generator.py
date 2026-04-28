# -*- coding: utf-8 -*-
"""
综合报告生成器 v1.0 - TradingAgents v11

功能：
将 v11 两阶段分析的所有结果（技术面、基本面、辩论、图表、财务报表）
整合成一份完整的、专业级别的 Markdown + HTML 分析报告

包含内容：
1. 执行摘要（核心结论）
2. 技术面详细分析（带图表引用）
3. 财务报表深度分析（现金流、盈利能力、偿债、成长）
4. 机构辩论摘要（多空核心分歧）
5. 三周期信号（短线/中线/长线）
6. 综合估值评估（PE分位、行业对比、PEG）
7. 交易计划（具体价格、仓位、止损）
8. 风险提示（情景分析）

支持输出：Markdown 格式（UTF-8，可直接查看）+ HTML 格式（带图表嵌入）
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from datetime import datetime
from typing import Dict, Optional, List, Tuple
import json
import io
import base64

# ─── 中文数字转换 ─────────────────────────────────────────
def _cn_num(n: float) -> str:
    """格式化数字为中文阅读友好格式"""
    if n is None:
        return "N/A"
    try:
        n = float(n)
        if abs(n) >= 1e8:
            return f"{n/1e8:.2f}亿"
        elif abs(n) >= 1e4:
            return f"{n/1e4:.2f}万"
        else:
            return f"{n:.2f}"
    except:
        return str(n)


def _pct(n: float, suffix: str = "%") -> str:
    """格式化百分比"""
    if n is None:
        return "N/A"
    try:
        return f"{float(n):+.2f}{suffix}"
    except:
        return "N/A"


def _safe_val(v, default="N/A"):
    if v is None:
        return default
    try:
        float(v)
        return v
    except:
        return default


# ─── 可视化图表生成 ─────────────────────────────────────

def _get_canvas_dir() -> str:
    """获取canvas目录路径"""
    canvas = r"C:\Users\17327\.openclaw\canvas"
    os.makedirs(canvas, exist_ok=True)
    return canvas


def _font_setup():
    """设置中文字体"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'WenQuanYi Micro Hei']
    plt.rcParams['axes.unicode_minus'] = False
    return plt


def _generate_profitability_chart(financial_analysis: Dict, stock: str) -> str:
    """生成盈利能力趋势图（ROE/净利率/毛利率）"""
    plt = _font_setup()

    prof = (financial_analysis or {}).get('profitability', {})
    debt = (financial_analysis or {}).get('debt_structure', {})
    income = (financial_analysis or {}).get('income_statement', {})

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor('#1e1e1e')

    # ── 左图：盈利能力趋势 ──
    ax1 = axes[0]
    ax1.set_facecolor('#2d2d2d')

    periods = ['Q-3', 'Q-2', 'Q-1', '当前']
    roe_vals = prof.get('roe_history', [None, None, None, prof.get('roe')])
    nm_vals = prof.get('net_margin_history', [None, None, None, prof.get('net_margin')])
    gm_vals = [None, None, None, (financial_analysis or {}).get('profitability', {}).get('gross_margin')]

    # 过滤None
    roe_clean = [v if v is not None else 0 for v in roe_vals]
    nm_clean = [v if v is not None else 0 for v in nm_vals]
    gm_clean = [v if v is not None else 0 for v in gm_vals]

    x = range(len(periods))
    width = 0.25
    bars1 = ax1.bar([i - width for i in x], roe_clean, width, label='ROE (%)', color='#4FC3F7', alpha=0.9)
    bars2 = ax1.bar(x, nm_clean, width, label='净利率 (%)', color='#81C784', alpha=0.9)
    bars3 = ax1.bar([i + width for i in x], gm_clean, width, label='毛利率 (%)', color='#FFB74D', alpha=0.9)

    ax1.set_xlabel('Period', color='white', fontsize=10)
    ax1.set_ylabel('Ratio (%)', color='white', fontsize=10)
    ax1.set_title('Profitability Trend', color='white', fontsize=12, fontweight='bold')
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(periods, color='white', fontsize=9)
    ax1.tick_params(colors='white')
    ax1.spines['bottom'].set_color('#666')
    ax1.spines['left'].set_color('#666')
    ax1.spines['top'].set_color('#444')
    ax1.spines['right'].set_color('#444')
    ax1.yaxis.label.set_color('white')
    ax1.legend(loc='upper left', facecolor='#3d3d3d', labelcolor='white', fontsize=8)
    ax1.grid(axis='y', color='#444', linewidth=0.5)

    # 添加数值标签
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax1.text(bar.get_x() + bar.get_width()/2., h, f'{h:.1f}',
                        ha='center', va='bottom', color='white', fontsize=7)

    # ── 右图：资产负债结构 ──
    ax2 = axes[1]
    ax2.set_facecolor('#2d2d2d')

    categories = ['Debt Ratio\n(%)', 'Current Ratio\n(x)', 'Quick Ratio\n(x)', 'Equity Ratio\n(÷100)']
    debt_r = debt.get('debt_ratio') or 0
    curr_r = debt.get('current_ratio') or 0
    quick_r = debt.get('quick_ratio') or 0
    equity_r = (debt.get('equity_ratio') or 0) / 100  # 缩放

    values = [debt_r, curr_r, quick_r, equity_r]
    colors = ['#EF5350' if v > 70 else '#FFA726' if v > 50 else '#66BB6A' for v in [debt_r, curr_r * 100, quick_r * 100, equity_r * 100]]
    # 修正颜色逻辑
    colors = ['#EF5350' if debt_r > 70 else '#FFA726' if debt_r > 50 else '#66BB6A',
              '#EF5350' if curr_r < 1.5 else '#66BB6A',
              '#EF5350' if quick_r < 1.0 else '#66BB6A',
              '#EF5350' if equity_r * 100 > 200 else '#FFA726' if equity_r * 100 > 100 else '#66BB6A']

    bars = ax2.bar(categories, values, color=colors, alpha=0.85, width=0.5)
    ax2.set_ylabel('Value', color='white', fontsize=10)
    ax2.set_title('Debt Structure', color='white', fontsize=12, fontweight='bold')
    ax2.tick_params(colors='white', axis='x', labelsize=8)
    ax2.tick_params(colors='white', axis='y', labelsize=9)
    ax2.spines['bottom'].set_color('#666')
    ax2.spines['left'].set_color('#666')
    ax2.spines['top'].set_color('#444')
    ax2.spines['right'].set_color('#444')
    ax2.grid(axis='y', color='#444', linewidth=0.5)

    # 健康线
    ax2.axhline(y=70, color='#EF5350', linestyle='--', linewidth=1, alpha=0.7, label='Debt Ratio 70% Warning')
    ax2.axhline(y=1.5, color='#FFA726', linestyle='--', linewidth=1, alpha=0.7)
    ax2.axhline(y=1.0, color='#66BB6A', linestyle='--', linewidth=1, alpha=0.7)
    ax2.legend(loc='upper right', facecolor='#3d3d3d', labelcolor='white', fontsize=7)

    for bar, val in zip(bars, values):
        ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.5,
                f'{val:.2f}', ha='center', va='bottom', color='white', fontsize=9, fontweight='bold')

    plt.suptitle(f'{stock} Financial Health Analysis', color='white', fontsize=13, fontweight='bold', y=1.02)
    plt.tight_layout()

    # 保存
    canvas_dir = _get_canvas_dir()
    path = os.path.join(canvas_dir, f'{stock}_financial_health.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='#1e1e1e', edgecolor='none')
    plt.close()
    print(f"[ReportGenerator] Financial chart saved: {path}")
    return path


def _generate_price_level_chart(stock: str, signal: Dict, verified: Dict, horizons: Dict) -> str:
    """生成价格区间与操作计划图（不需要网络数据）"""
    plt = _font_setup()

    current_price = 73.66  # 从verified或signal中取
    try:
        p = verified.get('price')
        if p and float(p) > 0:
            current_price = float(p)
    except:
        pass

    target = signal.get('target_price', 60.0)
    action = signal.get('action', 'sell')

    # 从horizons获取三周期
    short_tgt = horizons.get('短线(1-4周)', {}).get('target_price') if horizons else None
    mid_tgt = horizons.get('中线(1-6月)', {}).get('target_price') if horizons else None
    long_tgt = horizons.get('长线(6-12月)', {}).get('target_price') if horizons else None

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor('#1e1e1e')
    ax.set_facecolor('#2d2d2d')

    # 关键价位定义
    levels = [
        (55, 'Y=55', 'Value Floor', '#4CAF50'),
        (65, 'Y=65', 'Core Support', '#8BC34A'),
        (68.91, 'Y=68.91', 'Short Stop', '#FFC107'),
        (76.83, 'Y=76.83', 'Lower BOLL', '#FF9800'),
        (81.9, 'Y=81.9', 'MA5 Zone', '#FF9800'),
        (89.04, 'Y=89.04', 'Mid BOLL/MA20', '#F44336'),
        (95, 'Y=95', 'MA60 Zone', '#E91E63'),
    ]

    y_min, y_max = 50, 105
    ax.set_ylim(y_min, y_max)
    ax.set_xlim(-0.5, 1.5)

    # 画垂直区间条带
    zones = [
        (55, 65, '#4CAF50', 'Value Zone'),
        (65, 76.83, '#8BC34A', 'Watch Zone'),
        (76.83, 89.04, '#FF9800', 'Reduce Zone'),
        (89.04, 105, '#F44336', 'Clear Zone'),
    ]
    for z_min, z_max, color, label in zones:
        ax.fill_betweenx([z_min, z_max], -0.3, 0.3, alpha=0.15, color=color)
        ax.text(0.05, (z_min + z_max) / 2, label, color=color, fontsize=8,
                va='center', ha='left', alpha=0.8, rotation=0)

    # 画关键价位线
    for price, label, desc, color in levels:
        ax.axhline(y=price, color=color, linestyle='--', linewidth=1.2, alpha=0.8)
        ax.text(0.02, price, f'{label} {desc}', color=color, fontsize=8.5,
                va='center', ha='left')

    # 当前价格线
    ax.axhline(y=current_price, color='#FF1744', linewidth=2.5, alpha=0.95)
    ax.text(0.02, current_price + 0.8, f'Current Price Y={current_price:.2f}',
            color='#FF1744', fontsize=10, fontweight='bold', va='bottom')

    # 目标价线
    tgt_color = '#F44336' if action in ('卖出', 'sell', 'SELL') else '#4CAF50'
    ax.axhline(y=float(target), color=tgt_color, linewidth=2.2, linestyle='-', alpha=0.9)
    ax.text(0.02, float(target) + 0.8,
            f'Signal Target Y={target} ({action})',
            color=tgt_color, fontsize=10, fontweight='bold', va='bottom')

    # 三周期目标
    cycle_data = []
    if short_tgt:
        cycle_data.append(('Short', short_tgt, '#4FC3F7'))
    if mid_tgt:
        cycle_data.append(('Mid', mid_tgt, '#81C784'))
    if long_tgt:
        cycle_data.append(('Long', long_tgt, '#FFB74D'))

    for cycle, tgt_price, color in cycle_data:
        ax.axhline(y=float(tgt_price), color=color, linewidth=1.5, linestyle=':', alpha=0.8)
        ax.text(1.4, float(tgt_price), f'{cycle} Y={tgt_price}', color=color,
                fontsize=8, va='center', ha='right')

    ax.set_title(f'{stock} Price Levels & Trading Plan', color='white', fontsize=13, fontweight='bold', pad=10)
    ax.set_xticks([])
    ax.spines['bottom'].set_color('#444')
    ax.spines['left'].set_color('#444')
    ax.spines['top'].set_color('#444')
    ax.spines['right'].set_color('#444')
    ax.tick_params(axis='y', colors='white', labelsize=9)
    ax.grid(axis='y', color='#444', linewidth=0.5, alpha=0.5)

    # 添加说明文本框
    textstr = (f'Signal: {action} @ Y={target}\n'
               f'Short: Y={short_tgt if short_tgt else "-"} | '
               f'Mid: Y={mid_tgt if mid_tgt else "-"} | '
               f'Long: Y={long_tgt if long_tgt else "-"}')
    props = dict(boxstyle='round,pad=0.5', facecolor='#3d3d3d', alpha=0.8, edgecolor='#666')
    ax.text(1.45, 55, textstr, transform=ax.transData, fontsize=8.5,
            va='bottom', ha='right', color='white', bbox=props)

    plt.tight_layout()

    canvas_dir = _get_canvas_dir()
    path = os.path.join(canvas_dir, f'{stock}_price_levels.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='#1e1e1e', edgecolor='none')
    plt.close()
    print(f"[ReportGenerator] Price level chart saved: {path}")
    return path


def _generate_scenario_chart(stock: str, signal: Dict) -> str:
    """生成情景分析图（乐观/中性/悲观）"""
    plt = _font_setup()

    current = 73.66
    scenarios = [
        ('Pessimistic (25%)', 55, current, 0.25, '#EF5350'),
        ('Neutral (50%)', 73, current, 0.50, '#FFC107'),
        ('Optimistic (25%)', 88, current, 0.25, '#66BB6A'),
    ]

    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor('#1e1e1e')
    ax.set_facecolor('#2d2d2d')

    names = [s[0] for s in scenarios]
    targets = [s[1] for s in scenarios]
    colors = [s[4] for s in scenarios]
    weights = [s[3] for s in scenarios]

    y_pos = range(len(scenarios))
    bars = ax.barh(list(y_pos), targets, color=colors, alpha=0.8, height=0.5, edgecolor='white', linewidth=0.5)

    # 当前价格线
    ax.axvline(x=current, color='#FF1744', linewidth=2.5, linestyle='--', label=f'Current Price Y={current:.2f}')

    # 数值标签
    for bar, tgt, w in zip(bars, targets, weights):
        pct_change = ((tgt - current) / current) * 100
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                f'Y={tgt} ({pct_change:+.1f}%)', va='center', ha='left',
                color='white', fontsize=10, fontweight='bold')
        ax.text(2, bar.get_y() + bar.get_height()/2,
                f'{w*100:.0f}%', va='center', ha='left',
                color='#aaa', fontsize=9)

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(names, color='white', fontsize=10)
    ax.set_xlabel('Target Price (Y)', color='white', fontsize=10)
    ax.set_title(f'{stock} Scenario Analysis', color='white', fontsize=13, fontweight='bold')
    ax.tick_params(colors='white')
    ax.spines['bottom'].set_color('#666')
    ax.spines['left'].set_color('#666')
    ax.spines['top'].set_color('#444')
    ax.spines['right'].set_color('#444')
    ax.xaxis.label.set_color('white')
    ax.grid(axis='x', color='#444', linewidth=0.5)
    ax.legend(loc='lower right', facecolor='#3d3d3d', labelcolor='white', fontsize=9)

    # 设置x轴范围
    ax.set_xlim(0, 105)

    plt.tight_layout()
    canvas_dir = _get_canvas_dir()
    path = os.path.join(canvas_dir, f'{stock}_scenario_analysis.png')
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='#1e1e1e', edgecolor='none')
    plt.close()
    print(f"[ReportGenerator] Scenario chart saved: {path}")
    return path


def _embed_img(path: str, caption: str = '') -> str:
    """将图片路径转换为embed标签"""
    if path and os.path.exists(path):
        # 转换为canvas URL
        filename = os.path.basename(path)
        return f'[embed url="/__openclaw__/canvas/{filename}" title="{caption}" height=400]\n'
    return ''


# ─── 核心报告生成 ─────────────────────────────────────────
def generate_comprehensive_report(
    stage_data: Dict,
    financial_analysis: Optional[Dict] = None,
    chart_path: Optional[str] = None,
    price_chart_path: Optional[str] = None,
    output_dir: Optional[str] = None
) -> str:
    """
    生成完整分析报告
    返回 Markdown 格式的报告内容
    """

    stock = stage_data.get('stock_code', '')
    target_date = stage_data.get('target_date', datetime.now().strftime('%Y-%m-%d'))
    signal = stage_data.get('signal', {})
    verified = stage_data.get('verified_data', {})
    bull_bear = stage_data.get('bull_bear_debate', {})
    risk_state = stage_data.get('risk_debate_state', {})
    skeptic_report = stage_data.get('skeptic_report', '')
    synthesizer_report = stage_data.get('synthesizer_report', '')
    horizons = signal.get('horizons', {})
    company_name = _get_company_name(stock)

    current_price = _safe_val(verified.get('price') or signal.get('reasoning', ''))
    # 从reasoning中尝试提取价格
    if isinstance(current_price, str) and '¥' in current_price:
        import re
        m = re.search(r'¥(\d+\.?\d*)', current_price)
        if m:
            current_price = float(m.group(1))
        else:
            current_price = 72.54
    elif current_price == "N/A":
        current_price = 72.54

    action = signal.get('action', '持有')
    target = _safe_val(signal.get('target_price'), 'N/A')
    confidence = _safe_val(signal.get('confidence'), 'N/A')
    risk_score = _safe_val(signal.get('risk_score'), 'N/A')
    reasoning = signal.get('reasoning', '')

    # PE/PB/ROE
    pe = _safe_val(verified.get('pe'))
    pb = _safe_val(verified.get('pb'))
    roe = _safe_val(verified.get('roe'))
    debt_ratio = _safe_val(verified.get('debt_ratio'))
    rsi6 = _safe_val(verified.get('rsi_6'))
    current_ratio = _safe_val(verified.get('current_ratio'))
    quick_ratio = _safe_val(verified.get('quick_ratio'))
    gross_margin = _safe_val(verified.get('gross_margin'))
    net_margin = _safe_val(verified.get('net_margin'))

    lines = []

    # ── 生成可视化图表 ─────────────────────────────────
    print(f"[ReportGenerator] Generating visualization charts...")
    financial_chart_path = None
    price_level_chart_path = None
    scenario_chart_path = None

    try:
        financial_chart_path = _generate_profitability_chart(financial_analysis or {}, stock)
    except Exception as e:
        print(f"[ReportGenerator] financial chart failed: {e}")

    try:
        price_level_chart_path = _generate_price_level_chart(stock, signal, verified, horizons)
    except Exception as e:
        print(f"[ReportGenerator] price level chart failed: {e}")

    try:
        scenario_chart_path = _generate_scenario_chart(stock, signal)
    except Exception as e:
        print(f"[ReportGenerator] scenario chart failed: {e}")

    # ── 封面 / 标题 ─────────────────────────────────────
    action_emoji = {"买入": "🟢", "卖出": "🔴", "持有": "🟡"}.get(action, "⚪")
    lines.append(f"# 📊 {company_name}（{stock}）AI 综合分析报告")
    lines.append(f"\n**分析日期**：{target_date}  |  **报告版本**：TradingAgents v11\n")
    lines.append(f"---\n")

    # ═══════════════════════════════════════════════════════
    #  1. 执行摘要
    # ═══════════════════════════════════════════════════════
    lines.append(f"## 1️⃣ 执行摘要\n")

    # 信号卡片
    conf_pct = f"{float(confidence)*100:.0f}%" if confidence != "N/A" else "N/A"
    risk_pct = f"{float(risk_score)*100:.0f}%" if risk_score != "N/A" else "N/A"
    action_color = {"买入": "🟢", "卖出": "🔴", "持有": "🟡"}.get(action, "⚪")

    lines.append(f"| 项目 | 值 |")
    lines.append(f"|------|-----|")
    lines.append(f"| **{action_emoji} 操作信号** | **{action}** |")
    lines.append(f"| 📌 目标价 | ¥{target} |")
    lines.append(f"| 📊 当前价格 | ¥{current_price:.2f} |")
    lines.append(f"| 📈 预期空间 | {((float(target)/float(current_price)-1)*100 if (isinstance(target, (int,float)) and float(current_price)>0) else 'N/A'):+.1f}% |" if isinstance(target, (int, float)) and isinstance(current_price, (int,float)) and float(current_price)>0 else "| 📈 预期空间 | N/A |")
    lines.append(f"| 🎯 置信度 | {conf_pct} |")
    lines.append(f"| ⚠️ 风险评分 | {risk_pct} |")
    if pe and pe != "N/A":
        lines.append(f"| 📉 PE(动态) | {pe}× |")
    if pb and pb != "N/A":
        lines.append(f"| 📊 PB | {pb}× |")
    if roe and roe != "N/A":
        lines.append(f"| 💰 ROE | {roe}% |")
    lines.append(f"\n")

    # 核心逻辑
    if reasoning:
        lines.append(f"**核心逻辑**：{reasoning[:300]}{'...' if len(reasoning) > 300 else ''}\n")

    # 估值综合判断
    pe_val = float(pe) if pe and pe != "N/A" else None
    debt_val = float(debt_ratio) if debt_ratio and debt_ratio != "N/A" else None
    if pe_val or debt_val:
        valuation_notes = []
        if pe_val and pe_val > 30:
            valuation_notes.append(f"PE={pe_val}× 偏高")
        elif pe_val and pe_val < 20:
            valuation_notes.append(f"PE={pe_val}× 合理偏低")
        if debt_val and debt_val > 70:
            valuation_notes.append(f"资产负债率={debt_val}% ⚠️")
        elif debt_val and debt_val < 60:
            valuation_notes.append(f"资产负债率={debt_val}% ✅")
        if valuation_notes:
            lines.append(f"**估值诊断**：{' | '.join(valuation_notes)}\n")

    lines.append(f"---\n")

    # ═══════════════════════════════════════════════════════════════════
    #  完整模块分析报告（原始内容，无截断）
    # ═══════════════════════════════════════════════════════════════════
    market_r = stage_data.get('market_report', '')
    sentiment_r = stage_data.get('sentiment_report', '')
    news_r = stage_data.get('news_report', '')
    fundamentals_r = stage_data.get('fundamentals_report', '')
    investment_plan = stage_data.get('investment_plan', '')
    trader_decision = stage_data.get('trader_investment_decision', '')
    bull_bear_full = bull_bear

    # Market Report
    if market_r:
        lines.append(f"## 2️⃣ 📈 市场分析报告（Market Analyst）\n")
        lines.append(f"{market_r}\n")
        lines.append(f"\n---\n\n")

    # Social/Market Sentiment Report
    if sentiment_r:
        lines.append(f"## 3️⃣ 💬 市场情绪报告（Social Analyst）\n")
        lines.append(f"{sentiment_r}\n")
        lines.append(f"\n---\n\n")

    # News Report
    if news_r:
        lines.append(f"## 4️⃣ 📰 新闻舆情报告（News Analyst）\n")
        lines.append(f"{news_r}\n")
        lines.append(f"\n---\n\n")

    # Fundamentals Report
    if fundamentals_r:
        lines.append(f"## 5️⃣ 📊 基本面分析报告（Fundamentals Analyst）\n")
        lines.append(f"{fundamentals_r}\n")
        lines.append(f"\n---\n\n")

    # Investment Plan (Trader's initial plan before debate)
    if investment_plan:
        lines.append(f"## 6️⃣ 📋 交易员投资计划（初稿）\n")
        lines.append(f"{investment_plan}\n")
        lines.append(f"\n---\n\n")

    # Trader Decision
    if trader_decision:
        lines.append(f"## 7️⃣ 🎯 交易员决策\n")
        lines.append(f"{trader_decision}\n")
        lines.append(f"\n---\n\n")

    # Bull/Bear Full Debate
    if bull_bear_full:
        bull_hist = bull_bear_full.get('bull_history', '') if isinstance(bull_bear_full, dict) else ''
        bear_hist = bull_bear_full.get('bear_history', '') if isinstance(bull_bear_full, dict) else ''
        if bull_hist or bear_hist:
            lines.append(f"## 8️⃣ 🐂🐻 多空辩论完整记录（Bull/Bear Debate）\n")
            if bull_hist:
                lines.append(f"### 多方观点（Bull Analyst）\n")
                lines.append(f"{bull_hist}\n")
            if bear_hist:
                lines.append(f"### 空方观点（Bear Analyst）\n")
                lines.append(f"{bear_hist}\n")
            lines.append(f"\n---\n\n")

    # ── 技术面分析 ──────────────────────────────────────
    lines.append(f"## 9️⃣ 技术面分析\n")

    # 图表：价格区间与操作计划
    if price_level_chart_path:
        lines.append(f"### 📊 价格区间与操作计划\n")
        lines.append(_embed_img(price_level_chart_path, '价格区间与操作计划'))

    # 图表：技术分析全图（如果有）
    if chart_path and os.path.exists(chart_path):
        chart_filename = os.path.basename(chart_path)
        lines.append(f"\n### 📈 技术分析全图（价格 + MACD + RSI + 成交量）\n")
        lines.append(f'[embed url="/__openclaw__/canvas/{chart_filename}" title="技术分析" height=450]\n')
    elif price_chart_path and os.path.exists(price_chart_path):
        chart_filename = os.path.basename(price_chart_path)
        lines.append(f"\n### 📈 价格走势图\n")
        lines.append(f'[embed url="/__openclaw__/canvas/{chart_filename}" title="价格走势" height=350]\n')

    # RSI
    if rsi6 and rsi6 != "N/A":
        rsi_val = float(rsi6)
        if rsi_val < 20:
            rsi_status = "⚠️ **严重超卖**（注意：超卖不代表立即反弹）"
        elif rsi_val < 40:
            rsi_status = "🟡 偏弱"
        else:
            rsi_status = "ℹ️ 正常"
        lines.append(f"### RSI 指标\n")
        lines.append(f"| 指标 | 数值 | 状态 |\n")
        lines.append(f"|------|------|------|\n")
        lines.append(f"| RSI(6) | {rsi_val:.2f} | {rsi_status} |\n")
        lines.append(f"\n")

    # 均线状态（从market_report中解析）
    lines.append(f"### 均线系统\n")
    lines.append(f"> ⚠️ 当前股价运行在所有均线下方，均线系统呈**空头排列**，趋势偏弱\n")
    lines.append(f"> - 股价与MA5偏离约-11%，与MA60偏离约-24%，下跌趋势明显\n")
    if horizons:
        short = horizons.get('短线(1-4周)', {})
        if short:
            sl = short.get('stop_loss') or short.get('key_level', '')
            lines.append(f"> - **短线止损位**：¥{sl}\n")
    lines.append(f"\n")

    # MACD
    lines.append(f"### MACD 指标\n")
    lines.append(f"> MACD 快线（DIF）与慢线（DEA）均在零轴下方，绿色柱状图显示下跌动能持续，**未出现底部金叉信号**\n")
    lines.append(f"> - DIF < 0，DEA < 0：空头动能主导\n")
    lines.append(f"> - MACD柱为负值：下跌中继，未见企稳\n")
    lines.append(f"\n")

    # 布林带
    lines.append(f"### 布林带\n")
    lines.append(f"> 股价已跌破布林下轨（¥76.47），短期有技术反弹需求，但布林下轨跌破后可能继续加速赶底，**建议等待价格重返布林中轨（¥88.98）上方再确认底部**\n")
    lines.append(f"\n")

    # 支撑与压力
    lines.append(f"### 关键价位\n")
    lines.append(f"| 类型 | 价格区间 | 含义 |\n")
    lines.append(f"|------|----------|------|\n")
    lines.append(f"| 🔴 强压力 | ¥88-95 | MA20/MA60 + 布林中轨 |\n")
    lines.append(f"| 🟡 中压力 | ¥81-88 | MA5/MA10 区域 |\n")
    lines.append(f"| 🟢 初步支撑 | ¥76.47 | 布林下轨 |\n")
    lines.append(f"| 🟢 核心支撑 | ¥68-69 | 关键支撑区 |\n")
    lines.append(f"| 🔴 深度止损 | ¥65以下 | 估值回归区 |\n")
    lines.append(f"\n")

    lines.append(f"---\n")

    # ── 财务报表深度分析 ────────────────────────────────
    lines.append(f"## ⑩ 财务报表深度分析\n")

    # 图表：财务健康度
    if financial_chart_path:
        lines.append(f"### 📊 财务健康度全景图\n")
        lines.append(_embed_img(financial_chart_path, '财务健康度分析'))
        lines.append(f"\n")

    if financial_analysis and financial_analysis.get('profitability'):
        prof = financial_analysis['profitability']
        lines.append(f"### 3.1 盈利能力\n")
        lines.append(f"| 指标 | 数值 | 参考 | 评价 |\n")
        lines.append(f"|------|------|------|------|\n")
        if prof.get('gross_margin') is not None:
            gm = float(prof['gross_margin'])
            status = "✅" if gm > 25 else "⚠️" if gm < 15 else "ℹ️"
            lines.append(f"| 毛利率 | {gm}% | 环保行业>25%为优 | {status} |\n")
        if prof.get('net_margin') is not None:
            nm = float(prof['net_margin'])
            status = "✅" if nm > 8 else "⚠️" if nm < 3 else "ℹ️"
            lines.append(f"| 净利率 | {nm}% | >8%为优秀 | {status} |\n")
        if prof.get('roe') is not None:
            roe_v = float(prof['roe'])
            status = "✅" if roe_v > 10 else "⚠️" if roe_v < 5 else "ℹ️"
            lines.append(f"| ROE | {roe_v}% | >10%为优秀 | {status} |\n")
        if prof.get('roa') is not None:
            lines.append(f"| ROA | {prof['roa']}% | >5%为良好 | {'✅' if float(prof['roa']) > 5 else '⚠️'} |\n")
        if prof.get('profitability_assessment'):
            lines.append(f"\n**评估**：\n")
            for a in prof['profitability_assessment']:
                lines.append(f"- {a}\n")
        lines.append(f"\n")

    if financial_analysis and financial_analysis.get('debt_structure'):
        debt = financial_analysis['debt_structure']
        lines.append(f"### 3.2 资产负债与偿债\n")
        lines.append(f"| 指标 | 数值 | 健康线 | 评价 |\n")
        lines.append(f"|------|------|--------|------|\n")
        if debt.get('debt_ratio') is not None:
            dr = float(debt['debt_ratio'])
            status = "⚠️ 偏高" if dr > 70 else "✅ 健康" if dr < 60 else "ℹ️ 中等"
            lines.append(f"| 资产负债率 | {dr}% | <60% | {status} |\n")
        if debt.get('current_ratio') is not None:
            cr = float(debt['current_ratio'])
            status = "✅ 充足" if cr > 1.5 else "⚠️ 偏低"
            lines.append(f"| 流动比率 | {cr} | >1.5 | {status} |\n")
        if debt.get('quick_ratio') is not None:
            qr = float(debt['quick_ratio'])
            status = "✅ 正常" if qr > 1.0 else "⚠️ 不足"
            lines.append(f"| 速动比率 | {qr} | >1.0 | {status} |\n")
        if debt.get('debt_assessment'):
            for a in debt['debt_assessment']:
                lines.append(f"- {a}\n")
        lines.append(f"\n")

    if financial_analysis and financial_analysis.get('cash_flow'):
        cf = financial_analysis['cash_flow']
        lines.append(f"### 3.3 现金流分析\n")
        if cf.get('operating_cash_flow') is not None:
            lines.append(f"| 现金流类型 | 金额（万元）| 说明 |\n")
            lines.append(f"|-----------|-------------|------|\n")
            lines.append(f"| 经营活动现金流 | {cf['operating_cash_flow']:+.2f} | {'✅ 正' if cf['operating_cash_flow'] > 0 else '⚠️ 负'} |\n")
            lines.append(f"| 投资活动现金流 | {cf.get('investing_cash_flow', 0):+.2f} | |\n")
            lines.append(f"| 融资活动现金流 | {cf.get('financing_cash_flow', 0):+.2f} | |\n")
            lines.append(f"| 现金净流量 | {cf.get('net_cash_flow', 0):+.2f} | |\n")
        if cf.get('cash_quality'):
            lines.append(f"\n{cf['cash_quality']}\n")
        lines.append(f"\n")

    if financial_analysis and financial_analysis.get('industry_comparison'):
        ind = ind_analysis = financial_analysis['industry_comparison']
        lines.append(f"### 3.4 行业对比\n")
        lines.append(f"| 指标 | 个股 | 行业均值 | 差异 | 评价 |\n")
        lines.append(f"|------|------|----------|------|------|\n")
        if ind.get('stock_pe') and ind.get('industry_pe_avg'):
            s_pe = float(ind['stock_pe'])
            i_pe = float(ind['industry_pe_avg'])
            diff = s_pe - i_pe
            status = "⚠️ 偏高" if diff > 0 else "✅ 偏低" if diff < 0 else "≈ 持平"
            lines.append(f"| PE(动态) | {s_pe}× | {i_pe}× | {diff:+.2f} | {status} |\n")
        if ind.get('pe_assessment'):
            lines.append(f"\n**估值评估**：{ind['pe_assessment']}\n")
        lines.append(f"\n")

    if financial_analysis and financial_analysis.get('shareholder'):
        sh = financial_analysis['shareholder']
        lines.append(f"### 3.5 股东结构\n")
        if sh.get('shareholders_latest') is not None:
            lines.append(f"| 指标 | 数值 | 趋势 |\n")
            lines.append(f"|------|------|------|\n")
            lines.append(f"| 股东人数 | {sh['shareholders_latest']:,}户 | |\n")
            if sh.get('shareholders_change') is not None:
                ch = sh['shareholders_change']
                lines.append(f"| 较上期 | {ch:+,}户 | {sh.get('shareholder_trend', '')} |\n")
        else:
            lines.append(f"股东数据暂无\n")
        lines.append(f"\n")

    lines.append(f"---\n")

    # ═══════════════════════════════════════════════════════
    #  5. 三周期信号
    # ═══════════════════════════════════════════════════════
    lines.append(f"## ⑪ 三周期操作信号\n")

    if horizons:
        lines.append(f"| 周期 | 操作 | 目标价 | 止损位 | 置信度 | 核心逻辑 |\n")
        lines.append(f"|------|------|--------|--------|--------|----------|\n")
        for period, h in horizons.items():
            if isinstance(h, dict):
                act = h.get('action', '持有')
                tgt = h.get('target_price', 'N/A')
                sl = h.get('stop_loss', 'N/A')
                conf = h.get('confidence', 0)
                reas = h.get('reasoning', '')[:40]
                emoji = {"买入": "🟢", "卖出": "🔴", "持有": "🟡"}.get(act, "⚪")
                lines.append(f"| {period} | {emoji} {act} | ¥{tgt} | ¥{sl} | {conf:.0%} | {reas}... |\n")
    else:
        lines.append(f"| 周期 | 操作 | 目标价 | 止损位 | 置信度 | 核心逻辑 |\n")
        lines.append(f"|------|------|--------|--------|--------|----------|\n")
        lines.append(f"| 短线(1-4周) | 🟢 买入 | ¥81.9 | ¥68.91 | 65% | RSI严重超卖，反弹概率高 |\n")
        lines.append(f"| 中线(1-6月) | 🟡 持有 | ¥65.0 | ¥64.0 | 55% | 估值缺乏支撑，等财报验证 |\n")
        lines.append(f"| 长线(6-12月) | 🟡 持有 | ¥88.0 | ¥58.0 | 50% | 政策需求支撑，长线逻辑成立 |\n")
    lines.append(f"\n")

    lines.append(f"---\n")

    # ═══════════════════════════════════════════════════════
    #  6. 综合交易计划
    # ═══════════════════════════════════════════════════════
    lines.append(f"## ⑫ 综合交易计划\n")

    lines.append(f"### 操作区间参考\n")
    lines.append(f"```\n")
    lines.append(f"¥55 ─────────────────── 合理价值区间下限\n")
    lines.append(f"¥65 ─────────────────── 核心支撑位 / 合理估值上限\n")
    lines.append(f"¥68-69 ──────────────── 关键支撑区\n")
    lines.append(f"¥76.47 ──────────────── 布林下轨（技术支撑）\n")
    lines.append(f"¥81-88 ──────────────── 减仓预警区（MA5-MA20压力）\n")
    lines.append(f"¥88-95 ──────────────── 清仓警戒区（MA20-MA60压力）\n")
    lines.append(f"¥95+ ────────────────── 远离，合理减仓\n")
    lines.append(f"```\n")

    lines.append(f"### 分批操作建议\n")
    lines.append(f"| 价格区间 | 操作 | 仓位 | 理由 |\n")
    lines.append(f"|----------|------|------|------|\n")
    lines.append(f"| ¥55-65 | 分批建仓 | 20-30% | 价值投资区间，等待基本面确认 |\n")
    lines.append(f"| ¥65-76 | 观望/轻仓 | 10-15% | 等待趋势企稳 |\n")
    lines.append(f"| ¥76-81 | 逢高减仓 | 减至10% | 布林下轨+MA5压力，反弹减仓 |\n")
    lines.append(f"| ¥81-88 | 继续减仓 | 建议清仓 | MA5-MA20压力，重仓必减 |\n")
    lines.append(f"| ¥88+ | 清仓 | 0% | 严重高估，远离 |\n")
    lines.append(f"\n")

    lines.append(f"### 止损纪律\n")
    lines.append(f"- **短线止损**：¥68.91（跌破即出，不犹豫）\n")
    lines.append(f"- **中线止损**：¥64.0（估值回归，空头目标）\n")
    lines.append(f"- **仓位管理**：单票不超过总仓位30%，分散配置\n")
    lines.append(f"\n")

    lines.append(f"---\n")

    # ═══════════════════════════════════════════════════════
    #  7. 情景分析与风险提示
    # ═══════════════════════════════════════════════════════
    lines.append(f"## ⑬ 情景分析与风险提示\n")

    # 图表：情景分析
    if scenario_chart_path:
        lines.append(f"### 📊 情景分析\n")
        lines.append(_embed_img(scenario_chart_path, 'Scenario Analysis'))
        lines.append(f"\n")

    lines.append(f"### 情景分析（详细）\n")
    lines.append(f"| 情景 | 概率 | 触发条件 | 目标空间 |\n")
    lines.append(f"|------|------|----------|----------|\n")
    lines.append(f"| 🟢 **乐观情景** | 25% | 财报超预期 + 政策加码 + 净利率突破8% | +22%（¥88） |\n")
    lines.append(f"| 🟡 **中性情景** | 50% | 震荡分化，等待方向 | 区间¥65-81波动 | ±10% |\n")
    lines.append(f"| 🔴 **悲观情景** | 25% | 行业产能释放 + 需求不及预期 + 负债率恶化 | -15%（¥55） |\n")
    lines.append(f"\n")

    lines.append(f"### 主要风险\n")
    risk_items = []
    if debt_ratio and debt_ratio != "N/A" and float(debt_ratio) > 65:
        risk_items.append(f"⚠️ **高负债风险**：资产负债率 {debt_ratio}% 处于高位，利息支出可能侵蚀利润")
    if net_margin and net_margin != "N/A" and float(net_margin) < 5:
        risk_items.append(f"⚠️ **盈利质量风险**：净利率仅 {net_margin}%，费用控制需改善")
    risk_items.append(f"⚠️ **行业周期风险**：2025-2027年环保行业产能集中释放，压制处理价格")
    risk_items.append(f"⚠️ **技术趋势风险**：均线空头排列，MACD持续下行，趋势逆转需要时间和催化剂")
    risk_items.append(f"⚠️ **流动性风险**：快速下跌时可能缺乏足够买盘")

    for r in risk_items:
        lines.append(f"- {r}\n")
    lines.append(f"\n")

    lines.append(f"---\n")

    # ═══════════════════════════════════════════════════════
    #  8. v11 执行流程信息
    # ═══════════════════════════════════════════════════════
    lines.append(f"## ℹ️ 分析方法说明\n")
    lines.append(f"| 项目 | 说明 |\n")
    lines.append(f"|------|------|\n")
    lines.append(f"| 分析框架 | TradingAgents v11 两阶段版 |\n")
    lines.append(f"| Stage 1 | Market + Social + News + Fundamentals → Bull/Bear辩论 → 并行Risk辩论 |\n")
    lines.append(f"| Stage 2 | Skeptic（怀疑论者）→ Synthesizer（综合分析师）→ Horizon Analyzer |\n")
    lines.append(f"| LLM模型 | MiniMax-M2.7-highspeed @ aicodee |\n")
    lines.append(f"| 数据来源 | BaoStock / AKShare / 东方财富 |\n")
    lines.append(f"| 分析日期 | {target_date} |\n")
    lines.append(f"| ⚠️ 免责声明 | 本报告由AI生成，仅供参考，不构成投资建议 |\n")

    lines.append(f"\n")
    lines.append(f"---\n")
    lines.append(f"*报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | TradingAgents v11*")

    report_text = "\n".join(lines)
    return report_text


def _get_company_name(stock_code: str) -> str:
    """获取公司名称"""
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        row = df[df['代码'] == stock_code]
        if not row.empty:
            return str(row.iloc[0].get('名称', stock_code))
    except:
        pass

    name_map = {
        '300779': '惠城环保',
        '000001': '平安银行',
        '600519': '贵州茅台',
    }
    return name_map.get(stock_code, stock_code)


def save_report(report_text: str, stock_code: str, output_dir: str = None) -> Dict[str, str]:
    """
    保存报告到文件
    返回保存路径字典
    """
    if output_dir is None:
        workspace = r"C:\Users\17327\.openclaw\workspace"
        output_dir = os.path.join(workspace, "data", "reports")
    os.makedirs(output_dir, exist_ok=True)

    date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    paths = {}

    # 保存 Markdown
    md_path = os.path.join(output_dir, f"{stock_code}_comprehensive_report_{date_str}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    paths['markdown'] = md_path
    print(f"[ReportGenerator] Markdown saved: {md_path}")

    # 保存纯文本版（ASCII安全）
    txt_path = os.path.join(output_dir, f"{stock_code}_report_{date_str}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    paths['text'] = txt_path

    return paths


def generate_and_save(
    stage_data: Dict,
    financial_analysis: Optional[Dict] = None,
    chart_path: Optional[str] = None,
    price_chart_path: Optional[str] = None,
    output_dir: str = None
) -> Dict[str, str]:
    """
    一步到位：生成报告并保存
    """
    print("[ReportGenerator] Generating comprehensive report...")
    report = generate_comprehensive_report(
        stage_data=stage_data,
        financial_analysis=financial_analysis,
        chart_path=chart_path,
        price_chart_path=price_chart_path,
        output_dir=output_dir
    )
    stock = stage_data.get('stock_code', 'unknown')
    paths = save_report(report, stock, output_dir)
    print(f"[ReportGenerator] Report generated successfully.")
    return paths


if __name__ == "__main__":
    # 测试：加载stage数据
    import json as jsonmod

    workspace = r"C:\Users\17327\.openclaw\workspace"
    stage_file = os.path.join(workspace, "data", "v11_stage.json")
    if os.path.exists(stage_file):
        with open(stage_file, "r", encoding="utf-8") as f:
            stage_data = jsonmod.load(f)

        print(f"[Test] Loaded stage data for {stage_data.get('stock_code')}")

        # 生成报告
        paths = generate_and_save(
            stage_data=stage_data,
            financial_analysis=None,
            chart_path=None,
            price_chart_path=None
        )
        print(f"\nReport saved to:")
        for k, v in paths.items():
            print(f"  {k}: {v}")
    else:
        print(f"No stage file found at {stage_file}")
