import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import etl


def sample():
    return pd.DataFrame({
        "order_id": [1, 2, 3, 4, 5],
        "order_date": ["2026-01-05", "2026-01-06", "bad", "2026-02-01", "2026-02-01"],
        "customer_id": ["C1", None, "C2", "C2", "C2"],
        "customer_name": ["A", "B", "C", "C", "C"], "city": ["Pune"] * 5,
        "product_id": ["P1", "P1", "P2", "P2", "P2"],
        "product_name": ["x", "x", "y", "y", "y"], "category": ["c1", "c1", "c2", "c2", "c2"],
        "unit_price": [100, 100, 50, 50, 50], "quantity": [2, 1, 1, -1, 3],
    })


def test_clean_rejects_bad_rows():
    clean, rejected = etl.clean(sample())
    assert list(clean["order_id"]) == [1, 5]
    assert set(rejected["reject_reason"]) == {
        "missing customer_id", "invalid order_date", "quantity must be > 0"}


def test_star_schema_keys_and_amounts():
    clean, _ = etl.clean(sample())
    t = etl.build_star_schema(clean)
    assert len(t["fact_sales"]) == len(clean)
    assert t["fact_sales"]["total_amount"].tolist() == [200, 150]
    assert t["dim_customer"]["customer_key"].is_unique
