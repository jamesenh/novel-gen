import { useEffect, useMemo, useState } from "react";
import Layout from "../components/Layout";
import ProjectCard from "../components/ProjectCard";
import CreateProjectModal from "../components/CreateProjectModal";
import { useProjectStore } from "../stores/projectStore";

export default function ProjectList() {
  const { items, loading, fetch } = useProjectStore();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    fetch().catch(() => {
      // ignore for demo
    });
  }, [fetch]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((item) => item.name.toLowerCase().includes(q));
  }, [items, query]);

  return (
    <Layout>
      <CreateProjectModal open={open} onClose={() => setOpen(false)} onCreated={fetch} />
      <section className="glass-panel p-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Dashboard</p>
            <h1 className="page-title">项目空间</h1>
            <p className="muted">查看、搜索并快速进入你的小说生成项目。</p>
            <div className="flex flex-wrap gap-2 text-xs">
              <span className="pill">总项目 {items.length}</span>
              <span className="pill pill-info">匹配 {filtered.length}</span>
            </div>
          </div>
          <div className="flex w-full flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
            <div className="relative w-full sm:max-w-xs">
              <span className="pointer-events-none absolute left-3 top-2.5 text-slate-400">🔍</span>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="搜索项目"
                className="input-field pl-9"
              />
            </div>
            <button className="btn-primary sm:w-auto" onClick={() => setOpen(true)}>
              创建项目
            </button>
          </div>
        </div>

        <div className="divider my-5" />

        {loading && <div className="muted">加载中...</div>}
        {!loading && filtered.length === 0 && <div className="muted">暂无项目，点击「创建项目」开启新的故事。</div>}

        <div className="card-grid">
          {filtered.map((p) => (
            <ProjectCard
              key={p.name}
              name={p.name}
              status={p.status}
              createdAt={p.created_at}
              updatedAt={p.updated_at}
            />
          ))}
        </div>
      </section>
    </Layout>
  );
}

