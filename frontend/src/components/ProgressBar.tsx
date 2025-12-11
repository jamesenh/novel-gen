type Props = {
  value: number;
  label?: string;
};

export default function ProgressBar({ value, label }: Props) {
  const percent = Math.min(Math.max(value, 0), 100);
  return (
    <div className="space-y-1">
      {label && <div className="text-xs text-slate-600">{label}</div>}
      <div className="h-3 rounded-full bg-slate-100">
        <div
          className="h-3 rounded-full bg-gradient-to-r from-blue-500 to-indigo-500 shadow-inner shadow-blue-500/30 transition-all"
          style={{ width: `${percent}%` }}
        />
      </div>
      <div className="flex items-center justify-between text-[11px] text-slate-500">
        <span>进度</span>
        <span className="font-semibold text-slate-700">{percent.toFixed(1)}%</span>
      </div>
    </div>
  );
}

