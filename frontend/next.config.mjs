/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Produce a self-contained server (.next/standalone/server.js) for a small,
  // reliable production Docker image.
  output: "standalone",
};

export default nextConfig;
