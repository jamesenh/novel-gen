import clsx from "clsx";
import { Link } from "react-router-dom";
import { formatDateTime } from "../utils/date";

type Props = {
  name: string;
  status: string;
  createdAt: string;
  updatedAt: string;
};

export default function ProjectCard({ name, status, createdAt, updatedAt }: Props) {
  const created = formatDateTime(createdAt);
  const updated = formatDateTime(updatedAt);

  const statusTone = clsx("pill", {
    "pill-success": status.toLowerCase().includes("done") || status === "completed",
    "pill-warning": status.toLowerCase().includes("running") || status.toLowerCase().includes("processing"),
    "pill-info": !status.toLowerCase().includes("running") && !status.toLowerCase().includes("done"),
  });

  return (
    <article className="glass-panel group flex flex-col gap-4 p-5 transition duration-200 hover:-translate-y-1 hover:shadow-2xl">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-blue-500/70" />
            <h3 className="text-lg font-semibold text-slate-900">{name}</h3>
          </div>
          <p className="text-xs text-slate-500">最近更新：{updated}</p>
        </div>
        <span className={statusTone}>{status}</span>
      </div>
      <div className="flex items-center gap-3 text-xs text-slate-500">
        <span>创建 {created}</span>
        <span className="h-1 w-1 rounded-full bg-slate-300" />
        <span>修改 {updated}</span>
      </div>
      <div className="flex flex-wrap gap-2 text-sm">
        <Link className="btn-primary px-3 py-2" to={`/projects/${name}`}>
          查看详情
        </Link>
        <Link className="btn-soft px-3 py-2" to={`/projects/${name}/generate`}>
          生成控制
        </Link>
        <Link className="btn-ghost px-3 py-2" to={`/projects/${name}/read`}>
          阅读
        </Link>
      </div>
    </article>
  );
}

