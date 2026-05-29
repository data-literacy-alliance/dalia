import { BASE_PATH } from './lib/settings.mjs';

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  // images: { unoptimized: true },
  basePath: BASE_PATH,
  trailingSlash: true,
};

export default nextConfig;
