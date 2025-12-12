import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { deleteProject, DeleteProjectResult } from "../services/api";

type Props = {
  open: boolean;
  project: string;
  onClose: () => void;
};

export default function DeleteProjectModal({ open, project, onClose }: Props) {
  const navigate = useNavigate();
  const [confirmText, setConfirmText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DeleteProjectResult | null>(null);

  if (!open) return null;

  const canDelete = confirmText === project;

  const handleDelete = async () => {
    if (!canDelete) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await deleteProject(project);
      setResult(res);
      // 删除成功后延迟跳转，让用户看到结果
      setTimeout(() => {
        navigate("/", { replace: true });
      }, 1500);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "删除失败，请稍后重试");
      setResult(null);
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    if (submitting) return;
    setConfirmText("");
    setError(null);
    setResult(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur">
      <div className="glass-panel w-full max-w-lg p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-red-500">危险操作</p>
            <h2 className="mt-1 text-xl font-semibold text-slate-900">删除项目</h2>
          </div>
          <button className="btn-ghost text-sm" onClick={handleClose} disabled={submitting}>
            关闭
          </button>
        </div>

        {!result ? (
          <>
            <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4">
              <div className="flex items-start gap-3">
                <span className="text-2xl">⚠️</span>
                <div className="text-sm text-red-800">
                  <p className="font-semibold">此操作不可撤销！</p>
                  <p className="mt-1">
                    删除项目将永久移除以下内容：
                  </p>
                  <ul className="mt-2 list-disc pl-4 text-red-700">
                    <li>所有生成的章节和场景文本</li>
                    <li>世界观、角色、大纲等设定</li>
                    <li>检查点和进度数据</li>
                    <li>向量存储和记忆数据</li>
                  </ul>
                </div>
              </div>
            </div>

            <div className="mt-4 space-y-3 text-sm">
              <div>
                <label className="text-slate-700">
                  请输入项目名称 <span className="font-mono font-semibold text-slate-900">{project}</span> 以确认删除：
                </label>
                <input
                  type="text"
                  className="mt-2 w-full rounded border border-slate-200 px-3 py-2 focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500"
                  placeholder={project}
                  value={confirmText}
                  onChange={(e) => setConfirmText(e.target.value)}
                  disabled={submitting}
                />
              </div>
              {error && <div className="text-sm text-red-500">{error}</div>}
            </div>

            <div className="mt-5 flex justify-end gap-3 text-sm">
              <button
                className="rounded px-4 py-2 text-slate-700 hover:bg-slate-100"
                onClick={handleClose}
                disabled={submitting}
              >
                取消
              </button>
              <button
                className="rounded bg-red-600 px-4 py-2 text-white shadow hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60"
                onClick={handleDelete}
                disabled={!canDelete || submitting}
              >
                {submitting ? "删除中..." : "确认删除"}
              </button>
            </div>
          </>
        ) : (
          <div className="mt-4">
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
              <div className="flex items-start gap-3">
                <span className="text-2xl">✅</span>
                <div className="text-sm text-emerald-800">
                  <p className="font-semibold">项目已成功删除</p>
                  <p className="mt-2 text-emerald-700">正在跳转到项目列表...</p>
                </div>
              </div>
            </div>
            <div className="mt-3 rounded border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
              <div>已删除文件目录：{result.details.deleted_files ? "是" : "否"}</div>
              <div>清理 Redis 键数：{result.details.cleared_redis}</div>
              <div>清理 Mem0 记忆：{result.details.cleared_mem0 ? "是" : "否"}</div>
              <div>删除向量存储：{result.details.deleted_vectors ? "是" : "否"}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
