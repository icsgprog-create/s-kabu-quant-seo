import os, json, time
from datetime import datetime, timezone
from pydantic import BaseModel
from google import genai
from google.genai import types
from config import (
    STOCKS_OUTPUT_DIR, GEMINI_MODEL_NAME,
    AI_CACHE_EXPIRE_DAYS, AI_REGENERATE_CHANGE_THRESHOLD
)

class FAQItemSchema(BaseModel):
    question: str
    answer: str

class BatchStockSEOItem(BaseModel):
    code: str
    seo_title: str
    meta_description: str
    summary_points: list[str]
    accumulation_strategy_analysis: str
    dividend_and_risk_commentary: str
    faqs: list[FAQItemSchema]

class BatchStockSEOResponse(BaseModel):
    items: list[BatchStockSEOItem]

class AIGenerator:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        if self.api_key and self.api_key != "あなたのAPIキー":
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def load_valid_existing_seo(self, code: str, metrics: dict) -> dict | None:
        stock_file = STOCKS_OUTPUT_DIR / f"{code}.json"
        if not stock_file.exists():
            return None
        try:
            with open(stock_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            seo = data.get("seo", {})
            if not seo.get("is_ai_generated", False):
                return None
            gen_date_str = seo.get("generated_at", "2000-01-01")
            gen_date = datetime.strptime(gen_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - gen_date).days > AI_CACHE_EXPIRE_DAYS:
                return None
            prev_price = float(seo.get("snapshot_price_yen", 0))
            curr_price = float(metrics.get("current_price_yen", 0))
            if prev_price > 0 and (abs(curr_price - prev_price) / prev_price) >= AI_REGENERATE_CHANGE_THRESHOLD:
                return None
            return seo
        except Exception:
            return None

    def generate_batch_seo(self, metrics_list: list[dict]) -> dict[str, dict]:
        if not self.client or not metrics_list:
            return {}
        compact_inputs = [
            {
                "code": m["code"],
                "name": m["name"],
                "sector": m["sector"],
                "min_s_kabu_yen": m["min_s_kabu_yen"],
                "dividend_yield_pct": m["dividend_yield_pct"],
                "dps_yen": m["dps_yen"],
                "annual_volatility_pct": m["annual_volatility_pct"],
                "geometric_growth_pct": m["geometric_growth_pct"],
                "monthly_var_95_pct": m["monthly_var_95_pct"],
                "median_10y_yen": m["default_10y_projection"][-1]["median_yen"],
                "nisa_10k_shares": next((r["nisa_required_shares"] for r in m["dividend_roadmap"] if r["target_monthly_yen"] == 10000), 0),
                "nisa_10k_capital_yen": next((r["nisa_required_capital_yen"] for r in m["dividend_roadmap"] if r["target_monthly_yen"] == 10000), 0),
            }
            for m in metrics_list
        ]
        prompt = (
            "以下の日本株の定量データ配列から、各銘柄の単元未満株(1株)・新NISA積立・配当金に関するSEO解説データを日本語で作成してください。"
            "投資助言を避け、客観的な数値に基づく解説にしてください。\n"
            f"{json.dumps(compact_inputs, ensure_ascii=False)}"
        )
        try:
            res = self.client.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=BatchStockSEOResponse,
                    temperature=0.2,
                ),
            )
            parsed = json.loads(res.text)
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            price_map = {m["code"]: m["current_price_yen"] for m in metrics_list}
            results = {}
            for item in parsed.get("items", []):
                c = item["code"]
                item["is_ai_generated"] = True
                item["generated_at"] = today_str
                item["snapshot_price_yen"] = price_map.get(c, 0)
                results[c] = item
            return results
        except Exception as e:
            print(f"[WARN] Gemini batch API error (fallback maintained): {e}")
            return {}

    @staticmethod
    def build_fallback_content(metrics: dict) -> dict:
        name, code, price = metrics["name"], metrics["code"], metrics["min_s_kabu_yen"]
        div = metrics["dividend_yield_pct"]
        roadmap_10k = next((r for r in metrics["dividend_roadmap"] if r["target_monthly_yen"] == 10000), metrics["dividend_roadmap"][0])
        return {
            "seo_title": f"{name}({code})の単元未満株・NISA積立と配当金シミュレーション",
            "meta_description": f"{name}({code})を1株({price:,}円)から単元未満株で積立投資した場合の10年後資産推移を定量計算。",
            "summary_points": [
                f"最小{price:,}円（1株）から単元未満株で購入可能",
                f"過去5年の年率ボラティリティは{metrics['annual_volatility_pct']}%、幾何成長率は{metrics['geometric_growth_pct']}%",
                f"新NISAで月1万円の配当金を得るには{roadmap_10k['nisa_required_shares']:,}株（約{roadmap_10k['nisa_required_capital_yen']:,}円）が必要"
            ],
            "accumulation_strategy_analysis": f"{name}は単元未満株（S株・かぶミニ等）を利用することで1株（約{price:,}円）から定額積立が可能です。対数正規分布モデルに基づく月1万円積立時の10年後中央値予測は{metrics['default_10y_projection'][-1]['median_yen']:,}円となっています。",
            "dividend_and_risk_commentary": f"年間予想配当金は1株あたり{metrics['dps_yen']}円（利回り{div}%）です。月次95%VaR（最大想定損失率）は{metrics['monthly_var_95_pct']}%となっており、一括投資よりも時間分散を効かせた積立投資がリスク緩和に有効です。",
            "faqs": [
                {"question": f"{name}は1株いくらから買えますか？", "answer": f"単元未満株制度を利用すれば、1株あたり約{price:,}円から購入可能です。"},
                {"question": f"配当金で毎月1万円を得るにはいくら必要ですか？", "answer": f"新NISA（非課税）口座で保有する場合、{roadmap_10k['nisa_required_shares']:,}株（元本目安：約{roadmap_10k['nisa_required_capital_yen']:,}円）が必要です。"}
            ],
            "is_ai_generated": False,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "snapshot_price_yen": metrics["current_price_yen"],
        }
