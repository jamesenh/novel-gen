import { useState } from "react";
import clsx from "clsx";
import { ChapterContent, CharactersData, OutlineData, WorldView } from "../types";

type TabKey = "world" | "characters" | "outline" | "scenes";

type Props = {
  world: WorldView | null;
  characters: CharactersData | null;
  outline: OutlineData | null;
  scenes?: ChapterContent["scenes"];
  loading?: boolean;
  onJumpToScene?: (sceneNumber: number) => void;
  onEditWorld?: () => void;
  onEditCharacters?: () => void;
  onEditOutline?: () => void;
};

const TABS: { key: TabKey; label: string; icon: string }[] = [
  { key: "world", label: "世界观", icon: "🌍" },
  { key: "characters", label: "角色", icon: "👥" },
  { key: "outline", label: "大纲", icon: "📋" },
  { key: "scenes", label: "场景", icon: "📍" },
];

/**
 * 参考面板组件
 * - 用于展示世界观/角色/大纲/场景目录
 * - 支持 Tabs 切换
 */
export default function ReferencePanel({
  world,
  characters,
  outline,
  scenes,
  loading,
  onJumpToScene,
  onEditWorld,
  onEditCharacters,
  onEditOutline,
}: Props) {
  const [activeTab, setActiveTab] = useState<TabKey>("world");

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-slate-500">
        加载参考信息...
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Tab 切换 */}
      <div className="flex border-b border-slate-200 bg-slate-50/80">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={clsx(
              "flex-1 px-2 py-2.5 text-xs font-medium transition-colors",
              activeTab === tab.key
                ? "border-b-2 border-blue-500 bg-white text-blue-700"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
            )}
          >
            <span className="mr-1">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 内容 */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === "world" && <WorldTab data={world} onEdit={onEditWorld} />}
        {activeTab === "characters" && <CharactersTab data={characters} onEdit={onEditCharacters} />}
        {activeTab === "outline" && <OutlineTab data={outline} onEdit={onEditOutline} />}
        {activeTab === "scenes" && <ScenesTab scenes={scenes} onJump={onJumpToScene} />}
      </div>
    </div>
  );
}

/* ============ 子组件 ============ */

function WorldTab({ data, onEdit }: { data: WorldView | null; onEdit?: () => void }) {
  if (!data) {
    return <EmptyState text="暂无世界观信息" />;
  }

  const fields = [
    { label: "世界名称", value: data.world_name },
    { label: "时代背景", value: data.time_period },
    { label: "地理环境", value: data.geography },
    { label: "社会制度", value: data.social_system },
    { label: "科技水平", value: data.technology_level },
    { label: "文化习俗", value: data.culture_customs },
  ];

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-slate-800">🌍 {data.world_name || "世界观"}</h4>
        {onEdit && (
          <button onClick={onEdit} className="text-xs text-blue-600 hover:text-blue-700">
            编辑
          </button>
        )}
      </div>
      <div className="space-y-2">
        {fields.map(
          (f) =>
            f.value && (
              <div key={f.label} className="rounded-lg bg-slate-50 p-2.5">
                <div className="text-[10px] font-medium uppercase tracking-wide text-slate-500">
                  {f.label}
                </div>
                <div className="mt-1 text-xs leading-relaxed text-slate-700">{f.value}</div>
              </div>
            )
        )}
      </div>
    </div>
  );
}

function CharactersTab({ data, onEdit }: { data: CharactersData | null; onEdit?: () => void }) {
  if (!data) {
    return <EmptyState text="暂无角色信息" />;
  }

  const allCharacters = [
    data.protagonist && { ...data.protagonist, _role: "主角" },
    data.antagonist && { ...data.antagonist, _role: "反派" },
    ...(data.supporting_characters || []).map((c, i) => ({ ...c, _role: `配角 ${i + 1}` })),
  ].filter(Boolean);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-slate-800">👥 角色列表</h4>
        {onEdit && (
          <button onClick={onEdit} className="text-xs text-blue-600 hover:text-blue-700">
            编辑
          </button>
        )}
      </div>
      <div className="space-y-2">
        {allCharacters.map((char: any, idx) => (
          <div
            key={idx}
            className={clsx(
              "rounded-lg border p-2.5",
              char._role === "主角"
                ? "border-blue-200 bg-blue-50/50"
                : char._role === "反派"
                  ? "border-red-200 bg-red-50/50"
                  : "border-slate-200 bg-slate-50/50"
            )}
          >
            <div className="flex items-center gap-2">
              <span
                className={clsx(
                  "flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-bold",
                  char._role === "主角"
                    ? "bg-blue-200 text-blue-700"
                    : char._role === "反派"
                      ? "bg-red-200 text-red-700"
                      : "bg-slate-200 text-slate-700"
                )}
              >
                {char.name?.slice(0, 1) || "?"}
              </span>
              <div>
                <div className="text-xs font-semibold text-slate-800">{char.name}</div>
                <div className="text-[10px] text-slate-500">{char._role} · {char.role}</div>
              </div>
            </div>
            {char.personality && (
              <div className="mt-1.5 text-[11px] leading-relaxed text-slate-600">
                性格：{char.personality}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function OutlineTab({ data, onEdit }: { data: OutlineData | null; onEdit?: () => void }) {
  if (!data) {
    return <EmptyState text="暂无大纲信息" />;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-slate-800">📋 故事大纲</h4>
        {onEdit && (
          <button onClick={onEdit} className="text-xs text-blue-600 hover:text-blue-700">
            编辑
          </button>
        )}
      </div>

      {/* 故事结构摘要 */}
      <div className="space-y-2 text-xs">
        {data.story_premise && (
          <div className="rounded-lg bg-amber-50 p-2.5">
            <div className="font-medium text-amber-800">💡 故事前提</div>
            <div className="mt-1 leading-relaxed text-amber-700">{data.story_premise}</div>
          </div>
        )}
        <div className="grid grid-cols-2 gap-2">
          {data.beginning && (
            <div className="rounded-lg bg-slate-50 p-2">
              <div className="text-[10px] font-medium text-slate-500">🌅 开端</div>
              <div className="mt-0.5 line-clamp-2 text-slate-700">{data.beginning}</div>
            </div>
          )}
          {data.climax && (
            <div className="rounded-lg bg-slate-50 p-2">
              <div className="text-[10px] font-medium text-slate-500">🔥 高潮</div>
              <div className="mt-0.5 line-clamp-2 text-slate-700">{data.climax}</div>
            </div>
          )}
        </div>
      </div>

      {/* 章节列表 */}
      {data.chapters && data.chapters.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-[10px] font-medium uppercase tracking-wide text-slate-500">
            章节概览 ({data.chapters.length} 章)
          </div>
          {data.chapters.map((ch) => (
            <div key={ch.chapter_number} className="rounded-lg border border-slate-100 bg-white p-2">
              <div className="text-xs font-medium text-slate-800">
                第{ch.chapter_number}章 {ch.chapter_title}
              </div>
              {ch.summary && (
                <div className="mt-0.5 line-clamp-2 text-[11px] text-slate-500">{ch.summary}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ScenesTab({
  scenes,
  onJump,
}: {
  scenes?: ChapterContent["scenes"];
  onJump?: (sceneNumber: number) => void;
}) {
  if (!scenes || scenes.length === 0) {
    return <EmptyState text="请先选择章节" />;
  }

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold text-slate-800">📍 当前章节场景</h4>
      <div className="space-y-2">
        {scenes.map((scene) => (
          <button
            key={scene.scene_number}
            onClick={() => onJump?.(scene.scene_number)}
            className="w-full rounded-lg border border-slate-200 bg-white p-2.5 text-left transition hover:border-blue-300 hover:bg-blue-50/50"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-800">场景 {scene.scene_number}</span>
              <span className="text-[10px] text-slate-400">{scene.word_count || scene.content.length} 字</span>
            </div>
            <div className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-slate-600">
              {scene.content.slice(0, 80)}...
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="flex h-32 items-center justify-center text-sm text-slate-400">{text}</div>
  );
}
