"""
Cricket WBI Dashboard  —  Pure Viewer
======================================
File layout (all files in one folder, configured in FILE CONFIG below):

    data/
    ├── major_league_batting_stats_2023.csv   ← raw season 1
    ├── major_league_batting_stats_2024.csv   ← raw season 2
    ├── major_league_batting_stats_2025.csv   ← raw season 3
    └── wbi_rankings.csv                      ← output of cricket_wbi.py

This file contains ZERO analysis logic.
Run cricket_wbi.py first to generate wbi_rankings.csv, then start this dashboard.

Run from the repo root:
    streamlit run analyzer/dashboard.py

Requires:
    pip install streamlit pandas plotly
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path

# ─────────────────────────────────────────────
# PATH CONFIG  ← no need to change if folder layout stays the same
# ─────────────────────────────────────────────
BASE_DIR     = Path(__file__).resolve().parent
DATA_FOLDER   = BASE_DIR / "data"

SEASON1_FILE  = DATA_FOLDER / "major_league_batting_stats_2023.csv"
SEASON2_FILE  = DATA_FOLDER / "major_league_batting_stats_2024.csv"
SEASON3_FILE  = DATA_FOLDER / "major_league_batting_stats_2025.csv"
RANKINGS_FILE = DATA_FOLDER / "wbi_rankings.csv"
MIN_INNINGS = 10  # minimum total innings across all seasons to show a player in the dashboard

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Cricket WBI Dashboard",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# THEME  — light / cool blue-slate palette
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Inter:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── background & text ── */
.stApp                          { background: #f0f4f8; color: #1a2332; }
h1, h2, h3                      { font-family: 'Syne', sans-serif; }

/* ── sidebar ── */
section[data-testid="stSidebar"]          { background: #ffffff !important; border-right: 1px solid #d9e2ec; }
section[data-testid="stSidebar"] *        { color: #1a2332 !important; }

/* ── metric cards ── */
[data-testid="metric-container"] {
    background: #ffffff;
    border: 1px solid #d9e2ec;
    border-radius: 10px;
    padding: 14px;
    box-shadow: 0 1px 4px rgba(26,35,50,0.06);
}

/* ── tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #ffffff;
    border-radius: 10px;
    gap: 4px;
    padding: 5px;
    box-shadow: 0 1px 4px rgba(26,35,50,0.07);
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: #4a6080;
    border-radius: 7px;
    font-family: 'Inter', sans-serif;
    font-weight: 500;
    font-size: 13px;
}
.stTabs [aria-selected="true"] {
    background: #1565c0 !important;
    color: #ffffff !important;
}

/* ── dataframe ── */
.stDataFrame                    { border: 1px solid #d9e2ec; border-radius: 10px; }

/* ── custom components ── */
.section-header {
    font-family: 'Syne', sans-serif;
    font-size: 20px;
    font-weight: 800;
    letter-spacing: 1.5px;
    color: #1565c0;
    border-bottom: 2px solid #bbdefb;
    padding-bottom: 6px;
    margin-bottom: 18px;
    text-transform: uppercase;
}

.info-box {
    background: #e3f2fd;
    border-left: 3px solid #1565c0;
    padding: 10px 14px;
    border-radius: 0 8px 8px 0;
    font-size: 13px;
    color: #0d47a1;
    margin: 8px 0;
}

.warn-box {
    background: #fff8e1;
    border-left: 3px solid #f9a825;
    padding: 10px 14px;
    border-radius: 0 8px 8px 0;
    font-size: 13px;
    color: #e65100;
    margin: 8px 0;
}

.pillar-hero {
    background: linear-gradient(135deg, #1565c0 0%, #0288d1 100%);
    border-radius: 14px;
    padding: 28px 32px;
    color: white;
    margin-bottom: 20px;
}

.card {
    background: #ffffff;
    border: 1px solid #d9e2ec;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 1px 6px rgba(26,35,50,0.06);
    margin-bottom: 12px;
}

hr { border-color: #d9e2ec; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
PILLAR_COLORS = {
    "Quality":       "#1565c0",
    "Consistency":   "#00838f",
    "Participation": "#6a1b9a",
    "Dominance":     "#c62828",
}

PILLAR_LIGHT = {
    "Quality":       "#e3f2fd",
    "Consistency":   "#e0f7fa",
    "Participation": "#f3e5f5",
    "Dominance":     "#ffebee",
}

NORM_COL_MAP = {
    "Quality":       "Quality (Norm)",
    "Consistency":   "Consistency Quality-Weighted (Norm)",
    "Participation": "Participation (Norm)",
    "Dominance":     "Dominance (Norm)",
}

RAW_COL_MAP = {
    "Quality":       "Quality (Raw)",
    "Consistency":   "Consistency Quality-Weighted (Raw)",
    "Participation": "Participation (Raw)",
    "Dominance":     "Dominance (Raw)",
}

PILLAR_DESCRIPTIONS = {
    "Quality": {
        "subtitle": "Geometric Mean of Average & Runs",
        "weight":   "40%",
        "icon":     "🏅",
        "what":     "Measures how good a batter is — combining their average with total runs scored across all 3 seasons.",
        "formula":  "√(Innings-Weighted Average × Total Runs)",
        "why":      "Using a geometric mean means both components matter equally. A player with a high average but very few innings (low runs) gets pulled down — preventing small-sample flukes from ranking high.",
        "example":  "Player A: avg=80, runs=160 → Quality = √(80×160) = 113\nPlayer B: avg=50, runs=1000 → Quality = √(50×1000) = 224  ✅ correctly ranked higher",
    },
    "Consistency": {
        "subtitle": "Quality-Weighted Stability Across Seasons",
        "weight":   "20%",
        "icon":     "📈",
        "what":     "Measures how reliably a batter performs season after season — and whether that reliability is at a high level.",
        "formula":  "1/(1 + CV)  ×  Quality Norm\nwhere CV = Std Dev of seasonal averages / Mean average × 100",
        "why":      "CV alone would reward a player who scores a consistent average of 4 just as much as one who scores 50. Multiplying by Quality Norm ensures consistency only counts if you are consistently good.",
        "example":  "Player A: avgs [48,50,52] → CV=3.3% → raw=0.97 × quality_norm=1.0 → 0.97 ✅\nPlayer B: avgs [4,4,4]   → CV=0%   → raw=1.0  × quality_norm=0.02 → 0.02 ✅",
    },
    "Participation": {
        "subtitle": "Availability & Commitment Across Seasons",
        "weight":   "25%",
        "icon":     "📅",
        "what":     "Measures how often a player showed up — across matches and innings relative to the most-played player in the dataset.",
        "formula":  "0.5 × (Total Matches / Max Matches)\n+ 0.5 × (Total Innings / Max Innings)",
        "why":      "Raised to 25% (from 15%) specifically to counter high-average players with very few games. A two-match wonder cannot rank above a player who contributed across 20+ matches.",
        "example":  "Player A: 40 matches, 72 innings (max in dataset) → Participation = 1.0\nPlayer B: 2 matches, 4 innings → Participation = 0.06 ← heavily penalised",
    },
    "Dominance": {
        "subtitle": "Performance Relative to Season Peers",
        "weight":   "15%",
        "icon":     "⚡",
        "what":     "Measures not just how good a player was, but how much better they were than everyone else in the same season.",
        "formula":  "Z-score = (Player Avg − Season Mean) / Season Std Dev\nDominance = Average Z-score across all seasons played",
        "why":      "A 42 average in a tough bowling season may be more dominant than a 55 average in a high-scoring season. Z-scores normalise for season context, so era-adjusted excellence is rewarded.",
        "example":  "Season mean=32, std=12:\nPlayer A: avg=55 → Z = (55−32)/12 = +1.92  ← elite\nPlayer B: avg=35 → Z = (35−32)/12 = +0.25  ← slightly above average",
    },
}

PLOT_BG = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(240,244,248,0.8)",
    font=dict(family="Inter", color="#1a2332"),
)

# Default margin — each chart merges this in; override per chart where needed
DEFAULT_MARGIN = dict(l=20, r=20, t=40, b=20)

SEASON_LABELS = ["Season 1", "Season 2", "Season 3"]

# ─────────────────────────────────────────────
# DATA LOADERS
# ─────────────────────────────────────────────
@st.cache_data
def load_rankings(file) -> pd.DataFrame:
    df = pd.read_csv(str(file))
    df.columns = df.columns.str.strip()
    df["Player"] = df["Player"].str.strip()
    return df

@st.cache_data
def load_raw_season(file, label: str) -> pd.DataFrame:
    df = pd.read_csv(str(file))
    df.columns = df.columns.str.strip()
    df["Player"] = df["Player"].str.strip()
    for col in ["Matches","Innings","Runs","Average","Strike Rate","100s","50s","High Score"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["Season"] = label
    return df

def validate_rankings(df: pd.DataFrame):
    required = {"Player","Team","WBI Score",
                "Quality (Raw)","Participation (Raw)","Dominance (Raw)",
                "Quality (Norm)","Participation (Norm)","Dominance (Norm)"}
    return required - set(df.columns)

# ─────────────────────────────────────────────
# CHART HELPERS
# ─────────────────────────────────────────────
def radar_chart(row, title="", color="#1565c0"):
    pillars  = list(PILLAR_COLORS.keys())
    values   = [row[NORM_COL_MAP[p]] for p in pillars]
    values_c = values + [values[0]]
    pillars_c = pillars + [pillars[0]]
    r,g,b = int(color[1:3],16), int(color[3:5],16), int(color[5:7],16)
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values_c, theta=pillars_c, fill="toself",
        fillcolor=f"rgba({r},{g},{b},0.12)",
        line=dict(color=color, width=2.5),
    ))
    fig.update_layout(
        **PLOT_BG,
        polar=dict(
            bgcolor="rgba(255,255,255,0.8)",
            radialaxis=dict(visible=True, range=[0,1],
                            gridcolor="#d9e2ec", tickfont=dict(size=9, color="#4a6080")),
            angularaxis=dict(gridcolor="#d9e2ec",
                             tickfont=dict(size=11, color="#1a2332")),
        ),
        title=dict(text=title, font=dict(family="Syne", size=16, color="#1565c0")),
        showlegend=False, height=320,
        margin=DEFAULT_MARGIN,
    )
    return fig

def compare_radar(rows, names):
    colors = ["#1565c0","#00838f","#6a1b9a","#c62828","#e65100"]
    pillars = list(PILLAR_COLORS.keys())
    fig = go.Figure()
    for i,(row,name) in enumerate(zip(rows,names)):
        vals  = [row[NORM_COL_MAP[p]] for p in pillars]
        vals_c = vals + [vals[0]]
        c = colors[i % len(colors)]
        r,g,b = int(c[1:3],16), int(c[3:5],16), int(c[5:7],16)
        fig.add_trace(go.Scatterpolar(
            r=vals_c, theta=pillars+[pillars[0]],
            fill="toself", name=name,
            fillcolor=f"rgba({r},{g},{b},0.12)",
            line=dict(color=c, width=2),
        ))
    fig.update_layout(
        **PLOT_BG,
        polar=dict(
            bgcolor="rgba(255,255,255,0.8)",
            radialaxis=dict(visible=True, range=[0,1],
                            gridcolor="#d9e2ec", tickfont=dict(size=9)),
            angularaxis=dict(gridcolor="#d9e2ec",
                             tickfont=dict(size=11, color="#1a2332")),
        ),
        legend=dict(bgcolor="rgba(255,255,255,0.8)", font=dict(color="#1a2332"),
                    bordercolor="#d9e2ec", borderwidth=1),
        title=dict(text="Player Comparison",
                   font=dict(family="Syne", size=16, color="#1565c0")),
        height=380,
        margin=DEFAULT_MARGIN,
    )
    return fig

def stacked_bar_top_n(df, n):
    top = df.head(n).iloc[::-1]
    fig = go.Figure()
    for label, col in [
        ("Quality",       "Quality (Norm)"),
        ("Consistency",   "Consistency Quality-Weighted (Norm)"),
        ("Participation", "Participation (Norm)"),
        ("Dominance",     "Dominance (Norm)"),
    ]:
        if col not in top.columns: continue
        fig.add_trace(go.Bar(
            y=top["Player"], x=top[col]/4,
            name=label, orientation="h",
            marker_color=PILLAR_COLORS[label],
            hovertemplate=f"<b>%{{y}}</b><br>{label}: %{{customdata:.3f}}<extra></extra>",
            customdata=top[col],
        ))
    fig.update_layout(
        **PLOT_BG, barmode="stack",
        xaxis=dict(title="WBI Contribution", gridcolor="#d9e2ec"),
        yaxis=dict(gridcolor="#d9e2ec"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    bgcolor="rgba(255,255,255,0.8)", bordercolor="#d9e2ec", borderwidth=1),
        height=max(380, n*38),
        title=dict(text=f"Top {n} — WBI Pillar Breakdown",
                   font=dict(family="Syne", size=18, color="#1565c0")),
        margin=DEFAULT_MARGIN,
    )
    return fig

def pillar_bar_top10(df, norm_col, color, n=10):
    top = df.nlargest(n, norm_col).iloc[::-1]
    r,g,b = int(color[1:3],16), int(color[3:5],16), int(color[5:7],16)
    # Gradient: darker for top player
    bar_colors = [f"rgba({r},{g},{b},{0.5 + 0.5*(i/(n-1))})" for i in range(n)]
    fig = go.Figure(go.Bar(
        y=top["Player"],
        x=top[norm_col],
        orientation="h",
        marker=dict(color=bar_colors, line=dict(width=0)),
        text=[f"{v:.3f}" for v in top[norm_col]],
        textposition="outside",
        textfont=dict(size=11, color="#1a2332"),
        hovertemplate="<b>%{y}</b><br>Score: %{x:.3f}<extra></extra>",
    ))
    fig.update_layout(
        **PLOT_BG,
        height=340,
        xaxis=dict(range=[0,1.15], gridcolor="#d9e2ec", showgrid=True),
        yaxis=dict(gridcolor="rgba(0,0,0,0)"),
        showlegend=False,
        margin=DEFAULT_MARGIN,
    )
    return fig

def scatter_quality_consistency(df):
    q = "Quality (Norm)"
    c = NORM_COL_MAP["Consistency"]
    p = "Participation (Norm)"
    d = "Dominance (Norm)"
    if not all(col in df.columns for col in [q,c,p,d]): return None
    fig = px.scatter(
        df, x=q, y=c, size=p, color=d,
        hover_name="Player",
        hover_data={"Team":True,"WBI Score":":.3f", q:":.3f", c:":.3f"},
        color_continuous_scale=["#bbdefb","#1565c0","#0d47a1"],
        size_max=28,
        labels={q:"Quality (Norm)", c:"Consistency (Norm)", d:"Dominance"},
        title="Quality vs Consistency  (bubble = participation, colour = dominance)",
    )
    fig.update_layout(
        **PLOT_BG, height=460,
        title_font=dict(family="Syne", size=18, color="#1565c0"),
        margin=DEFAULT_MARGIN,
    )
    fig.update_traces(marker=dict(line=dict(width=1, color="white")))
    return fig

def pillar_dist(df, col, label, color):
    fig = px.histogram(df, x=col, nbins=20,
        color_discrete_sequence=[color],
        labels={col: label},
    )
    fig.update_layout(
        **PLOT_BG, height=220,
        xaxis=dict(gridcolor="#d9e2ec"),
        yaxis=dict(gridcolor="#d9e2ec", title="Players"),
        showlegend=False,
        margin=dict(l=10,r=10,t=20,b=20),
    )
    fig.update_traces(marker_line_width=0)
    return fig

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏏 WBI Dashboard")
    st.markdown("---")
    st.markdown("### Data Files")
    st.markdown(
        f"<div class='info-box'>"
        f"<b>Rankings:</b> <code>{RANKINGS_FILE.name}</code><br><br>"
        f"<b>Season 1:</b> <code>{SEASON1_FILE.name}</code><br>"
        f"<b>Season 2:</b> <code>{SEASON2_FILE.name}</code><br>"
        f"<b>Season 3:</b> <code>{SEASON3_FILE.name}</code><br><br>"
        f"Edit <code>FILE CONFIG</code> at top of script to change paths."
        f"</div>", unsafe_allow_html=True
    )
    st.markdown("---")
    top_n = st.slider("Top N players to show", 5, 30, 10, 5)

# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
st.markdown("# 🏏 CRICKET WBI DASHBOARD")
st.markdown("*Weighted Batting Index — 3-Season Analysis*")
st.markdown("---")

if not RANKINGS_FILE.exists():
    st.error(
        f"Rankings file not found: `{RANKINGS_FILE}`\n\n"
        f"Run `python cricket_wbi.py` first, then place output in `{DATA_FOLDER}/`."
    )
    st.stop()

with st.spinner("Loading data..."):
    df = load_rankings(RANKINGS_FILE)
    missing = validate_rankings(df)
    if missing:
        st.error(f"`{RANKINGS_FILE.name}` missing columns: {missing}\n\nRe-run `cricket_wbi.py`.")
        st.stop()

    if "WBI Score" not in df.columns and "WBI" in df.columns:
        df = df.rename(columns={"WBI": "WBI Score"})

    df = df.sort_values("WBI Score", ascending=False).reset_index(drop=True)
    if "Rank" not in df.columns:
        df.insert(0, "Rank", range(1, len(df)+1))

    raw_seasons = []
    for path, label in zip([SEASON1_FILE,SEASON2_FILE,SEASON3_FILE], SEASON_LABELS):
        if path.exists():
            raw_seasons.append(load_raw_season(str(path), label))
    seasons_loaded = len(raw_seasons)

    if raw_seasons:
        innings_total = pd.concat([s[["Player","Innings"]] for s in raw_seasons])
        innings_total = (
            innings_total.dropna(subset=["Player", "Innings"])
            .groupby("Player")["Innings"].sum()
        )
        eligible_players = innings_total[innings_total >= MIN_INNINGS].index
        if len(eligible_players):
            original_count = len(df)
            df = df[df["Player"].isin(eligible_players)].reset_index(drop=True)
            raw_seasons = [s[s["Player"].isin(eligible_players)].copy() for s in raw_seasons]
            st.info(
                f"Filtered dashboard to players with ≥{MIN_INNINGS} total innings across all seasons. "
                f"({len(df)} of {original_count} players remain.)"
            )
        else:
            st.warning(
                f"No players met the minimum {MIN_INNINGS} innings filter in the loaded raw season files."
            )

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🏆 Rankings",
    "🔬 Pillar Explainer",
    "📊 Pillar Analysis",
    "🔍 Player Profile",
    "⚖️ Compare",
    "📋 Full Data",
])

# ══════════════════════════════════════════════
# TAB 1 — RANKINGS
# ══════════════════════════════════════════════
with tab1:

    # Podium
    st.markdown("<div class='section-header'>Top 3 Players</div>", unsafe_allow_html=True)
    top3 = df.head(3)
    medals = ["🥇","🥈","🥉"]
    medal_colors = ["#f9a825","#90a4ae","#a1887f"]
    medal_bg     = ["#fff8e1","#eceff1","#efebe9"]

    pods = st.columns(3)
    for i,(col,medal,mc,bg) in enumerate(zip(pods,medals,medal_colors,medal_bg)):
        if i < len(top3):
            r = top3.iloc[i]
            col.markdown(f"""
            <div style='background:{bg}; border:1px solid {mc}44;
                        border-top:4px solid {mc}; border-radius:12px;
                        padding:22px 18px; text-align:center;
                        box-shadow:0 2px 8px rgba(0,0,0,0.07);'>
                <div style='font-size:30px; margin-bottom:6px;'>{medal}</div>
                <div style='font-family:Syne; font-size:20px; font-weight:800;
                            color:#1a2332; letter-spacing:0.5px;'>{r['Player']}</div>
                <div style='font-size:12px; color:#4a6080; margin:5px 0 10px;'>{r['Team']}</div>
                <div style='font-family:Syne; font-size:34px; font-weight:800;
                            color:{mc};'>{r['WBI Score']:.3f}</div>
                <div style='font-size:11px; color:#78909c; letter-spacing:1px;'>WBI SCORE</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Summary metrics
    st.markdown("<div class='section-header'>Dataset Summary</div>", unsafe_allow_html=True)
    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("Total Players",   len(df))
    m2.metric("Avg WBI Score",   f"{df['WBI Score'].mean():.3f}")
    m3.metric("Highest WBI",     f"{df['WBI Score'].max():.3f}")
    m4.metric("Avg Quality",     f"{df['Quality (Raw)'].mean():.1f}")
    m5.metric("Seasons Loaded",  f"{seasons_loaded} / 3")

    st.markdown("<br>", unsafe_allow_html=True)

    # Stacked bar
    st.markdown("<div class='section-header'>WBI Leaderboard</div>", unsafe_allow_html=True)
    st.plotly_chart(stacked_bar_top_n(df, top_n), use_container_width=True, key="tab1_stacked_bar")

    # Scatter
    fig_scatter = scatter_quality_consistency(df)
    if fig_scatter:
        st.markdown("<div class='section-header'>Quality vs Consistency Map</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(fig_scatter, use_container_width=True, key="tab1_scatter")


# ══════════════════════════════════════════════
# TAB 2 — PILLAR EXPLAINER  (presentation mode)
# ══════════════════════════════════════════════
with tab2:

    st.markdown("<div class='section-header'>How We Score Each Player</div>",
                unsafe_allow_html=True)
    st.markdown(
        "Step through each pillar below. Each section explains **what it measures**, "
        "**how it's calculated**, **why we designed it this way**, and shows the "
        "**top 10 players** for that pillar.",
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Weight overview strip
    weight_cols = st.columns(4)
    weights_display = [
        ("Quality",       "40%", "🏅"),
        ("Consistency",   "20%", "📈"),
        ("Participation", "25%", "📅"),
        ("Dominance",     "15%", "⚡"),
    ]
    for col,(pillar,wt,icon) in zip(weight_cols, weights_display):
        c = PILLAR_COLORS[pillar]
        bg = PILLAR_LIGHT[pillar]
        col.markdown(f"""
        <div style='background:{bg}; border:1px solid {c}33; border-top:4px solid {c};
                    border-radius:10px; padding:16px; text-align:center;'>
            <div style='font-size:22px;'>{icon}</div>
            <div style='font-family:Syne; font-size:15px; font-weight:800;
                        color:{c}; margin:4px 0;'>{pillar}</div>
            <div style='font-family:Syne; font-size:26px; font-weight:800;
                        color:#1a2332;'>{wt}</div>
            <div style='font-size:11px; color:#78909c;'>of WBI Score</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # One section per pillar
    for pillar, info in PILLAR_DESCRIPTIONS.items():
        color  = PILLAR_COLORS[pillar]
        light  = PILLAR_LIGHT[pillar]
        norm_col = NORM_COL_MAP[pillar]
        raw_col  = RAW_COL_MAP[pillar]

        if norm_col not in df.columns:
            continue

        # Hero banner
        r,g,b = int(color[1:3],16), int(color[3:5],16), int(color[5:7],16)
        st.markdown(f"""
        <div style='background:linear-gradient(135deg,{color} 0%,rgba({r},{g},{b},0.75) 100%);
                    border-radius:14px; padding:26px 30px; color:white; margin-bottom:4px;'>
            <div style='display:flex; align-items:center; gap:14px;'>
                <div style='font-size:36px;'>{info['icon']}</div>
                <div>
                    <div style='font-family:Syne; font-size:26px; font-weight:800;
                                letter-spacing:1px;'>{pillar.upper()}</div>
                    <div style='font-size:14px; opacity:0.88; margin-top:2px;'>
                        {info['subtitle']}  ·  Weight: {info['weight']}
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Detail columns
        left, right = st.columns([1.1, 1])

        with left:
            st.markdown(f"""
            <div class='card'>
                <div style='font-family:Syne; font-size:13px; font-weight:800;
                            color:{color}; letter-spacing:1px; margin-bottom:8px;'>
                    WHAT IT MEASURES
                </div>
                <div style='font-size:14px; color:#1a2332; line-height:1.6;'>
                    {info['what']}
                </div>
            </div>
            <div class='card'>
                <div style='font-family:Syne; font-size:13px; font-weight:800;
                            color:{color}; letter-spacing:1px; margin-bottom:8px;'>
                    FORMULA
                </div>
                <pre style='background:{light}; border-radius:6px; padding:10px;
                            font-size:12px; color:#1a2332; white-space:pre-wrap;
                            margin:0;'>{info['formula']}</pre>
            </div>
            <div class='card'>
                <div style='font-family:Syne; font-size:13px; font-weight:800;
                            color:{color}; letter-spacing:1px; margin-bottom:8px;'>
                    WHY WE DESIGNED IT THIS WAY
                </div>
                <div style='font-size:14px; color:#1a2332; line-height:1.6;'>
                    {info['why']}
                </div>
            </div>
            <div class='card'>
                <div style='font-family:Syne; font-size:13px; font-weight:800;
                            color:{color}; letter-spacing:1px; margin-bottom:8px;'>
                    WORKED EXAMPLE
                </div>
                <pre style='background:{light}; border-radius:6px; padding:10px;
                            font-size:12px; color:#1a2332; white-space:pre-wrap;
                            margin:0;'>{info['example']}</pre>
            </div>
            """, unsafe_allow_html=True)

        with right:
            st.markdown(f"""
            <div style='font-family:Syne; font-size:14px; font-weight:800;
                        color:{color}; margin-bottom:8px; letter-spacing:0.5px;'>
                TOP 10 PLAYERS — {pillar.upper()}
            </div>
            """, unsafe_allow_html=True)
            st.plotly_chart(pillar_bar_top10(df, norm_col, color), use_container_width=True, key=f"tab2_bar_{pillar}")

            top10 = df.nlargest(10, norm_col)[["Rank","Player","Team",raw_col,norm_col]].rename(columns={
                raw_col:  f"Raw Score",
                norm_col: f"Norm (0–1)",
            })
            st.dataframe(top10.reset_index(drop=True), use_container_width=True, hide_index=True)

        st.markdown("<br>", unsafe_allow_html=True)


# ══════════════════════════════════════════════
# TAB 3 — PILLAR ANALYSIS
# ══════════════════════════════════════════════
with tab3:

    st.markdown("<div class='section-header'>Pillar Distributions</div>",
                unsafe_allow_html=True)

    dist_cols = st.columns(4)
    for col_ui,(pillar,color) in zip(dist_cols, PILLAR_COLORS.items()):
        norm_col = NORM_COL_MAP[pillar]
        if norm_col in df.columns:
            col_ui.markdown(f"<div style='font-family:Syne;font-weight:800;"
                            f"color:{color};font-size:13px;margin-bottom:4px;'>"
                            f"{pillar}</div>", unsafe_allow_html=True)
            col_ui.plotly_chart(pillar_dist(df, norm_col, pillar, color),
                                use_container_width=True, key=f"tab3_dist_{pillar}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='section-header'>Top 10 per Pillar</div>",
                unsafe_allow_html=True)

    p_cols = st.columns(2)
    pillar_list = list(PILLAR_COLORS.items())
    for idx,(pillar,color) in enumerate(pillar_list):
        norm_col = NORM_COL_MAP[pillar]
        raw_col  = RAW_COL_MAP[pillar]
        if norm_col not in df.columns: continue
        target = p_cols[idx % 2]
        with target:
            st.markdown(f"<div style='font-family:Syne;font-weight:800;"
                        f"color:{color};font-size:15px;margin:10px 0 6px;'>"
                        f"{PILLAR_DESCRIPTIONS[pillar]['icon']} {pillar}</div>",
                        unsafe_allow_html=True)
            st.plotly_chart(pillar_bar_top10(df, norm_col, color),
                            use_container_width=True, key=f"tab3_bar_{pillar}")


# ══════════════════════════════════════════════
# TAB 4 — PLAYER PROFILE
# ══════════════════════════════════════════════
with tab4:
    st.markdown("<div class='section-header'>Player Profile</div>", unsafe_allow_html=True)

    selected_player = st.selectbox("Select a player", df["Player"].tolist())
    row  = df[df["Player"] == selected_player].iloc[0]
    rank = int(row["Rank"])

    # Header card
    wbi_val = row['WBI Score']
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#1565c0 0%,#0288d1 100%);
                border-radius:14px; padding:24px 28px; margin-bottom:22px; color:white;'>
        <div style='display:flex; align-items:center; gap:20px; flex-wrap:wrap;'>
            <div style='font-family:Syne; font-size:52px; font-weight:800;
                        opacity:0.3; line-height:1;'>#{rank}</div>
            <div>
                <div style='font-family:Syne; font-size:28px; font-weight:800;
                            letter-spacing:1px;'>{row['Player']}</div>
                <div style='font-size:14px; opacity:0.8; margin-top:3px;'>{row['Team']}</div>
            </div>
            <div style='margin-left:auto; text-align:right;'>
                <div style='font-family:Syne; font-size:46px; font-weight:800;
                            line-height:1;'>{wbi_val:.3f}</div>
                <div style='font-size:11px; opacity:0.7; letter-spacing:1.5px;'>WBI SCORE</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_radar, col_bars = st.columns([1,1])

    with col_radar:
        st.plotly_chart(radar_chart(row, f"{selected_player}", "#1565c0"),
                        use_container_width=True, key=f"tab4_radar_{selected_player}")

    with col_bars:
        st.markdown("**Pillar Breakdown**")
        for pillar in PILLAR_COLORS:
            norm_col = NORM_COL_MAP[pillar]
            raw_col  = RAW_COL_MAP[pillar]
            if norm_col not in df.columns: continue
            color    = PILLAR_COLORS[pillar]
            light    = PILLAR_LIGHT[pillar]
            raw_val  = row[raw_col]
            norm_val = row[norm_col]
            pct      = norm_val * 100
            desc     = PILLAR_DESCRIPTIONS[pillar]["subtitle"]
            st.markdown(f"""
            <div style='margin-bottom:16px;'>
                <div style='display:flex; justify-content:space-between;
                            font-size:13px; margin-bottom:5px;'>
                    <span style='color:{color}; font-weight:700;
                                 font-family:Syne;'>{pillar}</span>
                    <span style='color:#4a6080;'>
                        {raw_val:.3f} raw &nbsp;·&nbsp;
                        <b style="color:{color}">{norm_val:.3f}</b> norm
                    </span>
                </div>
                <div style='background:#e9eef4; border-radius:6px;
                            height:10px; overflow:hidden;'>
                    <div style='background:{color}; width:{pct:.1f}%;
                                height:100%; border-radius:6px;
                                transition:width 0.4s ease;'></div>
                </div>
                <div style='font-size:11px; color:#78909c; margin-top:3px;'>{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    # Season stats
    st.markdown("<div class='section-header'>Season-by-Season Stats</div>",
                unsafe_allow_html=True)

    if not raw_seasons:
        st.markdown(
            "<div class='warn-box'>Season CSV files not found on disk. "
            "Check <code>SEASON1/2/3_FILE</code> paths in FILE CONFIG.</div>",
            unsafe_allow_html=True,
        )
    else:
        rows_out = []
        for sdf in raw_seasons:
            p = sdf[sdf["Player"]==selected_player]
            if not p.empty:
                r2 = p.iloc[0]
                si = lambda v: int(v) if pd.notna(v) else "-"
                sf = lambda v,d=2: round(float(v),d) if pd.notna(v) else "-"
                rows_out.append({
                    "Season":r2["Season"],"Team":r2["Team"],
                    "Matches":si(r2["Matches"]),"Innings":si(r2["Innings"]),
                    "Runs":si(r2["Runs"]),"Average":sf(r2["Average"]),
                    "Strike Rate":sf(r2["Strike Rate"]),
                    "100s":si(r2["100s"]),"50s":si(r2["50s"]),
                    "High Score":r2["High Score"] if pd.notna(r2["High Score"]) else "-",
                })
        if rows_out:
            st.dataframe(pd.DataFrame(rows_out), use_container_width=True, hide_index=True)
        else:
            st.info(f"No season records found for {selected_player}.")


# ══════════════════════════════════════════════
# TAB 5 — COMPARE
# ══════════════════════════════════════════════
with tab5:
    st.markdown("<div class='section-header'>Compare Players</div>", unsafe_allow_html=True)

    selected_compare = st.multiselect(
        "Select 2–5 players",
        options=df["Player"].tolist(),
        default=df["Player"].head(3).tolist(),
        max_selections=5,
    )

    if len(selected_compare) < 2:
        st.info("Select at least 2 players to compare.")
    else:
        c_rows = [df[df["Player"]==p].iloc[0] for p in selected_compare]

        col_r, col_b = st.columns([1,1])
        with col_r:
            st.plotly_chart(compare_radar(c_rows, selected_compare), use_container_width=True, key="tab5_compare_radar")

        with col_b:
            st.markdown("<div style='font-family:Syne;font-weight:800;color:#1565c0;"
                        "font-size:15px;margin-bottom:10px;'>Pillar Scores</div>",
                        unsafe_allow_html=True)
            p_labels = list(PILLAR_COLORS.keys())
            p_colors_list = ["#1565c0","#00838f","#6a1b9a","#c62828","#e65100"]
            fig = go.Figure()
            for i,(cr,name) in enumerate(zip(c_rows,selected_compare)):
                nv = [cr[NORM_COL_MAP[p]] for p in p_labels if NORM_COL_MAP[p] in df.columns]
                vp = [p for p in p_labels if NORM_COL_MAP[p] in df.columns]
                fig.add_trace(go.Bar(
                    name=name, x=vp, y=nv,
                    marker_color=p_colors_list[i % len(p_colors_list)],
                    text=[f"{v:.3f}" for v in nv], textposition="outside",
                ))
            fig.update_layout(
                **PLOT_BG, barmode="group",
                yaxis=dict(range=[0,1.2], gridcolor="#d9e2ec", title="Norm Score"),
                xaxis=dict(gridcolor="#d9e2ec"),
                legend=dict(bgcolor="rgba(255,255,255,0.9)", bordercolor="#d9e2ec",
                            borderwidth=1),
                height=360,
                margin=dict(l=20,r=20,t=20,b=20),
            )
            st.plotly_chart(fig, use_container_width=True, key="tab5_compare_bar")

        # Summary table
        st.markdown("<div class='section-header'>Summary Table</div>", unsafe_allow_html=True)
        tbl = pd.DataFrame([{
            "Player":            r["Player"],
            "Team":              r["Team"],
            "Rank":              int(r["Rank"]),
            "WBI Score":         round(r["WBI Score"],4),
            "Quality (N)":       round(r["Quality (Norm)"],4),
            "Consistency (N)":   round(r[NORM_COL_MAP["Consistency"]],4),
            "Participation (N)": round(r["Participation (Norm)"],4),
            "Dominance (N)":     round(r["Dominance (Norm)"],4),
        } for r in c_rows])
        st.dataframe(tbl, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════
# TAB 6 — FULL DATA
# ══════════════════════════════════════════════
with tab6:
    st.markdown("<div class='section-header'>Full Rankings Table</div>",
                unsafe_allow_html=True)

    all_teams = sorted(df["Team"].dropna().unique().tolist())
    sel_teams = st.multiselect("Filter by team", all_teams, default=all_teams)
    filtered  = df[df["Team"].isin(sel_teams)].copy()

    display_cols = [c for c in [
        "Rank","Player","Team",
        "Quality (Raw)","Consistency Quality-Weighted (Raw)",
        "Participation (Raw)","Dominance (Raw)",
        "Quality (Norm)","Consistency Quality-Weighted (Norm)",
        "Participation (Norm)","Dominance (Norm)",
        "WBI Score",
    ] if c in filtered.columns]

    st.dataframe(filtered[display_cols].round(4),
                 use_container_width=True, hide_index=True, height=500)

    st.download_button(
        "⬇  Download as CSV",
        data=filtered[display_cols].round(4).to_csv(index=False),
        file_name="wbi_rankings_filtered.csv",
        mime="text/csv",
    )

    st.markdown(
        "<div class='info-box'>This table reads directly from <b>wbi_rankings.csv</b> "
        "— no recalculation is done here. Re-run <code>cricket_wbi.py</code> to refresh.</div>",
        unsafe_allow_html=True,
    )