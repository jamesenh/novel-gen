import CharacterCard from "./CharacterCard";
import { CharactersData } from "../types";

type Props = {
  data: CharactersData | null;
  loading?: boolean;
};

export default function CharacterList({ data, loading }: Props) {
  if (loading) {
    return (
      <div className="glass-panel p-4">
        <h3 className="section-title">角色</h3>
        <div className="mt-2 muted">加载中...</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="glass-panel p-4">
        <h3 className="section-title">角色</h3>
        <div className="mt-2 muted">暂无角色信息</div>
      </div>
    );
  }

  return (
    <div className="glass-panel p-4">
      <h3 className="section-title">角色</h3>
      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
        <CharacterCard title="主角" character={data.protagonist || undefined} />
        <CharacterCard title="反派" character={data.antagonist || undefined} />
        <CharacterCard title="配角" character={(data.supporting_characters || [])[0]} />
      </div>
      {data.supporting_characters && data.supporting_characters.length > 1 && (
        <div className="mt-3 space-y-2">
          <div className="text-xs font-semibold text-slate-500">更多配角</div>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            {data.supporting_characters.slice(1).map((c, idx) => (
              <CharacterCard key={idx} title={`配角 ${idx + 2}`} character={c} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

