# -*- coding: utf-8 -*-
"""Shioaji 連線與行情讀取（純讀取：僅登入、不啟用 CA、不下單）。"""

import time
from datetime import date, timedelta

import pandas as pd
import streamlit as st
import shioaji as sj

# 新舊版相容：1.5+ 建議 sj.QuoteType，舊版在 sj.constant 底下
QuoteType = getattr(sj, "QuoteType", None) or sj.constant.QuoteType
QuoteVersion = getattr(sj, "QuoteVersion", None) or sj.constant.QuoteVersion


# ---------------------------------------------------------------- 連線
def do_login(api_key: str, secret_key: str):
    """一律使用模擬模式（simulation=True），行情資料與正式相同。"""
    api = sj.Shioaji(simulation=True)
    api.login(api_key=api_key, secret_key=secret_key, contracts_timeout=10000)
    return api


def get_contract(api, code: str):
    try:
        return api.Contracts.Stocks[code]
    except Exception:
        return None


# ---------------------------------------------------------------- 快照
def batch_snapshots(api, contracts, chunk=200):
    rows = []
    for i in range(0, len(contracts), chunk):
        try:
            rows.extend(api.snapshots(contracts[i:i + chunk]))
        except Exception as e:
            st.warning(f"快照批次 {i // chunk + 1} 失敗：{e}")
    return rows


# ---------------------------------------------------------------- K 線
@st.cache_data(ttl=600, show_spinner=False)
def minute_kbars(_api, code: str, days: int = 10) -> pd.DataFrame:
    """原始 1 分 K（估波動用），cache 10 分鐘。"""
    end = date.today()
    start = end - timedelta(days=days)
    kb = _api.kbars(_api.Contracts.Stocks[code],
                    start=start.isoformat(), end=end.isoformat())
    df = pd.DataFrame({**kb})
    if not df.empty:
        df["ts"] = pd.to_datetime(df["ts"])
    return df


@st.cache_data(ttl=600, show_spinner=False)
def daily_kbars(_api, code: str, days: int = 90) -> pd.DataFrame:
    """由分 K resample 成日 K，cache 10 分鐘。"""
    df = minute_kbars(_api, code, days)
    if df.empty:
        return df
    return (df.set_index("ts")
              .resample("D")
              .agg({"Open": "first", "High": "max", "Low": "min",
                    "Close": "last", "Volume": "sum"})
              .dropna())


# ---------------------------------------------------------------- 五檔
def fetch_bidask(api, contract, wait: float = 2.0):
    """訂閱五檔，收到一筆即退訂；休市時可能拿不到。"""
    holder = {}

    def cb(exchange, bidask):
        holder["ba"] = bidask

    try:
        api.quote.set_on_bidask_stk_v1_callback(cb)
        api.quote.subscribe(contract, quote_type=QuoteType.BidAsk,
                            version=QuoteVersion.v1)
        t0 = time.time()
        while "ba" not in holder and time.time() - t0 < wait:
            time.sleep(0.1)
        api.quote.unsubscribe(contract, quote_type=QuoteType.BidAsk,
                              version=QuoteVersion.v1)
    except Exception:
        pass
    return holder.get("ba")


# ---------------------------------------------------------------- ETF
def classify_etf(code: str, name: str) -> str | None:
    """
    依台灣 ETF 代號規則分類；非 ETF 回傳 None。
    尾碼：A=主動式、L=槓桿、R=反向、U=期貨型、B=債券型，其餘視為被動式。
    """
    if not code.startswith("00"):
        return None
    tail = code[-1]
    if tail == "A" or (name or "").startswith("主動"):
        return "ETF-主動式"
    if tail in ("L", "R") or "正2" in (name or "") or "反1" in (name or ""):
        return "ETF-槓桿/反向"
    if tail == "B":
        return "ETF-債券型"
    if tail == "U":
        return "ETF-期貨型"
    return "ETF-被動式"


@st.cache_data(ttl=3600, show_spinner=False)
def list_all_etfs(_api, sig: str) -> pd.DataFrame:
    """掃描上市＋上櫃商品檔，列出全部 ETF（cache 1 小時）。"""
    rows = []
    for exch in (_api.Contracts.Stocks.TSE, _api.Contracts.Stocks.OTC):
        for c in exch:
            kind = classify_etf(c.code, c.name or "")
            if kind:
                rows.append({"code": c.code, "name": c.name, "kind": kind})
    return pd.DataFrame(rows).drop_duplicates("code")


@st.cache_data(ttl=3600, show_spinner=False)
def list_universe(_api, sig: str) -> pd.DataFrame:
    """上市＋上櫃全部股票與 ETF：code, name, label（產業或 ETF 類型）。"""
    from config import INDUSTRY_MAP
    rows = []
    for exch in (_api.Contracts.Stocks.TSE, _api.Contracts.Stocks.OTC):
        for c in exch:
            kind = classify_etf(c.code, c.name or "")
            label = kind or INDUSTRY_MAP.get(getattr(c, "category", ""),
                                             "未分類")
            rows.append({"code": c.code, "name": c.name or "",
                         "label": label})
    return pd.DataFrame(rows).drop_duplicates("code")


@st.cache_data(ttl=3600, show_spinner=False)
def name_to_code_map(_api, sig: str) -> dict:
    """公司名稱 → 代號（供 ETF 成分股名稱對照）。"""
    m = {}
    for exch in (_api.Contracts.Stocks.TSE, _api.Contracts.Stocks.OTC):
        for c in exch:
            if c.name:
                m[c.name] = c.code
    return m


# ---------------------------------------------------------------- tick
def tick_size(price: float, is_etf: bool = False) -> float:
    """台股升降單位。ETF（受益憑證）：未滿 50 元 0.01、50 元以上 0.05。"""
    if is_etf:
        return 0.01 if price < 50 else 0.05
    for limit, tick in [(10, 0.01), (50, 0.05), (100, 0.1),
                        (500, 0.5), (1000, 1.0), (float("inf"), 5.0)]:
        if price < limit:
            return tick
    return 5.0


def add_ticks(price: float, n: int, is_etf: bool = False) -> float:
    p = price
    for _ in range(abs(n)):
        t = tick_size(p if n > 0 else p - 1e-9, is_etf)
        p = p + t if n > 0 else p - t
    return round(p, 2)
