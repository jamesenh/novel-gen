import { useState } from "react";
import { WorldView } from "../types";

type Props = {
  data: WorldView | null;
  loading?: boolean;
  onSave: (payload: WorldView) => Promise<void> | void;
  onCancel: () => void;
};

export default function WorldEditor({ data, loading, onSave, onCancel }: Props) {
  const [form, setForm] = useState<WorldView>(
    data || { world_name: "", time_period: "", geography: "", social_system: "", technology_level: "", culture_customs: "" },
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const update = (patch: Partial<WorldView>) => setForm((prev) => ({ ...prev, ...patch }));

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
      <h3 className="section-title">编辑世界观</h3>
      {loading && <div className="mt-2 muted">加载中...</div>}
      <div className="mt-2 grid grid-cols-2 gap-3 text-sm">
        <label className="flex flex-col gap-1">
          <span className="text-slate-700">名称</span>
          <input className="input-field" value={form.world_name || ""} onChange={(e) => update({ world_name: e.target.value })} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-slate-700">时代</span>
          <input className="input-field" value={form.time_period || ""} onChange={(e) => update({ time_period: e.target.value })} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-slate-700">地理</span>
          <input className="input-field" value={form.geography || ""} onChange={(e) => update({ geography: e.target.value })} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-slate-700">社会</span>
          <input className="input-field" value={form.social_system || ""} onChange={(e) => update({ social_system: e.target.value })} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-slate-700">科技</span>
          <input className="input-field" value={form.technology_level || ""} onChange={(e) => update({ technology_level: e.target.value })} />
        </label>
        <label className="col-span-2 flex flex-col gap-1">
          <span className="text-slate-700">风俗</span>
          <textarea className="input-field" rows={2} value={form.culture_customs || ""} onChange={(e) => update({ culture_customs: e.target.value })} />
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

