import React from "react";
import Link from "next/link";
import { getAllStockSummaries } from "@/lib/data";

export default function HomePage() {
  const stocks = getAllStockSummaries();

  return (
    <main className="max-w-6xl mx-auto px-4 py-10 text-slate-800">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">
          日本株 単元未満株（1株）× 新NISA クオンツ積立シミュレーター
        </h1>
        <p className="text-sm text-slate-600">
          過去5年間の株価データから幾何成長率・ボラティリティ・配当利回りを定量計算。1株から買える単元未満株の積立推移と目標配当ロードマップを公開しています（現在 {stocks.length} 銘柄掲載）。
        </p>
      </header>

      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-x-auto">
        <table className="w-full text-sm text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-slate-600">
              <th className="py-3 px-4">銘柄コード・銘柄名</th>
              <th className="py-3 px-4">業種</th>
              <th className="py-3 px-4">1株目安</th>
              <th className="py-3 px-4">配当利回り</th>
              <th className="py-3 px-4">年率ボラ</th>
              <th className="py-3 px-4">クオンツスコア</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map((s: any) => (
              <tr key={s.code} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="py-3 px-4 font-bold">
                  <Link href={`/stocks/${s.code}`} className="text-blue-600 hover:underline">
                    {s.name}（{s.code}）
                  </Link>
                </td>
                <td className="py-3 px-4 text-slate-600">{s.sector}</td>
                <td className="py-3 px-4 font-medium">{s.min_s_kabu_yen.toLocaleString()}円</td>
                <td className="py-3 px-4 font-bold text-emerald-600">{s.dividend_yield_pct}%</td>
                <td className="py-3 px-4">{s.annual_volatility_pct}%</td>
                <td className="py-3 px-4 font-bold text-blue-600">{s.quant_score}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
