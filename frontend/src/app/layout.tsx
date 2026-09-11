import type { Metadata } from "next";
import { DM_Sans } from "next/font/google";
import "./globals.css";
import { ToastProvider } from "@/components/Input";

const dmSans = DM_Sans({
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Prism — Content Transformation Platform",
  description:
    "Transform any source material into audience-ready communication artefacts, grounded and validated.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={dmSans.className}>
        <div className="ambient" aria-hidden />
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  );
}
