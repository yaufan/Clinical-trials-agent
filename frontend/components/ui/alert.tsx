import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type Tone = "info" | "success" | "warning" | "danger";
const styles: Record<Tone, string> = {
  info: "border-info/40 bg-info/10 text-fg",
  success: "border-success/40 bg-success/10 text-fg",
  warning: "border-warning/40 bg-warning/10 text-fg",
  danger: "border-danger/40 bg-danger/10 text-fg",
};
const icons: Record<Tone, ReactNode> = {
  info: <Info size={16} className="text-info" />,
  success: <CheckCircle2 size={16} className="text-success" />,
  warning: <AlertTriangle size={16} className="text-warning" />,
  danger: <XCircle size={16} className="text-danger" />,
};

export function Alert({ tone = "info", title, children, className }: { tone?: Tone; title?: ReactNode; children?: ReactNode; className?: string }) {
  return (
    <div className={cn("flex gap-2 rounded-md border px-3 py-2 text-sm", styles[tone], className)}>
      <span className="mt-0.5 shrink-0">{icons[tone]}</span>
      <div>
        {title ? <div className="font-medium">{title}</div> : null}
        {children ? <div className={cn(title ? "mt-0.5" : undefined, "text-muted")}>{children}</div> : null}
      </div>
    </div>
  );
}
