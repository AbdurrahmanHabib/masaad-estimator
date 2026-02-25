/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  // Ensure the app knows it is being served behind a proxy
  poweredByHeader: false,
}

module.exports = nextConfig