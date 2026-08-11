import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Preloader from "@/components/Preloader";
import SmoothScroll from "@/components/SmoothScroll";
import { BASE_URL, INDEXABLE } from "@/lib/site";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const title = "Ilias Kalalou — AI & Data Engineer";
const description =
  "Final-year AI & Big Data engineering student at EPITA and freelance machine learning engineer. Open to freelance work and a final-year internship.";

export const metadata: Metadata = {
  metadataBase: new URL(BASE_URL),
  title,
  description,
  robots: INDEXABLE ? undefined : { index: false, follow: false },
  alternates: { canonical: "/" },
  openGraph: {
    title,
    description,
    url: "/",
    siteName: "Ilias Kalalou",
    type: "website",
    locale: "en_US",
  },
  twitter: { card: "summary_large_image", title, description },
};

// Runs before first paint so the page never flashes underneath the intro.
// If JS is off it simply never runs and the content shows immediately.
// The timeout is the safety net: should hydration ever fail, the gate lifts
// on its own instead of leaving a permanently blank page.
const preloaderGate = `try{if(!sessionStorage.getItem('ik-preloader-seen')&&!matchMedia('(prefers-reduced-motion: reduce)').matches){document.documentElement.dataset.preloader='pending';sessionStorage.setItem('ik-preloader-seen','1');setTimeout(function(){delete document.documentElement.dataset.preloader},2500)}}catch(e){}`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <script dangerouslySetInnerHTML={{ __html: preloaderGate }} />
        <Preloader />
        <SmoothScroll>{children}</SmoothScroll>
      </body>
    </html>
  );
}
