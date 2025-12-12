import { ReactNode, useEffect } from "react";
import clsx from "clsx";

type Props = {
  open: boolean;
  onClose: () => void;
  side: "left" | "right";
  title?: string;
  children: ReactNode;
};

/**
 * 阅读页抽屉组件
 * - 用于移动端/窄屏时展示章节列表或参考面板
 * - 支持左侧/右侧滑出
 */
export default function ReaderDrawer({ open, onClose, side, title, children }: Props) {
  // 打开时禁止 body 滚动
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <>
      {/* 遮罩层 */}
      <div
        className={clsx(
          "fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-sm transition-opacity duration-300",
          open ? "opacity-100" : "pointer-events-none opacity-0"
        )}
        onClick={onClose}
      />

      {/* 抽屉面板 */}
      <div
        className={clsx(
          "fixed top-0 z-50 flex h-full w-[85vw] max-w-sm flex-col bg-white shadow-2xl transition-transform duration-300",
          side === "left" ? "left-0" : "right-0",
          side === "left"
            ? open
              ? "translate-x-0"
              : "-translate-x-full"
            : open
              ? "translate-x-0"
              : "translate-x-full"
        )}
      >
        {/* 头部 */}
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h3 className="text-base font-semibold text-slate-900">{title}</h3>
          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-full text-slate-500 hover:bg-slate-100"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* 内容区域 */}
        <div className="flex-1 overflow-y-auto">{children}</div>
      </div>
    </>
  );
}
