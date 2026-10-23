export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("zh-TW", { hour12: false });
}

/** Split a newline-separated textarea into trimmed non-empty lines. */
export function linesToList(value: string | undefined | null): string[] {
  return (value ?? "")
    .split(/\r?\n/)
    .map((s) => s.trim())
    .filter(Boolean);
}

export function listToLines(value: string[] | undefined | null): string {
  return (value ?? []).join("\n");
}
