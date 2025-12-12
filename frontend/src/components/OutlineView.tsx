import { useState } from "react";
import clsx from "clsx";
import { OutlineData, OutlineChapter } from "../types";

type Props = {
  data: OutlineData;
  onChange: (newData: OutlineData) => void;
};

// 故事结构字段配置
const STRUCTURE_FIELDS = [
  { 
    key: "story_premise" as const, 
    label: "故事前提", 
    icon: "💡",
    color: "amber",
    description: "故事的核心设定与背景"
  },
  { 
    key: "beginning" as const, 
    label: "开端", 
    icon: "🌅",
    color: "blue",
    description: "故事的开始，介绍主要人物和背景"
  },
  { 
    key: "development" as const, 
    label: "发展", 
    icon: "📈",
    color: "green",
    description: "情节推进，冲突逐渐展开"
  },
  { 
    key: "climax" as const, 
    label: "高潮", 
    icon: "🔥",
    color: "red",
    description: "故事最紧张、最关键的转折点"
  },
  { 
    key: "resolution" as const, 
    label: "结局", 
    icon: "🏁",
    color: "purple",
    description: "冲突解决，故事收尾"
  },
];

const COLOR_CLASSES: Record<string, { border: string; bg: string; text: string; ring: string }> = {
  amber: { border: "border-amber-200", bg: "bg-gradient-to-br from-amber-50 to-white", text: "text-amber-900", ring: "focus:ring-amber-100" },
  blue: { border: "border-blue-200", bg: "bg-gradient-to-br from-blue-50 to-white", text: "text-blue-900", ring: "focus:ring-blue-100" },
  green: { border: "border-green-200", bg: "bg-gradient-to-br from-green-50 to-white", text: "text-green-900", ring: "focus:ring-green-100" },
  red: { border: "border-red-200", bg: "bg-gradient-to-br from-red-50 to-white", text: "text-red-900", ring: "focus:ring-red-100" },
  purple: { border: "border-purple-200", bg: "bg-gradient-to-br from-purple-50 to-white", text: "text-purple-900", ring: "focus:ring-purple-100" },
};

// 计算文本需要的行数
const calcRows = (text: string | undefined, minRows = 2, charsPerRow = 60): number => {
  if (!text) return minRows;
  const lines = text.split('\n');
  let totalRows = 0;
  for (const line of lines) {
    totalRows += Math.max(1, Math.ceil(line.length / charsPerRow));
  }
  return Math.max(minRows, totalRows);
};

export default function OutlineView({ data, onChange }: Props) {
  const [collapsedChapters, setCollapsedChapters] = useState<Set<number>>(new Set());
  const [editingEvent, setEditingEvent] = useState<{ chapter: number; event: number } | null>(null);

  const toggleChapter = (index: number) => {
    setCollapsedChapters(prev => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  const handleFieldChange = (key: keyof OutlineData, value: any) => {
    onChange({ ...data, [key]: value });
  };

  const handleChapterChange = (index: number, field: keyof OutlineChapter, value: any) => {
    const chapters = [...(data.chapters || [])];
    chapters[index] = { ...chapters[index], [field]: value };
    handleFieldChange("chapters", chapters);
  };

  const handleKeyEventChange = (chapterIndex: number, eventIndex: number, value: string) => {
    const chapters = [...(data.chapters || [])];
    const events = [...(chapters[chapterIndex].key_events || [])];
    events[eventIndex] = value;
    chapters[chapterIndex] = { ...chapters[chapterIndex], key_events: events };
    handleFieldChange("chapters", chapters);
  };

  const handleAddKeyEvent = (chapterIndex: number) => {
    const chapters = [...(data.chapters || [])];
    const events = [...(chapters[chapterIndex].key_events || []), ""];
    chapters[chapterIndex] = { ...chapters[chapterIndex], key_events: events };
    handleFieldChange("chapters", chapters);
    setEditingEvent({ chapter: chapterIndex, event: events.length - 1 });
  };

  const handleRemoveKeyEvent = (chapterIndex: number, eventIndex: number) => {
    const chapters = [...(data.chapters || [])];
    const events = (chapters[chapterIndex].key_events || []).filter((_, i) => i !== eventIndex);
    chapters[chapterIndex] = { ...chapters[chapterIndex], key_events: events };
    handleFieldChange("chapters", chapters);
    setEditingEvent(null);
  };

  const handleAddChapter = () => {
    const chapters = data.chapters || [];
    const newChapter: OutlineChapter = {
      chapter_number: chapters.length + 1,
      chapter_title: `第${chapters.length + 1}章`,
      summary: "",
      key_events: [],
    };
    handleFieldChange("chapters", [...chapters, newChapter]);
  };

  const handleRemoveChapter = (index: number) => {
    const chapters = (data.chapters || []).filter((_, i) => i !== index);
    // 重新编号
    const renumbered = chapters.map((ch, i) => ({ ...ch, chapter_number: i + 1 }));
    handleFieldChange("chapters", renumbered);
    // 清理已删除章节的折叠状态
    setCollapsedChapters(prev => {
      const newSet = new Set<number>();
      prev.forEach(i => {
        if (i < index) newSet.add(i);
        else if (i > index) newSet.add(i - 1);
      });
      return newSet;
    });
  };

  return (
    <div className="h-full overflow-y-auto pr-2">
      {/* 标题区域 */}
      <div className="mb-6 border-b border-slate-200 pb-4">
        <h2 className="text-2xl font-bold text-slate-900">📖 故事大纲</h2>
        <p className="mt-1 text-sm text-slate-500">
          定义故事结构与章节规划 · 点击各区域可编辑内容
        </p>
      </div>

      {/* 故事结构 */}
      <div className="mb-6">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-100 text-xs">
            📋
          </span>
          故事结构
        </h3>
        <div className="space-y-4">
          {STRUCTURE_FIELDS.map((field) => {
            const colors = COLOR_CLASSES[field.color];
            return (
              <section
                key={field.key}
                className={clsx(
                  "rounded-xl border p-4 transition-all",
                  colors.border,
                  colors.bg
                )}
              >
                <div className="mb-2 flex items-center gap-2">
                  <div className={clsx(
                    "flex h-8 w-8 items-center justify-center rounded-full",
                    `bg-${field.color}-100`
                  )}>
                    <span className="text-lg">{field.icon}</span>
                  </div>
                  <h4 className={clsx("text-base font-bold", colors.text)}>
                    {field.label}
                  </h4>
                </div>
                <p className={clsx("mb-2 text-xs", `text-${field.color}-700/70`)}>
                  {field.description}
                </p>
                <textarea
                  className={clsx(
                    "w-full rounded-lg border bg-white/80 p-3 text-sm text-slate-800 transition",
                    "focus:bg-white focus:outline-none focus:ring-2",
                    colors.border,
                    colors.ring
                  )}
                  rows={calcRows(data[field.key] as string, 2)}
                  value={(data[field.key] as string) || ""}
                  onChange={(e) => handleFieldChange(field.key, e.target.value)}
                  placeholder={`请输入${field.label}...`}
                />
              </section>
            );
          })}
        </div>
      </div>

      {/* 章节列表 */}
      <div className="mb-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-700">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-100 text-xs">
              📚
            </span>
            章节列表
            {data.chapters && data.chapters.length > 0 && (
              <span className="ml-1 rounded-full bg-slate-200 px-2 py-0.5 text-xs text-slate-600">
                共 {data.chapters.length} 章
              </span>
            )}
          </h3>
          <button
            onClick={handleAddChapter}
            className="rounded-lg bg-blue-100 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-200"
          >
            + 添加章节
          </button>
        </div>

        {(!data.chapters || data.chapters.length === 0) ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/50 py-8 text-center">
            <div className="mb-2 text-3xl">📝</div>
            <p className="text-sm text-slate-500">暂无章节</p>
            <p className="text-xs text-slate-400">点击「+ 添加章节」开始规划</p>
          </div>
        ) : (
          <div className="space-y-3">
            {data.chapters.map((chapter, index) => {
              const isCollapsed = collapsedChapters.has(index);
              return (
              <div
                key={index}
                className={clsx(
                  "rounded-xl border transition-all",
                  !isCollapsed
                    ? "border-blue-300 bg-blue-50/50 shadow-sm"
                    : "border-slate-200 bg-white/80 hover:border-slate-300"
                )}
              >
                {/* 章节头部 */}
                <div
                  className="flex cursor-pointer items-center gap-3 p-4"
                  onClick={() => toggleChapter(index)}
                >
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-blue-600 text-sm font-bold text-white shadow-sm">
                    {chapter.chapter_number}
                  </div>
                  <div className="flex-1 min-w-0">
                    <input
                      type="text"
                      className={clsx(
                        "w-full bg-transparent text-base font-semibold text-slate-800 focus:outline-none",
                        "border-b border-transparent hover:border-slate-300 focus:border-blue-400"
                      )}
                      value={chapter.chapter_title || ""}
                      onChange={(e) => handleChapterChange(index, "chapter_title", e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                      placeholder="章节标题"
                    />
                    {chapter.summary && isCollapsed && (
                      <p className="mt-1 truncate text-xs text-slate-500">
                        {chapter.summary}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {chapter.key_events && chapter.key_events.length > 0 && (
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                        {chapter.key_events.length} 个事件
                      </span>
                    )}
                    <svg
                      className={clsx(
                        "h-5 w-5 text-slate-400 transition-transform",
                        !isCollapsed && "rotate-180"
                      )}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                </div>

                {/* 展开内容 */}
                {!isCollapsed && (
                  <div className="border-t border-slate-200 p-4">
                    {/* 章节摘要 */}
                    <div className="mb-4">
                      <label className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-slate-600">
                        <span>📝</span> 章节摘要
                      </label>
                      <textarea
                        className="w-full rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-800 transition focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
                        rows={calcRows(chapter.summary, 2)}
                        value={chapter.summary || ""}
                        onChange={(e) => handleChapterChange(index, "summary", e.target.value)}
                        placeholder="描述这一章的主要内容..."
                      />
                    </div>

                    {/* 关键事件 */}
                    <div className="mb-4">
                      <div className="mb-2 flex items-center justify-between">
                        <label className="flex items-center gap-1.5 text-xs font-medium text-slate-600">
                          <span>⚡</span> 关键事件
                        </label>
                        <button
                          onClick={() => handleAddKeyEvent(index)}
                          className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600 hover:bg-slate-200"
                        >
                          + 添加
                        </button>
                      </div>
                      
                      {(!chapter.key_events || chapter.key_events.length === 0) ? (
                        <div className="rounded-lg border border-dashed border-slate-200 py-3 text-center text-xs text-slate-400">
                          暂无关键事件
                        </div>
                      ) : (
                        <div className="space-y-2">
                          {chapter.key_events.map((event, eventIndex) => (
                            <div
                              key={eventIndex}
                              className={clsx(
                                "group flex items-center gap-2 rounded-lg border p-2 transition-all",
                                editingEvent?.chapter === index && editingEvent?.event === eventIndex
                                  ? "border-blue-300 bg-blue-50"
                                  : "border-slate-200 bg-slate-50/50 hover:border-slate-300"
                              )}
                            >
                              <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-medium text-blue-700">
                                {eventIndex + 1}
                              </span>
                              <input
                                type="text"
                                className="flex-1 bg-transparent px-1 py-0.5 text-sm text-slate-800 focus:outline-none"
                                value={event}
                                onChange={(e) => handleKeyEventChange(index, eventIndex, e.target.value)}
                                onFocus={() => setEditingEvent({ chapter: index, event: eventIndex })}
                                onBlur={() => setEditingEvent(null)}
                                placeholder="描述关键事件..."
                              />
                              <button
                                onClick={() => handleRemoveKeyEvent(index, eventIndex)}
                                className="flex-shrink-0 rounded p-1 text-slate-400 opacity-0 hover:bg-red-50 hover:text-red-500 group-hover:opacity-100"
                              >
                                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* 删除章节按钮 */}
                    <div className="flex justify-end">
                      <button
                        onClick={() => handleRemoveChapter(index)}
                        className="rounded-lg bg-red-50 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-100"
                      >
                        删除此章节
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
