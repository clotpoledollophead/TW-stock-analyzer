# -*- coding: utf-8 -*-
"""共用常數：產業對照、顏色、主題 CSS（支援 淺色 / 深色 / 跟隨系統）。"""

INDUSTRY_MAP = {
    "01": "水泥", "02": "食品", "03": "塑膠", "04": "紡織纖維",
    "05": "電機機械", "06": "電器電纜", "08": "玻璃陶瓷", "09": "造紙",
    "10": "鋼鐵", "11": "橡膠", "12": "汽車", "14": "建材營造",
    "15": "航運", "16": "觀光餐旅", "17": "金融保險", "18": "貿易百貨",
    "19": "綜合", "20": "其他", "21": "化學", "22": "生技醫療",
    "23": "油電燃氣", "24": "半導體", "25": "電腦及週邊", "26": "光電",
    "27": "通信網路", "28": "電子零組件", "29": "電子通路", "30": "資訊服務",
    "31": "其他電子", "00": "ETF / 未分類",
}

TAIWAN_RED = "#b0524c"    # 台股慣例：紅漲（磚紅）
TAIWAN_GREEN = "#54806c"  # 綠跌（松綠）

PLACEHOLDER = "例：2330 2454 0050 00980A（空白或逗號分隔）"

THEME_MODES = {"跟隨系統": "system", "淺色": "light", "深色": "dark"}

# ------------------------------------------------------------ 主題 tokens
_LIGHT = """
    --page:   #f7f5f1;
    --ink:    #2b2f33;
    --muted:  #75726c;
    --card:   #fffefb;
    --card-2: #f1efe9;
    --line:   #e3e0d8;
    --accent: #46617a;
    --accent-ink: #fdfdfc;
    --accent-soft: rgba(70, 97, 122, .14);
"""

_DARK = """
    --page:   #16181c;
    --ink:    #e6e4de;
    --muted:  #97948d;
    --card:   #1e2126;
    --card-2: #1a1d21;
    --line:   #33363c;
    --accent: #93b0c4;
    --accent-ink: #14171b;
    --accent-soft: rgba(147, 176, 196, .18);
"""

_CSS_BODY = """
/* 隱藏 Streamlit header / 選單 / footer */
header[data-testid="stHeader"] { display: none; }
#MainMenu, footer { visibility: hidden; }

/* 頁面底色與內容寬度 */
.stApp { background-color: var(--page); }
.block-container {
    max-width: 1200px !important;
    padding: 2.4rem 2.2rem 5rem;
}

/* ---- 襯線字型全域（含列點、輸入欄、下拉、markdown 表格） ---- */
body, p, li, label, th, td, input, textarea, select, button, span,
h1, h2, h3, h4, h5, .stMarkdown, .stMarkdown *,
div[data-baseweb] input, div[data-baseweb="select"] * {
    font-family: 'Noto Serif TC', 'PingFang TC', serif !important;
}
code, pre, .mono { font-family: 'IBM Plex Mono', monospace !important; }
div[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-variant-numeric: tabular-nums;
}
body, p, label { color: var(--ink); line-height: 1.75; }
h1, h2, h3, h4, h5 { letter-spacing: .05em; color: var(--ink); }
h1 { font-weight: 600; margin-bottom: .2rem; }
h5 { margin-top: 2.2rem !important; font-weight: 600; }
.stMarkdown li { line-height: 1.9; margin-bottom: .3rem; color: var(--ink); }
.stMarkdown table { border-collapse: collapse; margin: .6rem 0 1rem; }
.stMarkdown th, .stMarkdown td {
    border: 1px solid var(--line); padding: .55rem .9rem;
    color: var(--ink);
}
.stMarkdown th { background: var(--card-2); font-weight: 600; }

/* ---- 表單元件表面：跟著主題走（手動切換模式時不脫隊） ---- */
.stTextInput input, .stNumberInput input, .stTextArea textarea,
div[data-baseweb="input"], div[data-baseweb="input"] input,
div[data-baseweb="textarea"], div[data-baseweb="base-input"],
div[data-baseweb="select"] > div {
    background-color: var(--card) !important;
    color: var(--ink) !important;
    border-color: var(--line) !important;
}
div[data-baseweb="popover"] [role="listbox"],
ul[role="listbox"], li[role="option"] {
    background-color: var(--card) !important;
    color: var(--ink) !important;
}
li[role="option"]:hover { background-color: var(--card-2) !important; }
div[data-baseweb="tag"] {
    background-color: var(--card-2) !important;
    color: var(--ink) !important;
}
div[data-testid="stExpander"] summary span { color: var(--ink) !important; }

/* 區塊間距 */
div[data-testid="stVerticalBlock"] { gap: 1.15rem; }
div[data-testid="stCaptionContainer"] {
    color: var(--muted); line-height: 1.7; margin-bottom: .4rem;
}
div[data-testid="stCaptionContainer"] * { color: var(--muted) !important; }

/* Metric 卡片 */
div[data-testid="stMetric"] {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 1rem 1.15rem .9rem;
}
div[data-testid="stMetricLabel"], div[data-testid="stMetricLabel"] * {
    color: var(--muted) !important;
}
div[data-testid="stMetricValue"] { color: var(--ink); }

/* Expander 卡片 */
details[data-testid="stExpander"] {
    border: 1px solid var(--line);
    border-radius: 12px;
    background: var(--card);
}
details[data-testid="stExpander"] summary { padding: .8rem 1.1rem; }

/* 分頁列 */
div[data-baseweb="tab-list"] {
    overflow-x: auto; flex-wrap: nowrap;
    gap: 2.2rem;
    border-bottom: 1px solid var(--line);
    margin-bottom: 1.4rem; padding-bottom: 2px;
}
button[data-baseweb="tab"] {
    padding: .7rem .35rem !important;
    letter-spacing: .08em; font-size: 1rem;
    background: transparent !important;
}
button[data-baseweb="tab"] * { color: var(--ink) !important; }
div[data-baseweb="tab-highlight"] { background-color: var(--accent); height: 2px; }
div[data-baseweb="tab-panel"] { padding-top: .6rem; }

/* ---- 自製 HTML 表格 ---- */
.sx-scroll {
    max-width: 980px; overflow: auto;
    border: 1px solid var(--line); border-radius: 12px;
    background: var(--card); margin: .4rem 0 1rem;
}
table.sx-table { width: 100%; border-collapse: collapse; font-size: .93rem; }
.sx-table thead th {
    position: sticky; top: 0; background: var(--card-2);
    color: var(--muted); font-weight: 600; letter-spacing: .04em;
    text-align: left; padding: .6rem .85rem;
    border-bottom: 1px solid var(--line); white-space: nowrap;
}
.sx-table tbody td {
    padding: .5rem .85rem; border-bottom: 1px solid var(--line);
    white-space: nowrap; color: var(--ink);
}
.sx-table tbody tr:last-child td { border-bottom: none; }
.sx-table tbody tr:hover td { background: var(--card-2); }
.sx-table td.num {
    font-family: 'IBM Plex Mono', monospace !important;
    font-variant-numeric: tabular-nums; text-align: right;
}
.sx-table td.up { color: #b0524c; }
.sx-table td.down { color: #54806c; }

/* ---- 新聞卡片 ---- */
.news-grid {
    display: grid; gap: .8rem;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    margin: .5rem 0 1.2rem;
}
a.news-card {
    display: block; text-decoration: none;
    background: var(--card); border: 1px solid var(--line);
    border-radius: 12px; padding: .9rem 1rem;
    transition: border-color .15s ease;
}
a.news-card:hover { border-color: var(--accent); }
.news-title { color: var(--ink); line-height: 1.6; font-size: .95rem; }
.news-meta { color: var(--muted); font-size: .8rem; margin-top: .5rem; }

/* ---- 模型觀點卡片 ---- */
.verdict-card {
    background: var(--card); border: 1px solid var(--line);
    border-left: 4px solid var(--accent);
    border-radius: 12px; padding: 1.1rem 1.3rem; margin: .6rem 0 1.2rem;
}
.verdict-pos { border-left-color: #b0524c; }
.verdict-neg { border-left-color: #54806c; }
.verdict-title { font-weight: 600; font-size: 1.05rem; margin-bottom: .7rem;
                 color: var(--ink); }
.verdict-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 1.2rem; }
.verdict-h { color: var(--muted); font-size: .85rem; margin-bottom: .3rem; }
.verdict-card ul { margin: 0; padding-left: 1.2rem; }
.verdict-card li { line-height: 1.8; font-size: .92rem; color: var(--ink); }
.verdict-note {
    color: var(--muted); font-size: .8rem; margin-top: .9rem;
    border-top: 1px dashed var(--line); padding-top: .6rem;
}

/* 按鈕 */
.stButton > button {
    min-height: 46px; border-radius: 10px;
    border: 1px solid var(--line);
    background: var(--card); color: var(--ink);
    letter-spacing: .06em; padding: .55rem 1.4rem;
}
.stButton > button:hover { border-color: var(--accent); color: var(--accent); }
.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"] {
    background: var(--accent); border-color: var(--accent);
    color: var(--accent-ink);
}
.stButton > button[kind="primary"] * { color: var(--accent-ink) !important; }
.stButton > button[kind="primary"]:hover { opacity: .92; }

/* 主題切換 radio：橫排、靜音 */
div[data-testid="stRadio"] label p { color: var(--ink); }

/* 漲跌語意色 */
.up   { color: #b0524c; font-weight: 600; }
.down { color: #54806c; font-weight: 600; }

/* 手機微調 */
@media (max-width: 640px) {
    .block-container { padding: 1rem .85rem 4.5rem; }
    h1 { font-size: 1.35rem; }
    div[data-baseweb="tab-list"] { gap: 1.2rem; }
    button[data-baseweb="tab"] { font-size: .92rem; }
    div[data-testid="stMetricValue"] { font-size: 1.02rem; }
    div[data-testid="stMetric"] { padding: .6rem .75rem .55rem; }
    .verdict-cols { grid-template-columns: 1fr; }
}
"""

_FONT_IMPORT = ("@import url('https://fonts.googleapis.com/css2?"
                "family=Noto+Serif+TC:wght@400;500;600;700&"
                "family=IBM+Plex+Mono:wght@400;500&display=swap');")


def build_css(mode: str = "system") -> str:
    """依外觀模式產生完整 CSS。mode: light / dark / system。"""
    if mode == "light":
        tokens = f":root {{{_LIGHT}}}"
    elif mode == "dark":
        tokens = f":root {{{_DARK}}}"
    else:  # 跟隨系統
        tokens = (f":root {{{_LIGHT}}}\n"
                  f"@media (prefers-color-scheme: dark) "
                  f"{{ :root {{{_DARK}}} }}")
    return f"<style>\n{_FONT_IMPORT}\n{tokens}\n{_CSS_BODY}\n</style>"


def plotly_font_color(mode: str) -> str | None:
    """強制模式時，Plotly 文字顏色需跟著主題（system 交給 Streamlit）。"""
    if mode == "light":
        return "#2b2f33"
    if mode == "dark":
        return "#e6e4de"
    return None


# 向下相容：預設跟隨系統
APP_CSS = build_css("system")
