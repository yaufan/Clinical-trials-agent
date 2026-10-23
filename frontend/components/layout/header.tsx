import Link from "next/link";
import { Stethoscope } from "lucide-react";

export function Header() {
  return (
    <header className="border-b border-border bg-surface">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-fg">
            <Stethoscope size={18} />
          </span>
          <span className="leading-tight">
            <span className="block text-sm">AI-SaMD 臨床試驗計畫書輔助系統</span>
            <span className="block text-xs font-normal text-muted">Clinical Protocol Copilot · MCP-powered</span>
          </span>
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          <Link href="/" className="text-muted hover:text-fg">
            專案 Projects
          </Link>
          <Link href="/projects/new" className="rounded-md bg-primary px-3 py-1.5 text-primary-fg hover:opacity-90">
            新建專案 New
          </Link>
        </nav>
      </div>
    </header>
  );
}
