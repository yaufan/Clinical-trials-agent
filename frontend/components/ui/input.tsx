import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Input(
  { className, ...props },
  ref,
) {
  return (
    <input
      ref={ref}
      className={cn(
        "h-10 w-full rounded-md border border-border bg-surface px-3 text-sm text-fg outline-none placeholder:text-muted/70 focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:opacity-60",
        className,
      )}
      {...props}
    />
  );
});
