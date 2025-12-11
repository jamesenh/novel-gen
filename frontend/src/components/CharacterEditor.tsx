import { useState } from "react";
import { Character, CharactersData } from "../types";

type Props = {
  data: CharactersData | null;
  loading?: boolean;
  onSave: (payload: CharactersData) => Promise<void> | void;
  onCancel: () => void;
};

const emptyChar: Character = { name: "", role: "", gender: "", appearance: "", personality: "", background: "", motivation: "" };

export default function CharacterEditor({ data, loading, onSave, onCancel }: Props) {
  const [form, setForm] = useState<CharactersData>({
    protagonist: data?.protagonist ? { ...emptyChar, ...data.protagonist } : { ...emptyChar },
    antagonist: data?.antagonist ? { ...emptyChar, ...data.antagonist } : { ...emptyChar },
    supporting_characters: data?.supporting_characters || [],
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateChar = (key: "protagonist" | "antagonist", patch: Partial<Character>) =>
    setForm((prev) => ({ ...prev, [key]: { ...(prev[key] || emptyChar), ...patch } }));

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
      <h3 className="section-title">编辑角色</h3>
      {loading && <div className="mt-2 muted">加载中...</div>}
      <div className="mt-2 grid grid-cols-2 gap-3 text-sm">
        {(["protagonist", "antagonist"] as const).map((roleKey) => {
          const label = roleKey === "protagonist" ? "主角" : "反派";
          const char = form[roleKey] || emptyChar;
          return (
            <div key={roleKey} className="flex flex-col gap-1 rounded-xl border border-slate-100 bg-white/70 p-3 shadow-inner shadow-slate-200/60">
              <div className="text-xs font-semibold text-slate-600">{label}</div>
              <input className="input-field" placeholder="姓名" value={char.name || ""} onChange={(e) => updateChar(roleKey, { name: e.target.value })} />
              <input className="input-field" placeholder="身份" value={char.role || ""} onChange={(e) => updateChar(roleKey, { role: e.target.value })} />
              <input className="input-field" placeholder="性别" value={char.gender || ""} onChange={(e) => updateChar(roleKey, { gender: e.target.value })} />
              <input className="input-field" placeholder="外貌" value={char.appearance || ""} onChange={(e) => updateChar(roleKey, { appearance: e.target.value })} />
              <input className="input-field" placeholder="性格" value={char.personality || ""} onChange={(e) => updateChar(roleKey, { personality: e.target.value })} />
              <input className="input-field" placeholder="背景" value={char.background || ""} onChange={(e) => updateChar(roleKey, { background: e.target.value })} />
              <input className="input-field" placeholder="动机" value={char.motivation || ""} onChange={(e) => updateChar(roleKey, { motivation: e.target.value })} />
            </div>
          );
        })}
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

