import json
import csv
from pathlib import Path

# ==========================================
# CONFIGURATION
# ==========================================

INPUT_JSON_FILE = "2025-batting.json"
OUTPUT_CSV_FILE = "major_league_batting_stats_2025.csv"

# CSV Header -> JSON Field mapping
# Only fields defined here will be exported
FIELD_MAPPING = {
    "Player": "StrikerName",
    "Team": "TeamName",
    "Matches": "Matches",
    "Innings": "Innings",
    "Runs": "TotalRuns",
    "Average": "BattingAverage",
    "Strike Rate": "StrikeRate",
    "100s": "Centuries",
    "50s": "FiftyPlusRuns",
    "High Score": "HighestScore"
}

# ==========================================
# LOAD JSON
# ==========================================

with open(INPUT_JSON_FILE, "r", encoding="utf-8") as f:
    raw_data = json.load(f)

data = raw_data["toprunsscorers"]  # Adjust this key if your JSON structure is different
# ==========================================
# WRITE CSV
# ==========================================

csv_headers = list(FIELD_MAPPING.keys())

with open(OUTPUT_CSV_FILE, "w", newline="", encoding="utf-8") as csv_file:
    writer = csv.writer(csv_file)

    # Write headers
    writer.writerow(csv_headers)

    # Write data rows
    for item in data:
        row = []

        for header, json_key in FIELD_MAPPING.items():
            value = item.get(json_key, "")

            if value is None:
                value = ""

            row.append(value)

        writer.writerow(row)

print(f"CSV created: {Path(OUTPUT_CSV_FILE).resolve()}")