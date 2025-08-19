/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:5272/api/:path*',
      },
      {
        source: '/socket.io/:path*',
        destination: 'http://localhost:5272/socket.io/:path*',
      },
    ]
  },
}

module.exports = nextConfig