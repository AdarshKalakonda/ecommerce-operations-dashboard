# =============================================================================
# build_date_table.py
# =============================================================================
# Purpose : Generates a complete date-dimension table (tbl_dates.csv) covering
#           the full Olist dataset window: 2016-09-01 → 2018-10-31.
#           This table is used as the time spine in Power BI / Tableau / etc.
#
# Output  : tbl_dates.csv  (in the same directory as this script)
#
# Run     : python build_date_table.py
# =============================================================================

import os
import sys
import io
import pandas as pd

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "tbl_dates.csv")

START_DATE = "2016-09-01"
END_DATE   = "2018-10-31"

print(f"\n  Generating date dimension: {START_DATE} to {END_DATE} ...")

dates = pd.date_range(start=START_DATE, end=END_DATE, freq="D")
df = pd.DataFrame({"Date": dates})

df["Year"]          = df["Date"].dt.year
df["Month_Num"]     = df["Date"].dt.month
df["Month_Name"]    = df["Date"].dt.strftime("%B")
df["Quarter"]       = df["Date"].dt.quarter
df["Quarter_Label"] = "Q" + df["Quarter"].astype(str) + " " + df["Year"].astype(str)
df["Week_Num"]      = df["Date"].dt.isocalendar().week.astype(int)
df["Day_Name"]      = df["Date"].dt.strftime("%A")
df["Day_Num"]       = df["Date"].dt.day
df["Is_Weekend"]    = df["Date"].dt.dayofweek.isin([5, 6]).astype(int)
df["Is_Month_Start"]= df["Date"].dt.is_month_start.astype(int)
df["Is_Month_End"]  = df["Date"].dt.is_month_end.astype(int)

# Format Date column as a clean string for BI tools
df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")

df.to_csv(OUTPUT_FILE, index=False)

print(f"  Rows generated : {len(df):,}")
print(f"  Saved → {OUTPUT_FILE}")
print(f"\n  Date dimension table complete.\n")
