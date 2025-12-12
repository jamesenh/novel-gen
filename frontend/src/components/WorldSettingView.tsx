import clsx from "clsx";
import { WorldView } from "../types";

type Props = {
  data: WorldView;
  onChange: (newData: WorldView) => void;
};

type FieldConfig = {
  key: keyof WorldView;
  label: string;
  description: string;
  multiline?: boolean;
  optional?: boolean;
};

const FIELDS: FieldConfig[] = [
  { key: "world_name", label: "世界名称", description: "这个世界的名字" },
  { key: "time_period", label: "时代背景", description: "故事发生的时代与历史背景" },
  { key: "geography", label: "地理环境", description: "世界的地理特征、重要地点", multiline: true },
  { key: "social_system", label: "社会制度", description: "政治体系、阶级结构、组织形式", multiline: true },
  { key: "power_system", label: "力量体系", description: "修炼/魔法/超能力等体系（如有）", multiline: true, optional: true },
  { key: "technology_level", label: "科技水平", description: "技术发展程度与特色科技" },
  { key: "culture_customs", label: "文化习俗", description: "文化传统、风俗习惯、宗教信仰", multiline: true },
  { key: "special_rules", label: "特殊规则", description: "世界观独有的特殊设定或规则", multiline: true, optional: true },
];

export default function WorldSettingView({ data, onChange }: Props) {
  const handleFieldChange = (key: keyof WorldView, value: string) => {
    onChange({ ...data, [key]: value });
  };

  return (
    <div className="h-full overflow-y-auto pr-2">
      {/* 标题区域 */}
      <div className="mb-6 border-b border-slate-200 pb-4">
        <h2 className="text-2xl font-bold text-slate-900">
          {data.world_name || "未命名世界"}
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          世界观设定 · 点击各区域可编辑内容
        </p>
      </div>

      {/* 字段卡片 */}
      <div className="space-y-4">
        {FIELDS.map((field) => (
          <section
            key={field.key}
            className={clsx(
              "rounded-xl border bg-white/80 p-4 transition-all",
              "border-slate-200/80 hover:border-slate-300 hover:shadow-sm"
            )}
          >
            {/* 标题行 */}
            <div className="mb-2 flex items-center gap-2">
              <h3 className="text-base font-semibold text-slate-800">
                {field.label}
              </h3>
              {field.optional && (
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                  可选
                </span>
              )}
            </div>
            
            {/* 描述 */}
            <p className="mb-2 text-xs text-slate-500">{field.description}</p>
            
            {/* 输入区域 */}
            {field.multiline ? (
              <textarea
                className="w-full resize-none rounded-lg border border-slate-200 bg-slate-50/50 p-3 text-sm text-slate-800 transition focus:border-blue-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100"
                rows={3}
                value={(data[field.key] as string) || ""}
                onChange={(e) => handleFieldChange(field.key, e.target.value)}
                placeholder={`请输入${field.label}...`}
              />
            ) : (
              <input
                type="text"
                className="w-full rounded-lg border border-slate-200 bg-slate-50/50 px-3 py-2 text-sm text-slate-800 transition focus:border-blue-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100"
                value={(data[field.key] as string) || ""}
                onChange={(e) => handleFieldChange(field.key, e.target.value)}
                placeholder={`请输入${field.label}...`}
              />
            )}
          </section>
        ))}
      </div>
    </div>
  );
}
