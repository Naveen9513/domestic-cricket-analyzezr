"""
Cricket Weighted Batting Index (WBI) Calculator
================================================
Computes a composite ranking score across 3 domestic cricket seasons.

Usage:
    python cricket_wbi.py   (file names are configured below in FILE CONFIG)

Output:
    wbi_rankings.csv  — all players ranked by WBI with raw + normalized pillar scores

Pillar summary:
    P1 Quality       (40%) — √(innings-weighted avg × total runs)
                             Geometric mean that rewards both average AND volume.
                             A fluky high average over 2 innings is pulled down
                             hard by the low total-runs term.
    P2 Consistency   (25%) — Quality-weighted inverted CV of season averages.
                             Consistent mediocrity is penalised via quality_norm.
    P3 Participation (10%) — (matches + innings) ratio vs dataset maximum.
                             Weight raised to counter small-sample bias.
    P4 Dominance     (25%) — Mean Z-score vs season peers.
"""

import pandas as pd
import numpy as np


# ─────────────────────────────────────────────
# 0. FILE CONFIG  ← edit these paths
# ─────────────────────────────────────────────
SEASON1_FILE  = "data/major_league_batting_stats_2023.csv"
SEASON2_FILE  = "data/major_league_batting_stats_2024.csv"
SEASON3_FILE  = "data/major_league_batting_stats_2025.csv"
OUTPUT_FILE   = "data/wbi_rankings.csv"


# ─────────────────────────────────────────────
# 1. WEIGHTS CONFIG
# ─────────────────────────────────────────────
WEIGHTS = {
    "quality":       0.40,   # was 0.30 — absorbs the old volume pillar
    "consistency":   0.20,
    "participation": 0.25,   # was 0.15 — raised to counter small-sample bias
    "dominance":     0.15,
}

REQUIRED_COLS = {"Player", "Team", "Matches", "Innings", "Runs", "Average",
                 "Strike Rate", "100s", "50s", "High Score"}

MIN_INNINGS = 10  # minimum total innings across all seasons to include a player in the WBI analysis

# ─────────────────────────────────────────────
# 2. LOAD & VALIDATE
# ─────────────────────────────────────────────
def load_season(path: str, season_label: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"[{season_label}] Missing columns: {missing}")

    numeric_cols = ["Matches", "Innings", "Runs", "Average", "Strike Rate",
                    "100s", "50s", "High Score"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Season"] = season_label
    df["Player"] = df["Player"].str.strip()
    return df


def apply_min_innings_filter(seasons: list[pd.DataFrame], min_innings: int) -> list[pd.DataFrame]:
    if min_innings <= 0:
        return seasons

    combined = pd.concat(
        [df[["Player", "Innings"]].copy() for df in seasons],
        ignore_index=True,
    ).dropna(subset=["Player", "Innings"])

    eligible = (
        combined.groupby("Player")["Innings"]
        .sum()
        .loc[lambda totals: totals >= min_innings]
        .index
    )

    return [df[df["Player"].isin(eligible)].copy() for df in seasons]


# ─────────────────────────────────────────────
# 3. MIN-MAX NORMALISATION  (0 → 1)
# ─────────────────────────────────────────────
def minmax(series: pd.Series) -> pd.Series:
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series(0.5, index=series.index)
    return (series - lo) / (hi - lo)


# ─────────────────────────────────────────────
# 4. PILLAR CALCULATIONS
# ─────────────────────────────────────────────

# --- P1: QUALITY  geometric mean of innings-weighted avg and total runs ---
def calc_quality(seasons: list[pd.DataFrame]) -> pd.Series:
    """
    Step 1 — Innings-weighted average across all seasons:
                weighted_avg = Σ(Avg_s × Inn_s) / Σ(Inn_s)

    Step 2 — Total runs across all seasons:
                total_runs = Σ(Runs_s)

    Step 3 — Geometric mean:
                quality_raw = √(weighted_avg × total_runs)

    Why geometric mean?
        - It rewards BOTH high average AND high volume simultaneously.
        - A player with 2 innings and avg=80 has total_runs ≈ 160
          → quality = √(80 × 160) = 113
        - A player with 20 innings, avg=50, total_runs=1000
          → quality = √(50 × 1000) = 224   ← correctly ranked higher
        - Neither metric alone can dominate the result.
    """
    combined = pd.concat(
        [df[["Player", "Average", "Innings", "Runs"]].copy() for df in seasons],
        ignore_index=True
    ).dropna(subset=["Average", "Innings", "Runs"])

    combined["weighted_avg"] = combined["Average"] * combined["Innings"]

    grp = combined.groupby("Player").agg(
        total_weighted=("weighted_avg", "sum"),
        total_innings=("Innings",       "sum"),
        total_runs=   ("Runs",          "sum"),
    )

    grp["innings_weighted_avg"] = grp["total_weighted"] / grp["total_innings"]

    # Geometric mean — sqrt of the product
    grp["quality_raw"] = np.sqrt(grp["innings_weighted_avg"] * grp["total_runs"])

    return grp["quality_raw"]


# --- P2: CONSISTENCY  quality-weighted inverted CV of season averages ---
def calc_consistency(seasons: list[pd.DataFrame], quality_norm: pd.Series) -> pd.Series:
    """
    Step 1 — CV = std(Avg across seasons) / mean(Avg across seasons) × 100
    Step 2 — consistency_raw = 1 / (1 + CV)      range (0,1]; higher = more consistent
    Step 3 — quality_weighted = consistency_raw × quality_norm
              Multiplying by quality_norm (0-1) ensures that a player who is
              consistently mediocre (low avg, low CV) is penalised relative to
              a player who is consistently excellent (high avg, low CV).
    Players appearing in only 1 season get CV = 0 — participation pillar
    penalises the absence separately.
    Duplicate player names within a season are averaged before pivoting.
    """
    avg_per_season = []
    for i, df in enumerate(seasons, 1):
        tmp = (
            df[["Player", "Average"]]
            .dropna(subset=["Average"])
            .groupby("Player", as_index=False)["Average"]
            .mean()
            .rename(columns={"Average": f"avg_s{i}"})
            .set_index("Player")
        )
        avg_per_season.append(tmp)

    wide = pd.concat(avg_per_season, axis=1)

    mean_avg = wide.mean(axis=1)
    std_avg  = wide.std(axis=1, ddof=0)

    cv = (std_avg / mean_avg.replace(0, np.nan)) * 100
    cv = cv.fillna(0)

    consistency_raw = 1 / (1 + cv)

    quality_norm_aligned = quality_norm.reindex(consistency_raw.index).fillna(0)
    consistency_quality_weighted = consistency_raw * quality_norm_aligned

    return consistency_quality_weighted.rename("consistency_raw")


# --- P3: PARTICIPATION  matches + innings vs dataset maximum ---
def calc_participation(seasons: list[pd.DataFrame]) -> pd.Series:
    """
    Participation = 0.5 × (total_matches / max_matches)
                  + 0.5 × (total_innings / max_innings)
    max_matches and max_innings are the highest values recorded by any player
    across all seasons — the natural ceiling for this dataset.
    """
    total_matches = pd.concat(
        [df[["Player", "Matches"]] for df in seasons]
    ).groupby("Player")["Matches"].sum()

    total_innings = pd.concat(
        [df[["Player", "Innings"]] for df in seasons]
    ).groupby("Player")["Innings"].sum()

    part_raw = (
        0.5 * (total_matches / total_matches.max()) +
        0.5 * (total_innings / total_innings.max())
    )
    return part_raw.rename("participation_raw")


# --- P4: DOMINANCE  mean Z-score vs season peers ---
def calc_dominance(seasons: list[pd.DataFrame]) -> pd.Series:
    """
    For each season:
        Z = (player_avg − season_mean_avg) / season_std_avg
    Dominance_raw = mean of Z-scores across all seasons the player appeared in.
    Players missing a season are excluded from that season's Z calculation
    rather than penalised with Z=0 (participation handles absence separately).
    Duplicate players within a season are averaged before Z is computed.
    """
    z_frames = []
    for i, df in enumerate(seasons, 1):
        tmp = (
            df[["Player", "Average"]]
            .dropna(subset=["Average"])
            .groupby("Player", as_index=False)["Average"]
            .mean()
        )
        season_mean = tmp["Average"].mean()
        season_std  = tmp["Average"].std(ddof=0)

        tmp[f"z_s{i}"] = (
            0.0 if season_std == 0
            else (tmp["Average"] - season_mean) / season_std
        )
        z_frames.append(tmp[["Player", f"z_s{i}"]].set_index("Player"))

    wide_z = pd.concat(z_frames, axis=1)
    return wide_z.mean(axis=1).rename("dominance_raw")


# ─────────────────────────────────────────────
# 5. ASSEMBLE & RANK
# ─────────────────────────────────────────────
def build_wbi(seasons: list[pd.DataFrame]) -> pd.DataFrame:

    # P1 quality norm is needed early — P2 consistency uses it as a multiplier
    quality      = calc_quality(seasons)
    quality_norm = minmax(quality)

    consistency   = calc_consistency(seasons, quality_norm)
    participation = calc_participation(seasons)
    dominance     = calc_dominance(seasons)

    # Merge all pillars (no volume pillar)
    result = (
        quality.to_frame()
        .join(consistency,    how="outer")
        .join(participation,  how="outer")
        .join(dominance,      how="outer")
    )

    # Attach team from most recent season available
    all_players = (
        pd.concat(seasons)[["Player", "Team"]]
        .drop_duplicates("Player", keep="last")
    )
    result = result.merge(all_players, on="Player", how="left")

    raw_cols = ["quality_raw", "consistency_raw", "participation_raw", "dominance_raw"]
    result[raw_cols] = result[raw_cols].fillna(0)

    # Normalised scores (re-apply minmax on merged result for consistency)
    result["quality_norm"]       = minmax(result["quality_raw"])
    result["consistency_norm"]   = minmax(result["consistency_raw"])
    result["participation_norm"] = minmax(result["participation_raw"])
    result["dominance_norm"]     = minmax(result["dominance_raw"])

    # WBI composite
    result["WBI"] = (
        WEIGHTS["quality"]       * result["quality_norm"] +
        WEIGHTS["consistency"]   * result["consistency_norm"] +
        WEIGHTS["participation"] * result["participation_norm"] +
        WEIGHTS["dominance"]     * result["dominance_norm"]
    )

    result = result.sort_values("WBI", ascending=False).reset_index()
    result.insert(0, "Rank", range(1, len(result) + 1))
    return result


# ─────────────────────────────────────────────
# 6. FORMAT OUTPUT CSV
# ─────────────────────────────────────────────
def format_output(df: pd.DataFrame) -> pd.DataFrame:
    cols = {
        "Rank":               "Rank",
        "Player":             "Player",
        "Team":               "Team",

        # Raw (not normalised)
        "quality_raw":        "Quality (Raw)",
        "consistency_raw":    "Consistency Quality-Weighted (Raw)",
        "participation_raw":  "Participation (Raw)",
        "dominance_raw":      "Dominance (Raw)",

        # Normalised (0-1)
        "quality_norm":       "Quality (Norm)",
        "consistency_norm":   "Consistency Quality-Weighted (Norm)",
        "participation_norm": "Participation (Norm)",
        "dominance_norm":     "Dominance (Norm)",

        "WBI":                "WBI Score",
    }
    out = df[list(cols.keys())].rename(columns=cols)

    round4_cols = [
        "Quality (Raw)",
        "Consistency Quality-Weighted (Raw)",
        "Participation (Raw)",
        "Dominance (Raw)",
        "Quality (Norm)",
        "Consistency Quality-Weighted (Norm)",
        "Participation (Norm)",
        "Dominance (Norm)",
        "WBI Score",
    ]
    out[round4_cols] = out[round4_cols].round(4)
    return out


# ─────────────────────────────────────────────
# 7. MAIN
# ─────────────────────────────────────────────
def main():
    paths  = [SEASON1_FILE, SEASON2_FILE, SEASON3_FILE]
    labels = ["Season 1", "Season 2", "Season 3"]

    print("Loading season files...")
    seasons = [load_season(p, l) for p, l in zip(paths, labels)]
    for label, df in zip(labels, seasons):
        dupes = df[df.duplicated("Player", keep=False)]["Player"].unique()
        if len(dupes) > 0:
            print(f"  WARNING  {label}: duplicate player names found "
                  f"(will be averaged): {list(dupes)}")
        print(f"  {label}: {len(df)} rows loaded "
              f"({df['Player'].nunique()} unique players)")

    if MIN_INNINGS > 0:
        print(f"\nApplying minimum innings filter: {MIN_INNINGS} total innings across all seasons")
        before = set(pd.concat(seasons)["Player"].dropna().unique())
        seasons = apply_min_innings_filter(seasons, MIN_INNINGS)
        after = set(pd.concat(seasons)["Player"].dropna().unique())
        dropped = len(before - after)
        print(f"  {dropped} players dropped by innings filter")

    print("\nCalculating WBI pillars...")
    wbi_df = build_wbi(seasons)

    print("\nFormatting output...")
    output = format_output(wbi_df)

    output.to_csv(OUTPUT_FILE, index=False)

    print(f"\nDone! Results saved to: {OUTPUT_FILE}")
    print(f"   Total players ranked: {len(output)}")
    print(f"\n{'─'*60}")
    print("TOP 10 PLAYERS")
    print(f"{'─'*60}")
    print(output.head(10)[["Rank", "Player", "Team", "WBI Score"]].to_string(index=False))


if __name__ == "__main__":
    main()