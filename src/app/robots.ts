import type { MetadataRoute } from "next";
import { BASE_URL, INDEXABLE } from "@/lib/site";

export default function robots(): MetadataRoute.Robots {
  if (!INDEXABLE) {
    return { rules: { userAgent: "*", disallow: "/" } };
  }

  return {
    rules: { userAgent: "*", allow: "/" },
    sitemap: `${BASE_URL}/sitemap.xml`,
  };
}
