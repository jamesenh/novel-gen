import { LogEntry } from "../types";

const shanghaiFormatter = new Intl.DateTimeFormat("zh-CN", {
  timeZone: "Asia/Shanghai",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

const formatTimestamp = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const parts = shanghaiFormatter.formatToParts(date).reduce<Record<string, string>>((acc, part) => {
    if (part.type !== "literal") acc[part.type] = part.value;
    return acc;
  }, {});
  return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}:${parts.second}`;
};

type Props = {
  logs: LogEntry[];
};

export default function LogViewer({ logs }: Props) {
  return (
    <div className="h-72 overflow-y-auto rounded-xl border border-slate-100 bg-slate-50/80 p-3 text-sm text-slate-700 shadow-inner">
      {logs.length === 0 && <div className="text-slate-400">暂无日志</div>}
      {logs.map((log) => (
        <div key={log.timestamp + log.message} className="mb-2 rounded-lg bg-white/80 p-2 shadow-sm last:mb-0">
          <div className="text-xs text-slate-500">
            {formatTimestamp(log.timestamp)} · {log.level}
          </div>
          <div className="mt-1 text-slate-800">{log.message}</div>
        </div>
      ))}
    </div>
  );
}

