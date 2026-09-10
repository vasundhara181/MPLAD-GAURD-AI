import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Produces a minimal standalone server bundle (.next/standalone) --
  // used by the multi-stage Docker build so the runtime image doesn't
  // need the full node_modules tree.
  output: "standalone",
};

export default nextConfig;
