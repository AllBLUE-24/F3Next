import type { Metadata } from "next";
import { Inter, Geist_Mono, Syne, Outfit } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  weight: ["300", "400", "500", "600", "700", "800"],
  display: "swap",
});

const geistMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
  weight: ["400", "500", "600"],
  display: "swap",
});

const syne = Syne({
  subsets: ["latin"],
  variable: "--font-syne",
  weight: ["400", "500", "600", "700", "800"],
  display: "swap",
});

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
  weight: ["300", "400", "500", "600", "700", "800", "900"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "F3Next — AI-Powered ERP for Manufacturers",
  description:
    "F3Next implements and operates your ERP through AI. From recommendation to deployment to day-to-day operations — all in plain English. Built for Indian MSMEs.",
  keywords: ["ERP", "ERPNext", "Manufacturing", "MSME", "AI ERP", "F3Next", "ERP Implementation"],
  openGraph: {
    title: "F3Next — AI-Powered ERP for Manufacturers",
    description:
      "Implement and run ERPNext in 48 hours. No consultants. No training. Just type what you need.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${geistMono.variable} ${syne.variable} ${outfit.variable}`}>
      <body className="antialiased font-sans bg-[var(--bg-void)] text-[var(--text-primary)]">
        {children}
      </body>
    </html>
  );
}