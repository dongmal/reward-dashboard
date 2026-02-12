"""상수 및 설정"""

SHEET_NAMES = {
    "포인트클릭": {"db": "포인트클릭_DB", "ga": "포인트클릭_GA"},
    "캐시플레이": {"db": "캐시플레이_DB", "ga": "캐시플레이_GA"}
}

PASTEL = {
    'blue': '#5B9BD5', 'green': '#70AD47', 'orange': '#ED7D31',
    'yellow': '#FFC000', 'purple': '#A855F7', 'red': '#E05252',
    'teal': '#4DB8A4', 'gray': '#A0AEC0', 'pink': '#E88B9E',
    'indigo': '#7B8FD4', 'revenue': '#5B9BD5', 'cost': '#E05252',
    'margin': '#70AD47', 'margin_rate': '#FFC000',
    'game': '#5B9BD5', 'gathering': '#A855F7', 'iaa': '#70AD47',
    'offerwall': '#ED7D31', 'pc_highlight': '#E05252',
}

PUB_COLORS = [
    '#5B9BD5', '#ED7D31', '#70AD47', '#A855F7',
    '#E05252', '#4DB8A4', '#FFC000', '#A0AEC0'
]

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(size=11),
    margin=dict(t=15, b=45, l=55, r=15),
    legend=dict(
        orientation="h", yanchor="bottom", y=1.03,
        xanchor="right", x=1, font=dict(size=10),
        bgcolor="rgba(0,0,0,0)"
    ),
    xaxis=dict(showgrid=False, tickfont=dict(size=10)),
    yaxis=dict(gridcolor="rgba(128,128,128,0.12)", gridwidth=1, tickfont=dict(size=10)),
    hoverlabel=dict(font_size=11),
    hovermode="x unified",
)

CSS_STYLE = """
<style>
.main .block-container { padding-top: 1rem; max-width: 1440px; }
div[data-testid="stMetric"] {
    border-radius: 8px; padding: 14px 16px; border-left: 4px solid #5B9BD5;
}
div[data-testid="stMetric"]:nth-of-type(2) { border-left-color: #70AD47; }
div[data-testid="stMetric"]:nth-of-type(3) { border-left-color: #FFC000; }
div[data-testid="stMetric"]:nth-of-type(4) { border-left-color: #ED7D31; }
div[data-testid="stMetric"]:nth-of-type(5) { border-left-color: #A855F7; }
div[data-testid="stMetric"] label {
    font-size: 0.72rem !important; font-weight: 600 !important;
    letter-spacing: 0.3px; opacity: 0.65; text-transform: uppercase;
}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    font-size: 1.4rem !important; font-weight: 700 !important;
}
@media (prefers-color-scheme: light) {
    div[data-testid="stMetric"] { background: #FFFFFF; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
}
@media (prefers-color-scheme: dark) {
    div[data-testid="stMetric"] { background: rgba(255,255,255,0.04); }
}
button[data-baseweb="tab"] { font-weight: 700 !important; font-size: 1rem !important; padding: 12px 24px !important; }
div[data-baseweb="tab-highlight"] { background-color: #5B9BD5 !important; height: 3px !important; }
.main h2 { font-size: 1.1rem !important; font-weight: 700 !important; margin-top: 0.2rem !important; margin-bottom: 0.3rem !important; }
hr { margin: 0.8rem 0 !important; opacity: 0.3; }
div[data-testid="stSegmentedControl"] { max-width: 420px !important; }
div[data-testid="stSegmentedControl"] button {
    font-size: 0.7rem !important; padding: 2px 10px !important;
    min-height: 0 !important; height: 26px !important;
}
div[data-testid="stDateInput"] { max-width: 130px !important; }
div[data-testid="stDateInput"] input {
    font-size: 0.8rem !important; padding: 5px 8px !important;
    border: 1.5px solid #94a3b8 !important; border-radius: 5px !important;
    background: #fff !important; color: #1e293b !important;
}
div[data-testid="stDateInput"] input:hover { border-color: #5B9BD5 !important; }
div[data-testid="stDateInput"] label {
    font-size: 0.65rem !important; margin-bottom: 1px !important; opacity: 0.7;
}
@media (prefers-color-scheme: dark) {
    div[data-testid="stDateInput"] input {
        background: #1e293b !important; border-color: #475569 !important; color: #e2e8f0 !important;
    }
}
.main [data-testid="stColumn"]:has(div[data-testid="stDateInput"]) {
    flex: 0 0 auto !important; width: auto !important; min-width: 0 !important;
}
.main .stDownloadButton > button {
    font-size: 0.7rem !important; padding: 3px 10px !important; height: 28px !important;
}
</style>
"""

ALLOWED_DOMAIN = "fsn.co.kr"
