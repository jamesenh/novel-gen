import clsx from "clsx";
import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import WorldView from "../components/WorldView";
import CharacterList from "../components/CharacterList";
import OutlineTree from "../components/OutlineTree";
import WorldEditor from "../components/WorldEditor";
import CharacterEditor from "../components/CharacterEditor";
import OutlineEditor from "../components/OutlineEditor";
import ChapterEditor from "../components/ChapterEditor";
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

export default function Reader() {
  const { name } = useParams();
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
  const [worldEditing, setWorldEditing] = useState(false);
  const [charsEditing, setCharsEditing] = useState(false);
  const [outlineEditing, setOutlineEditing] = useState(false);
  const [chapterEditing, setChapterEditing] = useState(false);

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
          : ch,
      ),
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
  };

  return (
    <Layout>
      <section className="glass-panel space-y-3 p-6">
        <h1 className="page-title">内容阅读</h1>
        <p className="muted">浏览项目 {name} 的章节内容，查看世界观、角色与大纲。</p>
        {name && (
          <div className="flex flex-wrap gap-2 text-xs">
            <a className="btn-ghost px-3" href={`/api/projects/${name}/export/txt`} target="_blank" rel="noreferrer">
              导出全书 TXT
            </a>
            <a className="btn-ghost px-3" href={`/api/projects/${name}/export/md`} target="_blank" rel="noreferrer">
              导出全书 MD
            </a>
            <a className="btn-ghost px-3" href={`/api/projects/${name}/export/json`} target="_blank" rel="noreferrer">
              导出全书 JSON
            </a>
            {selected && (
              <>
                <a className="btn-ghost px-3" href={`/api/projects/${name}/export/txt/${selected}`} target="_blank" rel="noreferrer">
                  导出当前章 TXT
                </a>
                <a className="btn-ghost px-3" href={`/api/projects/${name}/export/md/${selected}`} target="_blank" rel="noreferrer">
                  导出当前章 MD
                </a>
                <a className="btn-ghost px-3" href={`/api/projects/${name}/export/json/${selected}`} target="_blank" rel="noreferrer">
                  导出当前章 JSON
                </a>
              </>
            )}
          </div>
        )}
      </section>

      {error && <div className="text-red-500">{error}</div>}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="font-semibold text-slate-800">世界观</span>
            <button className="btn-ghost px-2 text-blue-600" onClick={() => setWorldEditing((v) => !v)}>
              {worldEditing ? "取消" : "编辑"}
            </button>
          </div>
          {worldEditing ? (
            <WorldEditor data={world} loading={infoLoading} onSave={handleSaveWorld} onCancel={() => setWorldEditing(false)} />
          ) : (
            <WorldView data={world} loading={infoLoading} />
          )}
        </div>
        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="font-semibold text-slate-800">角色</span>
            <button className="btn-ghost px-2 text-blue-600" onClick={() => setCharsEditing((v) => !v)}>
              {charsEditing ? "取消" : "编辑"}
            </button>
          </div>
          {charsEditing ? (
            <CharacterEditor data={characters} loading={infoLoading} onSave={handleSaveCharacters} onCancel={() => setCharsEditing(false)} />
          ) : (
            <CharacterList data={characters} loading={infoLoading} />
          )}
        </div>
        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="font-semibold text-slate-800">大纲</span>
            <button className="btn-ghost px-2 text-blue-600" onClick={() => setOutlineEditing((v) => !v)}>
              {outlineEditing ? "取消" : "编辑"}
            </button>
          </div>
          {outlineEditing ? (
            <OutlineEditor data={outline} loading={infoLoading} onSave={handleSaveOutline} onCancel={() => setOutlineEditing(false)} />
          ) : (
            <OutlineTree data={outline} loading={infoLoading} />
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <div className="glass-panel p-4 lg:col-span-1">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900">章节</h3>
            <span className="pill text-xs">共 {chapters.length}</span>
          </div>
          {loadingList && <div className="mt-2 text-xs text-slate-500">加载章节...</div>}
          <div className="mt-3 space-y-2 text-sm">
            {chapters.map((ch) => (
              <button
                key={ch.chapter_number}
                onClick={() => setSelected(ch.chapter_number)}
                className={clsx(
                  "w-full rounded-xl px-3 py-2 text-left transition",
                  selected === ch.chapter_number ? "bg-blue-50 text-blue-700 shadow-sm" : "hover:bg-slate-50",
                )}
              >
                第{ch.chapter_number}章 {ch.chapter_title}
              </button>
            ))}
            {chapters.length === 0 && <div className="muted">暂无章节</div>}
          </div>
        </div>
        <div className="glass-panel p-5 lg:col-span-3">
          {!content && !loadingContent && <div className="muted">请选择章节</div>}
          {loadingContent && <div className="muted">加载章节内容...</div>}
          {content && (
            <div className="space-y-4">
              <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <h2 className="text-lg font-semibold text-slate-900">
                  第{content.chapter_number}章 {content.chapter_title}
                </h2>
                <div className="flex flex-wrap gap-2 text-xs text-slate-600">
                  <button className="btn-soft px-3 py-1" onClick={() => setChapterEditing((v) => !v)}>
                    {chapterEditing ? "取消编辑" : "编辑章节"}
                  </button>
                  <button className="btn-ghost px-3 py-1 text-red-600" onClick={() => handleDeleteChapter(content.chapter_number)}>
                    删除章节
                  </button>
                  {content.scenes.length > 0 &&
                    content.scenes.map((scene) => (
                      <button
                        key={scene.scene_number}
                        onClick={() => jumpToScene(scene.scene_number)}
                        className="btn-ghost px-3 py-1"
                      >
                        场景 {scene.scene_number}
                      </button>
                    ))}
                </div>
              </div>
              {!chapterEditing && (
                <div className="space-y-6 text-sm leading-7 text-slate-800">
                  {content.scenes.map((scene) => (
                    <div key={scene.scene_number} id={`scene-${scene.scene_number}`} className="space-y-2">
                      <div className="text-xs font-semibold text-slate-500">场景 {scene.scene_number}</div>
                      <div>{scene.content}</div>
                    </div>
                  ))}
                </div>
              )}
              {chapterEditing && <ChapterEditor data={content} onSave={handleSaveChapter} onCancel={() => setChapterEditing(false)} />}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}

