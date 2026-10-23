import { forwardRef, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className, ...props }, ref) {
    return (
      <textarea
        ref={ref}
        className={cn(
          "min-h-[5.5rem] w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-fg outline-none placeholder:text-muted/70 focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:opacity-60",
          className,
        )}
        {...props}
      />
    );
  },
);
