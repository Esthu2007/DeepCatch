# DeepCatch

**Dive deep. Catch the best buy.**

DeepCatch is an AI shopping agent built for the **Swim with TinyFish** hackathon (presented by TinyFish, organised by Ignite Room, Presidency University, Bangalore, 30 Oct 2026). You type any product, pick the stores, and TinyFish web agents read the live store pages and bring the results back into one view you can filter, sort and trust-check.

## The problem

Buying something online means opening a dozen store tabs, comparing prices and ratings by hand, and still not knowing which discounts and reviews to trust. Comparison sites depend on stored feeds and fixed store lists, and they rarely tell you which listings to be careful about.

## The solution

1. **Search.** Type any product and choose up to 10 stores.
2. **TinyFish agents browse.** One TinyFish web agent per store opens the live search page and returns structured data: name, brand, price, MRP, rating, review count, delivery and link.
3. **Compare and filter.** Filter by price, brand, store, rating, number of reviews, trust, deals and delivery. Sort by best match, price, rating, reviews, trust or discount. The page shows the top 10 matches.
4. **Trust check.** Every listing gets a 0 to 100 trust score from review volume, rating, suspiciously large discounts and unusual prices. The reasons are shown on the card, and the top pick has a short "why it ranks first" line.

## How TinyFish powers it

TinyFish is the core of the app. Every product on screen was read from a live store page by a TinyFish agent: there is no product database and no hand-written scraper per store. The agent takes a plain-English goal and a URL, so a new store only needs a search URL added to `STORES` in `app.py`.

## Tech stack

- **Backend:** Python, Flask
- **Web agents:** TinyFish Agent API (Python SDK)
- **Concurrency:** Python threads plus a semaphore that queues agents to match the plan limit
- **Storage:** a local `cache.json` file for saved searches (no database)
- **Frontend:** plain HTML, CSS and JavaScript in a single page; filtering, ranking and trust scoring run in the browser

## Project structure

```
deepcatch_v4/
  app.py          # Flask backend, TinyFish agent calls, queue, cache
  seed_cache.py   # optional: loads real saved results for a demo (no API key needed)
  static/
    index.html    # the whole frontend
  cache.json      # created automatically (saved searches)
```

## Setup

You need Python 3.9+ and a TinyFish API key (from https://agent.tinyfish.ai/api-keys).

```bash
pip install tinyfish flask
```

Set the key as an environment variable. Never put it in the code.

```powershell
# Windows PowerShell
$env:TINYFISH_API_KEY="your-key"
```

```bash
# macOS / Linux
export TINYFISH_API_KEY="your-key"
```

Run the app:

```bash
python app.py
```

Open http://localhost:5000. To use another port, set `PORT` first (for example `$env:PORT=5060`).

### Optional: load saved demo results

`seed_cache.py` writes real results from earlier TinyFish runs (query: "wireless headphones", from Flipkart, Croma and Amazon) into `cache.json`. It needs no API key and makes no TinyFish calls.

```bash
python seed_cache.py
```

The saved search then appears as a clickable chip under the search bar and loads instantly.

## Using it

1. Type a product and tick the stores you want (open "Choose stores").
2. Press Search. Stores are checked as free agent slots become available, and results appear as each store finishes.
3. Use the sidebar filters and the sort menu. Hover over a trust badge to see why it scored that way.
4. Searches are saved automatically and shown as chips for instant, free repeats (valid for 24 hours).

## Limits and honest notes

- **Speed.** A live search takes minutes, not seconds. The TinyFish plan used for this prototype runs 2 agents at a time (`CONCURRENCY = 2` in `app.py`), and each agent takes roughly one to two and a half minutes. Extra stores wait in the app's queue. With a higher concurrency plan, change that one number and stores run in parallel.
- **One live search at a time.** This protects credits, because every agent step costs money. Saved searches are free.
- **Store pages change.** Some sites may block agents or change layout. A store that fails shows its error in the progress panel and doesn't stop the others. Verify each store's search URL in `STORES` before relying on it.
- **Trust score is a rule of thumb**, not a guarantee. It uses only what is visible on the listing page (no price history, no review authenticity checks). Always verify prices and details on the store before buying.
- **Not a production server.** It uses Flask's development server, an in-memory job list and a local JSON cache.
- If the server stops, the page shows a red "Server is down" banner. If the API key is missing, it shows a warning and live searches are disabled; saved searches still work.

## Roadmap

- More stores running in parallel on a higher concurrency plan
- Product-page checks with TinyFish agents for seller, delivery and warranty
- Price-drop alerts
- A chat interface and LLM layer for plain-English requests and short explanations
- Production deployment with access control and rate limits



## Acknowledgements

Thanks to TinyFish and Ignite Room for the workshop and hackathon, and to the mentors on the floor.
