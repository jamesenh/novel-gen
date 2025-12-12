import { useState } from "react";
import clsx from "clsx";
import { ThemeConflictData } from "../types";

type Props = {
  data: ThemeConflictData;
  onChange: (newData: ThemeConflictData) => void;
};

export default function ThemeConflictView({ data, onChange }: Props) {
  const [editingSubTheme, setEditingSubTheme] = useState<number | null>(null);
  const [editingSubConflict, setEditingSubConflict] = useState<number | null>(null);

  const handleFieldChange = (key: keyof ThemeConflictData, value: any) => {
    onChange({ ...data, [key]: value });
  };

  const handleSubThemeChange = (index: number, value: string) => {
    const newSubThemes = [...(data.sub_themes || [])];
    newSubThemes[index] = value;
    handleFieldChange("sub_themes", newSubThemes);
  };

  const handleAddSubTheme = () => {
    const newSubThemes = [...(data.sub_themes || []), ""];
    handleFieldChange("sub_themes", newSubThemes);
    setEditingSubTheme(newSubThemes.length - 1);
  };

  const handleRemoveSubTheme = (index: number) => {
    const newSubThemes = (data.sub_themes || []).filter((_, i) => i !== index);
    handleFieldChange("sub_themes", newSubThemes);
    setEditingSubTheme(null);
  };

  const handleSubConflictChange = (index: number, value: string) => {
    const newSubConflicts = [...(data.sub_conflicts || [])];
    newSubConflicts[index] = value;
    handleFieldChange("sub_conflicts", newSubConflicts);
  };

  const handleAddSubConflict = () => {
    const newSubConflicts = [...(data.sub_conflicts || []), ""];
    handleFieldChange("sub_conflicts", newSubConflicts);
    setEditingSubConflict(newSubConflicts.length - 1);
  };

  const handleRemoveSubConflict = (index: number) => {
    const newSubConflicts = (data.sub_conflicts || []).filter((_, i) => i !== index);
    handleFieldChange("sub_conflicts", newSubConflicts);
    setEditingSubConflict(null);
  };

  return (
    <div className="h-full overflow-y-auto pr-2">
      {/* 标题区域 */}
      <div className="mb-6 border-b border-slate-200 pb-4">
        <h2 className="text-2xl font-bold text-slate-900">主题与冲突设定</h2>
        <p className="mt-1 text-sm text-slate-500">
          定义故事的核心主题和主要冲突 · 点击各区域可编辑内容
        </p>
      </div>

      <div className="space-y-6">
        {/* 核心主题 */}
        <section className="rounded-xl border border-blue-200 bg-gradient-to-br from-blue-50 to-white p-5">
          <div className="mb-3 flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100">
              <span className="text-lg">🎯</span>
            </div>
            <h3 className="text-lg font-bold text-blue-900">核心主题</h3>
          </div>
          <p className="mb-2 text-xs text-blue-700/70">故事想要表达的中心思想</p>
          <textarea
            className="w-full resize-none rounded-lg border border-blue-200 bg-white/80 p-3 text-sm text-slate-800 transition focus:border-blue-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100"
            rows={2}
            value={data.core_theme || ""}
            onChange={(e) => handleFieldChange("core_theme", e.target.value)}
            placeholder="如：逆境中的成长、正义与邪恶的对抗..."
          />
        </section>

        {/* 次要主题 */}
        <section className="rounded-xl border border-slate-200/80 bg-white/80 p-5">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100">
                <span className="text-lg">📚</span>
              </div>
              <h3 className="text-base font-semibold text-slate-800">次要主题</h3>
            </div>
            <button
              onClick={handleAddSubTheme}
              className="rounded-lg bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600 hover:bg-slate-200"
            >
              + 添加
            </button>
          </div>
          <p className="mb-3 text-xs text-slate-500">辅助核心主题的其他思想元素</p>
          
          <div className="space-y-2">
            {(data.sub_themes || []).length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-200 py-4 text-center text-sm text-slate-400">
                暂无次要主题，点击「+ 添加」创建
              </div>
            ) : (
              (data.sub_themes || []).map((theme, index) => (
                <div
                  key={index}
                  className={clsx(
                    "group flex items-center gap-2 rounded-lg border p-2 transition-all",
                    editingSubTheme === index
                      ? "border-blue-300 bg-blue-50"
                      : "border-slate-200 bg-slate-50/50 hover:border-slate-300"
                  )}
                >
                  <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-slate-200 text-xs font-medium text-slate-600">
                    {index + 1}
                  </span>
                  <input
                    type="text"
                    className="flex-1 bg-transparent px-2 py-1 text-sm text-slate-800 focus:outline-none"
                    value={theme}
                    onChange={(e) => handleSubThemeChange(index, e.target.value)}
                    onFocus={() => setEditingSubTheme(index)}
                    onBlur={() => setEditingSubTheme(null)}
                    placeholder="输入次要主题..."
                  />
                  <button
                    onClick={() => handleRemoveSubTheme(index)}
                    className="flex-shrink-0 rounded p-1 text-slate-400 opacity-0 hover:bg-red-50 hover:text-red-500 group-hover:opacity-100"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))
            )}
          </div>
        </section>

        {/* 主要冲突 */}
        <section className="rounded-xl border border-red-200 bg-gradient-to-br from-red-50 to-white p-5">
          <div className="mb-3 flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-red-100">
              <span className="text-lg">⚔️</span>
            </div>
            <h3 className="text-lg font-bold text-red-900">主要冲突</h3>
          </div>
          <p className="mb-2 text-xs text-red-700/70">推动故事发展的核心矛盾</p>
          <textarea
            className="w-full resize-none rounded-lg border border-red-200 bg-white/80 p-3 text-sm text-slate-800 transition focus:border-red-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-red-100"
            rows={2}
            value={data.main_conflict || ""}
            onChange={(e) => handleFieldChange("main_conflict", e.target.value)}
            placeholder="如：主角与反派势力的对抗、内心矛盾的挣扎..."
          />
        </section>

        {/* 次要冲突 */}
        <section className="rounded-xl border border-slate-200/80 bg-white/80 p-5">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100">
                <span className="text-lg">💥</span>
              </div>
              <h3 className="text-base font-semibold text-slate-800">次要冲突</h3>
            </div>
            <button
              onClick={handleAddSubConflict}
              className="rounded-lg bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600 hover:bg-slate-200"
            >
              + 添加
            </button>
          </div>
          <p className="mb-3 text-xs text-slate-500">丰富故事层次的其他矛盾冲突</p>
          
          <div className="space-y-2">
            {(data.sub_conflicts || []).length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-200 py-4 text-center text-sm text-slate-400">
                暂无次要冲突，点击「+ 添加」创建
              </div>
            ) : (
              (data.sub_conflicts || []).map((conflict, index) => (
                <div
                  key={index}
                  className={clsx(
                    "group flex items-center gap-2 rounded-lg border p-2 transition-all",
                    editingSubConflict === index
                      ? "border-red-300 bg-red-50"
                      : "border-slate-200 bg-slate-50/50 hover:border-slate-300"
                  )}
                >
                  <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-slate-200 text-xs font-medium text-slate-600">
                    {index + 1}
                  </span>
                  <input
                    type="text"
                    className="flex-1 bg-transparent px-2 py-1 text-sm text-slate-800 focus:outline-none"
                    value={conflict}
                    onChange={(e) => handleSubConflictChange(index, e.target.value)}
                    onFocus={() => setEditingSubConflict(index)}
                    onBlur={() => setEditingSubConflict(null)}
                    placeholder="输入次要冲突..."
                  />
                  <button
                    onClick={() => handleRemoveSubConflict(index)}
                    className="flex-shrink-0 rounded p-1 text-slate-400 opacity-0 hover:bg-red-50 hover:text-red-500 group-hover:opacity-100"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))
            )}
          </div>
        </section>

        {/* 作品基调 */}
        <section className="rounded-xl border border-purple-200 bg-gradient-to-br from-purple-50 to-white p-5">
          <div className="mb-3 flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-purple-100">
              <span className="text-lg">🎭</span>
            </div>
            <h3 className="text-lg font-bold text-purple-900">作品基调</h3>
          </div>
          <p className="mb-2 text-xs text-purple-700/70">整体风格与情感氛围</p>
          <input
            type="text"
            className="w-full rounded-lg border border-purple-200 bg-white/80 px-3 py-2 text-sm text-slate-800 transition focus:border-purple-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-purple-100"
            value={data.tone || ""}
            onChange={(e) => handleFieldChange("tone", e.target.value)}
            placeholder="如：热血励志、黑暗沉重、轻松幽默..."
          />
        </section>
      </div>
    </div>
  );
}
