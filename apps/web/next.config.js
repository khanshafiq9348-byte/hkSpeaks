/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    unoptimized: true
  },
  async rewrites() {
    const rawTarget = process.env.BACKEND_INTERNAL_URL || process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
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
