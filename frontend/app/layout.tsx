import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "UseWorldview — AI-Powered Synthetic User Research",
  description:
    "Deploy AI personas into your live product. They explore, interact, and report back what they experienced — and why. Get persona-level, evidence-backed research in minutes.",
  keywords: [
    "user research",
    "AI UX testing",
    "synthetic users",
    "persona testing",
    "usability testing",
    "conversion optimization",
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} h-full`} suppressHydrationWarning>
      <body className="min-h-full flex flex-col font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
