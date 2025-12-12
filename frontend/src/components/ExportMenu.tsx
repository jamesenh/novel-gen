import { useState, useRef, useEffect } from "react";
import clsx from "clsx";

type Props = {
  projectName: string;
  selectedChapter?: number | null;
};

/**
 * 导出下拉菜单组件
 * - 收纳全书/当前章导出按钮
 * - 减少工具栏占用空间
 */
export default function ExportMenu({ projectName, selectedChapter }: Props) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // 点击外部关闭
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const fullBookExports = [
    { label: "导出全书 TXT", href: `/api/projects/${projectName}/export/txt` },
    { label: "导出全书 MD", href: `/api/projects/${projectName}/export/md` },
    { label: "导出全书 JSON", href: `/api/projects/${projectName}/export/json` },
  ];

  const chapterExports = selectedChapter
    ? [
        { label: `导出第${selectedChapter}章 TXT`, href: `/api/projects/${projectName}/export/txt/${selectedChapter}` },
        { label: `导出第${selectedChapter}章 MD`, href: `/api/projects/${projectName}/export/md/${selectedChapter}` },
        { label: `导出第${selectedChapter}章 JSON`, href: `/api/projects/${projectName}/export/json/${selectedChapter}` },
      ]
    : [];

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setOpen(!open)}
        className={clsx(
          "flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition",
          open
            ? "border-blue-300 bg-blue-50 text-blue-700"
            : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50"
        )}
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
          />
        </svg>
        导出
        <svg
          className={clsx("h-3 w-3 transition-transform", open && "rotate-180")}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* 下拉菜单 */}
      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 w-48 rounded-xl border border-slate-200 bg-white py-1 shadow-lg">
          {/* 全书导出 */}
          <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
            全书
          </div>
          {fullBookExports.map((item) => (
            <a
              key={item.href}
              href={item.href}
              target="_blank"
              rel="noreferrer"
              onClick={() => setOpen(false)}
              className="block px-3 py-2 text-xs text-slate-700 hover:bg-slate-50"
            >
              {item.label}
            </a>
          ))}

          {/* 当前章导出 */}
          {chapterExports.length > 0 && (
            <>
              <div className="my-1 border-t border-slate-100" />
              <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                当前章节
              </div>
              {chapterExports.map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  target="_blank"
                  rel="noreferrer"
                  onClick={() => setOpen(false)}
                  className="block px-3 py-2 text-xs text-slate-700 hover:bg-slate-50"
                >
                  {item.label}
                </a>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
