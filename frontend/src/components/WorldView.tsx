import { WorldView } from "../types";

type Props = {
  data: WorldView | null;
  loading?: boolean;
};

export default function WorldViewCard({ data, loading }: Props) {
  if (loading) {
    return (
      <div className="glass-panel p-4">
        <h3 className="section-title">世界观</h3>
        <div className="mt-2 muted">加载中...</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="glass-panel p-4">
        <h3 className="section-title">世界观</h3>
        <div className="mt-2 muted">暂无世界观信息</div>
      </div>
    );
  }

  return (
    <div className="glass-panel p-4">
      <h3 className="section-title">世界观</h3>
      <div className="mt-2 grid grid-cols-2 gap-2 text-sm text-slate-700">
        <div>名称：{data.world_name || "—"}</div>
        <div>时代：{data.time_period || "—"}</div>
        <div>地理：{data.geography || "—"}</div>
        <div>社会：{data.social_system || "—"}</div>
        <div>科技：{data.technology_level || "—"}</div>
        <div className="col-span-2">
          风俗：{data.culture_customs || "—"}
        </div>
      </div>
    </div>
  );
}

