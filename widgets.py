# -*- coding: utf-8 -*-
"""給投資人的提醒與建議小工具（教育性質，非投資建議）。"""

import math

import streamlit as st

from sj_client import tick_size

# 永豐金證券費率（牌告）
FEE_RATE = 0.001425      # 手續費 0.1425%
MIN_FEE_LOT = 20         # 整股電子下單低消（元）
MIN_FEE_ODD = 1          # 盤中零股低消（元）
TAX_STOCK = 0.003        # 證交稅：個股 0.3%
TAX_ETF = 0.001          # 證交稅：ETF 0.1%


def _fee(amount: float, disc: float, qty: int) -> float:
    """單邊手續費：牌告 0.1425% × 折數，含低消（整股 20 元、零股 1 元）。"""
    min_fee = MIN_FEE_ODD if qty < 1000 else MIN_FEE_LOT
    return max(min_fee, amount * FEE_RATE * disc)


def render_tools():
    st.markdown("#### 損益兩平試算（以永豐金證券費率計算）")
    st.caption("輸入買進價與股數，計算「賣多少錢才能賺回來」——"
               "含買賣兩邊手續費（牌告 0.1425% × 折數，"
               "整股低消 20 元、零股低消 1 元）與賣出時的證交稅"
               "（個股 0.3%、ETF 0.1%）。")

    c1, c2, c3 = st.columns(3)
    buy_price = c1.number_input("買進價（元）", min_value=0.0, value=100.0,
                                step=0.5)
    qty = c2.number_input("股數", min_value=1, value=1000, step=100)
    is_etf = c3.toggle("ETF（證交稅 0.1%）", value=False)
    disc = st.slider("手續費折數（依個人與營業員談定的方案調整）",
                     0.20, 1.00, 0.65, 0.05,
                     help="永豐電子下單依方案有不同折讓；1.0 = 無折扣牌告價")

    if buy_price > 0 and qty > 0:
        tax_rate = TAX_ETF if is_etf else TAX_STOCK
        buy_amt = buy_price * qty
        fee_buy = _fee(buy_amt, disc, qty)
        total_cost = buy_amt + fee_buy

        # 求 P：P·q − 手續費(P·q) − 稅(P·q) = 總成本
        # 先假設賣出手續費超過低消：P = 總成本 / (q·(1 − rate·disc − tax))
        denom = 1 - FEE_RATE * disc - tax_rate
        p_be = total_cost / (qty * denom)
        if p_be * qty * FEE_RATE * disc < (MIN_FEE_ODD if qty < 1000
                                           else MIN_FEE_LOT):
            # 賣出手續費落在低消區，改用固定手續費解
            min_fee = MIN_FEE_ODD if qty < 1000 else MIN_FEE_LOT
            p_be = (total_cost + min_fee) / (qty * (1 - tax_rate))

        # 對齊合法 tick（向上取，保證不虧）
        t = tick_size(p_be, is_etf)
        p_be_tick = math.ceil(round(p_be / t, 6)) * t

        sell_amt = p_be_tick * qty
        fee_sell = _fee(sell_amt, disc, qty)
        tax = sell_amt * tax_rate
        pnl = sell_amt - fee_sell - tax - total_cost
        need_pct = (p_be_tick / buy_price - 1) * 100

        k1, k2, k3 = st.columns(3)
        k1.metric("損益兩平賣價（tick 對齊）", f"{p_be_tick:,.2f}",
                  f"+{need_pct:.2f}% 漲幅")
        k2.metric("理論兩平價", f"{p_be:,.4f}")
        k3.metric("以兩平價賣出的損益", f"{pnl:+,.0f} 元",
                  "對齊 tick 後的微幅盈餘" if pnl > 0 else None)

        st.markdown(
            f"- 買進成本：{buy_amt:,.0f} 元 ＋ 買進手續費 "
            f"{fee_buy:,.0f} 元 ＝ **{total_cost:,.0f} 元**\n"
            f"- 以 {p_be_tick:,.2f} 賣出：{sell_amt:,.0f} 元 − 賣出手續費 "
            f"{fee_sell:,.0f} 元 − 證交稅 {tax:,.0f} 元\n"
            f"- 摩擦成本合計 {fee_buy + fee_sell + tax:,.0f} 元，"
            f"約佔買進金額 {(fee_buy + fee_sell + tax) / buy_amt:.3%}")
        if qty < 1000:
            st.caption("股數低於 1,000 股，以零股低消 1 元計算；"
                       "若為多筆成交，實際低消依券商逐筆計收，可能略高。")

    st.divider()
    st.markdown("#### 常備提醒")
    st.markdown(
        "- 排名分數是**機械式條件計分**，反映「現在的價格條件與短期技術面」，"
        "不含基本面與消息面，更不預測未來報酬。\n"
        "- 成交機率模型**假設無漂移**：趨勢明顯的日子，理論觸價機率會失準。\n"
        "- 主動式 ETF 多為 2025 年後掛牌，歷史短、費用率較高，"
        "技術分「K線不足」是資料限制而非優劣判斷。\n"
        "- 槓桿/反向 ETF 有**每日再平衡損耗**，不適合長期持有。\n"
        "- 分批進場、控制單一產業曝險，比找到完美價格更重要。\n"
        "- 本工具僅供研究參考，**不構成投資建議**；實際決策請自行評估風險。")