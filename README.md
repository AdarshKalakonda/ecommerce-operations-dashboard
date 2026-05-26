# E-Commerce Operations Dashboard

> End-to-end Python ETL pipeline and Excel analytics dashboard built on 100K+ real Brazilian e-commerce transactions — surfacing delivery performance, revenue drivers, and customer satisfaction signals.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-2.2-150458?style=flat-square&logo=pandas&logoColor=white)
![matplotlib](https://img.shields.io/badge/matplotlib-3.9-11557C?style=flat-square&logo=python&logoColor=white)
![Excel](https://img.shields.io/badge/Excel-Dashboard-217346?style=flat-square&logo=microsoftexcel&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-2.2-013243?style=flat-square&logo=numpy&logoColor=white)

---

## Overview

E-commerce operations teams need fast, reliable answers to questions like: *Which product categories drive the most revenue? Where are deliveries failing? What does a late order cost in customer satisfaction?*

This project builds a complete analytics stack — from raw CSV ingestion to a polished Excel dashboard — using the public Olist dataset. A modular ETL pipeline joins 9 relational source tables into a single analytics-ready fact table, a data quality audit validates every field, and a set of insight scripts generate 10 business-focused findings backed by charts.

The result is a portfolio-grade project demonstrating the full data analyst workflow: data engineering, exploratory analysis, and stakeholder-ready reporting.

---

## Dataset

**Source:** [Olist Brazilian E-Commerce Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — Kaggle

| Table | Rows | Description |
|---|---|---|
| `olist_orders_dataset.csv` | 99,441 | Order lifecycle with 5 timestamps |
| `olist_order_items_dataset.csv` | 112,650 | Line items — price, freight, product, seller |
| `olist_customers_dataset.csv` | 99,441 | Customer city and state |
| `olist_sellers_dataset.csv` | 3,095 | Seller city and state |
| `olist_products_dataset.csv` | 32,951 | Product dimensions, weight, category |
| `olist_order_reviews_dataset.csv` | 99,224 | Review scores 1–5 with timestamps |
| `olist_order_payments_dataset.csv` | 103,886 | Payment type, installments, value |
| `product_category_name_translation.csv` | 71 | Portuguese → English category names |
| `olist_geolocation_dataset.csv` | 1,000,163 | ZIP-level lat/lon *(excluded from repo — too large)* |

**Coverage:** September 2016 – October 2018 · ~100K orders · 27 Brazilian states

---

## Key Findings

| # | Finding |
|---|---|
| 1 | **98,207 orders** analyzed after removing canceled and unavailable records across 9 relational tables |
| 2 | **91.89% overall on-time delivery rate** — marketplace logistics performance is strong but uneven by category |
| 3 | **Late orders score 2.57 / 5 vs 4.29 / 5 for on-time orders** — Pearson r = −0.36, a statistically meaningful negative correlation |
| 4 | **Health & Beauty is the top revenue category at R$1.44M**, followed by Watches & Gifts (R$1.30M) and Bed, Bath & Table (R$1.24M) |
| 5 | **São Paulo state accounts for 41,127 orders — 42% of total marketplace volume**, more than the next four states combined |
| 6 | **Order volume grew ~3,700× from September 2016 to November 2017**, peaking at 7,423 orders in a single month |
| 7 | **Electronics carries the highest late-delivery risk at 9.85%** — nearly double the platform average |
| 8 | **Credit card is the dominant payment method (75.5% of orders)** with the highest average basket value at R$166.61 |

---

## Project Structure

```
E-Commerce Operations Dashboard/
│
├── etl_pipeline.py               # Loads, cleans, and joins all 9 source CSVs
├── data_quality_report.py        # Null audit, outlier detection, value distributions
├── insights_preview.py           # 10 business insights + 10 PNG charts
├── build_date_table.py           # Generates tbl_dates.csv date dimension
│
├── tbl_analytics.csv             # Master analytics table (98,207 rows × 31 cols)
├── tbl_dates.csv                 # Date dimension: 2016-09-01 to 2018-10-31
│
├── data_quality_summary.txt      # Full data quality report output
├── insights_preview.txt          # All 10 insights as plain text
│
├── charts/
│   ├── 01_top_states_by_volume.png
│   ├── 02_ontime_delivery_by_category.png
│   ├── 03_days_to_ship_by_state.png
│   ├── 04_revenue_by_category.png
│   ├── 05_late_delivery_by_category.png
│   ├── 06_review_vs_late.png
│   ├── 07_payment_type_breakdown.png
│   ├── 08_monthly_order_trend.png
│   ├── 09_freight_ratio_by_category.png
│   └── 10_speed_bucket_distribution.png
│
├── Olist_Ops_Dashboard.xlsx      # Interactive Excel dashboard
├── requirements.txt
├── .gitignore
└── README.md
```

---

## How to Run

**1. Clone the repository**
```bash
git clone https://github.com/AdarshKalakonda/ecommerce-operations-dashboard.git
cd ecommerce-operations-dashboard
```

**2. Download the raw data**

Download the Olist dataset from [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) and place all CSV files in the project root.

**3. Create and activate a virtual environment**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

**4. Install dependencies**
```bash
pip install -r requirements.txt
```

**5. Run the pipeline in order**
```bash
# Step 1 — Build the analytics table (required first)
python etl_pipeline.py

# Step 2 — Validate data quality
python data_quality_report.py

# Step 3 — Generate insights and charts
python insights_preview.py

# Step 4 — Build the date dimension table
python build_date_table.py
```

Each script prints a progress log to the terminal. Total runtime is approximately 15–30 seconds depending on hardware.

---

## Dashboard Preview

`Olist_Ops_Dashboard.xlsx` is an interactive Excel workbook connected to `tbl_analytics.csv` and `tbl_dates.csv`. It includes:

- **KPI Summary** — headline metrics (order volume, on-time rate, avg review score, total revenue)
- **Delivery Performance** — late rate by category, speed bucket distribution, state-level heatmap
- **Revenue Analysis** — category revenue ranking, payment type breakdown, avg basket by state
- **Customer Satisfaction** — review score distribution, on-time vs late score comparison
- **Trend View** — monthly order volume from 2016 to 2018

All pivot tables use `tbl_dates.csv` as a time spine for consistent Year / Quarter / Month filtering.

---

## ETL Pipeline — Merge Summary

The pipeline performs a series of left joins anchored on `order_id`, preserving all orders throughout:

| Stage | Rows |
|---|---|
| Orders (raw) | 99,441 |
| After removing canceled / unavailable | 98,207 |
| After join → order items | 98,207 |
| After join → customers | 98,207 |
| After join → reviews | 98,207 |
| After join → products | 98,207 |
| After join → sellers | 98,207 |
| After join → payments | 98,207 |
| **tbl_analytics (final)** | **98,207 × 31 columns** |

Zero row loss after filtering — all joins are left joins to prevent silently dropping unmatched orders.

---

## Tech Stack

| Tool | Role |
|---|---|
| Python 3.10+ | ETL scripting, data transformation |
| pandas | DataFrame operations, merges, aggregations |
| NumPy | Vectorized calculations, derived metrics |
| matplotlib | Chart generation (dark-theme PNGs) |
| seaborn | Statistical visualization support |
| colorama | Terminal color output in quality report |
| openpyxl | Excel read/write for dashboard integration |
| scipy | Pearson correlation (review score vs lateness) |
| Excel (Power Query) | Interactive dashboard layer |

---

## Author

Built by [Adarsh Kalakonda](mailto:kalakondaadarsh1@gmail.com) as a portfolio project demonstrating end-to-end data analytics engineering on a real-world e-commerce dataset.
