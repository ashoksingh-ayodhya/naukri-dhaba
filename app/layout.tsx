import type { Metadata } from "next";
import Script from "next/script";
import { Space_Grotesk, Inter } from "next/font/google";
import "./globals.css";
import { siteConfig } from "@/config/site";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import BottomNav from "@/components/layout/BottomNav";
import SmoothScroller from "@/components/ui/SmoothScroller";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-heading",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
  display: "swap",
});

const GTM_ID = "GTM-5L4D9C9M";
const GA4_ID = "G-E3C5CLPP6B";
const GSC_CODE = ""; // paste your Search Console HTML tag meta content value here

export const metadata: Metadata = {
  title: {
    default: `${siteConfig.name} — ${siteConfig.tagline}`,
    template: `%s | ${siteConfig.name}`,
  },
  description: siteConfig.description,
  metadataBase: new URL(siteConfig.url),
  verification: GSC_CODE ? { google: GSC_CODE } : undefined,
  openGraph: {
    type: "website",
    locale: "en_IN",
    url: siteConfig.url,
    siteName: siteConfig.name,
    title: `${siteConfig.name} — ${siteConfig.tagline}`,
    description: siteConfig.description,
    images: [{ url: siteConfig.ogImage, width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    title: `${siteConfig.name} — ${siteConfig.tagline}`,
    description: siteConfig.description,
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${spaceGrotesk.variable} ${inter.variable}`}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="alternate" type="application/rss+xml" title="Naukri Dhaba — Latest Jobs" href="/feed/jobs.xml" />
        <link rel="alternate" type="application/rss+xml" title="Naukri Dhaba — Results" href="/feed/results.xml" />
        <link rel="alternate" type="application/rss+xml" title="Naukri Dhaba — Admit Cards" href="/feed/admit-cards.xml" />

        {/* Google Tag Manager — dataLayer init + GTM script */}
        <Script id="gtm-init" strategy="beforeInteractive">{`
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          gtag('consent','default',{
            'ad_storage':'denied','analytics_storage':'denied',
            'ad_user_data':'denied','ad_personalization':'denied',
            'wait_for_update':500
          });
          gtag('js', new Date());
          gtag('config', '${GA4_ID}');
        `}</Script>
        <Script
          id="gtm-script"
          strategy="afterInteractive"
          src={`https://www.googletagmanager.com/gtm.js?id=${GTM_ID}`}
        />
      </head>
      <body>
        {/* GTM noscript fallback */}
        <noscript>
          <iframe
            src={`https://www.googletagmanager.com/ns.html?id=${GTM_ID}`}
            height="0" width="0"
            style={{ display: "none", visibility: "hidden" }}
          />
        </noscript>

        <SmoothScroller>
          <Header />
          <main className="min-h-screen pb-14 md:pb-0">{children}</main>
          <Footer />
          <BottomNav />
        </SmoothScroller>
      </body>
    </html>
  );
}
