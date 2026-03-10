import type { Metadata } from "next";

export const metadata: Metadata = {
  title: {
    template: "%s | F3Next",
    default: "F3Next — AI-Powered ERP for Manufacturers",
  },
};

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      {/*
        Marketing route group layout.
        Keeps marketing pages isolated from app/dashboard layouts.
        Add any marketing-specific providers or wrappers here.
      */}
      {children}
    </>
  );
}