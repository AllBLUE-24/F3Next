import type { Metadata } from "next";
import { Geist_Mono, Syne } from "next/font/google";
import "./globals.css";

const syne = Syne({
  subsets: ["latin"],
  variable: "--font-syne",
  weight: ["400", "500", "600", "700", "800"],
});

const geistMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500", "600"],
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
    <html lang="en" className={`${syne.variable} ${geistMono.variable}`}>
      <body className="antialiased font-sans bg-[#09090B] text-white">
        {children}
      </body>
    </html>
  );
}