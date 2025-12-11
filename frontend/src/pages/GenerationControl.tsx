import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import Layout from "../components/Layout";
import ProgressBar from "../components/ProgressBar";
import LogViewer from "../components/LogViewer";
import { useWebSocket } from "../hooks/useWebSocket";
import { useGenerationStore } from "../stores/generationStore";
import { ProgressSnapshot, LogEntry } from "../types";

export default function GenerationControl() {
  const { name } = useParams();
  const projectName = name || "";
  const { progress, logs, refresh, start, stop, resume } = useGenerationStore();
  const [localProgress, setLocalProgress] = useState<ProgressSnapshot | null>(null);
  const [localLogs, setLocalLogs] = useState<LogEntry[]>([]);
  const [stopAt, setStopAt] = useState<string>("");
  const [connected, setConnected] = useState<boolean>(false);

  useEffect(() => {
    if (!projectName) return;
    refresh(projectName).catch(() => {});
  }, [projectName, refresh]);

  useWebSocket(
    `${window.location.origin.replace("http", "ws")}/ws/projects/${projectName}/progress`,
    (payload) => {
      if (payload.type === "progress") {
        setLocalProgress(payload.data);
      } else if (payload.type === "log") {
        setLocalLogs((prev) => [payload.data as LogEntry, ...prev].slice(0, 200));
      }
    },
    {
      onOpen: () => setConnected(true),
      onClose: () => setConnected(false),
    },
  );

  useEffect(() => {
    if (!projectName || connected) return;
    let stopped = false;
    let timer: NodeJS.Timeout | null = null;
    const tick = async () => {
      try {
        await refresh(projectName);
      } catch {
        // ignore
      }
      if (!stopped) {
        timer = setTimeout(tick, 3000);
      }
    };
    tick();
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
    };
  }, [connected, projectName, refresh]);

  const mergedProgress = localProgress || progress;
  const mergedLogs = localLogs.length ? localLogs : logs;

  const handleStart = () => start(projectName, stopAt || undefined).catch(() => {});
  const handleStop = () => stop(projectName).catch(() => {});
  const handleResume = () => resume(projectName).catch(() => {});

  const stepOptions = useMemo(
    () => [
      { value: "", label: "全部生成" },
      { value: "world_creation", label: "世界观后停止" },
      { value: "theme_conflict_creation", label: "主题/冲突后停止" },
      { value: "character_creation", label: "角色后停止" },
      { value: "outline_creation", label: "大纲后停止" },
      { value: "chapter_planning", label: "章节计划后停止" },
    ],
    [],
  );

  return (
    <Layout>
      <section className="glass-panel space-y-4 p-6">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="page-title">生成控制</h1>
            <p className="muted">启动、停止、恢复生成任务，查看实时进度。</p>
            <div className="mt-2 flex flex-wrap gap-2 text-xs">
              <span className="pill">项目 {projectName}</span>
              <span className={connected ? "pill pill-success" : "pill pill-warning"}>
                WS连接：{connected ? "已连接" : "断开，使用HTTP轮询"}
              </span>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 text-sm">
            <select className="input-field w-full sm:w-56" value={stopAt} onChange={(e) => setStopAt(e.target.value)}>
              {stepOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <button className="btn-primary" onClick={handleStart}>
              开始生成
            </button>
            <button className="btn-soft" onClick={handleResume}>
              恢复
            </button>
            <button className="btn-ghost text-slate-800" onClick={handleStop}>
              停止
            </button>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="glass-panel p-5">
          <h2 className="section-title">进度</h2>
          <div className="mt-3 space-y-2 text-sm text-slate-700">
            <div className="flex items-center justify-between">
              <span>状态</span>
              <span className="pill pill-info">{mergedProgress?.status || "idle"}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>步骤</span>
              <span className="text-slate-900">{mergedProgress?.current_step || "-"}</span>
            </div>
            <ProgressBar value={mergedProgress?.progress_percent || 0} />
            <div className="muted">{mergedProgress?.message}</div>
          </div>
        </div>
        <div className="glass-panel p-5">
          <h2 className="section-title">日志</h2>
          <div className="mt-3">
            <LogViewer logs={mergedLogs} />
          </div>
        </div>
      </div>
    </Layout>
  );
}

