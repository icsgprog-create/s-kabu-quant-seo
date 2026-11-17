import io, os, re, sys, json, time
from html import unescape
from urllib.parse import urljoin
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import requests
from config import (
    DEFAULT_TARGET_TICKERS, DATA_OUTPUT_DIR, STOCKS_OUTPUT_DIR,
    CACHE_DIR, AI_BATCH_SIZE, AI_REQUEST_INTERVAL_SEC, MAX_AI_CALLS_PER_RUN
)
from quant_engine import QuantEngine
from ai_generator import AIGenerator

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

SECTORS_33 = {
    1: "水産・農林業", 2: "鉱業", 3: "建設業", 4: "食料品", 5: "繊維製品",
    6: "パルプ・紙", 7: "化学", 8: "医薬品", 9: "石油・石炭製品", 10: "ゴム製品",
    11: "ガラス・土石製品", 12: "鉄鋼", 13: "非鉄金属", 14: "金属製品", 15: "機械",
    16: "電気機器", 17: "輸送用機器", 18: "精密機器", 19: "その他製品", 20: "電気・ガス業",
    21: "陸運業", 22: "海運業", 23: "空運業", 24: "倉庫・運輸関連業", 25: "情報・通信業",
    26: "卸売業", 27: "小売業", 28: "銀行業", 29: "証券、商品先物取引業", 30: "保険業",
    31: "その他金融業", 32: "不動産業", 33: "サービス業"
}

def _try_fetch_from_jpx() -> list[dict]:
    jpx_pages = [
        "https://www.jpx.co.jp/markets/statistics-equities/misc/01.html",
        "https://www.jpx.co.jp/markets/statistics-equities/misc/index.html",
    ]
    xls_urls = []
    for page_url in jpx_pages:
        try:
            r = requests.get(page_url, headers=BROWSER_HEADERS, timeout=15)
            if r.status_code == 200:
                matches = re.findall(r'href=["\']([^"\']*\.xls[x]?)["\']', r.text, re.IGNORECASE)
                for m in matches:
                    full_url = urljoin(page_url, m)
                    if full_url not in xls_urls:
                        xls_urls.append(full_url)
        except Exception:
            pass

    for xls_url in xls_urls:
        try:
            print(f"[INFO] Trying JPX Excel URL: {xls_url}")
            resp = requests.get(xls_url, headers=BROWSER_HEADERS, timeout=30)
            if resp.status_code != 200:
                continue
            df = pd.read_excel(io.BytesIO(resp.content))
            if "コード" not in df.columns or "銘柄名" not in df.columns:
                continue
            if "市場・商品区分" in df.columns:
                df = df[df["市場・商品区分"].astype(str).str.contains("内国株式", na=False)]
            tickers = []
            for _, row in df.iterrows():
                code = str(row["コード"]).strip().split(".")[0]
                name = str(row["銘柄名"]).strip()
                sector = str(row.get("33業種区分", "その他")).strip()
                if sector in ("-", "", "nan"):
                    sector = "その他"
                if re.match(r"^[0-9A-Z]{4}$", code):
                    tickers.append({"code": code, "name": name, "sector": sector})
            if len(tickers) > 1000:
                return tickers
        except Exception as e:
            print(f"[WARN] Failed reading JPX file {xls_url}: {e}")
    return []

def _crawl_single_industry(ind_id: int, sector_name: str) -> list[dict]:
    items = []
    seen_in_sector = set()
    for page in range(1, 45):
        url = f"https://kabutan.jp/themes/?industry={ind_id}&market=0&capitalization=-1&stc=&stm=0&page={page}"
        try:
            r = requests.get(url, headers=BROWSER_HEADERS, timeout=15)
            if r.status_code != 200:
                break
            rows = re.findall(r"<tr[^>]*>(.*?)</tr>", r.text, re.DOTALL | re.IGNORECASE)
            added_on_page = 0
            for row_html in rows:
                code_match = re.search(r'/stock/\?code=([0-9A-Z]{4})', row_html)
                if not code_match:
                    continue
                code = code_match.group(1)
                if code in seen_in_sector:
                    continue
                cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.DOTALL | re.IGNORECASE)
                clean_cells = [
                    unescape(re.sub(r"<[^>]+>", "", c)).strip()
                    for c in cells
                ]
                clean_cells = [c for c in clean_cells if c]
                name = ""
                if len(clean_cells) >= 2 and clean_cells[0] == code:
                    name = clean_cells[1]
                else:
                    for c in clean_cells:
                        if c != code and len(c) > 1 and not re.match(r"^[0-9.,+\-%]+$", c):
                            name = c
                            break
                if name:
                    seen_in_sector.add(code)
                    items.append({"code": code, "name": name, "sector": sector_name})
                    added_on_page += 1
            if added_on_page == 0:
                break
            time.sleep(0.15)
        except Exception:
            break
    return items

def _try_fetch_from_kabutan() -> list[dict]:
    print("[INFO] Fetching all listed stocks across 33 TSE sectors from Kabutan fallback...")
    all_tickers = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(_crawl_single_industry, ind_id, sec_name): sec_name
            for ind_id, sec_name in SECTORS_33.items()
        }
        for future in as_completed(futures):
            sec_name = futures[future]
            res = future.result()
            for item in res:
                all_tickers[item["code"]] = item
            print(f"  -> Loaded {len(res)} stocks for sector: {sec_name} (Total unique: {len(all_tickers)})")
    return list(all_tickers.values())

def fetch_all_jpx_tickers() -> list[dict]:
    cache_json = CACHE_DIR / "jpx_tickers.json"
    if cache_json.exists() and (time.time() - cache_json.stat().st_mtime) < 86400 * 7:
        try:
            with open(cache_json, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if len(cached) > 1000:
                print(f"[INFO] Loaded {len(cached)} tickers from local cache.")
                return cached
        except Exception:
            pass

    tickers = _try_fetch_from_jpx()
    if len(tickers) < 1000:
        tickers = _try_fetch_from_kabutan()

    if len(tickers) < 100:
        raise RuntimeError("Failed to retrieve ticker list from both JPX and fallback sources.")

    with open(cache_json, "w", encoding="utf-8") as f:
        json.dump(tickers, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Cached {len(tickers)} listed stocks to {cache_json}.")
    return tickers

def calc_single_quant(item, ai_gen):
    code, name, sector = item["code"], item["name"], item["sector"]
    try:
        metrics = QuantEngine.calculate_stock_metrics(code, name, sector)
        if not metrics:
            return None
        existing_seo = ai_gen.load_valid_existing_seo(code, metrics)
        seo_content = existing_seo if existing_seo else ai_gen.build_fallback_content(metrics)
        with open(STOCKS_OUTPUT_DIR / f"{code}.json", "w", encoding="utf-8") as f:
            json.dump({"metrics": metrics, "seo": seo_content}, f, ensure_ascii=False, indent=2)
        time.sleep(0.15)
        return {"metrics": metrics, "needs_ai": existing_seo is None}
    except Exception as e:
        return None

def run_batch(use_all=False):
    ai_gen = AIGenerator()
    tickers = fetch_all_jpx_tickers() if use_all else DEFAULT_TARGET_TICKERS
    total = len(tickers)
    print(f"[PHASE 1] Calculating quantitative metrics for {total} stocks...")

    all_metrics = []
    pending_ai_metrics = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_item = {executor.submit(calc_single_quant, item, ai_gen): item for item in tickers}
        for idx, future in enumerate(as_completed(future_to_item), start=1):
            res = future.result()
            if res:
                all_metrics.append(res["metrics"])
                if res["needs_ai"]:
                    pending_ai_metrics.append(res["metrics"])
            if idx % 50 == 0 or idx == total:
                print(f"  -> Quant progress: {idx}/{total} (valid: {len(all_metrics)})")

    all_metrics.sort(key=lambda x: x["quant_score"], reverse=True)
    pending_ai_metrics.sort(key=lambda x: x["quant_score"], reverse=True)

    if ai_gen.client and pending_ai_metrics:
        max_stocks = MAX_AI_CALLS_PER_RUN * AI_BATCH_SIZE
        target_ai_list = pending_ai_metrics[:max_stocks]
        total_batches = (len(target_ai_list) + AI_BATCH_SIZE - 1) // AI_BATCH_SIZE
        print(f"[PHASE 2] Enriching {len(target_ai_list)} stocks via Gemini API in {total_batches} bulk requests...")

        for b_idx in range(total_batches):
            chunk = target_ai_list[b_idx * AI_BATCH_SIZE : (b_idx + 1) * AI_BATCH_SIZE]
            codes_str = ",".join(m["code"] for m in chunk)
            print(f"  -> AI Batch [{b_idx + 1}/{total_batches}] codes: {codes_str}")
            batch_results = ai_gen.generate_batch_seo(chunk)
            for m in chunk:
                c = m["code"]
                if c in batch_results:
                    with open(STOCKS_OUTPUT_DIR / f"{c}.json", "w", encoding="utf-8") as f:
                        json.dump({"metrics": m, "seo": batch_results[c]}, f, ensure_ascii=False, indent=2)
            if b_idx + 1 < total_batches:
                time.sleep(AI_REQUEST_INTERVAL_SEC)
    else:
        print("[PHASE 2] Skipping Gemini API calls (no API key set or all stocks already cached).")

    summary_index = []
    sector_groups = defaultdict(list)
    for m in all_metrics:
        summary_entry = {
            k: m[k] for k in [
                "code", "name", "sector", "current_price_yen", "min_s_kabu_yen",
                "dividend_yield_pct", "annual_volatility_pct", "geometric_growth_pct",
                "sharpe_ratio", "quant_score", "updated_at"
            ]
        }
        summary_index.append(summary_entry)
        sector_groups[m["sector"]].append(summary_entry)

    with open(DATA_OUTPUT_DIR / "index.json", "w", encoding="utf-8") as f:
        json.dump(summary_index, f, ensure_ascii=False, indent=2)

    sectors_payload = {}
    for sec_name, items in sector_groups.items():
        sectors_payload[sec_name] = {
            "sector_name": sec_name,
            "stock_count": len(items),
            "avg_dividend_yield_pct": round(sum(x["dividend_yield_pct"] for x in items) / len(items), 2),
            "avg_volatility_pct": round(sum(x["annual_volatility_pct"] for x in items) / len(items), 2),
            "stocks": sorted(items, key=lambda x: x["dividend_yield_pct"], reverse=True)
        }
    with open(DATA_OUTPUT_DIR / "sectors.json", "w", encoding="utf-8") as f:
        json.dump(sectors_payload, f, ensure_ascii=False, indent=2)

    print(f"[DONE] Generated {len(summary_index)} total stock pages safely.")

if __name__ == "__main__":
    use_all_flag = "--all" in sys.argv
    run_batch(use_all=use_all_flag)
