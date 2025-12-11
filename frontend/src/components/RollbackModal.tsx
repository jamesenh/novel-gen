import { useState } from "react";
import { rollbackProject } from "../services/api";
import { RollbackRequest, RollbackResult } from "../types";

type Props = {
  open: boolean;
  project: string;
  onClose: () => void;
};

const STEP_OPTIONS = [
  { value: "", label: "不按步骤清理" },
  { value: "world_creation", label: "世界观" },
  { value: "theme_conflict_creation", label: "主题/冲突" },
  { value: "character_creation", label: "角色" },
  { value: "outline_creation", label: "大纲" },
  { value: "chapter_planning", label: "章节计划" },
  { value: "chapter_generation", label: "章节生成" },
];

export default function RollbackModal({ open, project, onClose }: Props) {
  const [form, setForm] = useState<RollbackRequest>({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<RollbackResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const update = (patch: Partial<RollbackRequest>) => setForm((prev) => ({ ...prev, ...patch }));

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const payload: RollbackRequest = {
        step: form.step || undefined,
        chapter: form.chapter ? Number(form.chapter) : undefined,
        scene: form.scene ? Number(form.scene) : undefined,
      };
      const res = await rollbackProject(project, payload);
      setResult(res);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "回滚失败");
      setResult(null);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40">
      <div className="w-full max-w-xl rounded-lg bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">回滚项目</h2>
            <p className="text-xs text-slate-500">可按步骤、章节、场景进行回滚</p>
          </div>
          <button className="text-sm text-slate-500 hover:text-slate-800" onClick={onClose}>
            关闭
          </button>
        </div>
        <div className="mt-4 space-y-3 text-sm">
          <div>
            <label className="text-slate-700">步骤</label>
            <select
              className="mt-1 w-full rounded border border-slate-200 px-3 py-2 focus:border-blue-500 focus:outline-none"
              value={form.step || ""}
              onChange={(e) => update({ step: e.target.value || undefined })}
            >
              {STEP_OPTIONS.map((opt) => (
                <option key={opt.value || "none"} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-slate-700">章节号 (&gt;=1)</label>
              <input
                type="number"
                min={1}
                className="mt-1 w-full rounded border border-slate-200 px-3 py-2 focus:border-blue-500 focus:outline-none"
                value={form.chapter ?? ""}
                onChange={(e) => update({ chapter: e.target.value ? Number(e.target.value) : undefined })}
              />
            </div>
            <div>
              <label className="text-slate-700">场景号 (可选)</label>
              <input
                type="number"
                min={1}
                className="mt-1 w-full rounded border border-slate-200 px-3 py-2 focus:border-blue-500 focus:outline-none"
                value={form.scene ?? ""}
                onChange={(e) => update({ scene: e.target.value ? Number(e.target.value) : undefined })}
              />
            </div>
          </div>
          {error && <div className="text-sm text-red-500">{error}</div>}
          {result && (
            <div className="rounded border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
              <div>已删除文件：{result.deleted_files}</div>
              <div>清理内存键：{result.cleared_memories}</div>
              {result.files.length > 0 && (
                <details className="mt-1">
                  <summary className="cursor-pointer text-blue-600">文件列表</summary>
                  <ul className="mt-1 list-disc pl-4">
                    {result.files.map((f) => (
                      <li key={f}>{f}</li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          )}
        </div>
        <div className="mt-5 flex justify-end gap-3 text-sm">
          <button className="rounded px-4 py-2 text-slate-700 hover:bg-slate-100" onClick={onClose} disabled={submitting}>
            取消
          </button>
          <button
            className="rounded bg-blue-600 px-4 py-2 text-white shadow hover:bg-blue-700 disabled:opacity-60"
            onClick={handleSubmit}
            disabled={submitting}
          >
            {submitting ? "回滚中..." : "执行回滚"}
          </button>
        </div>
      </div>
    </div>
  );
}

