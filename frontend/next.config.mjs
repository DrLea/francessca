/** @type {import('next').NextConfig} */

// DESKTOP_BUILD=1 produces a fully static export in `out/`, which the
// desktop build's FastAPI process serves itself — one process, one port,
// no Node runtime inside the .exe. Trailing slashes matter there: they make
// every route a directory with an index.html, which is what a static file
// server can resolve.
const desktop = process.env.DESKTOP_BUILD === "1";

const nextConfig = {
  reactStrictMode: true,
  // Server build: a self-contained Node server (.next/standalone/server.js).
  output: desktop ? "export" : "standalone",
  ...(desktop ? { trailingSlash: true, images: { unoptimized: true } } : {}),
};

export default nextConfig;
