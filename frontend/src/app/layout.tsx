import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "F3Next",
  description: "Multi-agent control surface",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      {/* 
        We removed inter.className. 
        'antialiased' is a standard Tailwind class for better font smoothing.
      */}
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
