import clsx from "clsx";
import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import WorldEditor from "../components/WorldEditor";
import CharacterEditor from "../components/CharacterEditor";
import OutlineEditor from "../components/OutlineEditor";
import ChapterEditor from "../components/ChapterEditor";
import ReaderDrawer from "../components/ReaderDrawer";
import ReferencePanel from "../components/ReferencePanel";
import ExportMenu from "../components/ExportMenu";
import { useParams } from "react-router-dom";
import { ChapterContent, ChapterMeta, CharactersData, OutlineData, WorldView as WorldViewType } from "../types";
import {
  deleteChapter,
  fetchChapters,
  fetchChapterContent,
  fetchCharacters,
  fetchOutline,
  fetchWorld,
  updateChapter,
  updateCharacters,
  updateOutline,
  updateWorld,
} from "../services/api";

/**
 * 内容阅读页 - 重构版
 * 布局：桌面三栏（章节列表 | 正文 | 参考面板）+ 移动端抽屉
 */
export default function Reader() {
  const { name } = useParams();

  // 数据状态
  const [chapters, setChapters] = useState<ChapterMeta[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [content, setContent] = useState<ChapterContent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingList, setLoadingList] = useState(false);
  const [loadingContent, setLoadingContent] = useState(false);
  const [world, setWorld] = useState<WorldViewType | null>(null);
  const [characters, setCharacters] = useState<CharactersData | null>(null);
  const [outline, setOutline] = useState<OutlineData | null>(null);
  const [infoLoading, setInfoLoading] = useState(false);

  // 编辑状态
  const [worldEditing, setWorldEditing] = useState(false);
  const [charsEditing, setCharsEditing] = useState(false);
  const [outlineEditing, setOutlineEditing] = useState(false);
  const [chapterEditing, setChapterEditing] = useState(false);

  // 抽屉状态（移动端）
  const [chaptersDrawerOpen, setChaptersDrawerOpen] = useState(false);
  const [referenceDrawerOpen, setReferenceDrawerOpen] = useState(false);

  // 参考面板显示状态（桌面端）
  const [showReferencePanel, setShowReferencePanel] = useState(true);

  // 加载项目信息
  useEffect(() => {
    if (!name) return;
    setInfoLoading(true);
    Promise.all([fetchWorld(name), fetchCharacters(name), fetchOutline(name)])
      .then(([w, c, o]) => {
        setWorld(w);
        setCharacters(c);
        setOutline(o);
      })
      .catch((e) => setError(e?.response?.data?.detail || "加载项目信息失败"))
      .finally(() => setInfoLoading(false));
  }, [name]);

  // 加载章节列表
  useEffect(() => {
    if (!name) return;
    setLoadingList(true);
    fetchChapters(name)
      .then((data) => {
        setChapters(data);
        if (data.length > 0) {
          setSelected(data[0].chapter_number);
        }
      })
      .catch((e) => setError(e?.response?.data?.detail || "加载章节列表失败"))
      .finally(() => setLoadingList(false));
  }, [name]);

  // 加载章节内容
  useEffect(() => {
    if (!name || selected === null) return;
    setLoadingContent(true);
    fetchChapterContent(name, selected)
      .then((data) => {
        setContent(data);
        setError(null);
        setChapterEditing(false);
      })
      .catch((e) => setError(e?.response?.data?.detail || "加载章节内容失败"))
      .finally(() => setLoadingContent(false));
  }, [name, selected]);

  // 保存处理函数
  const handleSaveWorld = async (payload: WorldViewType) => {
    if (!name) return;
    await updateWorld(name, payload);
    setWorld(payload);
    setWorldEditing(false);
  };

  const handleSaveCharacters = async (payload: CharactersData) => {
    if (!name) return;
    await updateCharacters(name, payload);
    setCharacters(payload);
    setCharsEditing(false);
  };

  const handleSaveOutline = async (payload: OutlineData) => {
    if (!name) return;
    await updateOutline(name, payload);
    setOutline(payload);
    setOutlineEditing(false);
  };

  const handleSaveChapter = async (draft: ChapterContent) => {
    if (!name) return;
    await updateChapter(name, draft.chapter_number, {
      chapter_title: draft.chapter_title,
      scenes: draft.scenes.map((s) => ({ ...s, word_count: s.word_count ?? s.content.length })),
    });
    setContent(draft);
    setChapterEditing(false);
    setChapters((prev) =>
      prev.map((ch) =>
        ch.chapter_number === draft.chapter_number
          ? {
              ...ch,
              chapter_title: draft.chapter_title,
              scenes_count: draft.scenes.length,
              total_words: draft.scenes.reduce((acc, s) => acc + (s.word_count ?? s.content.length), 0),
            }
          : ch
      )
    );
  };

  const handleDeleteChapter = async (chapterNumber: number) => {
    if (!name) return;
    await deleteChapter(name, chapterNumber);
    setChapters((prev) => prev.filter((c) => c.chapter_number !== chapterNumber));
    if (selected === chapterNumber) {
      const next = chapters.find((c) => c.chapter_number !== chapterNumber);
      setSelected(next ? next.chapter_number : null);
      setContent(null);
    }
  };

  const jumpToScene = (sceneNumber: number) => {
    const target = document.getElementById(`scene-${sceneNumber}`);
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    // 移动端跳转后关闭抽屉
    setReferenceDrawerOpen(false);
  };

  const selectChapter = (chapterNumber: number) => {
    setSelected(chapterNumber);
    // 移动端选择后关闭抽屉
    setChaptersDrawerOpen(false);
  };

  return (
    <Layout>
      {/* ===== 移动端抽屉 ===== */}
      <ReaderDrawer
        open={chaptersDrawerOpen}
        onClose={() => setChaptersDrawerOpen(false)}
        side="left"
        title="章节列表"
      >
        <ChaptersList
          chapters={chapters}
          selected={selected}
          loading={loadingList}
          onSelect={selectChapter}
        />
      </ReaderDrawer>

      <ReaderDrawer
        open={referenceDrawerOpen}
        onClose={() => setReferenceDrawerOpen(false)}
        side="right"
        title="参考信息"
      >
        <ReferencePanel
          world={world}
          characters={characters}
          outline={outline}
          scenes={content?.scenes}
          loading={infoLoading}
          onJumpToScene={jumpToScene}
          onEditWorld={() => {
            setWorldEditing(true);
            setReferenceDrawerOpen(false);
          }}
          onEditCharacters={() => {
            setCharsEditing(true);
            setReferenceDrawerOpen(false);
          }}
          onEditOutline={() => {
            setOutlineEditing(true);
            setReferenceDrawerOpen(false);
          }}
        />
      </ReaderDrawer>

      {/* ===== Sticky 工具栏 ===== */}
      <div className="sticky top-0 z-30 -mx-4 mb-4 border-b border-slate-200 bg-white/95 px-4 py-3 backdrop-blur-sm lg:-mx-0 lg:rounded-xl lg:border lg:shadow-sm">
        <div className="flex items-center justify-between gap-3">
          {/* 左侧：标题 + 移动端章节按钮 */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setChaptersDrawerOpen(true)}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 xl:hidden"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" />
              </svg>
              <span className="hidden sm:inline">章节</span>
            </button>
            <div>
              <h1 className="text-base font-bold text-slate-900 sm:text-lg">内容阅读</h1>
              <p className="hidden text-xs text-slate-500 sm:block">项目：{name}</p>
            </div>
          </div>

          {/* 右侧：工具按钮 */}
          <div className="flex items-center gap-2">
            {name && <ExportMenu projectName={name} selectedChapter={selected} />}

            {/* 桌面端参考面板开关 */}
            <button
              onClick={() => setShowReferencePanel(!showReferencePanel)}
              className={clsx(
                "hidden items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition xl:flex",
                showReferencePanel
                  ? "border-blue-300 bg-blue-50 text-blue-700"
                  : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
              )}
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              参考
            </button>

            {/* 移动端参考面板按钮 */}
            <button
              onClick={() => setReferenceDrawerOpen(true)}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 xl:hidden"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="hidden sm:inline">参考</span>
            </button>
          </div>
        </div>
      </div>

      {error && <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

      {/* ===== 主体三栏布局 ===== */}
      <div className="flex gap-4">
        {/* 左栏：章节列表（桌面端） */}
        <aside className="hidden w-56 shrink-0 xl:block">
          <div className="sticky top-20 max-h-[calc(100vh-6rem)] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-100 px-4 py-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-900">章节</h3>
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
                  共 {chapters.length}
                </span>
              </div>
            </div>
            <div className="max-h-[calc(100vh-10rem)] overflow-y-auto">
              <ChaptersList
                chapters={chapters}
                selected={selected}
                loading={loadingList}
                onSelect={setSelected}
              />
            </div>
          </div>
        </aside>

        {/* 中栏：正文阅读区 */}
        <main className="min-w-0 flex-1">
          <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
            {!content && !loadingContent && (
              <div className="flex h-64 items-center justify-center text-sm text-slate-400">
                请选择章节开始阅读
              </div>
            )}
            {loadingContent && (
              <div className="flex h-64 items-center justify-center text-sm text-slate-500">
                加载章节内容...
              </div>
            )}
            {content && (
              <div className="p-5 sm:p-6">
                {/* 章节头部 */}
                <div className="mb-6 border-b border-slate-100 pb-4">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <h2 className="text-xl font-bold text-slate-900">
                      第{content.chapter_number}章 {content.chapter_title}
                    </h2>
                    <div className="flex flex-wrap gap-2">
                      <button
                        className={clsx(
                          "rounded-lg px-3 py-1.5 text-xs font-medium transition",
                          chapterEditing
                            ? "bg-slate-200 text-slate-700"
                            : "bg-blue-50 text-blue-700 hover:bg-blue-100"
                        )}
                        onClick={() => setChapterEditing((v) => !v)}
                      >
                        {chapterEditing ? "取消编辑" : "编辑章节"}
                      </button>
                      <button
                        className="rounded-lg bg-red-50 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-100"
                        onClick={() => handleDeleteChapter(content.chapter_number)}
                      >
                        删除
                      </button>
                    </div>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-500">
                    <span>{content.scenes.length} 个场景</span>
                    <span>·</span>
                    <span>{content.scenes.reduce((acc, s) => acc + (s.word_count ?? s.content.length), 0)} 字</span>
                  </div>
                </div>

                {/* 章节内容 */}
                {!chapterEditing && (
                  <article className="prose prose-slate max-w-none">
                    {content.scenes.map((scene) => (
                      <section
                        key={scene.scene_number}
                        id={`scene-${scene.scene_number}`}
                        className="mb-8 scroll-mt-24"
                      >
                        <div className="mb-3 flex items-center gap-2">
                          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-semibold text-slate-600">
                            场景 {scene.scene_number}
                          </span>
                          <span className="text-[10px] text-slate-400">
                            {scene.word_count || scene.content.length} 字
                          </span>
                        </div>
                        <div className="whitespace-pre-wrap text-base leading-8 text-slate-700">
                          {scene.content}
                        </div>
                      </section>
                    ))}
                  </article>
                )}

                {/* 章节编辑器 */}
                {chapterEditing && (
                  <ChapterEditor data={content} onSave={handleSaveChapter} onCancel={() => setChapterEditing(false)} />
                )}
              </div>
            )}
          </div>
        </main>

        {/* 右栏：参考面板（桌面端） */}
        {showReferencePanel && (
          <aside className="hidden w-72 shrink-0 xl:block">
            <div className="sticky top-20 max-h-[calc(100vh-6rem)] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
              <ReferencePanel
                world={world}
                characters={characters}
                outline={outline}
                scenes={content?.scenes}
                loading={infoLoading}
                onJumpToScene={jumpToScene}
                onEditWorld={() => setWorldEditing(true)}
                onEditCharacters={() => setCharsEditing(true)}
                onEditOutline={() => setOutlineEditing(true)}
              />
            </div>
          </aside>
        )}
      </div>

      {/* ===== 编辑弹窗 ===== */}
      {worldEditing && (
        <EditorModal title="编辑世界观" onClose={() => setWorldEditing(false)}>
          <WorldEditor data={world} loading={infoLoading} onSave={handleSaveWorld} onCancel={() => setWorldEditing(false)} />
        </EditorModal>
      )}
      {charsEditing && (
        <EditorModal title="编辑角色" onClose={() => setCharsEditing(false)}>
          <CharacterEditor data={characters} loading={infoLoading} onSave={handleSaveCharacters} onCancel={() => setCharsEditing(false)} />
        </EditorModal>
      )}
      {outlineEditing && (
        <EditorModal title="编辑大纲" onClose={() => setOutlineEditing(false)}>
          <OutlineEditor data={outline} loading={infoLoading} onSave={handleSaveOutline} onCancel={() => setOutlineEditing(false)} />
        </EditorModal>
      )}
    </Layout>
  );
}

/* ============ 子组件 ============ */

/** 章节列表 */
function ChaptersList({
  chapters,
  selected,
  loading,
  onSelect,
}: {
  chapters: ChapterMeta[];
  selected: number | null;
  loading: boolean;
  onSelect: (chapterNumber: number) => void;
}) {
  if (loading) {
    return <div className="p-4 text-xs text-slate-500">加载章节...</div>;
  }

  if (chapters.length === 0) {
    return <div className="p-4 text-xs text-slate-400">暂无章节</div>;
  }

  return (
    <div className="p-2">
      {chapters.map((ch) => (
        <button
          key={ch.chapter_number}
          onClick={() => onSelect(ch.chapter_number)}
          className={clsx(
            "w-full rounded-lg px-3 py-2.5 text-left text-sm transition",
            selected === ch.chapter_number
              ? "bg-blue-50 text-blue-700 shadow-sm"
              : "text-slate-700 hover:bg-slate-50"
          )}
        >
          <div className="font-medium">
            第{ch.chapter_number}章
          </div>
          <div className={clsx(
            "mt-0.5 truncate text-xs",
            selected === ch.chapter_number ? "text-blue-600" : "text-slate-500"
          )}>
            {ch.chapter_title}
          </div>
          <div className="mt-1 flex gap-2 text-[10px] text-slate-400">
            <span>{ch.scenes_count} 场景</span>
            <span>{ch.total_words} 字</span>
          </div>
        </button>
      ))}
    </div>
  );
}

/** 编辑器弹窗 */
function EditorModal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  // 禁止 body 滚动
  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
      <div className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        {/* 头部 */}
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <h3 className="text-lg font-bold text-slate-900">{title}</h3>
          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-full text-slate-500 hover:bg-slate-100"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        {/* 内容 */}
        <div className="flex-1 overflow-y-auto p-6">{children}</div>
      </div>
    </div>
  );
}
