"""Generate a sample raw sales file (data/raw_sales.csv) with some deliberately dirty rows."""
import os
import random
from datetime import date, timedelta

import pandas as pd

random.seed(42)
PRODUCTS = [
    ("P001", "Laptop", "Electronics", 55000), ("P002", "Mouse", "Electronics", 600),
    ("P003", "Keyboard", "Electronics", 1500), ("P004", "Office Chair", "Furniture", 7500),
    ("P005", "Desk", "Furniture", 12000), ("P006", "Notebook", "Stationery", 80),
    ("P007", "Pen Pack", "Stationery", 120), ("P008", "Monitor", "Electronics", 14000),
]
CITIES = ["Pune", "Mumbai", "Nagpur", "Nashik", "Aurangabad"]
CUSTOMERS = [(f"C{str(i).zfill(3)}", f"Customer {i}", random.choice(CITIES)) for i in range(1, 41)]

rows = []
start = date(2026, 1, 1)
for order_id in range(1, 1001):
    cust = random.choice(CUSTOMERS)
    prod = random.choice(PRODUCTS)
    order_date = start + timedelta(days=random.randint(0, 270))
    qty = random.randint(1, 5)
    rows.append({
        "order_id": order_id, "order_date": order_date.isoformat(),
        "customer_id": cust[0], "customer_name": cust[1], "city": cust[2],
        "product_id": prod[0], "product_name": prod[1], "category": prod[2],
        "unit_price": prod[3], "quantity": qty,
    })

df = pd.DataFrame(rows)

# Make the data realistically messy
df.loc[random.sample(range(1000), 15), "quantity"] = -1            # invalid quantity
df.loc[random.sample(range(1000), 10), "customer_id"] = None       # missing customer
df.loc[random.sample(range(1000), 8), "order_date"] = "not-a-date"  # bad date
df = pd.concat([df, df.sample(12, random_state=1)], ignore_index=True)  # duplicate rows

os.makedirs("data", exist_ok=True)
df.to_csv("data/raw_sales.csv", index=False)
print(f"Wrote data/raw_sales.csv with {len(df)} rows")
