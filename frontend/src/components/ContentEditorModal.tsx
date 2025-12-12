import { useEffect, useState, useMemo } from "react";
import clsx from "clsx";
import { fetchContent, generateContent, saveContent } from "../services/api";
import { ContentTarget, ContentVariant, CharactersData, WorldView, ThemeConflictData, OutlineData } from "../types";
import CharacterNetworkView from "./CharacterNetworkView";
import WorldSettingView from "./WorldSettingView";
import ThemeConflictView from "./ThemeConflictView";
import OutlineView from "./OutlineView";

type Props = {
  open: boolean;
  project: string;
  target: ContentTarget;
  onClose: () => void;
  onSaved?: () => void;
};

const TARGET_LABELS: Record<ContentTarget, string> = {
  world: "世界观",
  theme: "主题冲突",
  characters: "角色",
  outline: "大纲",
};

const TARGET_TIPS: Record<ContentTarget, string> = {
  world: "输入世界观描述（如「修仙世界」「赛博朋克都市」）",
  theme: "输入主题方向（如「复仇」「成长」「爱情」），需先完成世界观",
  characters: "基于世界观和主题冲突自动生成角色，需先完成前两步",
  outline: "基于所有前置内容自动生成大纲，需先完成世界观、主题、角色",
};

const CHARACTER_COUNT_OPTIONS = [3, 4, 5, 6, 7, 8];
const CHAPTER_COUNT_OPTIONS = [3, 5, 8, 10, 15, 20];

export default function ContentEditorModal({
  open,
  project,
  target,
  onClose,
  onSaved,
}: Props) {
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 用户输入的提示
  const [userPrompt, setUserPrompt] = useState("");
  const [numVariants, setNumVariants] = useState(3);
  const [numCharacters, setNumCharacters] = useState(5);
  const [numChapters, setNumChapters] = useState(5);
  const [expand, setExpand] = useState(false);

  // 生成的候选列表
  const [variants, setVariants] = useState<ContentVariant[]>([]);
  const [selectedVariantId, setSelectedVariantId] = useState<string | null>(null);

  // 编辑器内容（JSON 字符串）
  const [editorContent, setEditorContent] = useState("");
  const [jsonError, setJsonError] = useState<string | null>(null);

  // 视图模式 - 支持 world, theme, characters 的可视化视图
  const [viewMode, setViewMode] = useState<"visual" | "json">("visual");

  // 是否已有内容
  const [hasExisting, setHasExisting] = useState(false);

  useEffect(() => {
    if (!open) return;
    // 重置状态
    setError(null);
    setVariants([]);
    setSelectedVariantId(null);
    setEditorContent("");
    setJsonError(null);
    setUserPrompt("");
    setNumCharacters(5);
    setNumChapters(5);
    
    // 默认视图模式 - world/theme/characters/outline 使用可视化视图
    setViewMode("visual");

    // 尝试加载已有内容
    setLoading(true);
    fetchContent(project, target)
      .then((data) => {
        if (data) {
          setEditorContent(JSON.stringify(data, null, 2));
          setHasExisting(true);
        } else {
          setHasExisting(false);
        }
      })
      .catch(() => {
        setHasExisting(false);
      })
      .finally(() => setLoading(false));
  }, [open, project, target]);

  const handleGenerate = async () => {
    setError(null);
    setGenerating(true);
    try {
      let payload;
      if (target === "characters") {
        payload = {
          target,
          user_prompt: userPrompt,
          num_characters: numCharacters,
        };
      } else if (target === "outline") {
        payload = {
          target,
          user_prompt: userPrompt,
          num_chapters: numChapters,
        };
      } else {
        payload = {
          target,
          user_prompt: userPrompt,
          num_variants: numVariants,
          expand,
        };
      }
      const result = await generateContent(project, payload);
      setVariants(result.variants);
      setSelectedVariantId(null);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "生成失败，请重试");
    } finally {
      setGenerating(false);
    }
  };

  const handleSelectVariant = (variant: ContentVariant) => {
    setSelectedVariantId(variant.variant_id);
    setEditorContent(JSON.stringify(variant.payload, null, 2));
    setJsonError(null);
  };

  const handleEditorChange = (value: string) => {
    setEditorContent(value);
    // 实时校验 JSON
    try {
      JSON.parse(value);
      setJsonError(null);
    } catch {
      setJsonError("JSON 格式错误");
    }
  };

  const handleSave = async () => {
    if (!editorContent.trim()) {
      setError("内容不能为空");
      return;
    }

    let payload: Record<string, any>;
    try {
      payload = JSON.parse(editorContent);
    } catch {
      setError("JSON 格式错误，请检查");
      return;
    }

    setError(null);
    setSaving(true);
    try {
      await saveContent(project, target, payload);
      onSaved?.();
      onClose();
    } catch (e: any) {
      setError(e?.response?.data?.detail || "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const label = TARGET_LABELS[target];
  const tip = TARGET_TIPS[target];
  const canGenerate = target === "world" || target === "theme" || target === "characters" || target === "outline";
  
  // 解析 JSON 数据用于可视化视图
  const parsedData = useMemo(() => {
    if (!editorContent) return {};
    try {
      return JSON.parse(editorContent);
    } catch {
      return {};
    }
  }, [editorContent]);

  // 保持 Hook 顺序一致，确保在 open 变化时不会触发 Hook 次序错误
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur">
      <div className="glass-panel flex max-h-[90vh] w-full max-w-4xl flex-col p-6">
        {/* 头部 */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              内容编辑
            </p>
            <h2 className="mt-1 text-xl font-semibold text-slate-900">
              {label}
            </h2>
            <p className="muted text-sm">{tip}</p>
          </div>
          <button className="btn-ghost text-sm" onClick={onClose}>
            关闭
          </button>
        </div>

        {loading && (
          <div className="mt-4 text-center text-slate-500">加载中...</div>
        )}

        {!loading && (
          <div className="mt-4 flex flex-1 flex-col gap-4 overflow-hidden">
            {/* LLM 生成区 */}
            {canGenerate && (
              <div className="rounded-xl border border-slate-200/80 bg-white/60 p-4">
                <div className="flex flex-wrap items-end gap-3">
                  <div className="flex-1">
                    <label className="text-xs text-slate-600">提示词</label>
                    <input
                      className="input-field mt-1"
                      placeholder={target === "world" ? "如：修仙世界、现代都市" : "可选，留空自动推导"}
                      value={userPrompt}
                      onChange={(e) => setUserPrompt(e.target.value)}
                      disabled={generating}
                    />
                  </div>
                  {target === "characters" ? (
                    <div className="w-28">
                      <label className="text-xs text-slate-600">角色数量</label>
                      <select
                        className="input-field mt-1"
                        value={numCharacters}
                        onChange={(e) => setNumCharacters(Number(e.target.value))}
                        disabled={generating}
                      >
                        {CHARACTER_COUNT_OPTIONS.map((n) => (
                          <option key={n} value={n}>
                            {n}
                          </option>
                        ))}
                      </select>
                    </div>
                  ) : target === "outline" ? (
                    <div className="w-28">
                      <label className="text-xs text-slate-600">章节数量</label>
                      <select
                        className="input-field mt-1"
                        value={numChapters}
                        onChange={(e) => setNumChapters(Number(e.target.value))}
                        disabled={generating}
                      >
                        {CHAPTER_COUNT_OPTIONS.map((n) => (
                          <option key={n} value={n}>
                            {n}
                          </option>
                        ))}
                      </select>
                    </div>
                  ) : (
                    <div className="w-24">
                      <label className="text-xs text-slate-600">候选数</label>
                      <select
                        className="input-field mt-1"
                        value={numVariants}
                        onChange={(e) => setNumVariants(Number(e.target.value))}
                        disabled={generating}
                      >
                        {[1, 2, 3, 4, 5].map((n) => (
                          <option key={n} value={n}>
                            {n}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                  {target === "world" && (
                    <label className="flex items-center gap-1.5 text-xs text-slate-600">
                      <input
                        type="checkbox"
                        checked={expand}
                        onChange={(e) => setExpand(e.target.checked)}
                        disabled={generating}
                      />
                      扩写
                    </label>
                  )}
                  <button
                    className="btn-primary px-4 py-2"
                    onClick={handleGenerate}
                    disabled={generating}
                  >
                    {generating
                      ? "生成中..."
                      : target === "characters"
                        ? "生成角色"
                        : target === "outline"
                          ? "生成大纲"
                          : "生成候选"}
                  </button>
                </div>

                {/* 候选列表 */}
                {variants.length > 0 && (
                  <div className="mt-4 space-y-2">
                    <div className="text-xs font-medium text-slate-600">
                      候选列表（点击选择填入编辑器）
                    </div>
                    <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
                      {variants.map((v) => (
                        <div
                          key={v.variant_id}
                          onClick={() => handleSelectVariant(v)}
                          className={clsx(
                            "cursor-pointer rounded-lg border p-3 transition-all hover:shadow",
                            selectedVariantId === v.variant_id
                              ? "border-blue-400 bg-blue-50/80 ring-1 ring-blue-300"
                              : "border-slate-200 bg-white/80 hover:border-slate-300"
                          )}
                        >
                          <div className="flex items-center gap-2">
                            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                              {v.style_tag}
                            </span>
                            {selectedVariantId === v.variant_id && (
                              <span className="text-xs text-blue-600">已选</span>
                            )}
                          </div>
                          <p className="mt-1.5 line-clamp-2 text-xs text-slate-600">
                            {v.brief_description}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 编辑器区域 */}
            <div className="flex flex-1 flex-col overflow-hidden">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-3">
                  <label className="text-xs font-medium text-slate-600">
                    内容编辑器
                    {hasExisting && (
                      <span className="ml-2 rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-600">
                        已有内容
                      </span>
                    )}
                  </label>
                  
                  {/* 视图切换 (world/theme/characters/outline 支持可视化视图) */}
                  {(target === "world" || target === "theme" || target === "characters" || target === "outline") && (
                    <div className="flex items-center rounded-lg bg-slate-100 p-0.5">
                      <button
                        onClick={() => setViewMode("visual")}
                        className={clsx(
                          "rounded-md px-2 py-0.5 text-xs font-medium transition-all",
                          viewMode === "visual"
                            ? "bg-white text-slate-900 shadow-sm"
                            : "text-slate-500 hover:text-slate-700"
                        )}
                      >
                        可视化
                      </button>
                      <button
                        onClick={() => setViewMode("json")}
                        className={clsx(
                          "rounded-md px-2 py-0.5 text-xs font-medium transition-all",
                          viewMode === "json"
                            ? "bg-white text-slate-900 shadow-sm"
                            : "text-slate-500 hover:text-slate-700"
                        )}
                      >
                        JSON
                      </button>
                    </div>
                  )}
                </div>

                {jsonError && (
                  <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs text-red-500">
                    {jsonError}
                  </span>
                )}
              </div>
              
              {/* 可视化视图 */}
              {viewMode === "visual" && !jsonError && target === "world" ? (
                <div className="mt-1 flex-1 overflow-y-auto rounded-xl border border-slate-200/80 bg-slate-50/50 p-4" style={{ minHeight: "300px", maxHeight: "calc(90vh - 350px)" }}>
                  <WorldSettingView
                    data={parsedData as WorldView}
                    onChange={(newData) => handleEditorChange(JSON.stringify(newData, null, 2))}
                  />
                </div>
              ) : viewMode === "visual" && !jsonError && target === "theme" ? (
                <div className="mt-1 flex-1 overflow-y-auto rounded-xl border border-slate-200/80 bg-slate-50/50 p-4" style={{ minHeight: "300px", maxHeight: "calc(90vh - 350px)" }}>
                  <ThemeConflictView
                    data={parsedData as ThemeConflictData}
                    onChange={(newData) => handleEditorChange(JSON.stringify(newData, null, 2))}
                  />
                </div>
              ) : viewMode === "visual" && !jsonError && target === "characters" ? (
                <div className="mt-1 flex-1 overflow-y-auto rounded-xl border border-slate-200/80 bg-slate-50/50 p-4" style={{ minHeight: "300px", maxHeight: "calc(90vh - 350px)" }}>
                  <CharacterNetworkView
                    data={parsedData as CharactersData}
                    onChange={(newData) => handleEditorChange(JSON.stringify(newData, null, 2))}
                  />
                </div>
              ) : viewMode === "visual" && !jsonError && target === "outline" ? (
                <div className="mt-1 flex-1 overflow-y-auto rounded-xl border border-slate-200/80 bg-slate-50/50 p-4" style={{ minHeight: "300px", maxHeight: "calc(90vh - 350px)" }}>
                  <OutlineView
                    data={parsedData as OutlineData}
                    onChange={(newData) => handleEditorChange(JSON.stringify(newData, null, 2))}
                  />
                </div>
              ) : (
                <textarea
                  className={clsx(
                    "mt-1 flex-1 resize-none rounded-xl border bg-white/70 p-3 font-mono text-sm text-slate-800 shadow-sm transition focus:outline-none focus:ring-2",
                    jsonError
                      ? "border-red-300 focus:border-red-400 focus:ring-red-100"
                      : "border-slate-200/80 focus:border-blue-500 focus:ring-blue-100"
                  )}
                  value={editorContent}
                  onChange={(e) => handleEditorChange(e.target.value)}
                  placeholder='{"key": "value"}'
                  style={{ minHeight: "200px" }}
                />
              )}
            </div>

            {/* 错误提示 */}
            {error && (
              <div className="text-sm text-red-500">{error}</div>
            )}

            {/* 底部按钮 */}
            <div className="flex justify-end gap-3 text-sm">
              <button
                className="btn-ghost px-4"
                onClick={onClose}
                disabled={saving}
              >
                取消
              </button>
              <button
                className="btn-primary px-6"
                onClick={handleSave}
                disabled={saving || !!jsonError || !editorContent.trim()}
              >
                {saving ? "保存中..." : "保存"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
