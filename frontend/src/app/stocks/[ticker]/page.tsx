import React from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getAllStockSummaries, getStockFullData } from "@/lib/data";
import { AFFILIATE_BROKERS } from "@/lib/affiliate";
import SimulatorClient from "@/components/SimulatorClient";

export async function generateStaticParams() {
  const summaries = getAllStockSummaries();
  return summaries.map((s: any) => ({ ticker: String(s.code) }));
}

export async function generateMetadata({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = await params;
  const data = getStockFullData(ticker);
  if (!data) return { title: "銘柄が見つかりません" };
  return {
    title: data.seo.seo_title,
    description: data.seo.meta_description,
  };
}

export default async function StockDetailPage({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = await params;
  const data = getStockFullData(ticker);
  if (!data) notFound();

  const { metrics, seo } = data;

  return (
    <main className="max-w-5xl mx-auto px-4 py-8 text-slate-800">
      <nav className="text-sm text-slate-500 mb-4">
        <Link href="/" className="hover:underline text-blue-600">トップページ</Link>
        <span className="mx-2">/</span>
        <span>{metrics.sector}</span>
        <span className="mx-2">/</span>
        <span className="font-semibold text-slate-700">{metrics.name}（{metrics.code}）</span>
      </nav>

      <header className="mb-6">
        <span className="inline-block bg-blue-50 text-blue-700 text-xs font-bold px-2.5 py-1 rounded mb-2">
          {metrics.sector} | クオンツスコア {metrics.quant_score}点
        </span>
        <h1 className="text-2xl md:text-3xl font-bold text-slate-900">{seo.seo_title}</h1>
        <p className="text-xs text-slate-500 mt-1">最終データ更新日: {metrics.updated_at}</p>
      </header>

      <section className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm">
          <div className="text-xs text-slate-500">1株（S株/かぶミニ）目安</div>
          <div className="text-xl font-bold text-slate-900">{metrics.min_s_kabu_yen.toLocaleString()}円</div>
          <div className="text-xs text-slate-400">単元株(100株): {metrics.unit_lot_yen.toLocaleString()}円</div>
        </div>
        <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm">
          <div className="text-xs text-slate-500">予想配当利回り</div>
          <div className="text-xl font-bold text-emerald-600">{metrics.dividend_yield_pct}%</div>
          <div className="text-xs text-slate-400">1株配当: {metrics.dps_yen}円</div>
        </div>
        <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm">
          <div className="text-xs text-slate-500">年率ボラティリティ</div>
          <div className="text-xl font-bold text-slate-900">{metrics.annual_volatility_pct}%</div>
          <div className="text-xs text-slate-400">最大DD: {metrics.max_drawdown_pct}%</div>
        </div>
        <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm">
          <div className="text-xs text-slate-500">幾何成長率（年率）</div>
          <div className="text-xl font-bold text-blue-600">{metrics.geometric_growth_pct}%</div>
          <div className="text-xs text-slate-400">シャープレシオ: {metrics.sharpe_ratio}</div>
        </div>
      </section>

      <SimulatorClient
        name={metrics.name}
        code={metrics.code}
        minPrice={metrics.min_s_kabu_yen}
        geometricGrowthPct={metrics.geometric_growth_pct}
        annualVolatilityPct={metrics.annual_volatility_pct}
        dividendYieldPct={metrics.dividend_yield_pct}
      />

      <section className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm my-6">
        <h2 className="text-xl font-bold text-slate-900 mb-4">
          {metrics.name}の目標配当金ロードマップ（新NISA vs 特定口座）
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600">
                <th className="py-2 px-3">目標月額配当</th>
                <th className="py-2 px-3">新NISA 必要株数</th>
                <th className="py-2 px-3">新NISA 必要投資額</th>
                <th className="py-2 px-3">特定口座 必要投資額</th>
              </tr>
            </thead>
            <tbody>
              {metrics.dividend_roadmap.map((row: any) => (
                <tr key={row.target_monthly_yen} className="border-b border-slate-100">
                  <td className="py-2 px-3 font-bold">月 {row.target_monthly_yen.toLocaleString()}円</td>
                  <td className="py-2 px-3">{row.nisa_required_shares.toLocaleString()}株</td>
                  <td className="py-2 px-3 font-bold text-emerald-600">
                    {row.nisa_required_capital_yen.toLocaleString()}円
                  </td>
                  <td className="py-2 px-3 text-slate-600">
                    {row.specific_required_capital_yen.toLocaleString()}円
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="bg-blue-50 border border-blue-200 rounded-xl p-6 shadow-sm my-6">
        <h2 className="text-lg font-bold text-slate-900 mb-3">
          {metrics.name}を1株（{metrics.min_s_kabu_yen.toLocaleString()}円）から手数料無料で買う方法
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {AFFILIATE_BROKERS.map((b, i) => (
            <div key={i} className="bg-white p-4 rounded-lg border border-slate-200 flex flex-col justify-between">
              <div>
                <span className="inline-block bg-emerald-50 text-emerald-700 text-xs font-bold px-2 py-0.5 rounded mb-1">
                  {b.badge}
                </span>
                <h3 className="font-bold text-slate-900">{b.name}</h3>
                <p className="text-xs text-slate-600 mt-1 mb-4">{b.description}</p>
              </div>
              <a
                href={b.ctaUrl}
                target="_blank"
                rel="nofollow sponsored noopener"
                className="block text-center bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm py-2.5 px-4 rounded-lg"
              >
                無料口座開設・詳細を見る
              </a>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm my-6 space-y-4">
        <h2 className="text-xl font-bold text-slate-900">定量クオンツ分析・積立戦略</h2>
        <ul className="list-disc list-inside text-sm text-slate-700 space-y-1">
          {seo.summary_points.map((pt: string, i: number) => (
            <li key={i}>{pt}</li>
          ))}
        </ul>
        <p className="text-sm text-slate-700 leading-relaxed">{seo.accumulation_strategy_analysis}</p>
        <p className="text-sm text-slate-700 leading-relaxed">{seo.dividend_and_risk_commentary}</p>
      </section>

      <section className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm my-6">
        <h2 className="text-xl font-bold text-slate-900 mb-4">よくある質問（FAQ）</h2>
        <div className="space-y-4">
          {seo.faqs.map((faq: any, i: number) => (
            <div key={i} className="border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-800 text-sm">Q. {faq.question}</h3>
              <p className="text-sm text-slate-600 mt-1">A. {faq.answer}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
