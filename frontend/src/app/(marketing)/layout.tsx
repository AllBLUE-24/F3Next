import type { Metadata } from "next";
import ConsultantChatWidget from "@/components/marketing/ConsultantChatWidget";

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
      {children}
      <ConsultantChatWidget />
    </>
  );
}