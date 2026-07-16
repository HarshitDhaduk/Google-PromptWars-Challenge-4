import type { Metadata } from "next";

import { LocaleProvider } from "../lib/i18n";
import "./globals.css";

export const metadata: Metadata = {
  title: "Stadium Copilot - FIFA World Cup 2026",
  description:
    "GenAI multilingual fan assistant for MetLife Stadium: navigation, amenities, crowd-aware routing, and exit timing.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  // suppressHydrationWarning: LocaleProvider updates lang/dir on this element
  // after hydration when the fan switches language. System fonts keep the
  // build network-free.
  return (
    <html lang="en" className="h-full" suppressHydrationWarning>
      <body className="min-h-full flex flex-col antialiased">
        <LocaleProvider>{children}</LocaleProvider>
      </body>
    </html>
  );
}
