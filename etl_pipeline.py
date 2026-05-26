# =============================================================================
# etl_pipeline.py
# =============================================================================
# Purpose : Full ETL pipeline for the Olist Brazilian E-Commerce dataset.
#           Loads, cleans, transforms, and joins all 9 source CSVs into a
#           single analytics table (tbl_analytics.csv) ready for dashboarding.
#
# Input   : 9 CSV files in the same directory as this script
# Output  : tbl_analytics.csv
#
# Run     : python etl_pipeline.py
# =============================================================================

import os
import sys
import io
import traceback

# Force UTF-8 output on Windows terminals (handles box-drawing chars, etc.)
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SOURCES = {
    "orders":       "olist_orders_dataset.csv",
    "order_items":  "olist_order_items_dataset.csv",
    "products":     "olist_products_dataset.csv",
    "sellers":      "olist_sellers_dataset.csv",
    "customers":    "olist_customers_dataset.csv",
    "reviews":      "olist_order_reviews_dataset.csv",
    "payments":     "olist_order_payments_dataset.csv",
    "translation":  "product_category_name_translation.csv",
    "geolocation":  "olist_geolocation_dataset.csv",
}

OUTPUT_FILE = os.path.join(BASE_DIR, "tbl_analytics.csv")

TIMESTAMP_COLS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]

FINAL_COLUMNS = [
    "order_id", "order_status",
    "Purchase_Year", "Purchase_Month_Num", "Purchase_Month_Name",
    "Purchase_Quarter", "Purchase_Week",
    "Days_To_Ship", "Days_In_Transit", "Total_Delivery_Days",
    "Is_Late", "Days_Early_Or_Late", "Delivery_Speed_Bucket",
    "Total_Revenue", "Total_Items", "Total_Freight", "Avg_Item_Price", "Freight_Ratio",
    "product_category_name_english", "product_weight_g", "product_volume_cm3",
    "customer_state", "customer_city",
    "seller_state", "seller_city", "seller_id",
    "review_score", "Satisfaction_Label",
    "payment_type", "payment_installments", "payment_value",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def banner(text: str) -> None:
    print(f"\n{'-' * 60}")
    print(f"  {text}")
    print(f"{'-' * 60}")


def load_csv(name: str, filename: str) -> pd.DataFrame:
    path = os.path.join(BASE_DIR, filename)
    print(f"  Loading {filename} ...", end="  ")
    try:
        df = pd.read_csv(path, low_memory=False)
        print(f"{len(df):,} rows  ×  {df.shape[1]} cols")
        return df
    except FileNotFoundError:
        print(f"\n  [ERROR] File not found: {path}")
        sys.exit(1)
    except Exception as exc:
        print(f"\n  [ERROR] Could not read {filename}: {exc}")
        sys.exit(1)


def _delivery_speed(days: float) -> str:
    if pd.isna(days):
        return np.nan
    if days <= 7:
        return "Fast"
    if days <= 14:
        return "Normal"
    if days <= 21:
        return "Slow"
    return "Very Slow"


# ---------------------------------------------------------------------------
# Step 1 — Load raw CSVs
# ---------------------------------------------------------------------------

banner("STEP 1 — Loading source CSVs")

raw = {name: load_csv(name, fname) for name, fname in SOURCES.items()}

row_tracker = {}   # used for the final summary table

# ---------------------------------------------------------------------------
# Step 2 — Transform: Orders
# ---------------------------------------------------------------------------

banner("STEP 2 — Transforming: Orders")

orders = raw["orders"].copy()
row_tracker["01_orders_raw"] = len(orders)

# Convert timestamps
print("  Converting timestamp columns …")
for col in TIMESTAMP_COLS:
    try:
        orders[col] = pd.to_datetime(orders[col], errors="coerce")
    except Exception as exc:
        print(f"  [WARN] Could not parse {col}: {exc}")

# Drop canceled / unavailable
before = len(orders)
orders = orders[~orders["order_status"].isin(["unavailable", "canceled"])]
print(f"  Removed {before - len(orders):,} rows with status 'canceled' or 'unavailable'")
row_tracker["02_orders_filtered"] = len(orders)

# Delivery KPIs — these require non-null timestamps; clip negatives at 0
def safe_days(series_a: pd.Series, series_b: pd.Series) -> pd.Series:
    """Return (series_a - series_b).dt.days, NaN where either operand is NaT."""
    delta = series_a - series_b
    return delta.dt.days

orders["Days_To_Ship"]       = safe_days(orders["order_approved_at"],              orders["order_purchase_timestamp"])
orders["Days_In_Transit"]    = safe_days(orders["order_delivered_carrier_date"],    orders["order_approved_at"])
orders["Total_Delivery_Days"]= safe_days(orders["order_delivered_customer_date"],   orders["order_purchase_timestamp"])

orders["Is_Late"] = np.where(
    orders["order_delivered_customer_date"].isna() | orders["order_estimated_delivery_date"].isna(),
    np.nan,
    (orders["order_delivered_customer_date"] > orders["order_estimated_delivery_date"]).astype(int)
)

orders["Days_Early_Or_Late"] = safe_days(
    orders["order_estimated_delivery_date"],
    orders["order_delivered_customer_date"]
)  # positive = early, negative = late

# Date parts
ts = orders["order_purchase_timestamp"]
orders["Purchase_Year"]       = ts.dt.year
orders["Purchase_Month_Num"]  = ts.dt.month
orders["Purchase_Month_Name"] = ts.dt.strftime("%B")
orders["Purchase_Quarter"]    = ts.dt.quarter
orders["Purchase_Week"]       = ts.dt.isocalendar().week.astype("Int64")

# Delivery speed bucket
orders["Delivery_Speed_Bucket"] = orders["Total_Delivery_Days"].apply(_delivery_speed)

print(f"  Orders after transformation: {len(orders):,} rows")

# ---------------------------------------------------------------------------
# Step 3 — Transform: Order Items
# ---------------------------------------------------------------------------

banner("STEP 3 — Transforming: Order Items")

items = raw["order_items"].copy()
row_tracker["03_items_raw"] = len(items)

items["Revenue"]       = items["price"] + items["freight_value"]
items["Freight_Ratio"] = (items["freight_value"] / items["Revenue"]).round(4)

# Keep first product_id and seller_id per order for the product/seller join
item_first = (
    items.sort_values("order_item_id")
         .groupby("order_id", as_index=False)
         .first()[["order_id", "product_id", "seller_id"]]
)

# Aggregate metrics per order
items_grouped = (
    items.groupby("order_id", as_index=False)
         .agg(
             Total_Revenue  = ("Revenue",       "sum"),
             Total_Items    = ("order_item_id", "count"),
             Total_Freight  = ("freight_value", "sum"),
             Avg_Item_Price = ("price",         "mean"),
             Freight_Ratio  = ("Freight_Ratio", "mean"),
         )
)
items_grouped["Avg_Item_Price"] = items_grouped["Avg_Item_Price"].round(2)
items_grouped["Freight_Ratio"]  = items_grouped["Freight_Ratio"].round(4)
items_grouped["Total_Revenue"]  = items_grouped["Total_Revenue"].round(2)
items_grouped["Total_Freight"]  = items_grouped["Total_Freight"].round(2)

# Attach first product/seller identifiers
items_grouped = items_grouped.merge(item_first, on="order_id", how="left")

row_tracker["04_items_grouped"] = len(items_grouped)
print(f"  Items aggregated → {len(items_grouped):,} unique orders")

# ---------------------------------------------------------------------------
# Step 4 — Transform: Products
# ---------------------------------------------------------------------------

banner("STEP 4 — Transforming: Products")

products    = raw["products"].copy()
translation = raw["translation"].copy()
row_tracker["05_products_raw"] = len(products)

products = products.merge(translation, on="product_category_name", how="left")
products["product_category_name_english"] = (
    products["product_category_name_english"]
    .fillna(products["product_category_name"])
    .fillna("uncategorized")
)

products["product_volume_cm3"] = (
    products["product_length_cm"]
    * products["product_height_cm"]
    * products["product_width_cm"]
)

products_slim = products[[
    "product_id",
    "product_category_name_english",
    "product_weight_g",
    "product_volume_cm3",
]]

print(f"  Products enriched with English categories: {len(products_slim):,} rows")

# ---------------------------------------------------------------------------
# Step 5 — Transform: Reviews
# ---------------------------------------------------------------------------

banner("STEP 5 — Transforming: Reviews")

reviews = raw["reviews"].copy()
row_tracker["06_reviews_raw"] = len(reviews)

# Keep most recent review per order
reviews["review_creation_date"] = pd.to_datetime(
    reviews["review_creation_date"], errors="coerce"
)
reviews = (
    reviews.sort_values("review_creation_date", ascending=False)
           .drop_duplicates(subset="order_id", keep="first")
)

def satisfaction_label(score) -> str:
    try:
        s = int(score)
        if s <= 2:
            return "Negative"
        if s == 3:
            return "Neutral"
        return "Positive"
    except (ValueError, TypeError):
        return np.nan

reviews["Satisfaction_Label"] = reviews["review_score"].apply(satisfaction_label)
reviews_slim = reviews[["order_id", "review_score", "Satisfaction_Label"]]

row_tracker["07_reviews_deduped"] = len(reviews_slim)
print(f"  Reviews deduplicated → {len(reviews_slim):,} unique orders")

# ---------------------------------------------------------------------------
# Step 6 — Transform: Payments
# ---------------------------------------------------------------------------

banner("STEP 6 — Transforming: Payments")

payments = raw["payments"].copy()
row_tracker["08_payments_raw"] = len(payments)

# Dominant payment type = highest payment_value for that order
dominant = (
    payments.sort_values("payment_value", ascending=False)
            .drop_duplicates(subset="order_id", keep="first")[["order_id", "payment_type", "payment_installments"]]
)

# Total payment value per order
total_payment = (
    payments.groupby("order_id", as_index=False)["payment_value"]
            .sum()
            .rename(columns={"payment_value": "payment_value"})
)

payments_slim = dominant.merge(total_payment, on="order_id", how="left")

row_tracker["09_payments_processed"] = len(payments_slim)
print(f"  Payments processed → {len(payments_slim):,} unique orders")

# ---------------------------------------------------------------------------
# Step 7 — Transform: Sellers & Customers (slim down)
# ---------------------------------------------------------------------------

banner("STEP 7 — Slimming Sellers & Customers")

sellers = raw["sellers"][["seller_id", "seller_state", "seller_city"]].copy()
customers = raw["customers"][["customer_id", "customer_state", "customer_city"]].copy()

print(f"  Sellers:   {len(sellers):,} rows")
print(f"  Customers: {len(customers):,} rows")

# ---------------------------------------------------------------------------
# Step 8 — Master Merge → tbl_analytics
# ---------------------------------------------------------------------------

banner("STEP 8 — Building tbl_analytics (master merge)")

print("  Merging orders ← items_grouped …")
tbl = orders.merge(items_grouped, on="order_id", how="left")
row_tracker["10_after_items_join"] = len(tbl)

print("  Merging ← customers …")
tbl = tbl.merge(customers, on="customer_id", how="left")
row_tracker["11_after_customers_join"] = len(tbl)

print("  Merging ← reviews …")
tbl = tbl.merge(reviews_slim, on="order_id", how="left")
row_tracker["12_after_reviews_join"] = len(tbl)

print("  Merging ← products …")
tbl = tbl.merge(products_slim, on="product_id", how="left")
row_tracker["13_after_products_join"] = len(tbl)

print("  Merging ← sellers …")
tbl = tbl.merge(sellers, on="seller_id", how="left")
row_tracker["14_after_sellers_join"] = len(tbl)

print("  Merging ← payments …")
tbl = tbl.merge(payments_slim, on="order_id", how="left")
row_tracker["15_after_payments_join"] = len(tbl)

# ---------------------------------------------------------------------------
# Step 9 — Select final columns
# ---------------------------------------------------------------------------

banner("STEP 9 — Selecting final columns")

missing_cols = [c for c in FINAL_COLUMNS if c not in tbl.columns]
if missing_cols:
    print(f"  [WARN] These expected columns are missing and will be skipped: {missing_cols}")

available = [c for c in FINAL_COLUMNS if c in tbl.columns]
tbl_analytics = tbl[available].copy()

row_tracker["16_tbl_analytics_final"] = len(tbl_analytics)
print(f"  Final table shape: {tbl_analytics.shape[0]:,} rows × {tbl_analytics.shape[1]} columns")

# ---------------------------------------------------------------------------
# Step 10 — Save output
# ---------------------------------------------------------------------------

banner("STEP 10 — Saving tbl_analytics.csv")

try:
    tbl_analytics.to_csv(OUTPUT_FILE, index=False)
    size_mb = os.path.getsize(OUTPUT_FILE) / 1_048_576
    print(f"  Saved → {OUTPUT_FILE}")
    print(f"  File size: {size_mb:.2f} MB")
except Exception as exc:
    print(f"  [ERROR] Could not save output: {exc}")
    traceback.print_exc()
    sys.exit(1)

# ---------------------------------------------------------------------------
# Final Summary Table
# ---------------------------------------------------------------------------

banner("PIPELINE SUMMARY — Row counts at each stage")

col_w = 42
print(f"  {'Stage':<{col_w}} {'Rows':>10}")
print(f"  {'-' * col_w} {'-' * 10}")
for stage, count in row_tracker.items():
    label = stage.replace("_", " ").title()
    print(f"  {label:<{col_w}} {count:>10,}")

print(f"\n  {'tbl_analytics shape':<{col_w}} {str(tbl_analytics.shape):>10}")
print(f"\n  ETL pipeline complete.\n")
