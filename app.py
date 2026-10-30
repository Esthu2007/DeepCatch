"""DeepCatch v3 - TinyFish agents fetch live listings; filtering/sorting happens in the browser.
Run: set TINYFISH_API_KEY, then  python app.py
"""
import concurrent.futures as cf
import hashlib, json, os, re, threading, time, uuid
from copy import deepcopy
from urllib.parse import quote_plus

from flask import Flask, request, jsonify, send_from_directory
from tinyfish import TinyFish, CompleteEvent

app = Flask(__name__, static_folder="static")
# TIMEOUT: seconds before unfinished stores are dropped. Results show per store as they finish.
CACHE, TIMEOUT, TTL, MAX_STORES, PER_STORE, DEFAULT_ON = "cache.json", 240, 1800, 10, 5, 4

# First DEFAULT_ON are pre-selected. VERIFY each URL in a browser; delete any that fail.
STORES = {
    "Flipkart": "https://www.flipkart.com/search?q={q}",
    "Amazon": "https://www.amazon.in/s?k={q}",
    "Croma": "https://www.croma.com/searchB?q={q}",
    "Reliance Digital": "https://www.reliancedigital.in/search?q={q}",
    "Tata CLiQ": "https://www.tatacliq.com/search/?searchCategory=all&text={q}",
    "Snapdeal": "https://www.snapdeal.com/search?keyword={q}",
    "Vijay Sales": "https://www.vijaysales.com/search/{q}",
    "Meesho": "https://www.meesho.com/search?q={q}",
    "Ajio": "https://www.ajio.com/search/?text={q}",
    "Nykaa": "https://www.nykaa.com/search/result/?q={q}",
    "Pepperfry": "https://www.pepperfry.com/site_product/search?q={q}",
    "Decathlon": "https://www.decathlon.in/search?Ntt={q}",
}

jobs, lock = {}, threading.Lock()
pool = cf.ThreadPoolExecutor(max_workers=30)


def num(v, d=0.0):
    try:
        if isinstance(v, str):
            m = re.search(r"-?\d+(?:\.\d+)?", v.replace(",", ""))
            return float(m.group()) if m else d
        return float(v) if v is not None else d
    except (TypeError, ValueError):
        return d


def build_goal(query):
    return (
        f'This is a store search results page for: "{query}". Be FAST: read only the first screen '
        "of results (scroll at most once), never open product pages, never log in or add to cart. "
        f"Skip ads, sponsored items, accessories and unrelated products. Return up to {PER_STORE} real matching "
        "products. Use only visible info, null if missing. JSON only: "
        '{"products":[{"name":str,"brand":str|null,"price":number,"mrp":number|null,'
        '"rating":number|null,"review_count":number|null,"url":str|null,"delivery":str|null}]}. '
        "Prices are plain INR numbers."
    )


def run_store(store, query):
    url = STORES[store].format(q=quote_plus(query))
    client = TinyFish()  # one client per thread
    with client.agent.stream(url=url, goal=build_goal(query)) as stream:
        for ev in stream:
            if isinstance(ev, CompleteEvent):
                r = ev.result_json
                r = json.loads(r) if isinstance(r, str) else r
                out = []
                for p in (r or {}).get("products", []):
                    if not isinstance(p, dict) or not p.get("name"):
                        continue
                    p["store"] = store
                    for k in ("price", "mrp", "rating", "review_count"):
                        p[k] = num(p.get(k))
                    if p["price"] > 0:
                        out.append(p)
                return out
    return []


def worker(job_id, store):
    try:
        items, state = run_store(store, jobs[job_id]["query"]), "completed"
    except Exception as e:
        print(f"[{store}] failed: {e}")
        items, state = [], "failed"
    with lock:
        j = jobs.get(job_id)
        if j and j["stores"].get(store) == "searching":  # ignore late results after timeout
            j["products"].extend(items)
            j["stores"][store] = state


def dedupe(products):
    seen, out = set(), []
    for p in products:
        k = (p["store"], p["name"].lower())
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out


def load_cache():
    try:
        return json.load(open(CACHE, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_cache(key, products):
    c = load_cache()
    c[key] = {"ts": time.time(), "products": products}
    json.dump(c, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)


@app.get("/")
def home():
    return send_from_directory("static", "index.html")


@app.get("/api/config")
def config():
    return jsonify({"stores": [{"name": s, "default": i < DEFAULT_ON} for i, s in enumerate(STORES)],
                    "max_stores": MAX_STORES, "timeout": TIMEOUT})


@app.post("/api/search")
def search():
    d = request.get_json(silent=True) or {}
    query = str(d.get("query", "")).strip()
    stores = [s for s in d.get("stores", []) if s in STORES][:MAX_STORES]
    if not query: return jsonify({"error": "Enter what you want to buy."}), 400
    if not stores: return jsonify({"error": "Pick at least one store."}), 400
    key = hashlib.sha1(json.dumps([query.lower(), sorted(stores)]).encode()).hexdigest()
    hit = load_cache().get(key)
    job = {"query": query, "key": key, "products": [], "started": time.time(), "saved": False,
           "stores": {s: "searching" for s in stores}, "cached": False}
    if hit and time.time() - hit["ts"] < TTL:  # repeat search = instant
        job.update(products=hit["products"], stores={s: "completed" for s in stores}, cached=True, saved=True)
    job_id = str(uuid.uuid4())
    with lock:
        jobs[job_id] = job
    if not job["cached"]:
        for s in stores:
            pool.submit(worker, job_id, s)
    return jsonify({"job_id": job_id}), 202


@app.get("/api/search/<job_id>")
def status(job_id):
    with lock:
        job = jobs.get(job_id)
        if not job: return jsonify({"error": "Search not found."}), 404
        if time.time() - job["started"] > TIMEOUT:
            for s, v in job["stores"].items():
                if v == "searching": job["stores"][s] = "timed out"
        snap = deepcopy(job)
        done = "searching" not in snap["stores"].values()
        products = dedupe(snap["products"])
        if done and not job["saved"]:
            job["saved"] = True
            if products: save_cache(job["key"], products)
    source = "cached" if snap["cached"] else "live"
    if done and not products:  # nothing live: fall back to any older saved run
        old = load_cache().get(snap["key"])
        if old: products, source = old["products"], "cached"
    return jsonify({"products": products, "stores": snap["stores"], "done": done, "source": source,
                    "elapsed": round(time.time() - snap["started"], 1)})


if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5000)), debug=False, threaded=True)
