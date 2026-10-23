import { Wizard } from "@/components/wizard/wizard";

export default function NewProjectPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">新建計畫書專案 / New protocol project</h1>
        <p className="text-sm text-muted">四步驟結構化輸入 → 多代理人檢索、統計與草擬 → 人工確認實證 → 合規審查。</p>
      </div>
      <Wizard />
    </div>
  );
}
