import { Download, FileText } from "lucide-react";
import { api } from "@/lib/api";

export function ExportView({ runId, disabled }: { runId: string; disabled: boolean }) {
  const items = [
    { fmt: "md" as const, label: "Markdown (.md)", desc: "可直接貼入 Git / 文件系統，保留章節標題與引用。" },
    { fmt: "docx" as const, label: "Word (.docx)", desc: "依 TFDA / IRB 常用格式之章節編排，可再以 Word 調整版面。" },
  ];
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {items.map((it) => (
        <a
          key={it.fmt}
          href={disabled ? undefined : api.exportUrl(runId, it.fmt)}
          download
          aria-disabled={disabled}
          className={`flex items-start gap-3 rounded-md border border-border p-4 transition ${disabled ? "cursor-not-allowed opacity-50" : "hover:bg-surface-2"}`}
        >
          <FileText className="mt-0.5 text-primary" />
          <span className="flex-1">
            <span className="flex items-center gap-2 font-medium">
              {it.label} <Download size={14} className="text-muted" />
            </span>
            <span className="block text-sm text-muted">{it.desc}</span>
          </span>
        </a>
      ))}
      <p className="text-xs text-muted sm:col-span-2">匯出內容為草稿；提交 TFDA / IRB 前請完成專家審閱與簽核。Exports are drafts pending expert review.</p>
    </div>
  );
}
