# -*- coding: utf-8 -*-
"""
ETF 成分股：從 Yahoo 股市「持股分析」頁抓取（Shioaji 不提供此資料）。

來源頁：https://tw.stock.yahoo.com/quote/{代號}.TW/holding
頁面為前端框架渲染，解析採兩層策略：
  1. 內嵌 JSON（symbol / 權重欄位）
  2. HTML 錨點鄰近百分比的寬鬆比對
網站改版時可能失效，屆時 UI 會附上原始頁面連結供人工查看。
成分公司的產業類別以 Shioaji 商品檔 category 對照。
"""

import re

import pandas as pd
import requests
import streamlit as st

from config import INDUSTRY_MAP
from sj_client import classify_etf

YAHOO_HOLDING_URL = "https://tw.stock.yahoo.com/quote/{code}.TW/holding"
TWSE_FUND_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap47_L"
_UA = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/125.0 Safari/537.36"),
       "Accept-Language": "zh-TW,zh;q=0.9"}


def holding_page_url(etf_code: str) -> str:
    return YAHOO_HOLDING_URL.format(code=etf_code)


def _parse_embedded_json(html: str) -> pd.DataFrame | None:
    """策略 1：Yahoo 內嵌資料中的 symbol＋權重配對。"""
    pat = re.compile(
        r'"symbol"\s*:\s*"(\d{4,6}[A-Z]?)\.TWO?"'      # 代號
        r'.{0,300}?'                                    # 鄰近欄位
        r'"(?:percent|weight|holdingPercent)[^"]*"'     # 權重鍵
        r'\s*:\s*"?(\d{1,3}(?:\.\d{1,4})?)',            # 權重值
        re.DOTALL)
    hits = pat.findall(html)
    if len(hits) < 3:
        return None
    df = (pd.DataFrame(hits, columns=["code", "weight"])
          .drop_duplicates("code"))
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
    df = df.dropna(subset=["weight"])
    df = df[df["weight"].between(0.01, 100)]
    return df.reset_index(drop=True) if len(df) >= 3 else None


def _parse_anchor_percent(html: str) -> pd.DataFrame | None:
    """策略 2：/quote/XXXX.TW 連結後方最近的百分比。"""
    pat = re.compile(
        r'href="/quote/(\d{4,6}[A-Z]?)\.TWO?[^"]*"[^>]*>'
        r'(?:<[^>]+>)*([^<]{1,24})<'                    # 顯示名稱
        r'.{0,600}?(\d{1,3}\.\d{1,2})\s*%',             # 鄰近權重
        re.DOTALL)
    hits = pat.findall(html)
    if len(hits) < 3:
        return None
    df = pd.DataFrame(hits, columns=["code", "name", "weight"])
    df["name"] = df["name"].str.strip()
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
    df = (df.dropna(subset=["weight"])
            .drop_duplicates("code"))
    df = df[df["weight"].between(0.01, 100)]
    return df.reset_index(drop=True) if len(df) >= 3 else None


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_yahoo_holdings(etf_code: str) -> pd.DataFrame | None:
    """回傳欄位：code, weight（%），可能含 name。抓不到回傳 None。cache 1 天。"""
    try:
        html = requests.get(holding_page_url(etf_code),
                            headers=_UA, timeout=12).text
    except Exception:
        return None
    df = _parse_embedded_json(html)
    if df is None:
        df = _parse_anchor_percent(html)
    if df is None:
        return None
    return df.sort_values("weight", ascending=False).reset_index(drop=True)


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_twse_fund_info(etf_code: str) -> dict | None:
    """
    備援：證交所 OpenAPI「基金基本資料彙總表」(t187ap47_L)。
    OpenAPI 未提供成分股明細，此端點回傳基金名稱、標的/追蹤指數、
    投資比例說明等基本資料。cache 1 天。
    """
    try:
        r = requests.get(TWSE_FUND_URL, timeout=15,
                         headers={"accept": "application/json", **_UA})
        data = r.json()
    except Exception:
        return None
    for row in data:
        if str(row.get("基金代號", "")).strip() == etf_code:
            return row
    return None


def annotate_industries(holdings: pd.DataFrame, api) -> pd.DataFrame:
    """為成分股補上名稱與產業類別（Shioaji 商品檔對照）。"""
    names, industries = [], []
    for code in holdings["code"]:
        name, industry = "", "未知"
        etf_kind = classify_etf(code, "")
        try:
            c = api.Contracts.Stocks[code]
            name = c.name or ""
            etf_kind = etf_kind or classify_etf(code, name)
            industry = etf_kind or INDUSTRY_MAP.get(
                getattr(c, "category", ""), "未分類")
        except Exception:
            industry = etf_kind or "未分類"
        names.append(name)
        industries.append(industry)
    out = holdings.copy()
    if "name" not in out or out["name"].eq("").all():
        out["name"] = names
    else:
        out["name"] = [n or m for n, m in zip(out["name"], names)]
    out["industry"] = industries
    return out


def industry_weights(annotated: pd.DataFrame) -> pd.DataFrame:
    g = (annotated.groupby("industry")["weight"].sum()
         .sort_values(ascending=False).reset_index())
    g.columns = ["產業", "權重%"]
    return g
