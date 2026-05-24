"""
Cricket WBI Dashboard  —  Interactive
======================================
File layout (all CSVs in one folder, configured in FILE CONFIG below):

    data/
    ├── major_league_batting_stats_2023.csv
    ├── major_league_batting_stats_2024.csv
    └── major_league_batting_stats_2025.csv

The WBI engine is embedded here. Adjust pillar weights in the sidebar
and the entire dashboard recomputes and updates instantly.

Run:
    streamlit run cricket_dashboard.py

Requires:
    pip install streamlit pandas numpy plotly
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path

# ─────────────────────────────────────────────
# FILE CONFIG  ← edit these paths
# ─────────────────────────────────────────────
BASE_DIR     = Path(__file__).resolve().parent
DATA_FOLDER   = BASE_DIR / "data"

SEASON1_FILE = DATA_FOLDER / "major_league_batting_stats_2023.csv"
SEASON2_FILE = DATA_FOLDER / "major_league_batting_stats_2024.csv"
SEASON3_FILE = DATA_FOLDER / "major_league_batting_stats_2025.csv"

# ─────────────────────────────────────────────
# ANALYSIS CONFIG
# ─────────────────────────────────────────────
MIN_INNINGS = 10   # players with fewer total innings across all seasons are excluded

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
# THEME — light / cool blue-slate palette
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Inter:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp                 { background: #f0f4f8; color: #1a2332; }
h1, h2, h3             { font-family: 'Syne', sans-serif; }

section[data-testid="stSidebar"]       { background: #ffffff !important; border-right: 1px solid #d9e2ec; }
section[data-testid="stSidebar"] *     { color: #1a2332 !important; }

[data-testid="metric-container"] {
    background: #ffffff; border: 1px solid #d9e2ec;
    border-radius: 10px; padding: 14px;
    box-shadow: 0 1px 4px rgba(26,35,50,0.06);
}

.stTabs [data-baseweb="tab-list"] {
    background: #ffffff; border-radius: 10px;
    gap: 4px; padding: 5px;
    box-shadow: 0 1px 4px rgba(26,35,50,0.07);
}
.stTabs [data-baseweb="tab"] {
    background: transparent; color: #4a6080;
    border-radius: 7px; font-family: 'Inter',sans-serif;
    font-weight: 500; font-size: 13px;
}
.stTabs [aria-selected="true"] { background: #1565c0 !important; color: #fff !important; }

.stDataFrame { border: 1px solid #d9e2ec; border-radius: 10px; }

.stSlider > div > div > div > div { background: #1565c0 !important; }

.section-header {
    font-family: 'Syne', sans-serif; font-size: 20px; font-weight: 800;
    letter-spacing: 1.5px; color: #1565c0;
    border-bottom: 2px solid #bbdefb;
    padding-bottom: 6px; margin-bottom: 18px; text-transform: uppercase;
}
.info-box {
    background: #e3f2fd; border-left: 3px solid #1565c0;
    padding: 10px 14px; border-radius: 0 8px 8px 0;
    font-size: 13px; color: #0d47a1; margin: 8px 0;
}
.warn-box {
    background: #fff8e1; border-left: 3px solid #f9a825;
    padding: 10px 14px; border-radius: 0 8px 8px 0;
    font-size: 13px; color: #e65100; margin: 8px 0;
}
.card {
    background: #ffffff; border: 1px solid #d9e2ec;
    border-radius: 12px; padding: 20px;
    box-shadow: 0 1px 6px rgba(26,35,50,0.06); margin-bottom: 12px;
}
.weight-chip {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 12px; font-weight: 700; margin: 2px;
    font-family: 'Syne', sans-serif;
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
PILLAR_ICONS = {
    "Quality": "🏅", "Consistency": "📈",
    "Participation": "📅", "Dominance": "⚡",
}
DEFAULT_WEIGHTS = {
    "Quality": 40, "Consistency": 30, "Participation": 10, "Dominance": 20,
}
NORM_COL = {
    "Quality":       "Quality (Norm)",
    "Consistency":   "Consistency (Norm)",
    "Participation": "Participation (Norm)",
    "Dominance":     "Dominance (Norm)",
}
RAW_COL = {
    "Quality":       "Quality (Raw)",
    "Consistency":   "Consistency (Raw)",
    "Participation": "Participation (Raw)",
    "Dominance":     "Dominance (Raw)",
}
PILLAR_DESCRIPTIONS = {
    "Quality": {
        "subtitle": "Geometric Mean of Average & Runs",
        "what":  "Measures how good a batter is — combining their innings-weighted average with total runs scored across all 3 seasons.",
        "formula": "√(A1*I1 + A2*I2 + A3*I3)/(I1+I2+I3) × Total Runs)",
        "why":   "A geometric mean means both components matter equally. A player with a high average but very few innings (low runs) gets pulled down — preventing small-sample flukes from ranking high.",
        "example": "Player A: avg=80, runs=160  → Quality = √(80×160)   = 113\nPlayer B: avg=50, runs=1000 → Quality = √(50×1000) = 224  ✅ correctly ranked higher",
    },
    "Consistency": {
        "subtitle": "Quality-Weighted Stability Across Seasons",
        "what":  "Measures how reliably a batter performs season after season — and whether that reliability is at a high level.",
        "formula": "1/(1 + CV) × Quality_norm\nwhere CV = StdDev(seasonal avgs) / Mean(seasonal avgs) × 100",
        "why":   "CV alone would reward a player with a consistent average of 4 as much as one averaging 50. Multiplying by Quality_norm ensures consistency only scores if you are consistently good.",
        "example": "Player A: avgs [48,50,52] → CV=3.3% → raw=0.97 × quality_norm=1.0  → 0.97 ✅\nPlayer B: avgs [4,4,4]   → CV=0%   → raw=1.0  × quality_norm=0.02 → 0.02 ✅",
    },
    "Participation": {
        "subtitle": "Availability & Commitment Across Seasons",
        "what":  "Measures how often a player showed up — matches and innings relative to the most-played player in the dataset.",
        "formula": "0.5 × (Total Matches / Max Matches)\n+ 0.5 × (Total Innings / Max Innings)",
        "why":   "Raised to 25% by default to counter high-average players with very few games. A two-match wonder cannot outrank a player who contributed across 20+ matches.",
        "example": "Player A: 40 matches, 72 innings (max) → Participation = 1.0\nPlayer B: 2 matches,  4 innings       → Participation = 0.06 ← penalised",
    },
    "Dominance": {
        "subtitle": "Average + Runs vs Season Peers (Equal Weight)",
        "what":  "Measures how far above peers a player was each season — combining Z-scores of Average and Runs equally (50/50). Strike Rate is excluded due to unreliable data in domestic cricket.",
        "formula": "Season_Dom = 0.50×Z(Average) + 0.50×Z(Runs)\nDominance  = Mean Season_Dom across seasons played\n\nZ(metric) = (Player value − Season mean) / Season std dev",
        "why":   "Average alone double-counts quality (P1 already uses it). Adding Runs catches players who score heavily even at moderate average. Equal 50/50 split because both capture batting quality from complementary angles — rate vs volume. Absent seasons are excluded from the mean, not counted as zero — Participation handles absence separately.",
        "example": "Season means: avg=32, runs=420\nPlayer A: avg=55, runs=800 → Z_avg=+1.92, Z_runs=+1.71 → Dom = 0.5×1.92 + 0.5×1.71 = +1.82 ✅\nPlayer B: avg=55, runs=220 → Z_avg=+1.92, Z_runs=−0.90 → Dom = 0.5×1.92 + 0.5×−0.90 = +0.51 ← penalised for low runs",
    },
}

PLOT_BG = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(240,244,248,0.8)",
    font=dict(family="Inter", color="#1a2332"),
)
DEFAULT_MARGIN = dict(l=20, r=20, t=40, b=20)
SEASON_LABELS  = ["Season 1", "Season 2", "Season 3"]

# ─────────────────────────────────────────────
# WBI ENGINE  (embedded — runs on slider change)
# ─────────────────────────────────────────────
def minmax(series: pd.Series) -> pd.Series:
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series(0.5, index=series.index)
    return (series - lo) / (hi - lo)

def calc_quality(seasons):
    combined = pd.concat(
        [df[["Player","Average","Innings","Runs"]].copy() for df in seasons],
        ignore_index=True
    ).dropna(subset=["Average","Innings","Runs"])
    combined["weighted_avg"] = combined["Average"] * combined["Innings"]
    grp = combined.groupby("Player").agg(
        total_weighted=("weighted_avg","sum"),
        total_innings =("Innings","sum"),
        total_runs    =("Runs","sum"),
    )
    grp["innings_weighted_avg"] = grp["total_weighted"] / grp["total_innings"]
    grp["quality_raw"] = np.sqrt(grp["innings_weighted_avg"] * grp["total_runs"])
    return grp["quality_raw"]

def calc_consistency(seasons, quality_norm):
    frames = []
    for i, df in enumerate(seasons, 1):
        tmp = (
            df[["Player","Average"]].dropna(subset=["Average"])
            .groupby("Player", as_index=False)["Average"].mean()
            .rename(columns={"Average": f"avg_s{i}"})
            .set_index("Player")
        )
        frames.append(tmp)
    wide     = pd.concat(frames, axis=1)
    mean_avg = wide.mean(axis=1)
    std_avg  = wide.std(axis=1, ddof=0)
    cv       = (std_avg / mean_avg.replace(0, np.nan)) * 100
    cv       = cv.fillna(0)
    raw      = 1 / (1 + cv)
    q_aligned = quality_norm.reindex(raw.index).fillna(0)
    return (raw * q_aligned).rename("consistency_raw")

def calc_participation(seasons):
    m = pd.concat([df[["Player","Matches"]] for df in seasons]).groupby("Player")["Matches"].sum()
    i = pd.concat([df[["Player","Innings"]] for df in seasons]).groupby("Player")["Innings"].sum()
    return (0.5*(m/m.max()) + 0.5*(i/i.max())).rename("participation_raw")

def calc_dominance(seasons):
    """
    Two-metric dominance — Average and Runs, equal weight (50/50).

    Strike Rate excluded: unreliable in domestic cricket data
    (frequently missing, not recorded, or distorted by format).

    Per season:
        Z(Average) = (player_avg  - season_mean_avg)  / season_std_avg
        Z(Runs)    = (player_runs - season_mean_runs)  / season_std_runs
        Season_Dom = 0.50 * Z(Average) + 0.50 * Z(Runs)

    Final Dominance = mean of Season_Dom across all seasons the player
    appeared in. Seasons where the player was absent are excluded from
    the mean (not counted as zero) — Participation handles absence.
    """
    z_frames = []
    for idx, df in enumerate(seasons, 1):
        tmp = (
            df[["Player","Average","Runs"]]
            .dropna(subset=["Average","Runs"])
            .groupby("Player", as_index=False)
            .mean(numeric_only=True)
        )
        season_z = pd.Series(0.0, index=tmp.index)
        for metric in ["Average", "Runs"]:
            col_vals = pd.to_numeric(tmp[metric], errors="coerce").fillna(0)
            mu    = col_vals.mean()
            sigma = col_vals.std(ddof=0)
            z     = (col_vals - mu) / sigma if sigma > 0 else pd.Series(0.0, index=tmp.index)
            season_z = season_z + 0.50 * z
        tmp[f"dom_s{idx}"] = season_z.values
        z_frames.append(tmp[["Player", f"dom_s{idx}"]].set_index("Player"))
    wide = pd.concat(z_frames, axis=1)
    return wide.mean(axis=1).rename("dominance_raw")

def build_wbi(seasons, weights: dict, min_innings: int = MIN_INNINGS) -> pd.DataFrame:
    """Recompute WBI with the given weight dict {pillar: fraction}."""

    # ── Minimum innings filter ────────────────────────────────────────────────
    # Exclude players who have not accumulated enough innings across all seasons.
    # Filters before any pillar is computed so all pillars are affected equally.
    total_inn = (
        pd.concat([df[["Player","Innings"]] for df in seasons], ignore_index=True)
        .groupby("Player")["Innings"].sum()
    )
    qualified_players = set(total_inn[total_inn >= min_innings].index)
    seasons = [df[df["Player"].isin(qualified_players)].copy() for df in seasons]

    quality       = calc_quality(seasons)
    quality_norm  = minmax(quality)
    consistency   = calc_consistency(seasons, quality_norm)
    participation = calc_participation(seasons)
    dominance     = calc_dominance(seasons)

    result = (
        quality.to_frame()
        .join(consistency,   how="outer")
        .join(participation, how="outer")
        .join(dominance,     how="outer")
    )

    all_players = (
        pd.concat(seasons)[["Player","Team"]]
        .drop_duplicates("Player", keep="last")
    )
    result = result.merge(all_players, on="Player", how="left")

    raw_cols = ["quality_raw","consistency_raw","participation_raw","dominance_raw"]
    result[raw_cols] = result[raw_cols].fillna(0)

    result["Quality (Raw)"]       = result["quality_raw"]
    result["Consistency (Raw)"]   = result["consistency_raw"]
    result["Participation (Raw)"] = result["participation_raw"]
    result["Dominance (Raw)"]     = result["dominance_raw"]

    result["Quality (Norm)"]       = minmax(result["quality_raw"])
    result["Consistency (Norm)"]   = minmax(result["consistency_raw"])
    result["Participation (Norm)"] = minmax(result["participation_raw"])
    result["Dominance (Norm)"]     = minmax(result["dominance_raw"])

    result["WBI Score"] = (
        weights["Quality"]       * result["Quality (Norm)"] +
        weights["Consistency"]   * result["Consistency (Norm)"] +
        weights["Participation"] * result["Participation (Norm)"] +
        weights["Dominance"]     * result["Dominance (Norm)"]
    )

    result = result.sort_values("WBI Score", ascending=False).reset_index()
    result.insert(0, "Rank", range(1, len(result)+1))
    return result

# ─────────────────────────────────────────────
# DATA LOADERS
# ─────────────────────────────────────────────
@st.cache_data
def load_raw_season(path: str, label: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    df["Player"] = df["Player"].str.strip()
    for col in ["Matches","Innings","Runs","Average","Strike Rate","100s","50s","High Score"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["Season"] = label
    return df

# ─────────────────────────────────────────────
# CHART HELPERS
# ─────────────────────────────────────────────
def radar_chart(row, title="", color="#1565c0"):
    pillars   = list(PILLAR_COLORS.keys())
    values    = [row[NORM_COL[p]] for p in pillars]
    values_c  = values + [values[0]]
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
            angularaxis=dict(gridcolor="#d9e2ec", tickfont=dict(size=11, color="#1a2332")),
        ),
        title=dict(text=title, font=dict(family="Syne", size=15, color="#1565c0")),
        showlegend=False, height=310,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig

def compare_radar(rows, names):
    colors = ["#1565c0","#00838f","#6a1b9a","#c62828","#e65100"]
    pillars = list(PILLAR_COLORS.keys())
    fig = go.Figure()
    for i,(row,name) in enumerate(zip(rows, names)):
        vals  = [row[NORM_COL[p]] for p in pillars]
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
            angularaxis=dict(gridcolor="#d9e2ec", tickfont=dict(size=11, color="#1a2332")),
        ),
        legend=dict(bgcolor="rgba(255,255,255,0.8)", bordercolor="#d9e2ec", borderwidth=1,
                    font=dict(color="#1a2332")),
        title=dict(text="Player Comparison", font=dict(family="Syne",size=15,color="#1565c0")),
        height=380, margin=dict(l=20,r=20,t=40,b=20),
    )
    return fig

def stacked_bar(df, n, weights):
    top = df.head(n).iloc[::-1]
    fig = go.Figure()
    for pillar, col in NORM_COL.items():
        if col not in top.columns: continue
        w = weights[pillar]
        fig.add_trace(go.Bar(
            y=top["Player"], x=top[col] * w,
            name=f"{pillar} ({w:.0%})",
            orientation="h",
            marker_color=PILLAR_COLORS[pillar],
            hovertemplate=f"<b>%{{y}}</b><br>{pillar}: %{{customdata:.3f}}<extra></extra>",
            customdata=top[col],
        ))
    fig.update_layout(
        **PLOT_BG, barmode="stack",
        xaxis=dict(title="WBI Score", gridcolor="#d9e2ec", range=[0,1.05]),
        yaxis=dict(gridcolor="#d9e2ec"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    bgcolor="rgba(255,255,255,0.8)", bordercolor="#d9e2ec", borderwidth=1),
        height=max(380, n*40),
        title=dict(text=f"Top {n} — WBI Breakdown by Pillar",
                   font=dict(family="Syne", size=18, color="#1565c0")),
        margin=DEFAULT_MARGIN,
    )
    return fig

def pillar_bar(df, norm_col, color, n=10):
    top = df.nlargest(n, norm_col).iloc[::-1]
    r,g,b = int(color[1:3],16), int(color[3:5],16), int(color[5:7],16)
    shades = [f"rgba({r},{g},{b},{0.45 + 0.55*(i/(max(n-1,1)))})" for i in range(n)]
    fig = go.Figure(go.Bar(
        y=top["Player"], x=top[norm_col], orientation="h",
        marker=dict(color=shades, line=dict(width=0)),
        text=[f"{v:.3f}" for v in top[norm_col]],
        textposition="outside", textfont=dict(size=11, color="#1a2332"),
        hovertemplate="<b>%{y}</b><br>Score: %{x:.3f}<extra></extra>",
    ))
    fig.update_layout(
        **PLOT_BG, height=330,
        xaxis=dict(range=[0,1.15], gridcolor="#d9e2ec"),
        yaxis=dict(gridcolor="rgba(0,0,0,0)"),
        showlegend=False,
        margin=dict(l=10, r=20, t=10, b=10),
    )
    return fig

def scatter_map(df):
    q,c,p,d = NORM_COL["Quality"], NORM_COL["Consistency"], NORM_COL["Participation"], NORM_COL["Dominance"]
    if not all(col in df.columns for col in [q,c,p,d]): return None
    fig = px.scatter(
        df, x=q, y=c, size=p, color=d,
        hover_name="Player",
        hover_data={"Team":True,"WBI Score":":.3f", q:":.3f", c:":.3f"},
        color_continuous_scale=["#bbdefb","#1565c0","#0d47a1"],
        size_max=28,
        labels={q:"Quality",c:"Consistency",d:"Dominance"},
        title="Quality vs Consistency  (bubble = participation, colour = dominance)",
    )
    fig.update_layout(
        **PLOT_BG, height=440,
        title_font=dict(family="Syne", size=17, color="#1565c0"),
        margin=DEFAULT_MARGIN,
    )
    fig.update_traces(marker=dict(line=dict(width=1, color="white")))
    return fig

def dist_chart(df, col, color):
    fig = px.histogram(df, x=col, nbins=20, color_discrete_sequence=[color])
    fig.update_layout(
        **PLOT_BG, height=200, showlegend=False,
        xaxis=dict(gridcolor="#d9e2ec"),
        yaxis=dict(gridcolor="#d9e2ec", title="Players"),
        margin=dict(l=10,r=10,t=16,b=20),
    )
    fig.update_traces(marker_line_width=0)
    return fig

# ─────────────────────────────────────────────
# SIDEBAR — weight sliders
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏏 WBI Dashboard")
    st.markdown("---")

    st.markdown("### ⚖️ Pillar Weights")
    st.markdown(
        "<div class='info-box'>Drag sliders to adjust how much each pillar "
        "contributes to the final WBI score. Weights are auto-normalised to sum to 100%."
        "</div>", unsafe_allow_html=True
    )

    w_quality       = st.slider("🏅 Quality",       0, 100, DEFAULT_WEIGHTS["Quality"],       5)
    w_consistency   = st.slider("📈 Consistency",   0, 100, DEFAULT_WEIGHTS["Consistency"],   5)
    w_participation = st.slider("📅 Participation", 0, 100, DEFAULT_WEIGHTS["Participation"], 5)
    w_dominance     = st.slider("⚡ Dominance",     0, 100, DEFAULT_WEIGHTS["Dominance"],     5)

    total_w = w_quality + w_consistency + w_participation + w_dominance
    if total_w == 0:
        total_w = 1

    weights = {
        "Quality":       w_quality       / total_w,
        "Consistency":   w_consistency   / total_w,
        "Participation": w_participation / total_w,
        "Dominance":     w_dominance     / total_w,
    }

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Effective weights (normalised)**")
    for pillar, w in weights.items():
        color = PILLAR_COLORS[pillar]
        light = PILLAR_LIGHT[pillar]
        st.markdown(
            f"<span class='weight-chip' style='background:{light};color:{color};'>"
            f"{PILLAR_ICONS[pillar]} {pillar}: {w:.0%}</span>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    if st.button("↺  Reset to defaults"):
        st.session_state["w_quality"]       = DEFAULT_WEIGHTS["Quality"]
        st.session_state["w_consistency"]   = DEFAULT_WEIGHTS["Consistency"]
        st.session_state["w_participation"] = DEFAULT_WEIGHTS["Participation"]
        st.session_state["w_dominance"]     = DEFAULT_WEIGHTS["Dominance"]
        st.rerun()

    st.markdown("---")
    st.markdown("### 🔢 Minimum Innings Filter")
    st.markdown(
        "<div class='info-box'>Players with fewer total innings across all 3 seasons "
        "are excluded from the analysis entirely.</div>", unsafe_allow_html=True
    )
    min_innings_slider = st.slider("Min total innings", 1, 30, MIN_INNINGS, 1)

    st.markdown("---")
    top_n = st.slider("Top N players", 5, 30, 10, 5)

    st.markdown("---")
    st.markdown("### Data Files")
    st.markdown(
        f"<div class='info-box'>"
        f"<b>S1:</b> <code>{SEASON1_FILE.name}</code><br>"
        f"<b>S2:</b> <code>{SEASON2_FILE.name}</code><br>"
        f"<b>S3:</b> <code>{SEASON3_FILE.name}</code><br><br>"
        f"Edit <code>FILE CONFIG</code> at top of script to change paths."
        f"</div>", unsafe_allow_html=True
    )

# ─────────────────────────────────────────────
# LOAD RAW DATA
# ─────────────────────────────────────────────
st.markdown("# 🏏 CRICKET WBI DASHBOARD")
st.markdown("*Weighted Batting Index — Interactive 3-Season Analysis*")
st.markdown("---")

missing_files = [p for p in [SEASON1_FILE,SEASON2_FILE,SEASON3_FILE] if not p.exists()]
if missing_files:
    st.error(
        f"Missing season files: {[str(p) for p in missing_files]}\n\n"
        f"Check FILE CONFIG paths at the top of the script."
    )
    st.stop()

with st.spinner("Loading season data..."):
    seasons = [
        load_raw_season(str(SEASON1_FILE), "Season 1"),
        load_raw_season(str(SEASON2_FILE), "Season 2"),
        load_raw_season(str(SEASON3_FILE), "Season 3"),
    ]

# ─────────────────────────────────────────────
# COMPUTE WBI  (reruns whenever weights change)
# ─────────────────────────────────────────────
with st.spinner("Computing WBI..."):
    df = build_wbi(seasons, weights, min_innings=min_innings_slider)

# ─────────────────────────────────────────────
# ACTIVE WEIGHTS BANNER
# ─────────────────────────────────────────────
chips = "".join([
    f"<span class='weight-chip' style='background:{PILLAR_LIGHT[p]};color:{PILLAR_COLORS[p]};'>"
    f"{PILLAR_ICONS[p]} {p} {weights[p]:.0%}</span>"
    for p in weights
])
st.markdown(
    f"<div style='background:#fff;border:1px solid #d9e2ec;border-radius:10px;"
    f"padding:12px 16px;margin-bottom:18px;display:flex;align-items:center;gap:10px;"
    f"flex-wrap:wrap;box-shadow:0 1px 4px rgba(26,35,50,0.05);'>"
    f"<span style='font-family:Syne;font-weight:800;font-size:13px;color:#4a6080;"
    f"letter-spacing:1px;'>ACTIVE WEIGHTS</span>{chips}"
    f"<span style='margin-left:auto;font-size:12px;color:#78909c;'>"
    f"⚾ Min innings: <b>{min_innings_slider}</b> &nbsp;·&nbsp; "
    f"<b>{len(df)}</b> players qualified</span></div>",
    unsafe_allow_html=True,
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
    medals      = ["🥇","🥈","🥉"]
    medal_colors = ["#f9a825","#90a4ae","#a1887f"]
    medal_bg     = ["#fff8e1","#eceff1","#efebe9"]

    pods = st.columns(3)
    for i,(col,medal,mc,bg) in enumerate(zip(pods,medals,medal_colors,medal_bg)):
        if i < len(top3):
            r = top3.iloc[i]
            col.markdown(f"""
            <div style='background:{bg};border:1px solid {mc}44;border-top:4px solid {mc};
                        border-radius:12px;padding:22px 18px;text-align:center;
                        box-shadow:0 2px 8px rgba(0,0,0,0.06);'>
                <div style='font-size:30px;margin-bottom:6px;'>{medal}</div>
                <div style='font-family:Syne;font-size:19px;font-weight:800;
                            color:#1a2332;'>{r['Player']}</div>
                <div style='font-size:12px;color:#4a6080;margin:5px 0 10px;'>{r['Team']}</div>
                <div style='font-family:Syne;font-size:32px;font-weight:800;
                            color:{mc};'>{r['WBI Score']:.3f}</div>
                <div style='font-size:11px;color:#78909c;letter-spacing:1px;'>WBI SCORE</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Summary
    st.markdown("<div class='section-header'>Dataset Summary</div>", unsafe_allow_html=True)
    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("Total Players",  len(df))
    m2.metric("Avg WBI Score",  f"{df['WBI Score'].mean():.3f}")
    m3.metric("Highest WBI",    f"{df['WBI Score'].max():.3f}")
    m4.metric("Avg Quality",    f"{df['Quality (Raw)'].mean():.1f}")
    m5.metric("Avg Consistency",f"{df['Consistency (Raw)'].mean():.3f}")

    st.markdown("<br>", unsafe_allow_html=True)

    # Stacked bar
    st.markdown("<div class='section-header'>WBI Leaderboard</div>", unsafe_allow_html=True)
    st.plotly_chart(stacked_bar(df, top_n, weights), use_container_width=True,
                    key="tab1_stacked_bar")

    # Scatter map
    fig_sc = scatter_map(df)
    if fig_sc:
        st.markdown("<div class='section-header'>Quality vs Consistency Map</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(fig_sc, use_container_width=True, key="tab1_scatter")


# ══════════════════════════════════════════════
# TAB 2 — PILLAR EXPLAINER
# ══════════════════════════════════════════════
with tab2:
    st.markdown("<div class='section-header'>How We Score Each Player</div>",
                unsafe_allow_html=True)
    st.markdown(
        "Each pillar below explains **what it measures**, **how it's calculated**, "
        "**why it's designed this way**, and shows the **top 10 players** for that pillar "
        "under the current weights."
    )
    st.markdown("<br>", unsafe_allow_html=True)

    # Weight strip
    wcols = st.columns(4)
    for col_ui,(pillar,w) in zip(wcols, weights.items()):
        c  = PILLAR_COLORS[pillar]
        bg = PILLAR_LIGHT[pillar]
        col_ui.markdown(f"""
        <div style='background:{bg};border:1px solid {c}33;border-top:4px solid {c};
                    border-radius:10px;padding:16px;text-align:center;'>
            <div style='font-size:22px;'>{PILLAR_ICONS[pillar]}</div>
            <div style='font-family:Syne;font-size:14px;font-weight:800;
                        color:{c};margin:4px 0;'>{pillar}</div>
            <div style='font-family:Syne;font-size:26px;font-weight:800;
                        color:#1a2332;'>{w:.0%}</div>
            <div style='font-size:11px;color:#78909c;'>of WBI Score</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # One section per pillar
    for pillar, info in PILLAR_DESCRIPTIONS.items():
        color    = PILLAR_COLORS[pillar]
        light    = PILLAR_LIGHT[pillar]
        norm_col = NORM_COL[pillar]
        raw_col  = RAW_COL[pillar]
        w_pct    = weights[pillar]
        if norm_col not in df.columns: continue

        r,g,b = int(color[1:3],16), int(color[3:5],16), int(color[5:7],16)

        # Hero banner
        st.markdown(f"""
        <div style='background:linear-gradient(135deg,{color} 0%,rgba({r},{g},{b},0.72) 100%);
                    border-radius:14px;padding:22px 28px;color:white;margin-bottom:4px;'>
            <div style='display:flex;align-items:center;gap:14px;flex-wrap:wrap;'>
                <div style='font-size:34px;'>{PILLAR_ICONS[pillar]}</div>
                <div style='flex:1;'>
                    <div style='font-family:Syne;font-size:24px;font-weight:800;
                                letter-spacing:1px;'>{pillar.upper()}</div>
                    <div style='font-size:13px;opacity:0.88;margin-top:2px;'>
                        {info['subtitle']}
                    </div>
                </div>
                <div style='text-align:right;'>
                    <div style='font-family:Syne;font-size:36px;font-weight:800;
                                line-height:1;'>{w_pct:.0%}</div>
                    <div style='font-size:11px;opacity:0.75;letter-spacing:1px;'>
                        CURRENT WEIGHT</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        left, right = st.columns([1.05, 1])

        with left:
            for label, key in [("WHAT IT MEASURES","what"),("FORMULA","formula"),
                                ("WHY THIS DESIGN","why"),("WORKED EXAMPLE","example")]:
                is_code = key in ("formula","example")
                inner = (
                    f"<pre style='background:{light};border-radius:6px;padding:10px;"
                    f"font-size:12px;color:#1a2332;white-space:pre-wrap;margin:0;'>"
                    f"{info[key]}</pre>"
                ) if is_code else (
                    f"<div style='font-size:14px;color:#1a2332;line-height:1.6;'>"
                    f"{info[key]}</div>"
                )
                st.markdown(f"""
                <div class='card'>
                    <div style='font-family:Syne;font-size:12px;font-weight:800;
                                color:{color};letter-spacing:1px;margin-bottom:7px;'>
                        {label}</div>
                    {inner}
                </div>
                """, unsafe_allow_html=True)

        with right:
            st.markdown(
                f"<div style='font-family:Syne;font-weight:800;color:{color};"
                f"font-size:14px;margin-bottom:6px;letter-spacing:0.5px;'>"
                f"TOP 10 — {pillar.upper()}</div>",
                unsafe_allow_html=True,
            )
            st.plotly_chart(
                pillar_bar(df, norm_col, color),
                use_container_width=True,
                key=f"tab2_bar_{pillar}",
            )
            top10 = df.nlargest(10, norm_col)[
                ["Rank","Player","Team",raw_col,norm_col]
            ].rename(columns={raw_col:"Raw Score", norm_col:"Norm (0–1)"})
            st.dataframe(top10.reset_index(drop=True),
                         use_container_width=True, hide_index=True)

        st.markdown("<br>", unsafe_allow_html=True)


# ══════════════════════════════════════════════
# TAB 3 — PILLAR ANALYSIS
# ══════════════════════════════════════════════
with tab3:
    st.markdown("<div class='section-header'>Pillar Distributions</div>",
                unsafe_allow_html=True)
    d_cols = st.columns(4)
    for col_ui,(pillar,color) in zip(d_cols, PILLAR_COLORS.items()):
        nc = NORM_COL[pillar]
        if nc not in df.columns: continue
        col_ui.markdown(
            f"<div style='font-family:Syne;font-weight:800;color:{color};"
            f"font-size:13px;margin-bottom:4px;'>{PILLAR_ICONS[pillar]} {pillar}</div>",
            unsafe_allow_html=True,
        )
        col_ui.plotly_chart(
            dist_chart(df, nc, color),
            use_container_width=True,
            key=f"tab3_dist_{pillar}",
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='section-header'>Top 10 per Pillar</div>",
                unsafe_allow_html=True)
    p_cols = st.columns(2)
    for idx,(pillar,color) in enumerate(PILLAR_COLORS.items()):
        nc = NORM_COL[pillar]
        if nc not in df.columns: continue
        with p_cols[idx % 2]:
            st.markdown(
                f"<div style='font-family:Syne;font-weight:800;color:{color};"
                f"font-size:15px;margin:10px 0 6px;'>"
                f"{PILLAR_ICONS[pillar]} {pillar}</div>",
                unsafe_allow_html=True,
            )
            st.plotly_chart(
                pillar_bar(df, nc, color),
                use_container_width=True,
                key=f"tab3_bar_{pillar}",
            )


# ══════════════════════════════════════════════
# TAB 4 — PLAYER PROFILE
# ══════════════════════════════════════════════
with tab4:
    st.markdown("<div class='section-header'>Player Profile</div>", unsafe_allow_html=True)

    selected = st.selectbox("Select a player", df["Player"].tolist(), key="profile_player")
    row  = df[df["Player"] == selected].iloc[0]
    rank = int(row["Rank"])

    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#1565c0 0%,#0288d1 100%);
                border-radius:14px;padding:24px 28px;margin-bottom:22px;color:white;'>
        <div style='display:flex;align-items:center;gap:20px;flex-wrap:wrap;'>
            <div style='font-family:Syne;font-size:48px;font-weight:800;
                        opacity:0.25;line-height:1;'>#{rank}</div>
            <div>
                <div style='font-family:Syne;font-size:26px;font-weight:800;
                            letter-spacing:1px;'>{row['Player']}</div>
                <div style='font-size:13px;opacity:0.8;margin-top:3px;'>{row['Team']}</div>
            </div>
            <div style='margin-left:auto;text-align:right;'>
                <div style='font-family:Syne;font-size:44px;font-weight:800;
                            line-height:1;'>{row['WBI Score']:.3f}</div>
                <div style='font-size:11px;opacity:0.7;letter-spacing:1.5px;'>WBI SCORE</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_r, col_b = st.columns([1,1])
    with col_r:
        st.plotly_chart(
            radar_chart(row, f"{selected}", "#1565c0"),
            use_container_width=True,
            key=f"tab4_radar_{selected}",
        )
    with col_b:
        st.markdown("**Pillar Breakdown**")
        for pillar in PILLAR_COLORS:
            nc  = NORM_COL[pillar]
            rc  = RAW_COL[pillar]
            if nc not in df.columns: continue
            color    = PILLAR_COLORS[pillar]
            light    = PILLAR_LIGHT[pillar]
            raw_val  = row[rc]
            norm_val = row[nc]
            pct      = norm_val * 100
            w_pct    = weights[pillar]
            st.markdown(f"""
            <div style='margin-bottom:16px;'>
                <div style='display:flex;justify-content:space-between;
                            font-size:13px;margin-bottom:5px;'>
                    <span style='color:{color};font-weight:700;font-family:Syne;'>
                        {PILLAR_ICONS[pillar]} {pillar}
                        <span style='font-size:11px;font-weight:400;color:#78909c;'>
                            (weight {w_pct:.0%})</span>
                    </span>
                    <span style='color:#4a6080;'>
                        {raw_val:.3f} raw &nbsp;·&nbsp;
                        <b style='color:{color};'>{norm_val:.3f}</b> norm
                    </span>
                </div>
                <div style='background:#e9eef4;border-radius:6px;height:10px;overflow:hidden;'>
                    <div style='background:{color};width:{pct:.1f}%;height:100%;
                                border-radius:6px;'></div>
                </div>
                <div style='font-size:11px;color:#78909c;margin-top:3px;'>
                    {PILLAR_DESCRIPTIONS[pillar]['subtitle']}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Season breakdown
    st.markdown("<div class='section-header'>Season-by-Season Stats</div>",
                unsafe_allow_html=True)
    rows_out = []
    for sdf in seasons:
        p = sdf[sdf["Player"] == selected]
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
        st.info(f"No season data found for {selected}.")


# ══════════════════════════════════════════════
# TAB 5 — COMPARE
# ══════════════════════════════════════════════
with tab5:
    st.markdown("<div class='section-header'>Compare Players</div>", unsafe_allow_html=True)

    sel_compare = st.multiselect(
        "Select 2–5 players",
        options=df["Player"].tolist(),
        default=df["Player"].head(3).tolist(),
        max_selections=5,
        key="compare_players",
    )

    if len(sel_compare) < 2:
        st.info("Select at least 2 players to compare.")
    else:
        c_rows = [df[df["Player"]==p].iloc[0] for p in sel_compare]

        col_ra, col_ba = st.columns([1,1])
        with col_ra:
            st.plotly_chart(
                compare_radar(c_rows, sel_compare),
                use_container_width=True,
                key="tab5_radar",
            )
        with col_ba:
            p_colors_list = ["#1565c0","#00838f","#6a1b9a","#c62828","#e65100"]
            fig_cmp = go.Figure()
            valid_pillars = [p for p in PILLAR_COLORS if NORM_COL[p] in df.columns]
            for i,(cr,name) in enumerate(zip(c_rows, sel_compare)):
                fig_cmp.add_trace(go.Bar(
                    name=name,
                    x=valid_pillars,
                    y=[cr[NORM_COL[p]] for p in valid_pillars],
                    marker_color=p_colors_list[i % len(p_colors_list)],
                    text=[f"{cr[NORM_COL[p]]:.3f}" for p in valid_pillars],
                    textposition="outside",
                ))
            fig_cmp.update_layout(
                **PLOT_BG, barmode="group",
                yaxis=dict(range=[0,1.2], gridcolor="#d9e2ec", title="Norm Score"),
                xaxis=dict(gridcolor="#d9e2ec"),
                legend=dict(bgcolor="rgba(255,255,255,0.9)",
                            bordercolor="#d9e2ec", borderwidth=1),
                height=360, margin=dict(l=20,r=20,t=20,b=20),
            )
            st.plotly_chart(fig_cmp, use_container_width=True, key="tab5_bar")

        st.markdown("<div class='section-header'>Summary Table</div>",
                    unsafe_allow_html=True)
        tbl = pd.DataFrame([{
            "Player":r["Player"], "Team":r["Team"], "Rank":int(r["Rank"]),
            "WBI Score":round(r["WBI Score"],4),
            **{f"{p} (N)": round(r[NORM_COL[p]],4) for p in PILLAR_COLORS if NORM_COL[p] in df.columns}
        } for r in c_rows])
        st.dataframe(tbl, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════
# TAB 6 — FULL DATA
# ══════════════════════════════════════════════
with tab6:
    st.markdown("<div class='section-header'>Full Rankings Table</div>",
                unsafe_allow_html=True)

    all_teams = sorted(df["Team"].dropna().unique().tolist())
    sel_teams = st.multiselect("Filter by team", all_teams, default=all_teams,
                               key="full_data_teams")
    filtered  = df[df["Team"].isin(sel_teams)].copy()

    display_cols = [c for c in [
        "Rank","Player","Team",
        "Quality (Raw)","Consistency (Raw)","Participation (Raw)","Dominance (Raw)",
        "Quality (Norm)","Consistency (Norm)","Participation (Norm)","Dominance (Norm)",
        "WBI Score",
    ] if c in filtered.columns]

    st.dataframe(
        filtered[display_cols].round(4),
        use_container_width=True, hide_index=True, height=500,
    )

    st.download_button(
        "⬇  Download as CSV",
        data=filtered[display_cols].round(4).to_csv(index=False),
        file_name="wbi_rankings.csv",
        mime="text/csv",
    )

    st.markdown(
        "<div class='info-box'>Rankings recompute live whenever you adjust the "
        "pillar weights in the sidebar. Download saves the current weight configuration.</div>",
        unsafe_allow_html=True,
    )