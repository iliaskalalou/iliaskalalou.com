import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emitted to out/ and served as plain files by Caddy on the VPS.
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;
