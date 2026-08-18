import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AstroPlate AI",
  description: "Autonomous astronomical plate-solving, satellite detection, and multi-tier AI explanations.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-gray-950 text-gray-100 min-h-screen`}>
        {/* Top navbar */}
        <header className="border-b border-gray-800 bg-gray-900 px-6 py-4">
          <div className="mx-auto max-w-7xl flex items-center gap-3">
            <span className="text-2xl">🔭</span>
            <h1 className="text-lg font-semibold tracking-tight text-white">
              AstroPlate <span className="text-blue-400">AI</span>
            </h1>
            <span className="ml-2 rounded-full bg-blue-900/50 px-2 py-0.5 text-xs text-blue-300 border border-blue-800">
              Upgraded Sky Explainer
            </span>
          </div>
        </header>

        <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
