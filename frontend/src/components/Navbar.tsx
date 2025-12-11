import { Link } from "react-router-dom";

export default function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/80 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 lg:px-10">
        <Link to="/" className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 text-lg font-semibold text-white shadow-lg shadow-blue-500/30">
            N
          </div>
          <div className="leading-tight">
            <div className="text-lg font-semibold text-slate-900">NovelGen Web</div>
            <div className="text-xs text-slate-500">AI 小说生成工作台</div>
          </div>
        </Link>

        <nav className="hidden items-center gap-3 text-sm text-slate-600 md:flex">
          <Link to="/" className="rounded-full px-3 py-2 transition hover:bg-slate-100">
            项目列表
          </Link>
        </nav>

        <div className="flex items-center gap-3">
          <span className="pill pill-info">Beta</span>
          <Link to="/" className="btn-soft hidden md:inline-flex">
            返回首页
          </Link>
        </div>
      </div>
    </header>
  );
}

