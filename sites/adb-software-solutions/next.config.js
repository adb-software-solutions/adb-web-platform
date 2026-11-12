/** @type {import('next').NextConfig} */

const nextConfig = {
    reactStrictMode: true,
    trailingSlash: true,
    skipTrailingSlashRedirect: true,
    transpilePackages: ["@adb/ui", "@adb/api-client", "@adb/observability"],
    images: {
        // Widths /_next/image will resize to. Next's default list goes up
        // to 3840, and a crawler asking for every width at once made sharp
        // hold hundreds of MB of native memory. No image the sites render
        // through next/image is wider than 1920, so larger widths only cost
        // memory.
        deviceSizes: [640, 750, 828, 1080, 1200, 1920],
        remotePatterns: [
            {
                protocol: "http",
                hostname: "localhost",
                port: "8000",
                pathname: "/media/**",
            },
        ],
    },
};

module.exports = nextConfig;
