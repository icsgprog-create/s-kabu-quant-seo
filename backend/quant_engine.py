import math
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import numpy as np
import pandas as pd
import yfinance as yf

class QuantEngine:
    TRADING_DAYS_PER_YEAR = 245
    RISK_FREE_RATE = 0.01
    TAX_RATE_SPECIFIC = 0.20315

    @classmethod
    def calculate_stock_metrics(cls, code: str, fallback_name: str, fallback_sector: str) -> Optional[Dict[str, Any]]:
        ticker_symbol = f"{code}.T"
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="5y", interval="1d", auto_adjust=False)
        if hist is None or hist.empty or len(hist) < 60: return None
        hist = hist.dropna(subset=["Close"])
        if len(hist) < 60: return None

        close_prices = hist["Close"]
        adj_close = hist["Adj Close"] if "Adj Close" in hist.columns else close_prices
        current_price = float(close_prices.iloc[-1])

        log_returns = np.log(adj_close / adj_close.shift(1)).dropna()
        if len(log_returns) < 30: return None

        raw_annual_mu = float(log_returns.mean() * cls.TRADING_DAYS_PER_YEAR)
        annual_sigma = float(log_returns.std(ddof=1) * math.sqrt(cls.TRADING_DAYS_PER_YEAR))
        capped_annual_mu = max(-0.15, min(0.20, raw_annual_mu))
        sigma_sq = annual_sigma * annual_sigma
        geometric_growth = capped_annual_mu - (sigma_sq / 2.0)

        rolling_max = adj_close.cummax()
        drawdowns = (adj_close - rolling_max) / rolling_max
        max_drawdown = float(drawdowns.min())

        monthly_log_returns = np.log(adj_close / adj_close.shift(20)).dropna()
        var_95_monthly = float(np.percentile(monthly_log_returns, 5)) if len(monthly_log_returns) > 20 else float(-1.64485 * annual_sigma / math.sqrt(12.0))

        info = ticker.info if hasattr(ticker, "info") else {}
        dps = float(info.get("dividendRate") or info.get("trailingAnnualDividendRate") or 0.0)
        if dps == 0.0 and "Dividends" in hist.columns:
            one_year_ago = hist.index[-1] - pd.Timedelta(days=365)
            dps = float(hist.loc[hist.index >= one_year_ago, "Dividends"].sum())

        dividend_yield = (dps / current_price) if current_price > 0 else 0.0
        if dividend_yield > 0.25: dividend_yield, dps = 0.0, 0.0

        sharpe_ratio = ((geometric_growth + dividend_yield) - cls.RISK_FREE_RATE) / annual_sigma if annual_sigma > 0 else 0.0

        target_monthly_dividends = [1000, 5000, 10000, 30000, 50000]
        dividend_roadmap = []
        for target_m in target_monthly_dividends:
            annual_target = target_m * 12.0
            req_shares_nisa = math.ceil(annual_target / dps) if dps > 0 else 0
            req_shares_taxed = math.ceil(annual_target / (dps * (1.0 - cls.TAX_RATE_SPECIFIC))) if dps > 0 else 0
            dividend_roadmap.append({
                "target_monthly_yen": target_m,
                "nisa_required_shares": req_shares_nisa,
                "nisa_required_capital_yen": round(req_shares_nisa * current_price),
                "specific_required_shares": req_shares_taxed,
                "specific_required_capital_yen": round(req_shares_taxed * current_price),
            })

        default_projection = cls.simulate_dca_projection(10000, 0, 10, geometric_growth, annual_sigma, dividend_yield, True)

        yield_score = min(40.0, dividend_yield * 800.0)
        vol_score = max(0.0, 30.0 - max(0.0, (annual_sigma - 0.15) * 100.0))
        sharpe_score = max(0.0, min(30.0, (sharpe_ratio + 0.2) * 25.0))
        quant_score = round(yield_score + vol_score + sharpe_score, 1)

        return {
            "code": str(code), "name": fallback_name, "sector": fallback_sector,
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "current_price_yen": round(current_price, 1),
            "min_s_kabu_yen": math.ceil(current_price),
            "unit_lot_yen": round(current_price * 100),
            "dps_yen": round(dps, 2), "dividend_yield_pct": round(dividend_yield * 100.0, 2),
            "raw_annual_return_pct": round(raw_annual_mu * 100.0, 2),
            "capped_annual_return_pct": round(capped_annual_mu * 100.0, 2),
            "geometric_growth_pct": round(geometric_growth * 100.0, 2),
            "annual_volatility_pct": round(annual_sigma * 100.0, 2),
            "max_drawdown_pct": round(max_drawdown * 100.0, 2),
            "monthly_var_95_pct": round(var_95_monthly * 100.0, 2),
            "sharpe_ratio": round(sharpe_ratio, 2), "quant_score": quant_score,
            "dividend_roadmap": dividend_roadmap, "default_10y_projection": default_projection,
        }

    @classmethod
    def simulate_dca_projection(cls, monthly_contribution, initial_investment, years, geometric_growth, annual_sigma, dividend_yield, is_nisa):
        effective_drift = geometric_growth + dividend_yield * (1.0 - (0.0 if is_nisa else cls.TAX_RATE_SPECIFIC))
        results = []
        for y in range(1, years + 1):
            total_months = y * 12
            principal = initial_investment + (monthly_contribution * total_months)
            def calc_val(z_val):
                val = (initial_investment * math.exp(effective_drift * y + z_val * annual_sigma * math.sqrt(y))) if initial_investment > 0 else 0.0
                for m in range(1, total_months + 1):
                    t_frac = m / 12.0
                    val += monthly_contribution * math.exp(effective_drift * t_frac + z_val * annual_sigma * math.sqrt(t_frac))
                return round(val)
            results.append({"year": y, "principal_yen": round(principal), "median_yen": calc_val(0.0), "upper_90_yen": calc_val(1.28155), "lower_10_yen": calc_val(-1.28155)})
        return results
