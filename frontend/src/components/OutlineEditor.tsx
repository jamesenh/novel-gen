import { useState } from "react";
import { OutlineData } from "../types";

type Props = {
  data: OutlineData | null;
  loading?: boolean;
  onSave: (payload: OutlineData) => Promise<void> | void;
  onCancel: () => void;
};

export default function OutlineEditor({ data, loading, onSave, onCancel }: Props) {
  const [form, setForm] = useState<OutlineData>({
    story_premise: data?.story_premise || "",
    beginning: data?.beginning || "",
    development: data?.development || "",
    climax: data?.climax || "",
    resolution: data?.resolution || "",
    chapters: data?.chapters || [],
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const update = (patch: Partial<OutlineData>) => setForm((prev) => ({ ...prev, ...patch }));

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await onSave(form);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "保存失败");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="glass-panel p-4">
      <h3 className="section-title">编辑大纲</h3>
      {loading && <div className="mt-2 muted">加载中...</div>}
      <div className="mt-2 grid grid-cols-2 gap-3 text-sm">
        <label className="col-span-2 flex flex-col gap-1">
          <span className="text-slate-700">故事前提</span>
          <textarea className="input-field" rows={2} value={form.story_premise || ""} onChange={(e) => update({ story_premise: e.target.value })} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-slate-700">开端</span>
          <textarea className="input-field" rows={2} value={form.beginning || ""} onChange={(e) => update({ beginning: e.target.value })} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-slate-700">发展</span>
          <textarea className="input-field" rows={2} value={form.development || ""} onChange={(e) => update({ development: e.target.value })} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-slate-700">高潮</span>
          <textarea className="input-field" rows={2} value={form.climax || ""} onChange={(e) => update({ climax: e.target.value })} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-slate-700">结局</span>
          <textarea className="input-field" rows={2} value={form.resolution || ""} onChange={(e) => update({ resolution: e.target.value })} />
        </label>
      </div>
      {error && <div className="mt-2 text-sm text-red-500">{error}</div>}
      <div className="mt-3 flex justify-end gap-2 text-sm">
        <button className="btn-ghost px-3 py-1" onClick={onCancel} disabled={saving}>
          取消
        </button>
        <button
          className="btn-primary px-3 py-1 disabled:opacity-60"
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? "保存中..." : "保存"}
        </button>
      </div>
    </div>
  );
}

