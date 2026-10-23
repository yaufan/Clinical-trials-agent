"use client";

import type { FieldError, FieldErrors, FieldPath, UseFormReturn } from "react-hook-form";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { FormValues } from "./schema";

export type Form = UseFormReturn<FormValues>;
export type Path = FieldPath<FormValues>;

export function getError(errors: FieldErrors<FormValues>, path: string): string | undefined {
  const parts = path.split(".");
  let cur: unknown = errors;
  for (const p of parts) {
    if (cur && typeof cur === "object" && p in (cur as Record<string, unknown>)) {
      cur = (cur as Record<string, unknown>)[p];
    } else {
      return undefined;
    }
  }
  const fe = cur as FieldError | undefined;
  return typeof fe?.message === "string" ? fe.message : undefined;
}

export function TextField({ form, name, label, hint, required, placeholder }: { form: Form; name: Path; label: string; hint?: string; required?: boolean; placeholder?: string }) {
  return (
    <Field label={label} hint={hint} required={required} error={getError(form.formState.errors, name)}>
      <Input {...form.register(name)} placeholder={placeholder} />
    </Field>
  );
}

export function TextAreaField({ form, name, label, hint, required, placeholder, rows = 3, className }: { form: Form; name: Path; label: string; hint?: string; required?: boolean; placeholder?: string; rows?: number; className?: string }) {
  return (
    <Field label={label} hint={hint} required={required} error={getError(form.formState.errors, name)} className={className}>
      <Textarea {...form.register(name)} placeholder={placeholder} rows={rows} />
    </Field>
  );
}

export function NumberField({ form, name, label, hint, required, step = "any", min, max, placeholder }: { form: Form; name: Path; label: string; hint?: string; required?: boolean; step?: string; min?: number; max?: number; placeholder?: string }) {
  return (
    <Field label={label} hint={hint} required={required} error={getError(form.formState.errors, name)}>
      <Input
        type="number"
        inputMode="decimal"
        step={step}
        min={min}
        max={max}
        placeholder={placeholder}
        {...form.register(name, { setValueAs: (v) => (v === "" || v === null || v === undefined ? undefined : Number(v)) })}
      />
    </Field>
  );
}

export function SelectField({ form, name, label, options, labels, hint, required }: { form: Form; name: Path; label: string; options: readonly string[]; labels: Record<string, string>; hint?: string; required?: boolean }) {
  return (
    <Field label={label} hint={hint} required={required} error={getError(form.formState.errors, name)}>
      <Select {...form.register(name)}>
        {options.map((o) => (
          <option key={o} value={o}>
            {labels[o] ?? o}
          </option>
        ))}
      </Select>
    </Field>
  );
}

export function CheckboxGroup({ form, name, label, options, labels, hint, required, columns = 2 }: { form: Form; name: Path; label: string; options: readonly string[]; labels: Record<string, string>; hint?: string; required?: boolean; columns?: number }) {
  const err = getError(form.formState.errors, name);
  return (
    <div className="md:col-span-2">
      <span className="mb-1 block text-sm font-medium">
        {label}
        {required ? <span className="ml-0.5 text-danger">*</span> : null}
      </span>
      <div className={cn("grid gap-2", columns === 3 ? "sm:grid-cols-3" : "sm:grid-cols-2")}>
        {options.map((o) => (
          <label key={o} className="flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm hover:bg-surface-2">
            <input type="checkbox" value={o} {...form.register(name)} className="h-4 w-4 accent-[var(--primary)]" />
            <span>{labels[o] ?? o}</span>
          </label>
        ))}
      </div>
      {err ? <span className="mt-1 block text-xs text-danger">{err}</span> : hint ? <span className="mt-1 block text-xs text-muted">{hint}</span> : null}
    </div>
  );
}

export function SwitchField({ form, name, label, hint }: { form: Form; name: Path; label: string; hint?: string }) {
  return (
    <label className="flex items-start gap-3 rounded-md border border-border px-3 py-2">
      <input type="checkbox" {...form.register(name)} className="mt-1 h-4 w-4 accent-[var(--primary)]" />
      <span>
        <span className="block text-sm font-medium">{label}</span>
        {hint ? <span className="block text-xs text-muted">{hint}</span> : null}
      </span>
    </label>
  );
}
