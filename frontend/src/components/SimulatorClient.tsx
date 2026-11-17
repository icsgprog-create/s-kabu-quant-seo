"use client";
import React, { useState, useMemo } from "react";

interface Props {
  name: string;
  code: string;
  minPrice: number;
  geometricGrowthPct: number;
  annualVolatilityPct: number;
  dividendYieldPct: number;
}

export default function SimulatorClient({
  name,
  code,
  minPrice,
  geometricGrowthPct,
  annualVolatilityPct,
  dividendYieldPct,
}: Props) {
  const [monthlyYen, setMonthlyYen] = useState<number>(10000);
  const [initialYen, setInitialYen] = useState<number>(0);
  const [years, setYears] = useState<number>(10);
  const [isNisa, setIsNisa] = useState<boolean>(true);

  const projections = useMemo(() => {
    const g = geometricGrowthPct / 100.0;
    const sigma = annualVolatilityPct / 100.0;
    const div = dividendYieldPct / 100.0;
    const taxRate = isNisa ? 0.0 : 0.20315;
    const effectiveDrift = g + div * (1.0 - taxRate);

    const rows = [];
    for (let y = 1; y <= years; y++) {
      const totalMonths = y * 12;
      const principal = initialYen + monthlyYen * totalMonths;
      const calcVal = (z: number) => {
        let val =
          initialYen > 0
            ? initialYen * Math.exp(effectiveDrift * y + z * sigma * Math.sqrt(y))
            : 0;
        for (let m = 1; m <= totalMonths; m++) {
          const t = m / 12.0;
          val += monthlyYen * Math.exp(effectiveDrift * t + z * sigma * Math.sqrt(t));
        }
        return Math.round(val);
      };
      rows.push({
        year: y,
        principal: Math.round(principal),
        median: calcVal(0.0),
        upper90: calcVal(1.28155),
        lower10: calcVal(-1.28155),
      });
    }
    return rows;
  }, [monthlyYen, initialYen, years, isNisa, geometricGrowthPct, annualVolatilityPct, dividendYieldPct]);

  const finalRow = projections[projections.length - 1];

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm my-6">
      <h2 className="text-xl font-bold text-slate-900 mb-4">
        {name}（{code}）単元未満株・NISA積立シミュレーター
      </h2>
      <p className="text-sm text-slate-600 mb-6">
        1株あたり約{minPrice.toLocaleString()}円から購入可能。過去5年の定量データ（幾何成長率 {geometricGrowthPct}% / 年率ボラティリティ {annualVolatilityPct}% / 配当利回り {dividendYieldPct}%）をもとに将来資産を推計します。
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            毎月の積立金額: <span className="font-bold text-blue-600">{monthlyYen.toLocaleString()}円</span>
          </label>
          <input
            type="range"
            min={1000}
            max={100000}
            step={1000}
            value={monthlyYen}
            onChange={(e) => setMonthlyYen(Number(e.target.value))}
            className="w-full accent-blue-600"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            初期投資額: <span className="font-bold text-blue-600">{initialYen.toLocaleString()}円</span>
          </label>
          <input
            type="range"
            min={0}
            max={1000000}
            step={10000}
            value={initialYen}
            onChange={(e) => setInitialYen(Number(e.target.value))}
            className="w-full accent-blue-600"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            積立期間: <span className="font-bold text-blue-600">{years}年間</span>
          </label>
          <input
            type="range"
            min={1}
            max={30}
            step={1}
            value={years}
            onChange={(e) => setYears(Number(e.target.value))}
            className="w-full accent-blue-600"
          />
        </div>

        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-slate-700">口座区分:</span>
          <button
            type="button"
            onClick={() => setIsNisa(true)}
            className={`px-4 py-2 rounded-lg text-sm font-bold ${
              isNisa ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-700"
            }`}
          >
            新NISA（非課税）
          </button>
          <button
            type="button"
            onClick={() => setIsNisa(false)}
            className={`px-4 py-2 rounded-lg text-sm font-bold ${
              !isNisa ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-700"
            }`}
          >
            特定口座（税引後）
          </button>
        </div>
      </div>

      {finalRow && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-slate-50 p-4 rounded-lg mb-6">
          <div>
            <div className="text-xs text-slate-500">積立元本合計</div>
            <div className="text-lg font-bold text-slate-800">{finalRow.principal.toLocaleString()}円</div>
          </div>
          <div>
            <div className="text-xs text-slate-500">{years}年後 中央値予測</div>
            <div className="text-lg font-bold text-blue-600">{finalRow.median.toLocaleString()}円</div>
          </div>
          <div>
            <div className="text-xs text-slate-500">上位10%（好調時）</div>
            <div className="text-lg font-bold text-emerald-600">{finalRow.upper90.toLocaleString()}円</div>
          </div>
          <div>
            <div className="text-xs text-slate-500">下位10%（不調時）</div>
            <div className="text-lg font-bold text-amber-600">{finalRow.lower10.toLocaleString()}円</div>
          </div>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-200 text-slate-600 bg-slate-50">
              <th className="py-2 px-3">経過年数</th>
              <th className="py-2 px-3">元本</th>
              <th className="py-2 px-3">中央値予測</th>
              <th className="py-2 px-3">好調時(上位10%)</th>
              <th className="py-2 px-3">不調時(下位10%)</th>
            </tr>
          </thead>
          <tbody>
            {projections.map((r) => (
              <tr key={r.year} className="border-b border-slate-100">
                <td className="py-2 px-3 font-medium">{r.year}年目</td>
                <td className="py-2 px-3">{r.principal.toLocaleString()}円</td>
                <td className="py-2 px-3 font-bold text-blue-600">{r.median.toLocaleString()}円</td>
                <td className="py-2 px-3 text-emerald-600">{r.upper90.toLocaleString()}円</td>
                <td className="py-2 px-3 text-amber-600">{r.lower10.toLocaleString()}円</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
