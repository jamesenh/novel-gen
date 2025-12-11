export type ProjectSummary = {
  name: string;
  created_at: string;
  updated_at: string;
  status: string;
};

export type ProjectSteps = {
  world: boolean;
  theme: boolean;
  characters: boolean;
  outline: boolean;
  chapters_plan: boolean;
  chapters: boolean;
};

export type ProjectState = {
  steps: ProjectSteps;
  checkpoint_exists: boolean;
  chapters: ChapterMeta[];
};

export type ProjectDetail = {
  summary: ProjectSummary;
  settings: Record<string, any>;
  state: ProjectState;
};

export type ProgressSnapshot = {
  status: string;
  current_step?: string | null;
  current_chapter?: number | null;
  current_scene?: number | null;
  progress_percent: number;
  message?: string | null;
};

export type LogEntry = {
  timestamp: string;
  level: "INFO" | "ERROR" | "WARN" | "DEBUG";
  message: string;
};

export type WorldView = {
  world_name?: string;
  time_period?: string;
  geography?: string;
  social_system?: string;
  technology_level?: string;
  culture_customs?: string;
  [k: string]: any;
};

export type Character = {
  name?: string;
  role?: string;
  gender?: string;
  appearance?: string;
  personality?: string;
  background?: string;
  motivation?: string;
  [k: string]: any;
};

export type CharactersData = {
  protagonist?: Character | null;
  antagonist?: Character | null;
  supporting_characters?: Character[];
};

export type ChapterMeta = {
  chapter_number: number;
  chapter_title: string;
  scenes_count: number;
  total_words: number;
  status: string;
};

export type SceneContent = {
  scene_number: number;
  content: string;
  word_count: number;
};

export type ChapterContent = {
  chapter_number: number;
  chapter_title: string;
  scenes: SceneContent[];
};

export type ChapterUpdatePayload = {
  chapter_title?: string;
  scenes: SceneContent[];
};

export type OutlineChapter = {
  chapter_number: number;
  chapter_title: string;
  summary?: string;
  key_events?: string[];
};

export type OutlineData = {
  story_premise?: string;
  beginning?: string;
  development?: string;
  climax?: string;
  resolution?: string;
  chapters?: OutlineChapter[];
};

export type RollbackRequest = {
  step?: string;
  chapter?: number;
  scene?: number;
};

export type RollbackResult = {
  deleted_files: number;
  cleared_memories: number;
  files: string[];
};

