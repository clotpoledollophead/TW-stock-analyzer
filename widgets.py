# -*- coding: utf-8 -*-
"""給投資人的提醒與建議小工具（教育性質，非投資建議）。"""

import streamlit as st


def render_tools():
    st.markdown("#### 部位大小計算器（固定風險法）")
    st.caption("以「單筆交易最多虧總資金的 R%」反推可買張數，"
               "是風險管理文獻中最常見的 position sizing 方法。")
    c1, c2 = st.columns(2)
    capital = c1.number_input("總資金（元）", min_value=0, value=500_000,
                              step=10_000)
    risk_pct = c2.number_input("單筆風險上限（%）", min_value=0.1,
                               max_value=10.0, value=1.0, step=0.1)
    c3, c4 = st.columns(2)
    entry = c3.number_input("進場價", min_value=0.0, value=100.0, step=0.5)
    stop = c4.number_input("停損價", min_value=0.0, value=95.0, step=0.5)
    if entry > stop > 0:
        risk_per_share = entry - stop
        budget = capital * risk_pct / 100
        shares = int(budget // risk_per_share)
        lots, odd = divmod(shares, 1000)
        st.info(f"可承受風險金額 {budget:,.0f} 元 ÷ 每股風險 "
                f"{risk_per_share:.2f} 元 ≈ **{shares:,} 股**"
                f"（{lots} 張＋零股 {odd} 股）｜"
                f"部位市值約 {shares * entry:,.0f} 元"
                f"（佔資金 {shares * entry / capital:.1%}）")
        if shares * entry > capital:
            st.warning("計算出的部位超過總資金——停損距離太近或風險%過高，"
                       "請縮小部位。")
    elif stop >= entry:
        st.warning("停損價需低於進場價。")

    st.divider()
    st.markdown("#### 交易成本與回本試算")
    c5, c6, c7 = st.columns(3)
    price = c5.number_input("成交價", min_value=0.0, value=100.0, step=0.5,
                            key="cost_p")
    qty = c6.number_input("股數", min_value=1, value=1000, step=100)
    is_etf = c7.toggle("ETF（證交稅 0.1%）", value=False)
    fee_disc = st.slider("手續費折數（券商折扣）", 0.2, 1.0, 0.6, 0.05,
                         help="牌告手續費 0.1425%，多數電子下單有折扣")
    amt = price * qty
    fee_rate = 0.001425 * fee_disc
    tax_rate = 0.001 if is_etf else 0.003
    fee_buy = max(20, amt * fee_rate)
    fee_sell = max(20, amt * fee_rate)
    tax = amt * tax_rate
    total = fee_buy + fee_sell + tax
    breakeven = total / amt * 100 if amt else 0
    st.info(f"買進手續費 {fee_buy:,.0f} ＋ 賣出手續費 {fee_sell:,.0f} ＋ "
            f"證交稅 {tax:,.0f} ＝ {total:,.0f} 元｜"
            f"股價需上漲約 **{breakeven:.2f}%** 才回本"
            f"（手續費低消 20 元已計入）")

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
