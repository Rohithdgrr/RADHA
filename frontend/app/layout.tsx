import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Council",
  description: "Perplexity-style multi-model deliberation — frosted council chamber",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[var(--ink)] text-[var(--fog)] antialiased selection:bg-white/10">
        <div className="aurora" aria-hidden>
          <div className="orb orb--cyan" />
          <div className="orb orb--violet" />
          <div className="orb orb--amber" />
        </div>
        {children}
      </body>
    </html>
  );
}
