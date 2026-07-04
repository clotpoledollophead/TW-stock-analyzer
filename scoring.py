# -*- coding: utf-8 -*-
"""
評分與限價單成交機率模型。

成交機率模型（研究依據）
------------------------
Lo, MacKinlay & Zhang (2002, JFE)〈Econometric models of limit-order
executions〉將限價單的成交時間視為價格過程的「首次穿越時間」
(first-passage time)。在無漂移的布朗運動假設下，由反射原理：

    P(在 T 分鐘內觸及現價下方 δ 的價位) = 2 · Φ( −δ / (σ·√T) )

其中 σ 為每分鐘報酬波動度。給定目標成交機率 p，反解可得最大可退讓距離：

    δ* = −Φ⁻¹(p/2) · σ · √T        （p=0.6 時 −Φ⁻¹(0.3) ≈ 0.5244）

「最低掛價」= 現價 × (1 − δ*)，再向上對齊到合法 tick。
相關方法亦見 Avellaneda & Stoikov (2008) 造市模型中的成交強度函數。

重要假設與限制（實際成交率通常低於理論值）：
- 觸價即視為成交，忽略同價位排隊順序（可加 1 tick 保守緩衝）
- 無漂移假設：單邊下跌日會高估、單邊上漲日會低估觸價機率
- σ 由近期歷史 1 分 K 估計，波動 regime 改變時會失準
"""

import math
from statistics import NormalDist

import numpy as np
import pandas as pd

_N = NormalDist()


# ---------------------------------------------------------------- 技術面
def rsi(series: pd.Series, n: int = 14) -> float:
    delta = series.diff()
    up = delta.clip(lower=0).rolling(n).mean()
    dn = (-delta.clip(upper=0)).rolling(n).mean()
    rs = up / dn.replace(0, np.nan)
    val = 100 - 100 / (1 + rs)
    return float(val.iloc[-1]) if not val.dropna().empty else np.nan


def tech_score(daily: pd.DataFrame) -> dict:
    """技術面 0–5 分（範例策略，權重可自行調整）。"""
    out = {"MA5": np.nan, "MA20": np.nan, "RSI14": np.nan,
           "ret20": np.nan, "tech": 0, "notes": []}
    if daily is None or len(daily) < 25:
        out["notes"].append("K線不足")
        return out
    close = daily["Close"]
    ma5 = close.rolling(5).mean().iloc[-1]
    ma20 = close.rolling(20).mean().iloc[-1]
    vol20 = daily["Volume"].rolling(20).mean().iloc[-1]
    r = rsi(close)
    ret20 = close.iloc[-1] / close.iloc[-21] - 1 if len(close) > 21 else np.nan
    s, notes = 0, []
    if ma5 > ma20:
        s += 1; notes.append("MA5>MA20 多頭排列")
    if close.iloc[-1] > ma20:
        s += 1; notes.append("價在月線上")
    if not np.isnan(ret20) and ret20 > 0:
        s += 1; notes.append(f"20日漲幅 {ret20:+.1%}")
    if daily["Volume"].iloc[-1] > 1.3 * vol20:
        s += 1; notes.append("量能放大")
    if 45 <= r <= 70:
        s += 1; notes.append(f"RSI {r:.0f} 動能健康")
    elif r > 70:
        notes.append(f"RSI {r:.0f} 偏過熱")
    out.update({"MA5": ma5, "MA20": ma20, "RSI14": r,
                "ret20": ret20, "tech": s, "notes": notes})
    return out


def price_advantage(row: pd.Series) -> tuple[int, list[str]]:
    """買進「價格條件」0–4 分：衡量此刻進場條件，而非股票好壞。"""
    s, notes = 0, []
    close, avg = row["close"], row["vwap"]
    if avg and close and close <= avg:
        s += 1; notes.append("低於當日均價")
    rng = row["high"] - row["low"]
    if rng > 0:
        pos = (close - row["low"]) / rng
        if pos <= 0.4:
            s += 1; notes.append(f"日內位置 {pos:.0%}（近低點）")
    if row["ask"] and row["bid"] and row["ask"] > 0:
        spread_pct = (row["ask"] - row["bid"]) / row["ask"] * 100
        if spread_pct <= 0.3:
            s += 1; notes.append(f"價差 {spread_pct:.2f}% 窄")
    if row["bid_vol"] > row["ask_vol"] > 0:
        s += 1; notes.append("買方掛單力道強")
    return s, notes


# ---------------------------------------------------------------- 成交機率
def minute_sigma(minute_df: pd.DataFrame) -> float:
    """由近期 1 分 K 收盤估每分鐘報酬波動度 σ。"""
    if minute_df is None or minute_df.empty or "Close" not in minute_df:
        return float("nan")
    r = np.log(minute_df["Close"].astype(float)).diff().dropna()
    r = r[np.abs(r) < 0.05]          # 剔除跨日跳空等極端值
    return float(r.std()) if len(r) > 30 else float("nan")


def touch_prob(price: float, limit: float, sigma_1m: float,
               minutes: float) -> float:
    """在 minutes 分鐘內，價格觸及 limit（低於現價）的機率。"""
    if limit >= price:
        return 1.0
    if not sigma_1m or math.isnan(sigma_1m) or sigma_1m <= 0 or minutes <= 0:
        return float("nan")
    delta = (price - limit) / price          # 報酬空間的距離
    return min(1.0, 2 * _N.cdf(-delta / (sigma_1m * math.sqrt(minutes))))


def lowest_bid_for_prob(price: float, sigma_1m: float, minutes: float,
                        p: float, tick: float,
                        queue_buffer_ticks: int = 0) -> float | None:
    """
    達到目標觸價機率 p 的「最低」合法掛價。
    δ* = −Φ⁻¹(p/2)·σ·√T；掛價 = price·(1−δ*) 向上對齊 tick，
    再加 queue_buffer_ticks 檔作為排隊保守緩衝（0 = 不加）。
    """
    if not sigma_1m or math.isnan(sigma_1m) or sigma_1m <= 0:
        return None
    z = -_N.inv_cdf(p / 2)                   # p=0.6 → ≈0.5244
    delta = z * sigma_1m * math.sqrt(minutes)
    raw = price * (1 - delta)
    aligned = math.ceil(round(raw / tick, 6)) * tick   # 向上取 → 保證 ≥ p
    aligned += queue_buffer_ticks * tick
    return round(min(aligned, price), 2)


def prob_ladder(price: float, sigma_1m: float, minutes: float,
                tick: float, n_levels: int = 8) -> pd.DataFrame:
    """列出現價往下 n 檔的觸價機率表。"""
    rows = []
    for i in range(n_levels + 1):
        lv = round(price - i * tick, 2)
        rows.append({
            "掛價": lv,
            "距現價": f"-{i} tick" if i else "現價",
            "折讓%": (price - lv) / price * 100,
            "T內觸價機率": touch_prob(price, lv, sigma_1m, minutes),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 買進評估
def buy_assessment(daily: pd.DataFrame, row: pd.Series,
                   fundamentals: dict | None = None) -> dict:
    """
    「現在適合買嗎」的模型觀點：彙整技術面、價格條件與基本面訊號，
    輸出偏多/偏空條件清單與整體傾向。僅描述條件狀態，不預測未來。
    """
    bullish, bearish = [], []
    t = tech_score(daily)
    close = row["close"]

    if not np.isnan(t["MA20"]):
        if t["MA5"] > t["MA20"]:
            bullish.append("短均在長均之上（MA5>MA20），趨勢結構偏多"
                           "——若動能延續，歷史上續漲機率較高")
        else:
            bearish.append("短均在長均之下，趨勢結構偏空，"
                           "反彈常受均線壓制")
        if close > t["MA20"]:
            bullish.append("價格站上月線，中期支撐仍在")
        else:
            bearish.append("價格跌破月線，中期趨勢轉弱的風險升高")
    if not np.isnan(t["ret20"]):
        if t["ret20"] > 0:
            bullish.append(f"近 20 日累積 {t['ret20']:+.1%}，動能為正")
        elif t["ret20"] < -0.05:
            bearish.append(f"近 20 日累積 {t['ret20']:+.1%}，"
                           "下跌動能明顯，接刀風險高")
    r = t["RSI14"]
    if not np.isnan(r):
        if 45 <= r <= 65:
            bullish.append(f"RSI {r:.0f} 位於健康動能區，未過熱")
        elif r > 70:
            bearish.append(f"RSI {r:.0f} 屬過熱區，短線回檔機率升高")
        elif r < 30:
            bearish.append(f"RSI {r:.0f} 超賣——可能反彈，"
                           "但也代表趨勢極弱，兩面性訊號")

    if row["vwap"] and close <= row["vwap"]:
        bullish.append("現價低於今日均價（VWAP），此刻進場成本"
                       "優於今日多數成交者")
    rng = row["high"] - row["low"]
    if rng > 0 and (close - row["low"]) / rng > 0.85:
        bearish.append("價格貼近今日高點，屬追高位置，"
                       "短線買在區間頂的風險較高")
    if row["ask"] and row["bid"]:
        sp = (row["ask"] - row["bid"]) / row["ask"] * 100
        if sp > 0.6:
            bearish.append(f"買賣價差 {sp:.2f}% 偏寬，"
                           "流動性差、進出成本高")

    f = fundamentals or {}
    try:
        ma = float(str(f.get("月平均價", "")).replace(",", ""))
        if ma and close < ma:
            bullish.append(f"現價低於月平均價 {ma:.2f}，"
                           "位階相對近月便宜")
    except ValueError:
        pass
    try:
        pe = float(f.get("本益比", ""))
        if pe > 60:
            bearish.append(f"本益比 {pe:.1f} 偏高，"
                           "估值對利空的緩衝較薄")
    except ValueError:
        pass

    net = len(bullish) - len(bearish)
    if net >= 3:
        verdict, tone = "模型觀點：條件偏多——多數訊號支持進場", "pos"
    elif net <= -2:
        verdict, tone = "模型觀點：條件偏空——此刻進場勝率條件不佳", "neg"
    else:
        verdict, tone = "模型觀點：中性觀望——多空條件互見，不急於進場", "neu"
    return {"verdict": verdict, "tone": tone,
            "bullish": bullish, "bearish": bearish}
