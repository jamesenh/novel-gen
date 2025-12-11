import { OutlineData } from "../types";

type Props = {
  data: OutlineData | null;
  loading?: boolean;
};

export default function OutlineTree({ data, loading }: Props) {
  if (loading) {
    return (
      <div className="glass-panel p-4">
        <h3 className="section-title">大纲</h3>
        <div className="mt-2 muted">加载中...</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="glass-panel p-4">
        <h3 className="section-title">大纲</h3>
        <div className="mt-2 muted">暂无大纲信息</div>
      </div>
    );
  }

  return (
    <div className="glass-panel p-4">
      <h3 className="section-title">大纲</h3>
      <div className="mt-2 space-y-2 text-sm text-slate-700">
        <div>故事前提：{data.story_premise || "—"}</div>
        <div>开端：{data.beginning || "—"}</div>
        <div>发展：{data.development || "—"}</div>
        <div>高潮：{data.climax || "—"}</div>
        <div>结局：{data.resolution || "—"}</div>
        <div className="pt-2 text-xs font-semibold text-slate-500">章节概览</div>
        <div className="space-y-2">
          {(data.chapters || []).map((ch) => (
            <div key={ch.chapter_number} className="rounded-xl border border-slate-100 bg-slate-50 p-2">
              <div className="text-xs font-semibold text-slate-800">
                第{ch.chapter_number}章 {ch.chapter_title}
              </div>
              {ch.summary && <div className="mt-1 text-xs text-slate-600">{ch.summary}</div>}
              {ch.key_events && ch.key_events.length > 0 && (
                <div className="mt-1 text-[11px] text-slate-500">关键事件：{ch.key_events.join(" / ")}</div>
              )}
            </div>
          ))}
          {(data.chapters || []).length === 0 && <div className="text-xs text-slate-500">暂无章节摘要</div>}
        </div>
      </div>
    </div>
  );
}

