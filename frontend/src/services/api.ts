import axios from "axios";
import {
  ChapterContent,
  ChapterMeta,
  CharactersData,
  ContentGenerateRequest,
  ContentGenerateResponse,
  ContentTarget,
  LogEntry,
  OutlineData,
  ChapterUpdatePayload,
  ProgressSnapshot,
  ProjectDetail,
  ProjectState,
  ProjectSummary,
  RollbackRequest,
  RollbackResult,
  WorldView,
} from "../types";

const client = axios.create({
  baseURL: "/api",
  timeout: 10000,
});

export async function listProjects(): Promise<ProjectSummary[]> {
  const res = await client.get<ProjectSummary[]>("/projects");
  return res.data;
}

export async function createProject(payload: {
  project_name: string;
  initial_chapters?: number;
}): Promise<ProjectDetail> {
  const res = await client.post<ProjectDetail>("/projects", payload);
  return res.data;
}

export async function getProjectDetail(name: string): Promise<ProjectDetail> {
  const res = await client.get<ProjectDetail>(`/projects/${name}`);
  return res.data;
}

export async function getProjectState(name: string): Promise<ProjectState> {
  const res = await client.get<ProjectState>(`/projects/${name}/state`);
  return res.data;
}

export async function startGeneration(project: string, stop_at?: string) {
  return client.post(`/projects/${project}/generate`, { stop_at });
}

export async function stopGeneration(project: string) {
  return client.post(`/projects/${project}/generate/stop`);
}

export async function resumeGeneration(project: string) {
  return client.post(`/projects/${project}/generate/resume`);
}

export async function fetchProgress(project: string): Promise<ProgressSnapshot> {
  const res = await client.get<ProgressSnapshot>(`/projects/${project}/generate/progress`);
  return res.data;
}

export async function fetchLogs(project: string): Promise<LogEntry[]> {
  const res = await client.get<{ items: LogEntry[] }>(`/projects/${project}/generate/logs`);
  return res.data.items || [];
}

export async function fetchChapters(project: string): Promise<ChapterMeta[]> {
  const res = await client.get<ChapterMeta[]>(`/projects/${project}/chapters`);
  return res.data;
}

export async function fetchChapterContent(project: string, num: number): Promise<ChapterContent> {
  const res = await client.get<ChapterContent>(`/projects/${project}/chapters/${num}`);
  return res.data;
}

export async function updateWorld(project: string, payload: WorldView) {
  return client.put(`/projects/${project}/world`, payload);
}

export async function updateCharacters(project: string, payload: CharactersData) {
  return client.put(`/projects/${project}/characters`, payload);
}

export async function updateOutline(project: string, payload: OutlineData) {
  return client.put(`/projects/${project}/outline`, payload);
}

export async function updateChapter(project: string, num: number, payload: ChapterUpdatePayload) {
  return client.put(`/projects/${project}/chapters/${num}`, payload);
}

export async function deleteChapter(project: string, num: number, scene?: number) {
  return client.delete(`/projects/${project}/chapters/${num}`, { params: scene ? { scene } : {} });
}

export async function fetchWorld(project: string): Promise<WorldView> {
  const res = await client.get<WorldView>(`/projects/${project}/world`);
  return res.data;
}

export async function fetchCharacters(project: string): Promise<CharactersData> {
  const res = await client.get<CharactersData>(`/projects/${project}/characters`);
  return res.data;
}

export async function fetchOutline(project: string): Promise<OutlineData> {
  const res = await client.get<OutlineData>(`/projects/${project}/outline`);
  return res.data;
}

export async function rollbackProject(project: string, payload: RollbackRequest): Promise<RollbackResult> {
  const res = await client.post<RollbackResult>(`/projects/${project}/rollback`, payload);
  return res.data;
}

export type DeleteProjectResult = {
  deleted: boolean;
  project_name: string;
  details: {
    deleted_files: boolean;
    cleared_redis: number;
    cleared_mem0: boolean;
    deleted_vectors: boolean;
  };
};

export async function deleteProject(project: string): Promise<DeleteProjectResult> {
  const res = await client.delete<DeleteProjectResult>(`/projects/${project}`);
  return res.data;
}

// ==================== 内容生成 ====================

/**
 * 调用 LLM 生成内容草稿（支持多候选）
 * 
 * @param project 项目名称
 * @param request 生成请求参数
 * @returns 多候选生成结果
 */
export async function generateContent(
  project: string,
  request: ContentGenerateRequest,
): Promise<ContentGenerateResponse> {
  // LLM 生成可能需要较长时间，使用 120 秒超时
  const res = await client.post<ContentGenerateResponse>(
    `/projects/${project}/content/generate`,
    request,
    { timeout: 120000 },
  );
  return res.data;
}

/**
 * 保存内容到对应的 JSON 文件
 * 
 * @param project 项目名称
 * @param target 目标类型
 * @param payload 内容数据
 */
export async function saveContent(
  project: string,
  target: ContentTarget,
  payload: Record<string, any>,
): Promise<{ updated: boolean }> {
  const endpoints: Record<ContentTarget, string> = {
    world: `/projects/${project}/world`,
    theme: `/projects/${project}/theme_conflict`,
    characters: `/projects/${project}/characters`,
    outline: `/projects/${project}/outline`,
  };
  
  const res = await client.put<{ updated: boolean }>(endpoints[target], payload);
  return res.data;
}

/**
 * 获取内容（如果存在）
 * 
 * @param project 项目名称
 * @param target 目标类型
 * @returns 内容数据或 null（不存在时）
 */
export async function fetchContent(
  project: string,
  target: ContentTarget,
): Promise<Record<string, any> | null> {
  const endpoints: Record<ContentTarget, string> = {
    world: `/projects/${project}/world`,
    theme: `/projects/${project}/theme_conflict`,
    characters: `/projects/${project}/characters`,
    outline: `/projects/${project}/outline`,
  };
  
  try {
    const res = await client.get<Record<string, any>>(endpoints[target]);
    return res.data;
  } catch (e: any) {
    if (e?.response?.status === 404) {
      return null;
    }
    throw e;
  }
}

