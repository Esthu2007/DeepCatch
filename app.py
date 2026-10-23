
"""DeepCatch - TinyFish-powered earbuds buying agent."""

import concurrent.futures as cf
import json
import os
import re

from flask import Flask, request, jsonify, send_from_directory
from tinyfish import TinyFish, CompleteEvent

app = Flask(__name__, static_folder="static")
client = TinyFish()

CACHE = "cache.json"

STORES = {
    "Flipkart": "https://www.flipkart.com/search?q={q}"
}

GOAL = """
Extract the first 6 true wireless earbuds (not neckbands,
cases or accessories) priced at most {budget} INR.

Do not log in and do not click Buy or Add to cart.

Return valid JSON with this structure:
{{"products": [
  {{
    "name": "product name",
    "brand": "brand name",
    "price": 1500,
    "mrp": null,
    "rating": null,
    "review_count": null,
    "url": "product URL",
    "seller": null,
    "delivery": null
  }}
]}}

Prices must be plain numbers in INR.
"""


@app.route("/")
def home():
    return send_from_directory(app.static_folder, "index.html")


def parse_budget(query):
    match = re.search(
        r"(?:under|below|upto|up to|within|<)\s*₹?\s*([\d,]+)\s*(k)?",
        query.lower()
    )

    if not match:
        return 3000

    amount = int(match.group(1).replace(",", ""))
    return amount * 1000 if match.group(2) else amount


def run_store(store, url_template, query, budget):
    url = url_template.format(q=query.replace(" ", "+"))

    print(f"[{store}] Starting TinyFish search...")

    try:
        with client.agent.stream(
            url=url,
            goal=GOAL.format(budget=budget)
        ) as stream:
            print(f"[{store}] Stream opened; waiting for results...")

            for event in stream:
                if isinstance(event, CompleteEvent):
                    result = event.result_json

                    if isinstance(result, str):
                        print(f"[{store}] Received result JSON.")
                        result = json.loads(result)

                    if isinstance(result, dict):
                        products = result.get("products", [])
                    else:
                        products = []

                    if not isinstance(products, list):
                        products = []

                    valid_products = []

                    for product in products:
                        if not isinstance(product, dict):
                            continue

                        product["store"] = store
                        valid_products.append(product)

                    print(
                        f"[{store}] Products received: "
                        f"{len(valid_products)}"
                    )

                    return valid_products

        print(f"[{store}] Stream ended without a completion event.")

    except Exception as error:
        print(f"[{store}] Search failed: {error}")

    return []


def num(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def enrich(products, budget):
    # Keep products with valid prices within the requested budget.
    filtered = []

    for product in products:
        price = num(product.get("price"))

        if 0 < price <= budget:
            product["price"] = price
            filtered.append(product)

    if not filtered:
        return []

    prices = [p["price"] for p in filtered]
    low, high = min(prices), max(prices)

    for product in filtered:
        price = num(product.get("price"))
        mrp = num(product.get("mrp"))
        rating = num(product.get("rating"))
        reviews = num(product.get("review_count"))

        flags = []

        # A smoothed rating avoids overvaluing products with few reviews.
        bayes = (
            (rating * reviews + 4.0 * 50) / (reviews + 50)
            if rating > 0
            else 3.0
        )

        trust = 1.0

        if mrp > price > 0:
            discount = 1 - price / mrp
            product["discount_pct"] = round(discount * 100)

            if discount > 0.70:
                flags.append("Discount may be inflated")
                trust -= 0.4

        if reviews < 100:
            flags.append("Few reviews - rating is less reliable")
            trust -= 0.3

        if rating > 0 and rating < 3.8:
            flags.append("Below-average rating")
            trust -= 0.2

        product["f_price"] = (
            1.0
            if high == low
            else round(1 - (price - low) / (high - low), 3)
        )

        product["f_rating"] = round(
            max(0, min(1, (bayes - 3.0) / 2.0)), 3
        )

        product["f_trust"] = round(max(0, trust), 3)
        product["flags"] = flags

    # Put higher-quality candidates first.
    filtered.sort(
        key=lambda p: (
            0.4 * p["f_price"]
            + 0.35 * p["f_rating"]
            + 0.25 * p["f_trust"]
        ),
        reverse=True
    )

    return filtered


@app.post("/api/search")
def search():
    data = request.get_json(silent=True) or {}

    query = data.get("query", "").strip() or "earbuds under 2000"
    budget = parse_budget(query)

    # Remove the budget phrase to form the store search query.
    base = re.sub(
        r"(?:under|below|upto|up to|within)\s*₹?\s*[\d,]+\s*k?",
        "",
        query,
        flags=re.IGNORECASE
    ).strip() or "earbuds"

    products = []

    executor = cf.ThreadPoolExecutor(max_workers=len(STORES))

    futures = {
        executor.submit(
            run_store, store, template, base, budget
        ): store
        for store, template in STORES.items()
    }

    try:
        done, pending = cf.wait(
            futures,
            timeout=180,
            return_when=cf.ALL_COMPLETED
        )

        for future in done:
            store = futures[future]

            try:
                products.extend(future.result())
            except Exception as error:
                print(f"[{store}] failed: {error}")

        for future in pending:
            store = futures[future]
            print(
                f"[{store}] Timed out after 180 seconds. "
                "Returning available results."
            )
            future.cancel()

    finally:
        # Do not make Flask wait for unfinished background searches.
        executor.shutdown(wait=False, cancel_futures=True)

    products = enrich(products, budget)
    source = "live"

    if products:
        try:
            with open(CACHE, "w", encoding="utf-8") as file:
                json.dump(
                    {"budget": budget, "products": products},
                    file,
                    ensure_ascii=False
                )
        except OSError as error:
            print(f"Could not save cache: {error}")

    elif os.path.exists(CACHE):
        try:
            with open(CACHE, encoding="utf-8") as file:
                cached = json.load(file)

            # Only reuse cached results for the same budget.
            if cached.get("budget") == budget:
                products = cached.get("products", [])
                source = "cached"

        except (OSError, json.JSONDecodeError) as error:
            print(f"Could not read cache: {error}")

    return jsonify({
        "query": query,
        "budget": budget,
        "source": source,
        "products": products
    })


if __name__ == "__main__":
    app.run(port=5000, debug=False)
