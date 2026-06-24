import { BrowserRouter, Routes, Route } from "react-router-dom";
import ImportPage from "./pages/ImportPage";
import RepoGate from "./components/RepoGate";
import RepoWorkspace from "./components/RepoWorkspace";
import StructurePage from "./pages/StructurePage";
import ExplorerPage from "./pages/ExplorerPage";
import ChatPage from "./pages/ChatPage";
import DocsPage from "./pages/DocsPage";
import QualityPage from "./pages/QualityPage";
import DiagramPage from "./pages/DiagramPage";
import OnboardingPage from "./pages/OnboardingPage";
import BugInvestigationPage from "./pages/BugInvestigationPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ImportPage />} />
        <Route path="/repo/:repoId" element={<RepoGate />}>
          <Route element={<RepoWorkspace />}>
            <Route index element={<StructurePage />} />
            <Route path="structure" element={<StructurePage />} />
            <Route path="explorer" element={<ExplorerPage />} />
            <Route path="chat" element={<ChatPage />} />
            <Route path="docs" element={<DocsPage />} />
            <Route path="quality" element={<QualityPage />} />
            <Route path="diagram" element={<DiagramPage />} />
            <Route path="onboarding" element={<OnboardingPage />} />
            <Route path="bug" element={<BugInvestigationPage />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
