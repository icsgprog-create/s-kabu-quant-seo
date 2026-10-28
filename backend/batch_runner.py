import os, json, time
from collections import defaultdict
from config import DEFAULT_TARGET_TICKERS, DATA_OUTPUT_DIR, STOCKS_OUTPUT_DIR
from quant_engine import QuantEngine
from ai_generator import AIGenerator

def run_batch():
    ai_gen = AIGenerator()
    summary_index = []
    sector_groups = defaultdict(list)
    print(f"[INFO] Starting batch processing for {len(DEFAULT_TARGET_TICKERS)} test stocks...")
    for idx, item in enumerate(DEFAULT_TARGET_TICKERS, start=1):
        code, name, sector = item["code"], item["name"], item["sector"]
        print(f"[{idx}/{len(DEFAULT_TARGET_TICKERS)}] Processing {code} ({name})...")
        metrics = QuantEngine.calculate_stock_metrics(code, name, sector)
        if not metrics: continue
        seo_content = ai_gen.generate_or_load_seo_content(metrics)
        with open(STOCKS_OUTPUT_DIR / f"{code}.json", "w", encoding="utf-8") as f:
            json.dump({"metrics": metrics, "seo": seo_content}, f, ensure_ascii=False, indent=2)
        summary_entry = {k: metrics[k] for k in ["code", "name", "sector", "current_price_yen", "min_s_kabu_yen", "dividend_yield_pct", "annual_volatility_pct", "geometric_growth_pct", "sharpe_ratio", "quant_score", "updated_at"]}
        summary_index.append(summary_entry)
        sector_groups[sector].append(summary_entry)
        time.sleep(0.5)

    summary_index.sort(key=lambda x: x["quant_score"], reverse=True)
    with open(DATA_OUTPUT_DIR / "index.json", "w", encoding="utf-8") as f:
        json.dump(summary_index, f, ensure_ascii=False, indent=2)
    sectors_payload = {}
    for sec_name, items in sector_groups.items():
        sectors_payload[sec_name] = {"sector_name": sec_name, "stock_count": len(items), "avg_dividend_yield_pct": round(sum(x["dividend_yield_pct"] for x in items)/len(items), 2), "avg_volatility_pct": round(sum(x["annual_volatility_pct"] for x in items)/len(items), 2), "stocks": sorted(items, key=lambda x: x["dividend_yield_pct"], reverse=True)}
    with open(DATA_OUTPUT_DIR / "sectors.json", "w", encoding="utf-8") as f:
        json.dump(sectors_payload, f, ensure_ascii=False, indent=2)
    print(f"[DONE] Generated {len(summary_index)} stock pages.")

if __name__ == "__main__":
    run_batch()
