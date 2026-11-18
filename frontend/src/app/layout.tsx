import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "日本株 単元未満株（1株）× 新NISA クオンツ積立シミュレーター",
  description: "東証上場3,672銘柄の過去5年データから幾何成長率・ボラティリティ・配当利回りを定量計算。1株から買える単元未満株の積立推移と目標配当ロードマップを公開。",
  verification: {
    google: "I-Ac6MB-P308PZbfixHOpUqw0iM6fKOWz8oj61NnX-k",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <body className="bg-slate-50 text-slate-900 antialiased min-h-screen flex flex-col justify-between">
        <div>{children}</div>
        <footer className="bg-white border-t border-slate-200 mt-16 py-8 px-4 text-xs text-slate-500">
          <div className="max-w-5xl mx-auto space-y-3">
            <p className="font-semibold text-slate-700">免責事項・投資リスクについて</p>
            <p>
              当サイトで提供する株価データ、クオンツスコア、積立シミュレーションおよび配当金試算は、過去の市場データに基づく統計的・数学的な推計値であり、将来の運用成果や配当金の支払いを保証するものではありません。また、特定の金融商品の売買を推奨・勧誘する投資助言業務には該当しません。投資に関する最終決定は、ご自身の判断と責任において行われますようお願いいたします。
            </p>
            <p className="font-semibold text-slate-700 pt-2">広告の配信・プライバシーポリシーについて</p>
            <p>
              当サイトでは第三者配信の広告サービスおよびアフィリエイトプログラムを利用しています。Cookieを通じたアクセス解析や広告配信が行われる場合がありますが、個人を特定する情報は含まれません。
            </p>
            <p className="pt-2 text-slate-400">© {new Date().getFullYear()} 日本株 単元未満株×新NISA クオンツ積立シミュレーター</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
