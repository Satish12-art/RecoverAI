
import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { SimulationBanner } from "@/components/ui/SimulationBanner";

export const metadata: Metadata = {
  title: "RecoverAI — AI Revenue Recovery Agent",
  description: "Don't just tell merchants what revenue they lost. Recover it.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-slate-100 min-h-screen flex">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <SimulationBanner mode="simulation" />
          <Header />
          <main className="flex-1 p-8 overflow-y-auto">{children}</main>
        </div>
      </body>
    </html>
  );
}
