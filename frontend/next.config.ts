import type { NextConfig } from 'next'

const backendApiUrl = (
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.BACKEND_API_URL ||
  'http://localhost:8000'
).replace(/\/$/, '')

const nextConfig: NextConfig = {
  output: 'standalone',
  reactCompiler: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${backendApiUrl}/api/:path*`,
      },
    ]
  },
}

export default nextConfig
