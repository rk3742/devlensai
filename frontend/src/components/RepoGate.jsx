import { useParams, Outlet } from "react-router-dom";
import { useRepositoryStatus } from "../hooks/useRepositoryStatus";
import { Card, Spinner, Button, ErrorBanner } from "./ui";
import { useNavigate } from "react-router-dom";

const STAGES = [
  "Cloning / extracting repository",
  "Walking file tree and filtering",
  "Categorizing project structure",
  "Chunking and indexing for search",
  "Running static quality checks",
];

/**
 * Gatekeeper for the /repo/:repoId/* route tree. Polls repository status;
 * shows a loading/failed screen until analysis is 'ready', then renders
 * the actual workspace (sidebar + module pages) via <Outlet/>.
 */
export default function RepoGate() {
  const { repoId } = useParams();
  const { repo, error } = useRepositoryStatus(repoId);
  const navigate = useNavigate();

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6 bg-base-950">
        <Card className="p-8 max-w-md text-center">
          <ErrorBanner message={error} />
          <Button className="mt-4" onClick={() => navigate("/")}>Back to import</Button>
        </Card>
      </div>
    );
  }

  if (!repo || repo.status === "pending" || repo.status === "analyzing") {
    return (
      <div className="min-h-screen flex items-center justify-center px-6 bg-base-950">
        <Card className="p-8 max-w-md w-full text-center">
          <div className="flex justify-center mb-5">
            <Spinner size={32} />
          </div>
          <h2 className="font-mono text-lg text-ink mb-1">
            Analyzing {repo?.name || "repository"}…
          </h2>
          <p className="text-ink-dim text-sm mb-6">
            This usually takes a few seconds to a couple of minutes depending on repository size.
          </p>
          <div className="space-y-2 text-left">
            {STAGES.map((stage, i) => (
              <div key={i} className="flex items-center gap-2 text-sm text-ink-dim font-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-accent/60 shrink-0" />
                {stage}
              </div>
            ))}
          </div>
        </Card>
      </div>
    );
  }

  if (repo.status === "failed") {
    return (
      <div className="min-h-screen flex items-center justify-center px-6 bg-base-950">
        <Card className="p-8 max-w-md text-center">
          <h2 className="font-mono text-lg text-danger mb-3">Analysis failed</h2>
          <ErrorBanner message={repo.error_message || "Unknown error occurred."} />
          <Button className="mt-4" onClick={() => navigate("/")}>Try another repository</Button>
        </Card>
      </div>
    );
  }

  return <Outlet />;
}
