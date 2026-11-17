import { MetadataRoute } from "next";
import { getAllStockSummaries } from "@/lib/data";

export const dynamic = "force-static";

const BASE_URL = "https://s-kabu-quant-seo.pages.dev";

export default function sitemap(): MetadataRoute.Sitemap {
  const stocks = getAllStockSummaries();
  const stockEntries: MetadataRoute.Sitemap = stocks.map((s: any) => ({
    url: `${BASE_URL}/stocks/${s.code}`,
    lastModified: new Date(s.updated_at || Date.now()),
    changeFrequency: "weekly",
    priority: 0.8,
  }));

  return [
    {
      url: BASE_URL,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 1.0,
    },
    ...stockEntries,
  ];
}
