"""Loads REAL results from your completed TinyFish runs (query: "wireless headphones") into cache.json.
No API key needed, and it makes no TinyFish calls, so it costs nothing.

Run it from inside the deepcatch_v4 folder, next to app.py:
    python seed_cache.py
Then start the app. You will see a "Saved searches" chip you can click for an instant result.
"""
import hashlib, itertools, json, time

F, C, A = "Flipkart", "Croma", "Amazon"
FK, CR, AM = "https://www.flipkart.com/", "https://www.croma.com/", "https://www.amazon.in/"
# (store, name, brand, price, mrp, rating, review_count, delivery, url)
ROWS = [
    (F, "boAt Rockerz 110 with 40 HRS Playback, ENx Technology, Beast Mode & ASAP Charge Bluetooth", "boAt", 699, 2490, 4.1, 224080, None, FK + "boat-rockerz-110-40-hrs-playback-enx-technology-beast-mode-asap-charge-bluetooth/p/itm1707c9f88f559"),
    (F, "TRIGGR Arcus One 60H Battery, 4 Mic ENC, Dual Pairing, Rubber Grip, 13mm Drivers, v6.0 Bluetooth", "TRIGGR", 799, 4999, 4.0, 5737, None, FK + "triggr-arcus-one-60h-battery-4-mic-enc-dual-pairing-rubber-grip-13mm-drivers-v6-0-bluetooth/p/itmc75b69ddbd3df"),
    (F, "Noise Buds F1, 50H playtime, Matte finish Case, Quad Mic with ENC, In-built EQ Modes Bluetooth", "Noise", 899, 3499, 3.9, 23019, None, FK + "noise-buds-f1-50h-playtime-matte-finish-case-quad-mic-enc-in-built-eq-modes-bluetooth/p/itm0eae964f93f1c"),
    (F, "boAt Rockerz 411, 40H Battery, 40ms Latency, Stream Ad Free Music via App, BT v5.4 Bluetooth", "boAt", 1099, 2999, 4.1, 8527, None, FK + "boat-rockerz-411-40h-battery-40ms-latency-stream-ad-free-music-via-app-bt-v5-4-bluetooth/p/itmf824790d6dde3"),
    (F, "Noise TWO with 50 Hours Playtime, Low latency (up to 42ms), and Dual pairing Wireless Bluetooth", "Noise", 1699, 4999, 4.0, 21118, None, FK + "noise-two-50-hours-playtime-low-latency-up-42ms-dual-pairing-wireless-bluetooth/p/itm0b5799a64b0aa"),
    (C, "SONY 1000X Series WH-1000XM6 Bluetooth Headphone with Mic (Adaptive Noise Cancellation, Over Ear, Black)", "SONY", 35990, 49990, 4.8, 8, "Standard Delivery by Wed, 4th Nov", CR + "sony-1000x-series-wh-1000xm6-bluetooth-headphone-with-mic-adaptive-noise-cancellation-over-ear-black-/p/319022"),
    (C, "SONY WH-1000XM5 Bluetooth Headphone with Mic (Auto Noise Cancellation Optimizer, Over Ear, Black)", "SONY", 19989, 34990, 4.6, 41, "Express Delivery by today", CR + "sony-wh-1000xm5-bluetooth-headphone-with-mic-auto-noise-cancellation-optimizer-over-ear-black-/p/262565"),
    (C, "SONY 1000X Series WH-1000XM6 Bluetooth Headphone with Mic (Adaptive Noise Cancellation, Over Ear, Midnight Blue)", "SONY", 35990, 49990, 3.0, 2, "Standard Delivery by Mon, 2nd Nov", CR + "sony-1000x-series-wh-1000xm6-bluetooth-headphone-with-mic-adaptive-noise-cancellation-over-ear-midnight-blue-/p/319024"),
    (C, "Croma HE101 Bluetooth Headphone with Mic (Environmental Noise Cancellation, Over Ear, Black)", "Croma", 1299, 3000, 4.6, 12, "Express Delivery by today", CR + "croma-he101-bluetooth-headphone-with-mic-environmental-noise-cancellation-over-ear-black-/p/316208"),
    (C, "SONY WH-CH720N Bluetooth Headphone with Mic (Digital Sound Enhancement Engine, Over Ear, Pink)", "SONY", 7390, 14990, 5.0, 2, "Standard Delivery by Mon, 2nd Nov", CR + "sony-wh-ch720n-bluetooth-headphone-with-mic-digital-sound-enhancement-engine-over-ear-pink-/p/315745"),
    (A, "ZEBRONICS Thunder Neo Wireless Headphone, BT v6.0, True 50hrs Playback, 40mm Driver, ENC", "ZEBRONICS", 599, 1899, 4.0, 637, None, AM + "ZEBRONICS-Thunder-Neo-Headphone-Assistant/dp/B0HK7H7DSD"),
    (A, "boAt Rockerz 411, 40Ms Low Latency, 40Hrs Battery, 40Mm Drivers, Bluetooth Headphones with Mic", "boAt", 1099, 2999, 4.2, 29413, None, AM + "boAt-Bluetooth-Headphones-Wireless-Headphone/dp/B0FC2Y8XYF"),
    (A, "boAt Rockerz 255 Pro+, 60H Battery, Fast Charge, IPX7, Dual Pair, Low Latency, Magnetic Buds, Neckband Earphones with Mic", "boAt", 999, 3990, 4.0, 207793, None, AM + "boAt-Rockerz-255-Pro-Earphones/dp/B08TV2P1N8"),
    (A, "boAt Rockerz 113, 40 Hours Battery, Dual Pair, Fast Charge, ENx Technology, Magnetic Buds, Bluetooth Neckband Earphones with Mic", "boAt", 699, 2490, 4.0, 14401, None, AM + "boAt-Rockerz-Magnetic-Bluetooth-Earphones/dp/B0F7Y54PJX"),
    (A, "pTron Studio Evo 70hrs Playtime Wireless Over Ear Headphones, HD Mic, Custom EQ, BT5.3, Type-C Fast Charging", "pTron", 693, 3199, 4.1, 3110, None, AM + "pTron-Studio-Headphones-Low-Latency-Assistant/dp/B0DQ212KP4"),
]
PRODUCTS = [dict(store=s, name=n, brand=b, price=p, mrp=m, rating=r, review_count=rc, delivery=d, url=u)
            for s, n, b, p, m, r, rc, d, u in ROWS]
QUERY = "wireless headphones"


def key(query, stores):  # must match app.py
    return hashlib.sha1(json.dumps([query.lower(), sorted(stores)]).encode()).hexdigest()


try:
    with open("cache.json", encoding="utf-8") as f:
        cache = json.load(f)
except (OSError, json.JSONDecodeError):
    cache = {}

ts = time.time() + 86400  # stays "fresh" for about two days
count = 0
for n in (1, 2, 3):
    for combo in itertools.combinations([F, C, A], n):
        items = [p for p in PRODUCTS if p["store"] in combo]
        cache[key(QUERY, combo)] = {"ts": ts, "query": QUERY, "stores": sorted(combo), "products": items}
        count += 1
with open("cache.json", "w", encoding="utf-8") as f:
    json.dump(cache, f, ensure_ascii=False)
print(f"Saved {count} saved searches for '{QUERY}' (any mix of Flipkart, Croma, Amazon).")
print("Start the app and click the 'wireless headphones' chip, or type it and tick those stores.")
