import os, sys, json, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import requests
from config import DEFAULT_TARGET_TICKERS, DATA_OUTPUT_DIR, STOCKS_OUTPUT_DIR, JPX_LISTED_COMPANIES_URL, CACHE_DIR
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

def process_single_ticker(item, ai_gen):
    code, name, sector = item["code"], item["name"], item["sector"]
    try:
        metrics = QuantEngine.calculate_stock_metrics(code, name, sector)
        if not metrics:
            return None
        seo_content = ai_gen.generate_or_load_seo_content(metrics)
        with open(STOCKS_OUTPUT_DIR / f"{code}.json", "w", encoding="utf-8") as f:
            json.dump({"metrics": metrics, "seo": seo_content}, f, ensure_ascii=False, indent=2)
        summary_entry = {
            k: metrics[k] for k in [
                "code", "name", "sector", "current_price_yen", "min_s_kabu_yen",
                "dividend_yield_pct", "annual_volatility_pct", "geometric_growth_pct",
                "sharpe_ratio", "quant_score", "updated_at"
            ]
        }
        time.sleep(0.2)
        return summary_entry
    except Exception as e:
        print(f"[WARN] Skipped {code}: {e}")
        return None

def run_batch(use_all=False):
    ai_gen = AIGenerator()
    tickers = fetch_all_jpx_tickers() if use_all else DEFAULT_TARGET_TICKERS
    summary_index = []
    sector_groups = defaultdict(list)
    total = len(tickers)
    print(f"[INFO] Starting batch processing for {total} stocks (use_all={use_all})...")

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_item = {executor.submit(process_single_ticker, item, ai_gen): item for item in tickers}
        for idx, future in enumerate(as_completed(future_to_item), start=1):
            item = future_to_item[future]
            res = future.result()
            if res:
                summary_index.append(res)
                sector_groups[res["sector"]].append(res)
                if idx % 25 == 0 or not use_all:
                    print(f"[{idx}/{total}] Processed {item['code']} ({item['name']})...")

    summary_index.sort(key=lambda x: x["quant_score"], reverse=True)
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
    print(f"[DONE] Successfully generated {len(summary_index)} stock pages.")

if __name__ == "__main__":
    use_all_flag = "--all" in sys.argv
    run_batch(use_all=use_all_flag)
