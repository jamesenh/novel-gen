import { Route, Routes } from "react-router-dom";
import ProjectList from "./pages/ProjectList";
import ProjectDetail from "./pages/ProjectDetail";
import GenerationControl from "./pages/GenerationControl";
import Reader from "./pages/Reader";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<ProjectList />} />
      <Route path="/projects/:name" element={<ProjectDetail />} />
      <Route path="/projects/:name/generate" element={<GenerationControl />} />
      <Route path="/projects/:name/read" element={<Reader />} />
    </Routes>
  );
}

