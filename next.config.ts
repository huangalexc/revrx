import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    serverActions: {
      bodySizeLimit: '5mb', // Increase from default 1MB for large text inputs
    },
  },
};

export default nextConfig;
