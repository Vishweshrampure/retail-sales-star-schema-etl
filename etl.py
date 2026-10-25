"""
Retail sales ETL: raw CSV -> staging -> clean -> star schema (dimensions + fact) -> validation.

Default database is a local SQLite file. Set DB_URL to load into SQL Server (see README).
"""
import logging
import os

import pandas as pd
from sqlalchemy import create_engine, text

DB_URL = os.getenv("DB_URL", "sqlite:///sales_dw.db")
RAW_FILE = "data/raw_sales.csv"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("etl")


# ------------------------------------------------------------------ extract
def extract(path: str = RAW_FILE) -> pd.DataFrame:
    df = pd.read_csv(path)
    log.info("Extracted %d raw rows", len(df))
    return df


# ------------------------------------------------------------------- clean
def clean(raw: pd.DataFrame):
    """Returns (clean_df, rejected_df). Rejected rows carry a reject_reason."""
    df = raw.copy()
    rejected = []

    before = len(df)
    df = df.drop_duplicates()
    log.info("Removed %d exact duplicate rows", before - len(df))

    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")

    rules = [
        ("missing customer_id", lambda d: d["customer_id"].isna()),
        ("invalid order_date", lambda d: d["order_date"].isna()),
        ("quantity must be > 0", lambda d: d["quantity"] <= 0),
        ("unit_price must be > 0", lambda d: d["unit_price"] <= 0),
    ]
    for reason, rule in rules:
        mask = rule(df)          # evaluated on the current df so indexes always line up
        rejected.append(df[mask].assign(reject_reason=reason))
        log.info("Rejected %d rows: %s", int(mask.sum()), reason)
        df = df[~mask]

    rejected_df = pd.concat(rejected, ignore_index=True) if rejected else pd.DataFrame()
    return df.reset_index(drop=True), rejected_df


# --------------------------------------------------------------- transform
def build_star_schema(df: pd.DataFrame) -> dict:
    """Build dimension tables with surrogate keys, then the fact table."""
    dim_customer = (df[["customer_id", "customer_name", "city"]]
                    .drop_duplicates("customer_id").sort_values("customer_id").reset_index(drop=True))
    dim_customer.insert(0, "customer_key", dim_customer.index + 1)

    dim_product = (df[["product_id", "product_name", "category"]]
                   .drop_duplicates("product_id").sort_values("product_id").reset_index(drop=True))
    dim_product.insert(0, "product_key", dim_product.index + 1)

    dates = pd.DataFrame({"full_date": sorted(df["order_date"].dt.normalize().unique())})
    dates["date_key"] = dates["full_date"].dt.strftime("%Y%m%d").astype(int)
    dates["year"] = dates["full_date"].dt.year
    dates["quarter"] = dates["full_date"].dt.quarter
    dates["month"] = dates["full_date"].dt.month
    dates["month_name"] = dates["full_date"].dt.month_name()
    dates["day_of_week"] = dates["full_date"].dt.day_name()
    dim_date = dates[["date_key", "full_date", "year", "quarter", "month", "month_name", "day_of_week"]]

    fact = df.copy()
    fact["date_key"] = fact["order_date"].dt.strftime("%Y%m%d").astype(int)
    fact = (fact.merge(dim_customer[["customer_key", "customer_id"]], on="customer_id")
                .merge(dim_product[["product_key", "product_id"]], on="product_id"))
    fact["total_amount"] = fact["unit_price"] * fact["quantity"]
    fact_sales = fact[["order_id", "date_key", "customer_key", "product_key",
                       "quantity", "unit_price", "total_amount"]].reset_index(drop=True)

    return {"dim_customer": dim_customer, "dim_product": dim_product,
            "dim_date": dim_date, "fact_sales": fact_sales}


# -------------------------------------------------------------------- load
def load(engine, staging: pd.DataFrame, rejected: pd.DataFrame, tables: dict):
    staging.to_sql("stg_sales", engine, if_exists="replace", index=False)
    if not rejected.empty:
        rejected.to_sql("rejected_sales", engine, if_exists="replace", index=False)
    for name, frame in tables.items():
        frame.to_sql(name, engine, if_exists="replace", index=False)
    log.info("Loaded stg_sales, rejected_sales and star schema tables")


# ---------------------------------------------------------------- validate
def validate(engine) -> list:
    """Post-load checks, written as plain SQL. Returns a list of (check, passed, detail)."""
    checks = {
        "fact rows equal clean staging rows":
            ("SELECT (SELECT COUNT(*) FROM fact_sales) - (SELECT COUNT(*) FROM stg_sales)", 0),
        "no orphan customer keys in fact":
            ("SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_customer c "
             "ON f.customer_key = c.customer_key WHERE c.customer_key IS NULL", 0),
        "no orphan product keys in fact":
            ("SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_product p "
             "ON f.product_key = p.product_key WHERE p.product_key IS NULL", 0),
        "no orphan date keys in fact":
            ("SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_date d "
             "ON f.date_key = d.date_key WHERE d.date_key IS NULL", 0),
        "no duplicate order ids in fact":
            ("SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM fact_sales", 0),
        "revenue matches between staging and fact":
            ("SELECT ROUND((SELECT SUM(unit_price * quantity) FROM stg_sales) - "
             "(SELECT SUM(total_amount) FROM fact_sales), 2)", 0),
    }
    results = []
    with engine.connect() as conn:
        for name, (sql, expected) in checks.items():
            value = conn.execute(text(sql)).scalar()
            passed = value == expected
            results.append((name, passed, f"value={value}, expected={expected}"))
            log.info("VALIDATION %-45s %s (%s)", name, "PASS" if passed else "FAIL", value)
    return results


def main():
    engine = create_engine(DB_URL)
    raw = extract()
    clean_df, rejected_df = clean(raw)
    tables = build_star_schema(clean_df)
    load(engine, clean_df, rejected_df, tables)
    results = validate(engine)
    if not all(passed for _, passed, _ in results):
        raise SystemExit("Validation failed - check the log above")
    log.info("ETL finished successfully")


if __name__ == "__main__":
    main()
