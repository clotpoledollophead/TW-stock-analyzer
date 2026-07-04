# -*- coding: utf-8 -*-
"""
外部開放資料源：
  1. 臺灣證券交易所 OpenAPI（openapi.twse.com.tw/v1）
     - BWIBBU_ALL：上市個股本益比、殖利率、股價淨值比
     - STOCK_DAY_AVG_ALL：上市個股收盤價與月平均價
     （僅涵蓋上市；上櫃個股查不到屬正常）
  2. FinMind（api.finmindtrade.com，開源台股資料 75+ 資料集）
     - TaiwanStockNews：個股新聞（標題、來源、連結）
     匿名可用但有流量限制；可於連線設定填入免費 token 提高額度。
  3. Google News RSS：新聞備援，無需金鑰。
"""

import xml.etree.ElementTree as ET
from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st

_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
       "accept": "application/json"}

TWSE_BASE = "https://openapi.twse.com.tw/v1"
FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"


# ------------------------------------------------------------- TWSE OpenAPI
@st.cache_data(ttl=43200, show_spinner=False)
def _twse_list(endpoint: str) -> list:
    try:
        r = requests.get(f"{TWSE_BASE}{endpoint}", headers=_UA, timeout=15)
        return r.json()
    except Exception:
        return []


def twse_fundamentals(code: str) -> dict:
    """合併 BWIBBU_ALL 與 STOCK_DAY_AVG_ALL，回傳單檔基本面。"""
    out = {}
    for row in _twse_list("/exchangeReport/BWIBBU_ALL"):
        if row.get("Code") == code:
            out["本益比"] = row.get("PEratio", "")
            out["殖利率%"] = row.get("DividendYield", "")
            out["股價淨值比"] = row.get("PBratio", "")
            break
    for row in _twse_list("/exchangeReport/STOCK_DAY_AVG_ALL"):
        if row.get("Code") == code:
            out["月平均價"] = row.get("MonthlyAveragePrice", "")
            break
    return {k: v for k, v in out.items() if str(v).strip() not in ("", "-")}


# ------------------------------------------------------------- FinMind
@st.cache_data(ttl=1800, show_spinner=False)
def finmind_news(code: str, token: str = "", days: int = 14) -> pd.DataFrame:
    """FinMind TaiwanStockNews：回傳 date, title, link, source。"""
    params = {"dataset": "TaiwanStockNews", "data_id": code,
              "start_date": (date.today() - timedelta(days=days)).isoformat()}
    if token:
        params["token"] = token
    try:
        r = requests.get(FINMIND_URL, params=params, headers=_UA, timeout=15)
        data = r.json().get("data", [])
    except Exception:
        return pd.DataFrame()
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    keep = [c for c in ["date", "title", "link", "source"] if c in df.columns]
    return (df[keep].dropna(subset=["title"])
              .sort_values("date", ascending=False).head(12)
              .reset_index(drop=True))


# ------------------------------------------------------------- Google News RSS
@st.cache_data(ttl=1800, show_spinner=False)
def google_news(query: str) -> pd.DataFrame:
    """Google News RSS 搜尋（備援）：回傳 date, title, link, source。"""
    url = ("https://news.google.com/rss/search?q=" + requests.utils.quote(query)
           + "&hl=zh-TW&gl=TW&ceid=TW:zh-Hant")
    try:
        xml = requests.get(url, headers=_UA, timeout=15).text
        root = ET.fromstring(xml)
    except Exception:
        return pd.DataFrame()
    rows = []
    for item in root.iter("item"):
        rows.append({
            "date": (item.findtext("pubDate") or "")[:16],
            "title": item.findtext("title") or "",
            "link": item.findtext("link") or "",
            "source": (item.find("source").text
                       if item.find("source") is not None else "Google News"),
        })
        if len(rows) >= 12:
            break
    return pd.DataFrame(rows)
