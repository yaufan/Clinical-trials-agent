import { Check } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface StepperStep {
  id: string;
  title: ReactNode;
  subtitle?: ReactNode;
  state: "done" | "current" | "todo" | "error" | "waiting";
}

export function Stepper({ steps, onSelect, className }: { steps: StepperStep[]; onSelect?: (id: string) => void; className?: string }) {
  return (
    <ol className={cn("flex flex-wrap gap-y-3", className)}>
      {steps.map((s, i) => {
        const dot = {
          done: "bg-success text-white border-success",
          current: "bg-primary text-primary-fg border-primary",
          todo: "bg-surface text-muted border-border",
          error: "bg-danger text-white border-danger",
          waiting: "bg-warning text-white border-warning",
        }[s.state];
        return (
          <li key={s.id} className="flex min-w-[9rem] flex-1 items-start gap-2">
            <button
              type="button"
              onClick={onSelect ? () => onSelect(s.id) : undefined}
              className={cn("flex items-start gap-2 text-left", onSelect ? "cursor-pointer" : "cursor-default")}
            >
              <span className={cn("mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs font-semibold", dot)}>
                {s.state === "done" ? <Check size={14} /> : i + 1}
              </span>
              <span>
                <span className={cn("block text-sm font-medium leading-tight", s.state === "todo" && "text-muted")}>{s.title}</span>
                {s.subtitle ? <span className="block text-xs text-muted">{s.subtitle}</span> : null}
              </span>
            </button>
            {i < steps.length - 1 ? <span className="mt-3 hidden h-px flex-1 bg-border lg:block" /> : null}
          </li>
        );
      })}
    </ol>
  );
}
