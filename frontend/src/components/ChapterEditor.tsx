import { useState } from "react";
import { ChapterContent, SceneContent } from "../types";

type Props = {
  data: ChapterContent | null;
  loading?: boolean;
  onSave: (payload: ChapterContent) => Promise<void> | void;
  onCancel: () => void;
};

export default function ChapterEditor({ data, loading, onSave, onCancel }: Props) {
  const [draft, setDraft] = useState<ChapterContent | null>(data);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateScene = (scene_number: number, patch: Partial<SceneContent>) => {
    if (!draft) return;
    setDraft({
      ...draft,
      scenes: draft.scenes.map((s) => (s.scene_number === scene_number ? { ...s, ...patch } : s)),
    });
  };

  const handleSave = async () => {
    if (!draft) return;
    setSaving(true);
    setError(null);
    try {
      const payload: ChapterContent = {
        ...draft,
        scenes: draft.scenes.map((s) => ({
          ...s,
          word_count: s.word_count ?? s.content.length,
        })),
      };
      await onSave(payload);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "保存失败");
    } finally {
      setSaving(false);
    }
  };

  if (!draft) {
    return (
      <div className="glass-panel p-4">
        <h3 className="section-title">编辑章节</h3>
        <div className="muted">请先选择章节</div>
      </div>
    );
  }

  return (
    <div className="glass-panel p-4">
      <h3 className="section-title">编辑章节</h3>
      {loading && <div className="mt-2 muted">加载中...</div>}
      <div className="mt-2 space-y-3 text-sm">
        <div className="flex flex-col gap-1">
          <span className="text-slate-700">章节标题</span>
          <input className="input-field" value={draft.chapter_title} onChange={(e) => setDraft({ ...draft, chapter_title: e.target.value })} />
        </div>
        <div className="space-y-3">
          {draft.scenes.map((scene) => (
            <div key={scene.scene_number} className="rounded-xl border border-slate-100 bg-slate-50 p-3">
              <div className="text-xs font-semibold text-slate-600">场景 {scene.scene_number}</div>
              <textarea
                className="mt-2 w-full rounded-xl border border-slate-200 bg-white/80 px-3 py-2 shadow-inner"
                rows={4}
                value={scene.content}
                onChange={(e) => updateScene(scene.scene_number, { content: e.target.value })}
              />
            </div>
          ))}
          {draft.scenes.length === 0 && <div className="text-xs text-slate-500">暂无场景</div>}
        </div>
        {error && <div className="text-sm text-red-500">{error}</div>}
        <div className="flex justify-end gap-2">
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
    </div>
  );
}

