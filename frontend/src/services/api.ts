import axios from "axios";
import {
  ChapterContent,
  ChapterMeta,
  CharactersData,
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
  world_description: string;
  theme_description?: string;
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

