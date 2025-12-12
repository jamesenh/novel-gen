import { useState } from "react";
import { createProject } from "../services/api";

type Props = {
  open: boolean;
  onClose: () => void;
  onCreated: () => Promise<void> | void;
};

export default function CreateProjectModal({ open, onClose, onCreated }: Props) {
  const [projectName, setProjectName] = useState("");
  const [chapters, setChapters] = useState(3);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const handleSubmit = async () => {
    if (!projectName.trim()) {
      setError("项目名称不能为空");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await createProject({
        project_name: projectName.trim(),
        initial_chapters: chapters,
      });
      await onCreated();
      onClose();
      setProjectName("");
      setChapters(3);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "创建失败");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur">
      <div className="glass-panel w-full max-w-3xl p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">新建项目</p>
            <h2 className="mt-1 text-xl font-semibold text-slate-900">创建项目</h2>
            <p className="muted">先创建项目目录，进入详情页再完善世界观等基础配置。</p>
          </div>
          <button className="btn-ghost text-sm" onClick={onClose}>
            关闭
          </button>
        </div>

        <div className="mt-5 grid gap-4 text-sm md:grid-cols-2">
          <div className="space-y-2">
            <label className="text-slate-700">项目名称</label>
            <input
              className="input-field"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="如 demo_101"
            />
          </div>
          <div className="space-y-2">
            <label className="text-slate-700">初始章节数</label>
            <input
              type="number"
              min={1}
              className="input-field w-full"
              value={chapters}
              onChange={(e) => setChapters(Number(e.target.value))}
            />
          </div>
          {error && <div className="text-sm text-red-500 md:col-span-2">{error}</div>}
        </div>

        <div className="mt-6 flex justify-end gap-3 text-sm">
          <button className="btn-ghost px-4" onClick={onClose} disabled={submitting}>
            取消
          </button>
          <button className="btn-primary px-6" onClick={handleSubmit} disabled={submitting}>
            {submitting ? "创建中..." : "创建"}
          </button>
        </div>
      </div>
    </div>
  );
}

