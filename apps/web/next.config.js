/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    unoptimized: true
  },
  async rewrites() {
    const isVercel = Boolean(process.env.VERCEL || process.env.VERCEL_ENV);
    const backendUrl = process.env.BACKEND_INTERNAL_URL || process.env.BACKEND_URL;

    // If persistent cloud backend is configured (e.g. on Render), proxy API requests to it
    if (backendUrl) {
      const target = backendUrl.replace(/\/v1\/?$/, '');
      return [
        {
          source: '/v1/:path*',
          destination: `${target}/v1/:path*`,
        },
      ];
    }

    // In local development, proxy to local FastAPI backend on port 8000
    if (!isVercel) {
      return [
        {
          source: '/v1/:path*',
          destination: 'http://127.0.0.1:8000/v1/:path*',
        },
      ];
    }

    // In Vercel production without external backend, fall through to native app/v1 Route Handlers
    return [];
  },
};

module.exports = nextConfig;
