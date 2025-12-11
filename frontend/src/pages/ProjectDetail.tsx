import clsx from "clsx";
import { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import Layout from "../components/Layout";
import RollbackModal from "../components/RollbackModal";
import ProgressBar from "../components/ProgressBar";
import { fetchProgress, getProjectDetail } from "../services/api";
import { formatDateTime } from "../utils/date";
import { ProgressSnapshot, ProjectDetail as ProjectDetailType } from "../types";

export default function ProjectDetail() {
  const { name } = useParams();
  const [detail, setDetail] = useState<ProjectDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<ProgressSnapshot | null>(null);
  const [progressLoading, setProgressLoading] = useState(false);
  const [rollbackOpen, setRollbackOpen] = useState(false);

  const stepOrder = useMemo(
    () => [
      ["world", "世界观"],
      ["theme", "主题冲突"],
      ["characters", "角色"],
      ["outline", "大纲"],
      ["chapters_plan", "章节计划"],
      ["chapters", "章节生成"],
    ],
    [],
  );

  useEffect(() => {
    if (!name) return;
    setLoading(true);
    getProjectDetail(name)
      .then((data) => {
        setDetail(data);
        setError(null);
      })
      .catch((e) => setError(e?.response?.data?.detail || "加载失败"))
      .finally(() => setLoading(false));
  }, [name]);

  useEffect(() => {
    if (!name) return;
    setProgressLoading(true);
    fetchProgress(name)
      .then((data) => setProgress(data))
      .catch(() => setProgress(null))
      .finally(() => setProgressLoading(false));
  }, [name]);

  return (
    <Layout>
      <RollbackModal open={rollbackOpen} onClose={() => setRollbackOpen(false)} project={name || ""} />
      <section className="space-y-6">
        <div className="glass-panel p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Project</p>
              <h1 className="page-title">项目：{name}</h1>
              <p className="muted">查看当前生成状态、时间线与章节概览。</p>
              <div className="flex flex-wrap gap-2 text-xs">
                {detail && <span className="pill pill-info">状态 {detail.summary.status}</span>}
                {detail && <span className="pill">章节 {detail.state.chapters.length}</span>}
                {progress && (
                  <span className="pill pill-warning">
                    进度 {progress.progress_percent !== undefined ? progress.progress_percent.toFixed(1) : "0.0"}%
                  </span>
                )}
              </div>
            </div>
            <div className="flex flex-wrap gap-2 text-sm">
              <Link className="btn-primary px-4 py-2" to={`/projects/${name}/generate`}>
                生成控制
              </Link>
              <Link className="btn-soft px-4 py-2" to={`/projects/${name}/read`}>
                内容阅读
              </Link>
              <button className="btn-ghost px-4 py-2 text-red-600" onClick={() => setRollbackOpen(true)}>
                回滚
              </button>
            </div>
          </div>
          {loading && <div className="muted">加载中...</div>}
          {error && <div className="text-red-500">{error}</div>}
        </div>

        {detail && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <div className="glass-panel space-y-3 p-5 lg:col-span-2">
                <div className="flex items-center justify-between">
                  <h2 className="section-title">项目概览</h2>
                  <span className="pill">作者：{detail.settings.author || "未知"}</span>
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm text-slate-700 md:grid-cols-3">
                  <div className="glass-panel bg-white/60 p-3 shadow-none">
                    <div className="text-xs text-slate-500">状态</div>
                    <div className="text-base font-semibold text-slate-900">{detail.summary.status}</div>
                  </div>
                  <div className="glass-panel bg-white/60 p-3 shadow-none">
                    <div className="text-xs text-slate-500">创建时间</div>
                    <div className="text-sm text-slate-800">{formatDateTime(detail.summary.created_at)}</div>
                  </div>
                  <div className="glass-panel bg-white/60 p-3 shadow-none">
                    <div className="text-xs text-slate-500">最近修改</div>
                    <div className="text-sm text-slate-800">{formatDateTime(detail.summary.updated_at)}</div>
                  </div>
                  <div className="glass-panel bg-white/60 p-3 shadow-none">
                    <div className="text-xs text-slate-500">初始章节</div>
                    <div className="text-sm text-slate-800">{detail.settings.initial_chapters}</div>
                  </div>
                  <div className="glass-panel bg-white/60 p-3 shadow-none">
                    <div className="text-xs text-slate-500">最大章节</div>
                    <div className="text-sm text-slate-800">{detail.settings.max_chapters}</div>
                  </div>
                  <div className="glass-panel bg-white/60 p-3 shadow-none">
                    <div className="text-xs text-slate-500">检查点</div>
                    <div className="text-sm text-slate-800">{detail.state.checkpoint_exists ? "存在" : "无"}</div>
                  </div>
                </div>
              </div>

              <div className="glass-panel space-y-3 p-5">
                <h2 className="section-title">当前进度</h2>
                {progressLoading && <div className="muted">加载进度...</div>}
                {!progressLoading && progress && (
                  <div className="space-y-2 text-sm text-slate-700">
                    <div className="flex items-center justify-between">
                      <span>状态</span>
                      <span className="pill pill-info">{progress.status}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>步骤</span>
                      <span className="text-slate-900">{progress.current_step || "未开始"}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>章节/场景</span>
                      <span>
                        {progress.current_chapter ?? "-"} / {progress.current_scene ?? "-"}
                      </span>
                    </div>
                    <ProgressBar value={progress.progress_percent || 0} />
                    {progress.message && <div className="muted">{progress.message}</div>}
                  </div>
                )}
                {!progressLoading && !progress && <div className="muted">暂无进度数据</div>}
              </div>
            </div>

            <div className="glass-panel p-5">
              <h2 className="section-title">生成进度时间线</h2>
              <div className="mt-4 space-y-3 text-sm">
                {stepOrder.map(([key, label]) => {
                  const done = detail.state.steps[key as keyof typeof detail.state.steps];
                  const isCurrent = progress?.current_step === key;
                  return (
                    <div
                      key={key}
                      className={clsx(
                        "flex items-center justify-between rounded-xl border px-3 py-2",
                        done
                          ? "border-emerald-100 bg-emerald-50/70 text-emerald-800"
                          : isCurrent
                            ? "border-blue-100 bg-blue-50/70 text-blue-800"
                            : "border-slate-200/80 bg-white/70 text-slate-700",
                      )}
                    >
                      <div className="flex items-center gap-3">
                        <span
                          className={clsx(
                            "flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold",
                            done
                              ? "bg-emerald-100 text-emerald-700"
                              : isCurrent
                                ? "bg-blue-100 text-blue-700"
                                : "bg-slate-100 text-slate-500",
                          )}
                        >
                          {done ? "✓" : isCurrent ? "→" : "·"}
                        </span>
                        <span className="font-medium">{label}</span>
                      </div>
                      {isCurrent && <span className="text-xs text-blue-600">进行中</span>}
                      {done && <span className="text-xs text-emerald-600">已完成</span>}
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="glass-panel p-5">
              <h2 className="section-title">章节列表</h2>
              <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                {detail.state.chapters.length === 0 && <div className="muted">暂无章节</div>}
                {detail.state.chapters.map((ch) => (
                  <div
                    key={ch.chapter_number}
                    className="flex items-start justify-between rounded-xl border border-slate-200/80 bg-white/80 px-4 py-3 shadow-sm"
                  >
                    <div>
                      <div className="font-semibold text-slate-900">
                        第{ch.chapter_number}章 {ch.chapter_title}
                      </div>
                      <div className="text-xs text-slate-500">
                        场景 {ch.scenes_count} · {ch.total_words} 字 · {ch.status}
                      </div>
                    </div>
                    <Link className="btn-ghost text-sm text-blue-600" to={`/projects/${name}/read`}>
                      查看
                    </Link>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </section>
    </Layout>
  );
}

