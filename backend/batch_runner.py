import os, sys, json, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import requests
from config import (
    DEFAULT_TARGET_TICKERS, DATA_OUTPUT_DIR, STOCKS_OUTPUT_DIR,
    JPX_LISTED_COMPANIES_URL, CACHE_DIR,
    AI_BATCH_SIZE, AI_REQUEST_INTERVAL_SEC, MAX_AI_CALLS_PER_RUN
)
from quant_engine import QuantEngine
from ai_generator import AIGenerator

def fetch_all_jpx_tickers():
    xls_path = CACHE_DIR / "data_j.xls"
    if not xls_path.exists() or (time.time() - xls_path.stat().st_mtime) > 86400 * 7:
        print("[INFO] Downloading JPX listed companies list...")
        resp = requests.get(JPX_LISTED_COMPANIES_URL, timeout=30)
        resp.raise_for_status()
        xls_path.write_bytes(resp.content)
    df = pd.read_excel(xls_path)
    target_markets = ["プライム（内国株式）", "スタンダード（内国株式）", "グロース（内国株式）"]
    df = df[df["市場・商品区分"].isin(target_markets)]
    tickers = []
    for _, row in df.iterrows():
        code = str(row["コード"]).strip()
        name = str(row["銘柄名"]).strip()
        sector = str(row["33業種区分"]).strip()
        if sector == "-" or not sector:
            sector = "その他"
        tickers.append({"code": code, "name": name, "sector": sector})
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
        print(f"[WARN] Skipped {code}: {e}")
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
