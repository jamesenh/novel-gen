import { create } from "zustand";
import { listProjects } from "../services/api";
import { ProjectSummary } from "../types";

type ProjectState = {
  items: ProjectSummary[];
  loading: boolean;
  fetch: () => Promise<void>;
};

export const useProjectStore = create<ProjectState>((set) => ({
  items: [],
  loading: false,
  fetch: async () => {
    set({ loading: true });
    try {
      const data = await listProjects();
      set({ items: data, loading: false });
    } catch (e) {
      set({ loading: false });
      throw e;
    }
  },
}));

