import { forwardRef, type SelectHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(function Select(
  { className, children, ...props },
  ref,
) {
  return (
    <select
      ref={ref}
      className={cn(
        "h-10 w-full rounded-md border border-border bg-surface px-3 text-sm text-fg outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:opacity-60",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
});
