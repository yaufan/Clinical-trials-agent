import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { Header } from "@/components/layout/header";

export const metadata: Metadata = {
  title: "AI-SaMD Clinical Protocol Copilot",
  description: "MCP-powered clinical trial protocol generator for AI/ML-enabled medical devices (AI-SaMD)",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-Hant-TW">
      <body className="min-h-screen antialiased">
        <Header />
        <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
        <footer className="mx-auto max-w-7xl px-4 py-6 text-xs text-muted">
          草稿僅供輔助，提交前須經法規、統計與臨床專家審閱。Drafts are decision support only; review by regulatory, biostatistics
          and clinical experts is required before submission.
        </footer>
      </body>
    </html>
  );
}
