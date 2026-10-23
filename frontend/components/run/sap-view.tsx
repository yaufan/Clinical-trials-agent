import { Markdown } from "@/components/ui/markdown";
import type { StatisticalAnalysisPlan } from "@/lib/types";

function kv(o: Record<string, unknown>): Array<[string, string]> {
  return Object.entries(o ?? {}).map(([k, v]) => [k, typeof v === "object" ? JSON.stringify(v) : String(v)]);
}

export function SapView({ sap }: { sap: StatisticalAnalysisPlan }) {
  return (
    <div className="space-y-5 text-sm">
      <section className="grid gap-4 lg:grid-cols-2">
        <div>
          <h3 className="mb-1 font-semibold">主要假設 Primary hypotheses</h3>
          <ul className="list-disc space-y-0.5 pl-5">
            {sap.primary_hypotheses.map((h, i) => (
              <li key={i}>{h}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="mb-1 font-semibold">最終樣本數 Final sample size</h3>
          <dl className="grid grid-cols-2 gap-x-3 gap-y-1 rounded-md border border-border p-3">
            {kv(sap.final_sample_size).map(([k, v]) => (
              <div key={k} className="contents">
                <dt className="text-muted">{k}</dt>
                <dd className="font-mono">{v}</dd>
              </div>
            ))}
          </dl>
          {Object.keys(sap.stratified_allocation ?? {}).length ? (
            <>
              <h4 className="mb-1 mt-3 font-medium">分層配置 Stratified allocation</h4>
              <pre className="overflow-auto rounded-md border border-border bg-surface-2 p-2 text-xs">{JSON.stringify(sap.stratified_allocation, null, 1)}</pre>
            </>
          ) : null}
        </div>
      </section>

      <section>
        <h3 className="mb-2 font-semibold">樣本數計算 (mcp-biostat-calc) Computations</h3>
        <div className="overflow-x-auto rounded-md border border-border">
          <table className="w-full text-sm">
            <thead className="bg-surface-2 text-left">
              <tr>
                <th className="px-3 py-2">工具 Tool</th>
                <th className="px-3 py-2">輸入 Inputs</th>
                <th className="px-3 py-2">輸出 Outputs</th>
                <th className="px-3 py-2">解讀 Interpretation</th>
              </tr>
            </thead>
            <tbody>
              {sap.computations.map((c, i) => (
                <tr key={i} className="border-t border-border align-top">
                  <td className="px-3 py-2 font-mono text-xs">{c.tool}</td>
                  <td className="px-3 py-2">
                    <pre className="max-h-48 overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify(c.inputs, null, 1)}</pre>
                  </td>
                  <td className="px-3 py-2">
                    <pre className="max-h-48 overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify(c.outputs, null, 1)}</pre>
                  </td>
                  <td className="px-3 py-2 text-muted">{c.interpretation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <div>
          <h3 className="mb-1 font-semibold">分析方法 Analysis methods</h3>
          <ul className="list-disc pl-5">
            {sap.analysis_methods.map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="mb-1 font-semibold">次族群分析 Subgroups</h3>
          <ul className="list-disc pl-5">
            {sap.subgroup_analyses.map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="mb-1 font-semibold">缺漏 / 無法判定資料 Missing & indeterminate</h3>
          <p className="text-muted">{sap.handling_of_missing_and_indeterminate}</p>
        </div>
      </section>

      <section>
        <h3 className="mb-2 font-semibold">SAP 敘述 Narrative</h3>
        <div className="rounded-md border border-border p-4">
          <Markdown>{sap.sap_markdown}</Markdown>
        </div>
      </section>
    </div>
  );
}
