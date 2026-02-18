import type { Metadata, Viewport } from "next";
import { Playfair_Display, Inter } from "next/font/google";
import "./globals.css";

const playfair = Playfair_Display({
  subsets: ["latin"],
  variable: "--font-playfair",
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const viewport: Viewport = {
  themeColor: "#0A0A0A",
  width: "device-width",
  initialScale: 1,
};

export const metadata: Metadata = {
  title: "Fragrances Jamaica | Premium Designer Fragrances",
  description:
    "Jamaica's premier destination for authentic designer fragrances. Browse our collection of 4,800+ colognes and perfumes for men and women. Inquire via WhatsApp.",
  keywords: [
    "fragrances",
    "cologne",
    "perfume",
    "Jamaica",
    "designer fragrances",
    "men's cologne",
    "women's perfume",
    "authentic perfume",
    "Kingston Jamaica",
  ],
  openGraph: {
    title: "Fragrances Jamaica | Premium Designer Fragrances",
    description:
      "Jamaica's premier destination for authentic designer fragrances. Browse 4,800+ colognes and perfumes.",
    type: "website",
    locale: "en_US",
    siteName: "Fragrances Jamaica",
  },
  twitter: {
    card: "summary_large_image",
    title: "Fragrances Jamaica | Premium Designer Fragrances",
    description:
      "Jamaica's premier destination for authentic designer fragrances. Browse 4,800+ colognes and perfumes.",
  },
  robots: {
    index: true,
    follow: true,
  },
  icons: {
    icon: "/favicon.svg",
    apple: "/apple-touch-icon.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="scroll-smooth">
      <body className={`${playfair.variable} ${inter.variable} antialiased`}>
        {children}
      </body>
    </html>
  );
}
