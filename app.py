# -*- coding: utf-8 -*-
"""
股票行情分析儀（Shioaji ＋ 開放資料，模組化）
=============================================
純行情讀取：一律模擬模式、不啟用 CA、無下單功能。

檔案結構：
    app.py         主介面（本檔）
    config.py      常數、產業對照、主題 CSS（隨系統切換淺色/深色）
    sj_client.py   Shioaji 連線與行情、全市場商品清單
    scoring.py     技術評分、成交機率模型（first-passage）、買進評估
    holdings.py    ETF 成分股（Yahoo 持股分析→證交所 OpenAPI 備援）
    datasources.py 證交所 OpenAPI 基本面、FinMind 新聞、Google News 備援
    ui.py          襯線 HTML 表格、新聞卡片、模型觀點卡片
    widgets.py     投資人小工具

執行：
    pip install shioaji streamlit pandas numpy plotly requests
    streamlit run app.py

本工具為研究示範，所有分數、機率與模型觀點皆為條件計算輸出，
不預測未來、不構成投資建議。
"""

import os
import time

import numpy as np
import pandas as pd
import streamlit as st

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

from config import (INDUSTRY_MAP, PLACEHOLDER, TAIWAN_GREEN, TAIWAN_RED,
                    THEME_MODES, build_css, plotly_font_color)
import sj_client as sjc
import scoring
import holdings as hld
import datasources as ds
import ui
from widgets import render_tools

# ---------------------------------------------------------------- 版面
st.set_page_config(page_title="股票行情分析儀", layout="wide",
                   initial_sidebar_state="collapsed")

# ---- 外觀模式：淺色 / 深色 / 跟隨系統 ----
_default_mode = st.session_state.get("theme_choice", "跟隨系統")
head_l, head_r = st.columns([3, 2])
with head_r:
    theme_choice = st.radio(
        "外觀", list(THEME_MODES.keys()),
        index=list(THEME_MODES.keys()).index(_default_mode),
        horizontal=True, label_visibility="collapsed",
        key="theme_choice")
theme_mode = THEME_MODES[theme_choice]
st.markdown(build_css(theme_mode), unsafe_allow_html=True)
_plotly_font = plotly_font_color(theme_mode)

with head_l:
    st.title("股票行情分析儀")
st.caption("模擬模式・純行情讀取（無下單功能）｜紅漲綠跌｜"
           "所有評分、機率與模型觀點為條件計算輸出，僅供研究參考，"
           "不構成投資建議")

# ---------------------------------------------------------------- 連線
api = st.session_state.get("api")
with st.expander("連線設定（一律模擬模式）", expanded=api is None):
    c1, c2 = st.columns(2)
    api_key = c1.text_input("API Key", value=os.getenv("SJ_API_KEY", ""),
                            type="password")
    secret_key = c2.text_input("Secret Key",
                               value=os.getenv("SJ_SECRET_KEY", ""),
                               type="password")
    fm_token = st.text_input(
        "FinMind Token（選填，用於個股新聞；留空為匿名低額度）",
        value=os.getenv("FINMIND_TOKEN", ""), type="password")
    st.session_state["fm_token"] = fm_token
    if st.button("登入 / 重新連線", use_container_width=True):
        try:
            with st.spinner("登入中…"):
                st.session_state["api"] = sjc.do_login(api_key, secret_key)
            st.success("登入成功，商品檔已載入")
            st.rerun()
        except Exception as e:
            st.error(f"登入失敗：{e}")

api = st.session_state.get("api")
if api is None:
    st.info("請先在上方「連線設定」輸入 API Key / Secret Key 並登入。"
            "金鑰可在永豐「API 管理平台」申請；本工具僅讀取行情。")
    st.stop()


# ---------------------------------------------------------------- 掃描流程
def run_scan(codes, add_labels):
    universe = sjc.list_universe(api, sig=str(id(api)))
    label_map = dict(zip(universe["code"], universe["label"]))
    if add_labels:
        picked = universe[universe["label"].isin(add_labels)]
        codes = list(dict.fromkeys(codes + picked["code"].tolist()))

    contracts, meta = [], {}
    for code in codes:
        c = sjc.get_contract(api, code)
        if c is None:
            continue
        contracts.append(c)
        kind = label_map.get(code) or sjc.classify_etf(code, c.name or "")
        meta[code] = {
            "name": c.name,
            "industry": kind or INDUSTRY_MAP.get(
                getattr(c, "category", ""), "未分類"),
            "limit_down": float(getattr(c, "limit_down", 0) or 0),
            "limit_up": float(getattr(c, "limit_up", 0) or 0),
        }
    if not contracts:
        return None, "清單中沒有可辨識的代號，請確認輸入。"

    with st.spinner(f"抓取 {len(contracts)} 檔快照…"):
        snaps = sjc.batch_snapshots(api, contracts)

    rows = []
    for s in snaps:
        m = meta.get(s.code, {})
        rows.append({
            "code": s.code, "name": m.get("name", ""),
            "industry": m.get("industry", "未分類"),
            "close": float(s.close), "change_pct": float(s.change_rate),
            "open": float(s.open), "high": float(s.high),
            "low": float(s.low),
            "vwap": float(getattr(s, "average_price", 0) or 0),
            "total_volume": int(s.total_volume),
            "volume_ratio": float(getattr(s, "volume_ratio", 0) or 0),
            "bid": float(s.buy_price), "bid_vol": int(s.buy_volume),
            "ask": float(s.sell_price), "ask_vol": int(s.sell_volume),
            "limit_down": m.get("limit_down", np.nan),
            "limit_up": m.get("limit_up", np.nan),
        })
    df = pd.DataFrame(rows)
    return (df, None) if not df.empty else (None, "未取得任何快照資料。")


# ---------------------------------------------------------------- 分頁
tab_scan, tab_rank, tab_stock, tab_tools = st.tabs(
    ["掃描與過濾", "排名", "個股分析", "投資人小工具"])

# ================================================================ ① 掃描
with tab_scan:
    wl_text = st.text_area("股票 / ETF 代號", value="", height=90,
                           placeholder=PLACEHOLDER)
    codes = [c.strip().upper() for c in wl_text.replace(",", " ").split()
             if c.strip()]

    with st.expander("自動加入整個產業或 ETF 類型"):
        st.caption("從上市＋上櫃全部商品挑選：可選公司產業（如半導體、"
                   "金融保險），或 ETF 類型（依代號尾碼分類，含新掛牌）。")
        universe = sjc.list_universe(api, sig=str(id(api)))
        counts = universe["label"].value_counts()
        etf_labels = sorted(l for l in counts.index if l.startswith("ETF"))
        ind_labels = sorted(l for l in counts.index if not l.startswith("ETF"))
        add_labels = st.multiselect(
            "產業 / ETF 類型（可複選）", ind_labels + etf_labels,
            format_func=lambda l: f"{l}（{counts[l]} 檔）")

    with st.expander("篩選設定（作用於已抓取的快照，不會重打 API）"):
        p1, p2, p3 = st.columns(3)
        price_lo = p1.number_input("價格下限（元）", min_value=0.0,
                                   value=0.0, step=10.0)
        price_hi = p2.number_input("價格上限（元，0 = 不限）", min_value=0.0,
                                   value=0.0, step=10.0)
        min_vol = p3.number_input("最低成交量（張）", min_value=0, value=500,
                                  step=100)
        if price_hi <= 0:
            price_hi = float("inf")

    if st.button("開始掃描", type="primary", use_container_width=True):
        if not codes and not add_labels:
            st.warning("請先輸入代號，或選擇要加入的產業 / ETF 類型。")
        else:
            df, err = run_scan(codes, add_labels)
            if err:
                st.error(err)
            else:
                st.session_state["scan_df"] = df
                st.session_state["scan_time"] = time.strftime("%H:%M:%S")
                st.session_state.pop("rank_df", None)

    if "scan_df" not in st.session_state:
        st.info("輸入代號或選擇產業後按「開始掃描」；"
                "在此之前不會發出任何行情請求。")
    else:
        df = st.session_state["scan_df"]
        st.caption(f"快照時間 {st.session_state['scan_time']}"
                   "（調整篩選不會重抓，要更新請再按掃描）")

        f1, f2 = st.columns([2, 3])
        kw = f1.text_input("以公司名稱或代號篩選", value="",
                           placeholder="例：台積 或 2330")
        industries = sorted(df["industry"].unique().tolist())
        sel_ind = f2.multiselect("以產業 / ETF 類型篩選（不選 = 全部）",
                                 industries)
        mask = (df["close"].between(price_lo, price_hi)
                & (df["total_volume"] >= min_vol))
        if sel_ind:
            mask &= df["industry"].isin(sel_ind)
        if kw.strip():
            k = kw.strip().upper()
            mask &= (df["code"].str.contains(k, na=False)
                     | df["name"].str.contains(kw.strip(), na=False))
        fdf = df[mask].copy()

        if fdf.empty:
            st.warning("沒有標的通過目前篩選條件。")
            st.session_state["filtered_df"] = fdf
        else:
            adv, notes = [], []
            for _, r in fdf.iterrows():
                s, n = scoring.price_advantage(r)
                adv.append(s)
                notes.append("、".join(n) or "—")
            fdf["價格優勢分"] = adv
            fdf["價格優勢說明"] = notes
            fdf["spread_pct"] = np.where(
                fdf["ask"] > 0,
                (fdf["ask"] - fdf["bid"]) / fdf["ask"] * 100, np.nan)
            st.session_state["filtered_df"] = fdf

            show = fdf[["code", "name", "industry", "close", "change_pct",
                        "vwap", "bid", "ask", "spread_pct", "total_volume",
                        "價格優勢分", "價格優勢說明"]].rename(columns={
                "code": "代號", "name": "名稱", "industry": "產業",
                "close": "現價", "change_pct": "漲跌%", "vwap": "當日均價",
                "bid": "最佳買價", "ask": "最佳賣價", "spread_pct": "價差%",
                "total_volume": "總量(張)"}).sort_values(
                "價格優勢分", ascending=False)
            ui.df_table(
                show,
                fmts={"現價": "{:,.2f}", "漲跌%": "{:+.2f}%",
                      "當日均價": "{:,.2f}", "最佳買價": "{:,.2f}",
                      "最佳賣價": "{:,.2f}", "價差%": "{:.2f}%",
                      "總量(張)": "{:,.0f}", "價格優勢分": "{:.0f}"},
                signed={"漲跌%"}, bar_col="價格優勢分", bar_max=4,
                height=460)
            st.caption(f"{len(fdf)}/{len(df)} 檔通過篩選")

# ================================================================ ② 排名
with tab_rank:
    fdf = st.session_state.get("filtered_df")
    if fdf is None or fdf.empty:
        st.info("請先在「掃描與過濾」分頁完成掃描。")
    else:
        top_n = st.slider("排名計算檔數", 5, 30, 15,
                          help="對篩選後價格優勢分最高的前 N 檔抓日 K，"
                               "越多越慢")
        if st.button("計算排名", type="primary", use_container_width=True):
            stage2 = fdf.sort_values(["價格優勢分", "volume_ratio"],
                                     ascending=False).head(top_n)
            prog = st.progress(0.0, text="抓取日 K…")
            rows = []
            for i, (_, r) in enumerate(stage2.iterrows()):
                t = scoring.tech_score(sjc.daily_kbars(api, r["code"]))
                total = round(0.6 * t["tech"] / 5 * 100
                              + 0.4 * r["價格優勢分"] / 4 * 100, 1)
                rows.append({
                    "排名": 0, "代號": r["code"], "名稱": r["name"],
                    "產業": r["industry"], "現價": r["close"],
                    "漲跌%": r["change_pct"],
                    "技術分": t["tech"], "價格優勢分": r["價格優勢分"],
                    "總分": total,
                    "重點": "、".join(t["notes"][:3]) or "—"})
                prog.progress((i + 1) / len(stage2),
                              text=f"{r['code']} {r['name']} 完成")
            prog.empty()
            rank_df = pd.DataFrame(rows).sort_values("總分",
                                                     ascending=False)
            rank_df["排名"] = range(1, len(rank_df) + 1)
            st.session_state["rank_df"] = rank_df

        rank_df = st.session_state.get("rank_df")
        if rank_df is not None:
            ui.df_table(
                rank_df,
                fmts={"現價": "{:,.2f}", "漲跌%": "{:+.2f}%",
                      "技術分": "{:.0f}", "價格優勢分": "{:.0f}",
                      "總分": "{:.1f}", "排名": "{:.0f}"},
                signed={"漲跌%"}, bar_col="總分", bar_max=100)
            st.caption("總分 = 技術面 60% ＋ 買進價格條件 40%。"
                       "機械式計分，不代表未來報酬。")

# ================================================================ ③ 個股分析
with tab_stock:
    fdf = st.session_state.get("filtered_df")
    if fdf is None or fdf.empty:
        st.info("請先在「掃描與過濾」分頁完成掃描。")
    else:
        options = (fdf["code"] + " " + fdf["name"]).tolist()
        pick = st.selectbox("選擇標的（來自篩選後清單）", options)
        pick_code = pick.split()[0]
        pick_name = pick.split(maxsplit=1)[1] if " " in pick else pick_code
        prow = fdf[fdf["code"] == pick_code].iloc[0]
        is_etf = str(prow["industry"]).startswith("ETF")
        contract = sjc.get_contract(api, pick_code)
        tick = sjc.tick_size(prow["close"], is_etf)

        st.markdown(f"**{pick}**｜類別：{prow['industry']}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("現價", f"{prow['close']:.2f}",
                  f"{prow['change_pct']:+.2f}%")
        m2.metric("當日均價 VWAP", f"{prow['vwap']:.2f}" if prow["vwap"]
                  else "—")
        m3.metric("最佳買價（排隊）", f"{prow['bid']:.2f}",
                  f"{prow['bid_vol']} 張")
        m4.metric("最佳賣價（立即成交）", f"{prow['ask']:.2f}",
                  f"{prow['ask_vol']} 張")

        # ---- 現在適合買嗎（模型觀點） --------------------------------------
        st.markdown("##### 現在適合買嗎（模型觀點）")
        st.caption("彙整技術面（日 K）、今日價格條件（快照）與"
                   "證交所 OpenAPI 基本面（本益比、殖利率、月均價，"
                   "僅上市有資料），列出偏多與偏空條件。")
        if st.button("產生評估", use_container_width=True):
            with st.spinner("抓取日 K 與證交所基本面…"):
                daily = sjc.daily_kbars(api, pick_code)
                funda = ds.twse_fundamentals(pick_code)
            st.session_state["assess_" + pick_code] = \
                scoring.buy_assessment(daily, prow, funda)
            st.session_state["funda_" + pick_code] = funda

        assess = st.session_state.get("assess_" + pick_code)
        if assess:
            ui.verdict_card(assess["verdict"], assess["tone"],
                            assess["bullish"], assess["bearish"])
            funda = st.session_state.get("funda_" + pick_code) or {}
            if funda:
                ui.df_table(pd.DataFrame([funda]),
                            fmts={}, height=90)
                st.caption("資料來源：臺灣證券交易所 OpenAPI"
                           "（BWIBBU_ALL、STOCK_DAY_AVG_ALL，前一交易日）")

        # ---- 新聞與討論 ------------------------------------------------------
        st.markdown("##### 新聞與討論")
        if st.button("載入近期新聞", use_container_width=True):
            with st.spinner("查詢 FinMind 個股新聞…"):
                news = ds.finmind_news(pick_code,
                                       st.session_state.get("fm_token", ""))
            src_label = "FinMind（TaiwanStockNews）"
            if news.empty:
                with st.spinner("FinMind 無資料，改用 Google News…"):
                    news = ds.google_news(f"{pick_name} {pick_code}")
                src_label = "Google News"
            st.session_state["news_" + pick_code] = (news, src_label)

        news_pack = st.session_state.get("news_" + pick_code)
        if news_pack:
            news, src_label = news_pack
            if news.empty:
                st.info("目前查無近期新聞。")
            else:
                ui.news_cards(news)
                st.caption(f"來源：{src_label}，點卡片開啟原文。"
                           "標題僅代表媒體觀點，請自行判讀。")

        # ---- 成交機率模型 ----------------------------------------------------
        st.markdown("##### 最低掛價試算（first-passage 成交機率模型）")
        st.caption("依 Lo, MacKinlay & Zhang (2002) 的首次穿越框架："
                   "P(觸價) = 2Φ(−δ/σ√T)，σ 以近 10 日 1 分 K 估計。"
                   "假設觸價即成交且無漂移，實際成交率通常較低。")
        s1, s2, s3 = st.columns(3)
        target_p = s1.slider("目標成交機率", 0.50, 0.90, 0.60, 0.05)
        horizon = s2.slider("等待時間（分鐘）", 10, 270, 60, 10)
        buffer_t = s3.slider("排隊保守緩衝（tick）", 0, 3, 1,
                             help="+1 tick 相當於要求價格「穿過」掛價，"
                                  "抵銷排隊順位的樂觀偏誤")

        if st.button("計算最低掛價", use_container_width=True):
            with st.spinner("抓取 1 分 K 估計波動…"):
                mdf = sjc.minute_kbars(api, pick_code)
            st.session_state["sigma_" + pick_code] = scoring.minute_sigma(mdf)

        sigma = st.session_state.get("sigma_" + pick_code)
        if sigma is not None:
            if np.isnan(sigma):
                st.warning("1 分 K 不足以估計波動（新掛牌或流動性過低）。")
            else:
                lb = scoring.lowest_bid_for_prob(
                    prow["close"], sigma, horizon, target_p, tick,
                    queue_buffer_ticks=buffer_t)
                p_at_lb = scoring.touch_prob(prow["close"], lb, sigma,
                                             horizon)
                k1, k2, k3 = st.columns(3)
                k1.metric("建議最低掛價", f"{lb:.2f}",
                          f"{(lb / prow['close'] - 1) * 100:+.2f}% vs 現價")
                k2.metric("模型觸價機率", f"{p_at_lb:.0%}",
                          f"目標 {target_p:.0%}")
                k3.metric("每分鐘波動 σ", f"{sigma * 100:.3f}%")
                st.caption(f"制度下限＝跌停 {prow['limit_down']:.2f}；"
                           f"tick＝{tick}（{'ETF' if is_etf else '個股'}級距）")
                ladder = scoring.prob_ladder(prow["close"], sigma, horizon,
                                             tick)
                ladder["T內觸價機率%"] = ladder.pop("T內觸價機率") * 100
                ui.df_table(ladder,
                            fmts={"掛價": "{:,.2f}", "折讓%": "{:.2f}%",
                                  "T內觸價機率%": "{:.0f}%"},
                            bar_col="T內觸價機率%", bar_max=100)

        # ---- 三種掛價策略 ----------------------------------------------------
        aggressive = sjc.add_ticks(prow["bid"], 1, is_etf) \
            if prow["bid"] else None
        if aggressive and prow["ask"] and aggressive >= prow["ask"]:
            aggressive = prow["bid"]
        spread_pct = ((prow["ask"] - prow["bid"]) / prow["ask"] * 100
                      if prow["ask"] else float("nan"))
        st.markdown("##### 三種掛價選擇")
        ui.df_table(pd.DataFrame([
            {"策略": "立即成交（吃外盤）", "委託價": prow["ask"],
             "成交機率": "幾乎必成",
             "成本": f"付出價差 {spread_pct:.2f}%"},
            {"策略": "積極排隊（買一 +1 tick）", "委託價": aggressive,
             "成交機率": "中", "成本": "省下部分價差"},
            {"策略": "保守排隊（掛買一）", "委託價": prow["bid"],
             "成交機率": "看盤勢", "成本": "最低，可能不成交"},
        ]), fmts={"委託價": "{:,.2f}"})

        # ---- 五檔（按需） -----------------------------------------------------
        if contract is not None and st.button("抓取即時五檔報價",
                                              use_container_width=True):
            with st.spinner("訂閱五檔…"):
                ba = sjc.fetch_bidask(api, contract)
            if ba is not None:
                b1, b2 = st.columns(2)
                with b1:
                    st.markdown("**委買五檔（紅）**")
                    ui.df_table(pd.DataFrame({
                        "價格": [float(x) for x in ba.bid_price],
                        "張數": [int(x) for x in ba.bid_volume]}),
                        fmts={"價格": "{:,.2f}", "張數": "{:,.0f}"})
                with b2:
                    st.markdown("**委賣五檔（綠）**")
                    ui.df_table(pd.DataFrame({
                        "價格": [float(x) for x in ba.ask_price],
                        "張數": [int(x) for x in ba.ask_volume]}),
                        fmts={"價格": "{:,.2f}", "張數": "{:,.0f}"})
                tb, ta = sum(ba.bid_volume), sum(ba.ask_volume)
                if ta:
                    st.caption(f"五檔委買/委賣量比 {tb}/{ta} = {tb/ta:.2f}"
                               "（>1 買方掛單較厚）")
            else:
                st.info("收不到五檔回報（可能為非交易時段）。")

        # ---- ETF 成分與產業 ---------------------------------------------------
        if is_etf:
            st.markdown("##### ETF 成分與產業分布")
            st.caption("成分來源：Yahoo 股市「持股分析」；失敗時退證交所 "
                       "OpenAPI 基金基本資料（OpenAPI 與 FinMind 均未提供"
                       "成分明細）。產業類別以 Shioaji 商品檔對照。")
            if st.button("抓取成分股", use_container_width=True):
                with st.spinner("抓取 Yahoo 持股分析…"):
                    h = hld.fetch_yahoo_holdings(pick_code)
                st.session_state["hold_" + pick_code] = h
                if h is None:
                    with st.spinner("Yahoo 無法取得，改查證交所 OpenAPI…"):
                        info = hld.fetch_twse_fund_info(pick_code)
                    st.session_state["fundinfo_" + pick_code] = info

            if st.session_state.get("hold_" + pick_code) is None and \
                    st.session_state.get("fundinfo_" + pick_code):
                info = st.session_state["fundinfo_" + pick_code]
                st.warning("Yahoo 持股明細暫時無法取得，"
                           "以下為證交所 OpenAPI 基金基本資料。")
                fields = [("基金中文名稱", "名稱"),
                          ("標的指數/追蹤指數名稱", "標的 / 追蹤指數"),
                          ("股票及債券投資比例說明", "投資比例說明"),
                          ("基金經理人", "經理人"),
                          ("成立日期", "成立日期"),
                          ("上市日期", "上市日期")]
                rows = [{"項目": label, "內容": str(info.get(k, "")).strip()}
                        for k, label in fields
                        if str(info.get(k, "")).strip()]
                if rows:
                    ui.df_table(pd.DataFrame(rows))
                st.caption(f"持股明細可至 Yahoo 頁面查看："
                           f"{hld.holding_page_url(pick_code)}")

            h = st.session_state.get("hold_" + pick_code)
            if h is not None and not h.empty:
                ann = hld.annotate_industries(h, api)
                iw = hld.industry_weights(ann)
                c1, c2 = st.columns([3, 2])
                with c1:
                    ui.df_table(
                        ann[["code", "name", "weight", "industry"]].rename(
                            columns={"code": "代號", "name": "名稱",
                                     "weight": "權重%",
                                     "industry": "產業"}),
                        fmts={"權重%": "{:.2f}%"}, height=360)
                with c2:
                    if HAS_PLOTLY:
                        fig = go.Figure(go.Pie(labels=iw["產業"],
                                               values=iw["權重%"],
                                               hole=0.45))
                        fig.update_layout(
                            height=360, paper_bgcolor="rgba(0,0,0,0)",
                            font=dict(family="Noto Serif TC",
                                      color=_plotly_font),
                            margin=dict(l=0, r=0, t=10, b=10))
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        ui.df_table(iw, fmts={"權重%": "{:.2f}%"})
                top3 = iw.head(3)["權重%"].sum()
                st.caption(f"前三大產業合計權重 {top3:.1f}%"
                           "——越高代表產業集中度越高，"
                           "與既有持股重複曝險的風險越大。")

        # ---- K 線 -------------------------------------------------------------
        if HAS_PLOTLY and st.button("顯示日 K 線圖", use_container_width=True):
            d = sjc.daily_kbars(api, pick_code).copy()
            if d.empty:
                st.info("無 K 線資料。")
            else:
                d["MA5"] = d["Close"].rolling(5).mean()
                d["MA20"] = d["Close"].rolling(20).mean()
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=d.index, open=d["Open"], high=d["High"],
                    low=d["Low"], close=d["Close"], name="日K",
                    increasing_line_color=TAIWAN_RED,
                    decreasing_line_color=TAIWAN_GREEN))
                fig.add_trace(go.Scatter(x=d.index, y=d["MA5"], name="MA5",
                                         line=dict(width=1.2)))
                fig.add_trace(go.Scatter(x=d.index, y=d["MA20"],
                                         name="MA20", line=dict(width=1.2)))
                if prow["vwap"]:
                    fig.add_hline(y=prow["vwap"], line_dash="dot",
                                  annotation_text="今日均價",
                                  line_color="#888")
                fig.update_layout(height=420,
                                  xaxis_rangeslider_visible=False,
                                  paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(0,0,0,0)",
                                  font=dict(family="Noto Serif TC",
                                            color=_plotly_font),
                                  margin=dict(l=10, r=10, t=30, b=10),
                                  legend=dict(orientation="h"))
                st.plotly_chart(fig, use_container_width=True)

# ================================================================ ④ 小工具
with tab_tools:
    render_tools()
