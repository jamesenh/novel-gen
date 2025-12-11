import { Character } from "../types";

type Props = {
  title: string;
  character?: Character | null;
};

export default function CharacterCard({ title, character }: Props) {
  return (
    <div className="rounded-xl border border-slate-100 bg-white/80 p-3 shadow-inner shadow-slate-200/60">
      <div className="text-sm font-semibold text-slate-900">{title}</div>
      {!character && <div className="mt-1 text-xs text-slate-500">暂无</div>}
      {character && (
        <div className="mt-1 space-y-1 text-xs text-slate-700">
          <div>姓名：{character.name || "—"}</div>
          <div>身份：{character.role || "—"}</div>
          <div>性别：{character.gender || "—"}</div>
          <div>外貌：{character.appearance || "—"}</div>
          <div>性格：{character.personality || "—"}</div>
          <div>背景：{character.background || "—"}</div>
          <div>动机：{character.motivation || "—"}</div>
        </div>
      )}
    </div>
  );
}

