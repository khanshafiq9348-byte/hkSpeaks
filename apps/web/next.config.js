/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    unoptimized: true
  },
  async rewrites() {
    const isVercel = Boolean(process.env.VERCEL || process.env.VERCEL_ENV);
    const defaultBackend = isVercel ? 'https://upon-separately-stuffed-becomes.trycloudflare.com' : 'http://127.0.0.1:8000';
    const rawTarget = process.env.BACKEND_INTERNAL_URL || process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || defaultBackend;
    const target = rawTarget.replace(/\/v1\/?$/, '');
    return [
      {
        source: '/v1/:path*',
        destination: `${target}/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
