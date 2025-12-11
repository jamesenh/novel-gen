import clsx from "clsx";
import { Link, useLocation, useParams } from "react-router-dom";

type Props = {
  className?: string;
  layout?: "vertical" | "horizontal";
};

export default function Sidebar({ className = "", layout = "vertical" }: Props) {
  const location = useLocation();
  const params = useParams();
  const name = params.name;
  const isHorizontal = layout === "horizontal";

  type NavLink = { to: string; label: string; match?: "exact" | "prefix" };

  const links = [
    { to: "/", label: "项目列表", match: "exact" },
    name && { to: `/projects/${name}`, label: "项目概览", match: "exact" },
    name && { to: `/projects/${name}/generate`, label: "生成控制" },
    name && { to: `/projects/${name}/read`, label: "内容阅读" },
  ].filter(Boolean) as NavLink[];

  const isActive = (path: string, match: "exact" | "prefix" = "prefix") =>
    match === "exact"
      ? location.pathname === path
      : location.pathname === path || location.pathname.startsWith(`${path}/`);

  return (
    <aside className={clsx(className, isHorizontal ? "w-full" : "w-64 shrink-0")}>
      <nav
        aria-label="页面导航"
        className={clsx(
          "glass-panel",
          isHorizontal ? "flex items-center gap-2 overflow-x-auto p-2" : "sticky top-24 space-y-4 p-4",
        )}
      >
        {!isHorizontal && (
          <div className="flex items-center justify-between">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">导航</div>
            {name && <span className="pill">{name}</span>}
          </div>
        )}
        <div className={clsx(isHorizontal ? "flex items-center gap-2" : "space-y-2")}>
          {links.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              aria-current={isActive(link.to, link.match) ? "page" : undefined}
              className={clsx(
                isHorizontal
                  ? "flex flex-none items-center gap-2 rounded-xl px-3 py-2 text-sm"
                  : "flex items-center gap-3 rounded-xl px-3 py-2 text-sm",
                isActive(link.to, link.match)
                  ? "border border-blue-100 bg-blue-50 text-blue-700 shadow-sm shadow-blue-100"
                  : "border border-transparent text-slate-600 hover:border-slate-200 hover:bg-slate-50",
              )}
            >
              <span className="h-2 w-2 rounded-full bg-blue-500/60" />
              <span>{link.label}</span>
            </Link>
          ))}
        </div>
      </nav>
    </aside>
  );
}

