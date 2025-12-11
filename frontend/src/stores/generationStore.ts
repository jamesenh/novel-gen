import { create } from "zustand";
import { fetchLogs, fetchProgress, resumeGeneration, startGeneration, stopGeneration } from "../services/api";
import { LogEntry, ProgressSnapshot } from "../types";

type GenerationState = {
  progress: ProgressSnapshot | null;
  logs: LogEntry[];
  loading: boolean;
  start: (project: string, stop_at?: string) => Promise<void>;
  resume: (project: string) => Promise<void>;
  stop: (project: string) => Promise<void>;
  refresh: (project: string) => Promise<void>;
};

export const useGenerationStore = create<GenerationState>((set) => ({
  progress: null,
  logs: [],
  loading: false,
  start: async (project: string, stop_at?: string) => {
    set({ loading: true });
    try {
      await startGeneration(project, stop_at);
    } finally {
      set({ loading: false });
    }
  },
  resume: async (project: string) => {
    set({ loading: true });
    try {
      await resumeGeneration(project);
    } finally {
      set({ loading: false });
    }
  },
  stop: async (project: string) => {
    set({ loading: true });
    try {
      await stopGeneration(project);
    } finally {
      set({ loading: false });
    }
  },
  refresh: async (project: string) => {
    const [progress, logs] = await Promise.all([fetchProgress(project), fetchLogs(project)]);
    set({ progress, logs });
  },
}));

