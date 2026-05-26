# =============================================================================
# data_quality_report.py
# =============================================================================
# Purpose : Runs a structured data-quality audit on tbl_analytics.csv and
#           surfaces issues a recruiter or stakeholder would care about:
#           null rates, value distributions, numeric summaries, and outliers.
#
# Input   : tbl_analytics.csv  (produced by etl_pipeline.py)
# Output  : data_quality_summary.txt  (in the same directory)
#
# Run     : python data_quality_report.py   (after etl_pipeline.py)
# =============================================================================

import os
import sys
import io
import numpy as np
import pandas as pd

# Force UTF-8 output on Windows terminals
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    from colorama import init as colorama_init, Fore, Style
    colorama_init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    print("[INFO] colorama not installed — output will be plain text.")
    print("       Install with:  pip install colorama\n")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE_DIR, "tbl_analytics.csv")
REPORT_FILE= os.path.join(BASE_DIR, "data_quality_summary.txt")

NULL_FLAG_THRESHOLD  = 5.0    # % above which nulls are highlighted red
REVENUE_OUTLIER_PCT  = 99     # percentile threshold for revenue outliers
SHIP_DAYS_OUTLIER    = 30     # days threshold for shipping outlier flag

# ---------------------------------------------------------------------------
# Color helpers (gracefully degrade if colorama absent)
# ---------------------------------------------------------------------------

def red(text: str) -> str:
    return f"{Fore.RED}{text}{Style.RESET_ALL}" if HAS_COLOR else text

def green(text: str) -> str:
    return f"{Fore.GREEN}{text}{Style.RESET_ALL}" if HAS_COLOR else text

def yellow(text: str) -> str:
    return f"{Fore.YELLOW}{text}{Style.RESET_ALL}" if HAS_COLOR else text

def cyan(text: str) -> str:
    return f"{Fore.CYAN}{text}{Style.RESET_ALL}" if HAS_COLOR else text

def bold(text: str) -> str:
    return f"{Style.BRIGHT}{text}{Style.RESET_ALL}" if HAS_COLOR else text


def banner(text: str) -> str:
    line = "─" * 60
    return f"\n{line}\n  {text}\n{line}"


# ---------------------------------------------------------------------------
# Helpers for the plain-text report (no ANSI codes)
# ---------------------------------------------------------------------------

def plain_banner(text: str) -> str:
    line = "─" * 60
    return f"\n{line}\n  {text}\n{line}"


# Collect all report lines in plain text for the .txt file
_report_lines: list[str] = []

def log(console_text: str, plain_text: str | None = None) -> None:
    """Print with color to console; append plain version to report buffer."""
    print(console_text)
    _report_lines.append(plain_text if plain_text is not None else console_text)


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

print(banner("DATA QUALITY REPORT — tbl_analytics"))
_report_lines.append(plain_banner("DATA QUALITY REPORT — tbl_analytics"))

if not os.path.exists(INPUT_FILE):
    print(red(f"  [ERROR] {INPUT_FILE} not found. Run etl_pipeline.py first."))
    sys.exit(1)

print(f"  Loading {INPUT_FILE} …")
df = pd.read_csv(INPUT_FILE, low_memory=False)

# ---------------------------------------------------------------------------
# Section 1 — Shape
# ---------------------------------------------------------------------------

section1 = banner("SECTION 1 — Dataset Shape")
print(section1)
_report_lines.append(plain_banner("SECTION 1 — Dataset Shape"))

shape_line = f"  Total rows   : {len(df):>10,}\n  Total columns: {df.shape[1]:>10}"
log(bold(shape_line), shape_line)

# ---------------------------------------------------------------------------
# Section 2 — Null % per column
# ---------------------------------------------------------------------------

section2_hdr = banner("SECTION 2 — Null % per Column (red = above 5%)")
print(section2_hdr)
_report_lines.append(plain_banner("SECTION 2 — Null % per Column (> 5% flagged)"))

null_pct = (df.isnull().sum() / len(df) * 100).round(2).sort_values(ascending=False)

for col, pct in null_pct.items():
    bar = "█" * int(pct / 2)
    line_plain = f"  {col:<40} {pct:>6.2f}%  {bar}"
    if pct > NULL_FLAG_THRESHOLD:
        print(red(f"  {col:<40} {pct:>6.2f}%  {bar}"))
    elif pct > 0:
        print(yellow(f"  {col:<40} {pct:>6.2f}%  {bar}"))
    else:
        print(green(f"  {col:<40} {pct:>6.2f}%  {bar}"))
    _report_lines.append(line_plain)

# ---------------------------------------------------------------------------
# Section 3 — Value Counts
# ---------------------------------------------------------------------------

section3_hdr = banner("SECTION 3 — Value Counts for Categorical Columns")
print(section3_hdr)
_report_lines.append(plain_banner("SECTION 3 — Value Counts for Categorical Columns"))

cat_cols = ["order_status", "Delivery_Speed_Bucket", "Satisfaction_Label", "payment_type"]

for col in cat_cols:
    if col not in df.columns:
        log(yellow(f"  [SKIP] Column '{col}' not found."), f"  [SKIP] Column '{col}' not found.")
        continue

    print(cyan(f"\n  {col}:"))
    _report_lines.append(f"\n  {col}:")

    vc = df[col].value_counts(dropna=False)
    total = len(df)
    for val, cnt in vc.items():
        pct = cnt / total * 100
        row_plain = f"    {str(val):<30} {cnt:>8,}  ({pct:>5.1f}%)"
        print(row_plain)
        _report_lines.append(row_plain)

# ---------------------------------------------------------------------------
# Section 4 — Numeric Summaries
# ---------------------------------------------------------------------------

section4_hdr = banner("SECTION 4 — Numeric Summaries")
print(section4_hdr)
_report_lines.append(plain_banner("SECTION 4 — Numeric Summaries"))

num_cols = ["Total_Revenue", "Total_Delivery_Days", "Days_To_Ship", "review_score"]
stats_labels = ["min", "max", "mean", "median"]

header = f"  {'Column':<25} {'Min':>10} {'Max':>10} {'Mean':>10} {'Median':>10}"
print(bold(header))
_report_lines.append(header)
print("  " + "─" * 65)
_report_lines.append("  " + "─" * 65)

for col in num_cols:
    if col not in df.columns:
        log(yellow(f"  [SKIP] '{col}' not found."), f"  [SKIP] '{col}' not found.")
        continue
    s = df[col].dropna()
    row = (
        f"  {col:<25}"
        f" {s.min():>10.2f}"
        f" {s.max():>10.2f}"
        f" {s.mean():>10.2f}"
        f" {s.median():>10.2f}"
    )
    print(row)
    _report_lines.append(row)

# ---------------------------------------------------------------------------
# Section 5 — Outlier Detection
# ---------------------------------------------------------------------------

section5_hdr = banner("SECTION 5 — Outlier Detection")
print(section5_hdr)
_report_lines.append(plain_banner("SECTION 5 — Outlier Detection"))

# Revenue outliers
if "Total_Revenue" in df.columns:
    rev_threshold = df["Total_Revenue"].quantile(REVENUE_OUTLIER_PCT / 100)
    rev_outliers = df[df["Total_Revenue"] > rev_threshold]
    rev_line = (
        f"  Total_Revenue > 99th percentile (threshold = R$ {rev_threshold:,.2f}): "
        f"{len(rev_outliers):,} orders  ({len(rev_outliers)/len(df)*100:.2f}%)"
    )
    print(red(rev_line) if len(rev_outliers) > 0 else green(rev_line))
    _report_lines.append(rev_line)

# Days_To_Ship outliers
if "Days_To_Ship" in df.columns:
    ship_outliers = df[df["Days_To_Ship"] > SHIP_DAYS_OUTLIER]
    ship_line = (
        f"  Days_To_Ship > {SHIP_DAYS_OUTLIER} days: "
        f"{len(ship_outliers):,} orders  ({len(ship_outliers)/len(df)*100:.2f}%)"
    )
    print(red(ship_line) if len(ship_outliers) > 0 else green(ship_line))
    _report_lines.append(ship_line)

# Negative Days_To_Ship (data integrity check)
if "Days_To_Ship" in df.columns:
    neg_ship = df[df["Days_To_Ship"] < 0]
    neg_line = f"  Negative Days_To_Ship (timestamp anomaly): {len(neg_ship):,} orders"
    print(red(neg_line) if len(neg_ship) > 0 else green(neg_line))
    _report_lines.append(neg_line)

# Late orders
if "Is_Late" in df.columns:
    late_orders = df[df["Is_Late"] == 1]
    late_line = (
        f"  Late orders (Is_Late = 1): "
        f"{len(late_orders):,}  ({len(late_orders)/len(df)*100:.2f}%)"
    )
    print(yellow(late_line))
    _report_lines.append(late_line)

# ---------------------------------------------------------------------------
# Section 6 — Duplicate Check
# ---------------------------------------------------------------------------

section6_hdr = banner("SECTION 6 — Duplicate order_id Check")
print(section6_hdr)
_report_lines.append(plain_banner("SECTION 6 — Duplicate order_id Check"))

if "order_id" in df.columns:
    dup_count = df["order_id"].duplicated().sum()
    dup_line = f"  Duplicate order_id rows: {dup_count:,}"
    print(red(dup_line) if dup_count > 0 else green(dup_line))
    _report_lines.append(dup_line)

# ---------------------------------------------------------------------------
# Save report to file
# ---------------------------------------------------------------------------

save_banner = banner("Saving report …")
print(save_banner)
_report_lines.append(plain_banner("Report saved"))

try:
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(_report_lines))
    print(f"  Saved → {REPORT_FILE}")
except Exception as exc:
    print(red(f"  [ERROR] Could not save report: {exc}"))

print(f"\n  Data quality report complete.\n")
