# -*- coding: utf-8 -*-
"""HTML 呈現元件：襯線表格、新聞卡片、評估卡片。
st.dataframe 以 canvas 繪製、CSS 無法改字型，故全站表格改用 HTML 渲染。"""

import html as _html

import numpy as np
import pandas as pd
import streamlit as st


def df_table(df: pd.DataFrame, fmts: dict | None = None,
             signed: set | None = None, height: int | None = None,
             bar_col: str | None = None, bar_max: float | None = None):
    """
    以 HTML 渲染 DataFrame（襯線字、數字等寬右對齊）。
    fmts:   欄名 -> format 字串（如 "{:.2f}"、"{:+.2f}%"）
    signed: 正負著色欄（正=紅、負=綠，台股慣例）
    bar_col/bar_max: 以底色長條呈現的分數欄
    """
    fmts = fmts or {}
    signed = signed or set()
    head = "".join(f"<th>{_html.escape(str(c))}</th>" for c in df.columns)
    body = []
    for _, row in df.iterrows():
        tds = []
        for c in df.columns:
            v = row[c]
            is_num = isinstance(v, (int, float, np.integer, np.floating))
            cls = "num" if is_num else ""
            txt = ""
            if v is None or (is_num and pd.isna(v)):
                txt = "—"
            elif c in fmts and is_num:
                txt = fmts[c].format(v)
            elif is_num:
                txt = f"{v:,.0f}" if float(v).is_integer() else f"{v:,.2f}"
            else:
                txt = _html.escape(str(v))
            if c in signed and is_num and not pd.isna(v):
                cls += " up" if v > 0 else (" down" if v < 0 else "")
            style = ""
            if c == bar_col and is_num and not pd.isna(v) and bar_max:
                pct = max(0.0, min(1.0, float(v) / bar_max)) * 100
                style = (f' style="background:linear-gradient(90deg,'
                         f'var(--accent-soft) {pct}%,transparent {pct}%)"')
            tds.append(f'<td class="{cls}"{style}>{txt}</td>')
        body.append("<tr>" + "".join(tds) + "</tr>")
    h = f' style="max-height:{height}px"' if height else ""
    st.markdown(
        f'<div class="sx-scroll"{h}><table class="sx-table">'
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody>"
        f"</table></div>", unsafe_allow_html=True)


def news_cards(df: pd.DataFrame):
    """新聞卡片：標題（連結）、來源、日期。"""
    cards = []
    for _, r in df.iterrows():
        title = _html.escape(str(r.get("title", ""))[:120])
        link = _html.escape(str(r.get("link", "")))
        src = _html.escape(str(r.get("source", "")))
        dt = _html.escape(str(r.get("date", "")))
        cards.append(
            f'<a class="news-card" href="{link}" target="_blank" '
            f'rel="noopener">'
            f'<div class="news-title">{title}</div>'
            f'<div class="news-meta">{src}｜{dt}</div></a>')
    st.markdown('<div class="news-grid">' + "".join(cards) + "</div>",
                unsafe_allow_html=True)


def verdict_card(verdict: str, tone: str, bullish: list, bearish: list):
    """模型觀點卡片。tone: pos / neu / neg"""
    b1 = "".join(f"<li>{_html.escape(x)}</li>" for x in bullish) or \
         "<li>（無明顯偏多條件）</li>"
    b2 = "".join(f"<li>{_html.escape(x)}</li>" for x in bearish) or \
         "<li>（無明顯風險警示）</li>"
    st.markdown(f"""
<div class="verdict-card verdict-{tone}">
  <div class="verdict-title">{_html.escape(verdict)}</div>
  <div class="verdict-cols">
    <div><div class="verdict-h">支持買進的條件</div><ul>{b1}</ul></div>
    <div><div class="verdict-h">風險與反向訊號</div><ul>{b2}</ul></div>
  </div>
  <div class="verdict-note">以上為機械式條件的當下狀態，描述「若歷史統計關係延續」的傾向；
  未來漲跌無法被預測，本工具不構成投資建議。</div>
</div>""", unsafe_allow_html=True)
