import os, json, time
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from config import CACHE_DIR, GEMINI_MODEL_NAME, AI_CACHE_EXPIRE_DAYS, AI_REGENERATE_CHANGE_THRESHOLD

class FAQItemSchema(BaseModel):
    question: str
    answer: str

class StockSEOContentSchema(BaseModel):
    seo_title: str
    meta_description: str
    summary_points: list[str]
    accumulation_strategy_analysis: str
    dividend_and_risk_commentary: str
    faqs: list[FAQItemSchema]

class AIGenerator:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    def _should_use_cache(self, code, metrics):
        cache_path = CACHE_DIR / f"ai_cache_{code}.json"
        if not cache_path.exists(): return False
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            generated_date = datetime.strptime(cached.get("generated_at", "2000-01-01"), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - generated_date).days > AI_CACHE_EXPIRE_DAYS: return False
            prev_price = float(cached.get("snapshot_price_yen", 0))
            curr_price = float(metrics.get("current_price_yen", 0))
            if prev_price > 0 and (abs(curr_price - prev_price) / prev_price) >= AI_REGENERATE_CHANGE_THRESHOLD: return False
            return True
        except: return False

    def generate_or_load_seo_content(self, metrics):
        code = metrics["code"]
        cache_path = CACHE_DIR / f"ai_cache_{code}.json"
        if self._should_use_cache(code, metrics):
            with open(cache_path, "r", encoding="utf-8") as f: return json.load(f)["content"]
        if not self.client: return self._build_fallback_content(metrics)
        prompt = f"定量データからSEOコンテンツ生成:\n{json.dumps(metrics, ensure_ascii=False)}"
        try:
            res = self.client.models.generate_content(
                model=GEMINI_MODEL_NAME, contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=StockSEOContentSchema, temperature=0.2)
            )
            parsed = json.loads(res.text)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "snapshot_price_yen": metrics["current_price_yen"], "content": parsed}, f, ensure_ascii=False, indent=2)
            return parsed
        except: return self._build_fallback_content(metrics)

    @staticmethod
    def _build_fallback_content(metrics):
        name, code, price = metrics["name"], metrics["code"], metrics["min_s_kabu_yen"]
        div = metrics["dividend_yield_pct"]
        roadmap_10k = next((r for r in metrics["dividend_roadmap"] if r["target_monthly_yen"] == 10000), metrics["dividend_roadmap"][0])
        return {
            "seo_title": f"{name}({code})の単元未満株・NISA積立と配当金シミュレーション",
            "meta_description": f"{name}({code})を1株({price:,}円)から単元未満株で積立投資した場合の10年後資産推移を定量計算。",
            "summary_points": [f"最小{price:,}円から購入可能", f"年率ボラティリティは{metrics['annual_volatility_pct']}%", f"月1万円の配当には{roadmap_10k['nisa_required_shares']:,}株が必要"],
            "accumulation_strategy_analysis": f"{name}は1株（約{price:,}円）から定額積立が可能です。対数正規分布モデルによる10年後中央値予測は{metrics['default_10y_projection'][-1]['median_yen']:,}円です。",
            "dividend_and_risk_commentary": f"年間予想配当金は{metrics['dps_yen']}円（利回り{div}%）です。月次95%VaRは{metrics['monthly_var_95_pct']}%であり、時間分散が有効です。",
            "faqs": [{"question": f"{name}はいくらから買えますか？", "answer": f"1株あたり約{price:,}円から購入可能です。"}, {"question": f"配当で月1万円を得るにはいくら必要ですか？", "answer": f"新NISAで約{roadmap_10k['nisa_required_capital_yen']:,}円必要です。"}]
        }
