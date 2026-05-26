# =============================================================================
# insights_preview.py
# =============================================================================
# Purpose : Generates 10 business insights from tbl_analytics.csv, prints a
#           human-readable summary, saves insights_preview.txt, and exports
#           10 publication-ready PNG charts to a /charts subfolder.
#
# Input   : tbl_analytics.csv  (produced by etl_pipeline.py)
# Output  : insights_preview.txt
#           charts/01_top_states_by_volume.png  … charts/10_speed_bucket.png
#
# Run     : python insights_preview.py   (after etl_pipeline.py)
# =============================================================================

import os
import sys
import io
import textwrap
import numpy as np

# Force UTF-8 output on Windows terminals
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy import stats as sp_stats

matplotlib.use("Agg")   # non-interactive backend — safe for all environments

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE  = os.path.join(BASE_DIR, "tbl_analytics.csv")
REPORT_FILE = os.path.join(BASE_DIR, "insights_preview.txt")
CHARTS_DIR  = os.path.join(BASE_DIR, "charts")

os.makedirs(CHARTS_DIR, exist_ok=True)

plt.style.use("dark_background")

ACCENT   = "#00D4FF"    # bright cyan for bars
ACCENT2  = "#FF6B6B"    # coral for secondary series
ACCENT3  = "#FFD700"    # gold for annotations
BG       = "#0D1117"    # chart background
GRID_CLR = "#2D3139"    # subtle gridlines

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def banner(text: str) -> None:
    print(f"\n{'─' * 60}\n  {text}\n{'─' * 60}")


banner("INSIGHTS PREVIEW — Loading tbl_analytics.csv")

if not os.path.exists(INPUT_FILE):
    print(f"[ERROR] {INPUT_FILE} not found. Run etl_pipeline.py first.")
    sys.exit(1)

df = pd.read_csv(INPUT_FILE, low_memory=False)
print(f"  Loaded {len(df):,} rows × {df.shape[1]} columns")

# ---------------------------------------------------------------------------
# Chart boilerplate
# ---------------------------------------------------------------------------

def new_fig(title: str, figsize=(12, 6)):
    fig, ax = plt.subplots(figsize=figsize, facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_title(title, fontsize=14, fontweight="bold", color="white", pad=15)
    ax.tick_params(colors="white", labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRID_CLR)
    ax.spines["bottom"].set_color(GRID_CLR)
    ax.yaxis.grid(True, color=GRID_CLR, linewidth=0.6, linestyle="--")
    ax.set_axisbelow(True)
    return fig, ax


def annotate_bars(ax, fmt="{:.0f}", color=ACCENT3, fontsize=8):
    for bar in ax.patches:
        h = bar.get_height()
        if h == 0 or np.isnan(h):
            continue
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            h * 1.01,
            fmt.format(h),
            ha="center", va="bottom",
            fontsize=fontsize, color=color, fontweight="bold",
        )


def save_chart(fig, filename: str) -> None:
    path = os.path.join(CHARTS_DIR, filename)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  Chart saved → charts/{filename}")


# ---------------------------------------------------------------------------
# Report buffer
# ---------------------------------------------------------------------------

_lines: list[str] = []

def log(text: str) -> None:
    print(text)
    _lines.append(text)


def section(title: str) -> None:
    hdr = f"\n{'═' * 60}\n  {title}\n{'═' * 60}"
    print(hdr)
    _lines.append(hdr)


# ---------------------------------------------------------------------------
# Insight 1 — Top 5 states by order volume + avg review score
# ---------------------------------------------------------------------------

section("INSIGHT 1 — Top 5 States by Order Volume + Avg Review Score")

if "customer_state" in df.columns:
    state_vol = (
        df.groupby("customer_state", as_index=False)
          .agg(
              Order_Volume = ("order_id",    "count"),
              Avg_Review   = ("review_score","mean"),
          )
          .sort_values("Order_Volume", ascending=False)
          .head(5)
    )
    state_vol["Avg_Review"] = state_vol["Avg_Review"].round(2)
    log(state_vol.to_string(index=False))

    fig, ax1 = new_fig("Top 5 States — Order Volume & Avg Review Score")
    ax2 = ax1.twinx()

    x      = range(len(state_vol))
    bars   = ax1.bar(x, state_vol["Order_Volume"], color=ACCENT, alpha=0.85, width=0.5, label="Order Volume")
    line,  = ax2.plot(x, state_vol["Avg_Review"], color=ACCENT2, marker="o", linewidth=2, markersize=8, label="Avg Review Score")

    ax1.set_xticks(x)
    ax1.set_xticklabels(state_vol["customer_state"], color="white")
    ax1.set_xlabel("State", color="white")
    ax1.set_ylabel("Order Volume", color=ACCENT)
    ax2.set_ylabel("Avg Review Score", color=ACCENT2)
    ax2.set_ylim(0, 5.5)
    ax2.tick_params(colors="white")
    ax2.spines["right"].set_color(GRID_CLR)

    annotate_bars(ax1, fmt="{:,.0f}")
    for xi, yi in zip(x, state_vol["Avg_Review"]):
        ax2.text(xi, yi + 0.1, f"{yi:.2f}", ha="center", va="bottom",
                 fontsize=8, color=ACCENT3, fontweight="bold")

    ax1.legend(loc="upper right", facecolor=BG, labelcolor="white")
    ax2.legend(loc="upper left",  facecolor=BG, labelcolor="white")
    save_chart(fig, "01_top_states_by_volume.png")
else:
    log("  [SKIP] customer_state column not available.")

# ---------------------------------------------------------------------------
# Insight 2 — On-time delivery rate overall + by top 5 categories
# ---------------------------------------------------------------------------

section("INSIGHT 2 — On-Time Delivery Rate Overall & Top 5 Categories")

if "Is_Late" in df.columns:
    delivered = df[df["Is_Late"].notna()]
    overall_ontime = (delivered["Is_Late"] == 0).mean() * 100
    log(f"  Overall on-time delivery rate: {overall_ontime:.2f}%")

    if "product_category_name_english" in df.columns:
        cat_ontime = (
            delivered.groupby("product_category_name_english")["Is_Late"]
            .apply(lambda x: (x == 0).mean() * 100)
            .reset_index()
            .rename(columns={"Is_Late": "OnTime_Rate"})
            .sort_values("OnTime_Rate", ascending=False)
            .head(5)
        )
        log(cat_ontime.to_string(index=False))

        fig, ax = new_fig("On-Time Delivery Rate — Top 5 Categories")
        bars = ax.barh(
            cat_ontime["product_category_name_english"],
            cat_ontime["OnTime_Rate"],
            color=ACCENT, alpha=0.85,
        )
        ax.axvline(overall_ontime, color=ACCENT2, linestyle="--", linewidth=1.5,
                   label=f"Overall avg: {overall_ontime:.1f}%")
        ax.set_xlabel("On-Time Rate (%)", color="white")
        ax.set_ylabel("Product Category", color="white")
        for bar in bars:
            w = bar.get_width()
            ax.text(w + 0.3, bar.get_y() + bar.get_height() / 2,
                    f"{w:.1f}%", va="center", fontsize=8, color=ACCENT3, fontweight="bold")
        ax.legend(facecolor=BG, labelcolor="white")
        save_chart(fig, "02_ontime_delivery_by_category.png")
else:
    log("  [SKIP] Is_Late column not available.")

# ---------------------------------------------------------------------------
# Insight 3 — Avg Days_To_Ship by seller_state (top 10 fastest / slowest)
# ---------------------------------------------------------------------------

section("INSIGHT 3 — Avg Days_To_Ship by Seller State (Fastest & Slowest)")

if "Days_To_Ship" in df.columns and "seller_state" in df.columns:
    ship_by_state = (
        df.groupby("seller_state", as_index=False)["Days_To_Ship"]
          .mean()
          .rename(columns={"Days_To_Ship": "Avg_Days_To_Ship"})
          .dropna()
    )
    ship_by_state["Avg_Days_To_Ship"] = ship_by_state["Avg_Days_To_Ship"].round(2)

    fastest = ship_by_state.nsmallest(10, "Avg_Days_To_Ship")
    slowest = ship_by_state.nlargest(10,  "Avg_Days_To_Ship")

    log("  Top 10 Fastest States:")
    log(fastest.to_string(index=False))
    log("  Top 10 Slowest States:")
    log(slowest.to_string(index=False))

    fig, (ax_f, ax_s) = plt.subplots(1, 2, figsize=(14, 6), facecolor=BG)

    for ax, data, title, color in [
        (ax_f, fastest, "Top 10 Fastest — Avg Days to Ship", "#00D4FF"),
        (ax_s, slowest, "Top 10 Slowest — Avg Days to Ship", "#FF6B6B"),
    ]:
        ax.set_facecolor(BG)
        ax.set_title(title, fontsize=11, fontweight="bold", color="white")
        bars = ax.barh(data["seller_state"], data["Avg_Days_To_Ship"], color=color, alpha=0.85)
        ax.tick_params(colors="white", labelsize=8)
        ax.set_xlabel("Avg Days to Ship", color="white")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(GRID_CLR)
        ax.spines["bottom"].set_color(GRID_CLR)
        for bar in bars:
            w = bar.get_width()
            ax.text(w + 0.05, bar.get_y() + bar.get_height() / 2,
                    f"{w:.1f}d", va="center", fontsize=7, color=ACCENT3, fontweight="bold")

    fig.suptitle("Days to Ship by Seller State", fontsize=14, fontweight="bold",
                 color="white", y=1.01)
    save_chart(fig, "03_days_to_ship_by_state.png")
else:
    log("  [SKIP] Days_To_Ship or seller_state column not available.")

# ---------------------------------------------------------------------------
# Insight 4 — Revenue by product category (top 10)
# ---------------------------------------------------------------------------

section("INSIGHT 4 — Revenue by Product Category (Top 10)")

if "Total_Revenue" in df.columns and "product_category_name_english" in df.columns:
    rev_by_cat = (
        df.groupby("product_category_name_english", as_index=False)["Total_Revenue"]
          .sum()
          .sort_values("Total_Revenue", ascending=False)
          .head(10)
    )
    rev_by_cat["Total_Revenue"] = rev_by_cat["Total_Revenue"].round(2)
    log(rev_by_cat.to_string(index=False))

    fig, ax = new_fig("Top 10 Categories by Total Revenue (R$)")
    bars = ax.bar(
        rev_by_cat["product_category_name_english"],
        rev_by_cat["Total_Revenue"],
        color=ACCENT, alpha=0.85,
    )
    ax.set_xlabel("Category", color="white")
    ax.set_ylabel("Total Revenue (R$)", color="white")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"R${x/1e6:.1f}M"))
    plt.xticks(rotation=35, ha="right", color="white")
    annotate_bars(ax, fmt="R${:,.0f}", fontsize=7)
    save_chart(fig, "04_revenue_by_category.png")
else:
    log("  [SKIP] Required columns not available.")

# ---------------------------------------------------------------------------
# Insight 5 — Cancellation rate by category  (from raw orders in the table)
# ---------------------------------------------------------------------------

section("INSIGHT 5 — Cancellation Rate by Category")

# tbl_analytics already has canceled orders removed in the ETL.
# We flag "Late" orders as a proxy for customer dissatisfaction by category.
if "Is_Late" in df.columns and "product_category_name_english" in df.columns:
    cat_late = (
        df[df["Is_Late"].notna()]
        .groupby("product_category_name_english")["Is_Late"]
        .agg(Late_Count="sum", Total="count")
        .reset_index()
    )
    cat_late["Late_Rate_%"] = (cat_late["Late_Count"] / cat_late["Total"] * 100).round(2)
    top_late = cat_late.sort_values("Late_Rate_%", ascending=False).head(10)
    log("  Top 10 categories by Late Delivery Rate:")
    log(top_late.to_string(index=False))

    fig, ax = new_fig("Top 10 Categories — Late Delivery Rate (%)")
    bars = ax.bar(
        top_late["product_category_name_english"],
        top_late["Late_Rate_%"],
        color=ACCENT2, alpha=0.85,
    )
    ax.set_xlabel("Category", color="white")
    ax.set_ylabel("Late Delivery Rate (%)", color="white")
    plt.xticks(rotation=35, ha="right", color="white")
    annotate_bars(ax, fmt="{:.1f}%", fontsize=7)
    save_chart(fig, "05_late_delivery_by_category.png")
else:
    log("  [SKIP] Required columns not available.")

# ---------------------------------------------------------------------------
# Insight 6 — Review score vs Is_Late correlation
# ---------------------------------------------------------------------------

section("INSIGHT 6 — Review Score vs Is_Late Correlation")

if "review_score" in df.columns and "Is_Late" in df.columns:
    corr_df = df[["review_score", "Is_Late"]].dropna()
    corr_val = corr_df["review_score"].corr(corr_df["Is_Late"])
    log(f"  Pearson correlation (review_score ↔ Is_Late): {corr_val:.4f}")

    avg_score = (
        corr_df.groupby("Is_Late")["review_score"]
               .agg(["mean", "count"])
               .reset_index()
    )
    avg_score.columns = ["Is_Late", "Avg_Review_Score", "Count"]
    avg_score["Is_Late_Label"] = avg_score["Is_Late"].map({0: "On-Time", 1: "Late"})
    log(avg_score.to_string(index=False))

    fig, ax = new_fig("Avg Review Score — On-Time vs Late Orders")
    colors_map = {0: ACCENT, 1: ACCENT2}
    clrs = [colors_map.get(v, ACCENT) for v in avg_score["Is_Late"]]
    bars = ax.bar(avg_score["Is_Late_Label"], avg_score["Avg_Review_Score"],
                  color=clrs, alpha=0.85, width=0.4)
    ax.set_ylim(0, 5.5)
    ax.set_xlabel("Delivery Status", color="white")
    ax.set_ylabel("Avg Review Score", color="white")
    ax.text(0.98, 0.95, f"Pearson r = {corr_val:.4f}",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=10, color=ACCENT3, fontweight="bold")
    annotate_bars(ax, fmt="{:.2f}")
    save_chart(fig, "06_review_vs_late.png")
else:
    log("  [SKIP] Required columns not available.")

# ---------------------------------------------------------------------------
# Insight 7 — Payment type breakdown + avg order value per type
# ---------------------------------------------------------------------------

section("INSIGHT 7 — Payment Type Breakdown + Avg Order Value")

if "payment_type" in df.columns and "Total_Revenue" in df.columns:
    pay = (
        df.groupby("payment_type", as_index=False)
          .agg(
              Order_Count = ("order_id",    "count"),
              Avg_Revenue = ("Total_Revenue","mean"),
          )
          .sort_values("Order_Count", ascending=False)
    )
    pay["Avg_Revenue"] = pay["Avg_Revenue"].round(2)
    log(pay.to_string(index=False))

    fig, ax1 = new_fig("Payment Type — Order Count & Avg Revenue (R$)")
    ax2 = ax1.twinx()
    x = range(len(pay))
    ax1.bar(x, pay["Order_Count"],  color=ACCENT,  alpha=0.85, width=0.4, label="Order Count")
    ax2.plot(x, pay["Avg_Revenue"], color=ACCENT2, marker="D", linewidth=2,
             markersize=8, label="Avg Revenue (R$)")

    ax1.set_xticks(x)
    ax1.set_xticklabels(pay["payment_type"], color="white")
    ax1.set_xlabel("Payment Type", color="white")
    ax1.set_ylabel("Order Count", color=ACCENT)
    ax2.set_ylabel("Avg Revenue (R$)", color=ACCENT2)
    ax2.tick_params(colors="white")
    ax2.spines["right"].set_color(GRID_CLR)

    annotate_bars(ax1, fmt="{:,.0f}")
    for xi, yi in zip(x, pay["Avg_Revenue"]):
        ax2.text(xi, yi + 5, f"R${yi:.0f}", ha="center", va="bottom",
                 fontsize=8, color=ACCENT3, fontweight="bold")

    ax1.legend(loc="upper right", facecolor=BG, labelcolor="white")
    ax2.legend(loc="upper left",  facecolor=BG, labelcolor="white")
    save_chart(fig, "07_payment_type_breakdown.png")
else:
    log("  [SKIP] Required columns not available.")

# ---------------------------------------------------------------------------
# Insight 8 — Monthly order volume trend (2016-2018)
# ---------------------------------------------------------------------------

section("INSIGHT 8 — Monthly Order Volume Trend (2016–2018)")

if "Purchase_Year" in df.columns and "Purchase_Month_Num" in df.columns:
    trend = (
        df.groupby(["Purchase_Year", "Purchase_Month_Num"], as_index=False)["order_id"]
          .count()
          .rename(columns={"order_id": "Order_Count"})
          .sort_values(["Purchase_Year", "Purchase_Month_Num"])
    )
    trend["Period"] = trend.apply(
        lambda r: f"{int(r['Purchase_Year'])}-{int(r['Purchase_Month_Num']):02d}", axis=1
    )
    log(trend[["Period", "Order_Count"]].to_string(index=False))

    fig, ax = new_fig("Monthly Order Volume Trend — 2016 to 2018", figsize=(14, 6))
    ax.fill_between(range(len(trend)), trend["Order_Count"],
                    alpha=0.2, color=ACCENT)
    ax.plot(range(len(trend)), trend["Order_Count"],
            color=ACCENT, linewidth=2.5, marker="o", markersize=5)

    tick_step = max(1, len(trend) // 12)
    ax.set_xticks(range(0, len(trend), tick_step))
    ax.set_xticklabels(trend["Period"].iloc[::tick_step], rotation=45, ha="right", color="white")
    ax.set_xlabel("Month", color="white")
    ax.set_ylabel("Order Count", color="white")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))

    # Annotate peak
    peak_idx = trend["Order_Count"].idxmax()
    peak_val = trend.loc[peak_idx, "Order_Count"]
    peak_lbl = trend.loc[peak_idx, "Period"]
    ax.annotate(
        f"Peak: {peak_val:,}\n({peak_lbl})",
        xy=(list(trend.index).index(peak_idx), peak_val),
        xytext=(list(trend.index).index(peak_idx) - 2, peak_val * 1.08),
        arrowprops=dict(arrowstyle="->", color=ACCENT3),
        fontsize=9, color=ACCENT3, fontweight="bold",
    )
    save_chart(fig, "08_monthly_order_trend.png")
else:
    log("  [SKIP] Required columns not available.")

# ---------------------------------------------------------------------------
# Insight 9 — Freight ratio by category (top 10 highest)
# ---------------------------------------------------------------------------

section("INSIGHT 9 — Freight Ratio by Category (Top 10 Highest)")

if "Freight_Ratio" in df.columns and "product_category_name_english" in df.columns:
    freight_cat = (
        df.groupby("product_category_name_english", as_index=False)["Freight_Ratio"]
          .mean()
          .sort_values("Freight_Ratio", ascending=False)
          .head(10)
    )
    freight_cat["Freight_Ratio"] = (freight_cat["Freight_Ratio"] * 100).round(2)
    freight_cat.rename(columns={"Freight_Ratio": "Freight_Pct"}, inplace=True)
    log(freight_cat.to_string(index=False))

    fig, ax = new_fig("Top 10 Categories — Avg Freight as % of Revenue")
    bars = ax.barh(
        freight_cat["product_category_name_english"],
        freight_cat["Freight_Pct"],
        color=ACCENT3, alpha=0.85,
    )
    ax.set_xlabel("Avg Freight Ratio (%)", color="white")
    ax.set_ylabel("Product Category", color="white")
    for bar in bars:
        w = bar.get_width()
        ax.text(w + 0.3, bar.get_y() + bar.get_height() / 2,
                f"{w:.1f}%", va="center", fontsize=8, color=ACCENT3, fontweight="bold")
    save_chart(fig, "09_freight_ratio_by_category.png")
else:
    log("  [SKIP] Required columns not available.")

# ---------------------------------------------------------------------------
# Insight 10 — Delivery Speed Bucket distribution
# ---------------------------------------------------------------------------

section("INSIGHT 10 — Delivery Speed Bucket Distribution")

if "Delivery_Speed_Bucket" in df.columns:
    speed_order = ["Fast", "Normal", "Slow", "Very Slow"]
    speed = (
        df["Delivery_Speed_Bucket"]
          .value_counts()
          .reindex(speed_order, fill_value=0)
          .reset_index()
    )
    speed.columns = ["Bucket", "Count"]
    speed["Pct"] = (speed["Count"] / speed["Count"].sum() * 100).round(1)
    log(speed.to_string(index=False))

    palette = [ACCENT, "#00FF9F", ACCENT3, ACCENT2]
    fig, (ax_bar, ax_pie) = plt.subplots(1, 2, figsize=(14, 6), facecolor=BG)

    # Bar chart
    ax_bar.set_facecolor(BG)
    ax_bar.set_title("Delivery Speed — Count", fontsize=12, fontweight="bold", color="white")
    bars = ax_bar.bar(speed["Bucket"], speed["Count"], color=palette, alpha=0.9)
    ax_bar.tick_params(colors="white")
    ax_bar.spines["top"].set_visible(False)
    ax_bar.spines["right"].set_visible(False)
    ax_bar.spines["left"].set_color(GRID_CLR)
    ax_bar.spines["bottom"].set_color(GRID_CLR)
    ax_bar.yaxis.grid(True, color=GRID_CLR, linewidth=0.6, linestyle="--")
    ax_bar.set_axisbelow(True)
    ax_bar.set_xlabel("Speed Bucket", color="white")
    ax_bar.set_ylabel("Order Count", color="white")
    for bar in bars:
        h = bar.get_height()
        ax_bar.text(bar.get_x() + bar.get_width() / 2, h * 1.01, f"{int(h):,}",
                    ha="center", va="bottom", fontsize=9, color=ACCENT3, fontweight="bold")

    # Pie chart
    ax_pie.set_facecolor(BG)
    ax_pie.set_title("Delivery Speed — Share (%)", fontsize=12, fontweight="bold", color="white")
    wedges, texts, autotexts = ax_pie.pie(
        speed["Count"], labels=speed["Bucket"], colors=palette,
        autopct="%1.1f%%", startangle=140,
        textprops={"color": "white", "fontsize": 9},
        wedgeprops={"edgecolor": BG, "linewidth": 2},
    )
    for at in autotexts:
        at.set_color(BG)
        at.set_fontweight("bold")

    fig.suptitle("Delivery Speed Bucket Distribution", fontsize=14,
                 fontweight="bold", color="white")
    save_chart(fig, "10_speed_bucket_distribution.png")
else:
    log("  [SKIP] Delivery_Speed_Bucket column not available.")

# ---------------------------------------------------------------------------
# Save text report
# ---------------------------------------------------------------------------

banner("Saving insights_preview.txt")

try:
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(_lines))
    print(f"  Saved → {REPORT_FILE}")
except Exception as exc:
    print(f"  [ERROR] Could not save report: {exc}")

print(f"\n  Insights preview complete — {len(os.listdir(CHARTS_DIR))} charts in /charts\n")
