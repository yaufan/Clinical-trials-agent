"use client";

import { Save } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Markdown } from "@/components/ui/markdown";
import { Textarea } from "@/components/ui/textarea";
import { type DraftSection, SECTION_KEYS } from "@/lib/types";
import { cn } from "@/lib/utils";

export function SectionEditor({
  sections,
  onSave,
  busy,
}: {
  sections: DraftSection[];
  onSave: (key: string, markdown: string) => Promise<void>;
  busy?: boolean;
}) {
  const ordered = useMemo(() => {
    const byKey = new Map(sections.map((s) => [s.key, s]));
    const out: Array<{ key: string; zh: string; en: string; section: DraftSection | undefined }> = SECTION_KEYS.map(([key, en, zh]) => ({ key, zh, en, section: byKey.get(key) }));
    for (const s of sections) if (!SECTION_KEYS.some(([k]) => k === s.key)) out.push({ key: s.key, zh: s.title_zh, en: s.title_en, section: s });
    return out;
  }, [sections]);

  const [selected, setSelected] = useState<string>(ordered.find((o) => o.section)?.key ?? ordered[0]?.key ?? "synopsis");
  const current = ordered.find((o) => o.key === selected);
  const [draft, setDraft] = useState(current?.section?.markdown ?? "");
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    setDraft(current?.section?.markdown ?? "");
    setDirty(false);
  }, [selected, current?.section?.markdown, current?.section?.revision]);

  return (
    <div className="grid gap-4 lg:grid-cols-[16rem_1fr_1fr]">
      <nav className="space-y-1">
        {ordered.map((o) => (
          <button
            key={o.key}
            onClick={() => setSelected(o.key)}
            className={cn(
              "w-full rounded-md border px-3 py-2 text-left text-sm transition",
              o.key === selected ? "border-primary bg-primary/10" : "border-border hover:bg-surface-2",
              !o.section && "opacity-60",
            )}
          >
            <div className="font-medium leading-tight">{o.zh}</div>
            <div className="text-xs text-muted">{o.en}</div>
            {o.section ? (
              <div className="mt-1 flex flex-wrap gap-1">
                <Badge className="text-[10px]">rev {o.section.revision}</Badge>
                {o.section.open_questions.length ? (
                  <Badge tone="warning" className="text-[10px]">
                    {o.section.open_questions.length} open Q
                  </Badge>
                ) : null}
              </div>
            ) : (
              <div className="mt-1 text-[10px] text-muted">尚未生成 / not generated</div>
            )}
          </button>
        ))}
      </nav>

      <div className="flex min-h-[32rem] flex-col">
        <div className="mb-2 flex items-center justify-between gap-2">
          <div className="text-sm font-medium">
            Markdown 編輯 <span className="text-muted">({current?.zh})</span>
          </div>
          <Button
            size="sm"
            disabled={!dirty || busy || !current}
            onClick={async () => {
              if (!current) return;
              await onSave(current.key, draft);
              setDirty(false);
            }}
          >
            <Save size={14} /> 儲存 Save
          </Button>
        </div>
        <Textarea
          className="min-h-0 flex-1 resize-none font-mono text-xs leading-relaxed"
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value);
            setDirty(true);
          }}
          placeholder="此章節尚未生成 / section not generated yet"
        />
        {current?.section?.open_questions.length ? (
          <div className="mt-2 rounded-md border border-warning/40 bg-warning/10 p-2 text-xs">
            <div className="font-medium">待釐清 Open questions</div>
            <ul className="list-disc pl-4">
              {current.section.open_questions.map((q, i) => (
                <li key={i}>{q}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {current?.section?.citations.length ? (
          <div className="mt-2 rounded-md border border-border p-2 text-xs">
            <div className="font-medium">引用 Citations</div>
            <ol className="list-decimal pl-4 text-muted">
              {current.section.citations.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ol>
          </div>
        ) : null}
      </div>

      <div className="min-h-[32rem] overflow-auto rounded-md border border-border bg-surface p-4">
        <div className="mb-2 text-xs text-muted">預覽 Preview{dirty ? " · 未儲存 unsaved" : ""}</div>
        <Markdown>{draft}</Markdown>
      </div>
    </div>
  );
}
