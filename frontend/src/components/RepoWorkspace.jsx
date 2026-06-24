import { NavLink, Outlet, useParams, useNavigate } from "react-router-dom";
import { useRepositoryStatus } from "../hooks/useRepositoryStatus";
import { Badge } from "../components/ui";

const NAV_ITEMS = [
  { to: "structure", label: "Structure", icon: "▦" },
  { to: "explorer", label: "Code Explainer", icon: "◧" },
  { to: "chat", label: "Ask Questions", icon: "›_" },
  { to: "docs", label: "Documentation", icon: "▤" },
  { to: "quality", label: "Dead Code & Debt", icon: "▲" },
  { to: "diagram", label: "Architecture", icon: "◇" },
  { to: "onboarding", label: "Onboarding", icon: "→" },
  { to: "bug", label: "Bug Investigation", icon: "?" },
];

export default function RepoWorkspace() {
  const { repoId } = useParams();
  const { repo } = useRepositoryStatus(repoId);
  const navigate = useNavigate();

  return (
    <div className="flex h-screen bg-base-950">
      <aside className="w-60 border-r border-base-700 bg-base-900 flex flex-col shrink-0">
        <div
          className="px-4 py-4 border-b border-base-700 cursor-pointer"
          onClick={() => navigate("/")}
        >
          <div className="font-mono text-sm font-bold text-ink">
            DevLens <span className="text-accent">AI</span>
          </div>
          {repo && (
            <div className="mt-2">
              <div className="text-xs text-ink-dim font-mono truncate" title={repo.name}>
                {repo.name}
              </div>
              <div className="mt-1 flex gap-1.5">
                <Badge tone="accent">{repo.file_count} files</Badge>
              </div>
            </div>
          )}
        </div>

        <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? "bg-accent/10 text-accent"
                    : "text-ink-dim hover:text-ink hover:bg-base-800"
                }`
              }
            >
              <span className="w-4 text-center font-mono text-xs">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="px-3 py-3 border-t border-base-700">
          <button
            onClick={() => navigate("/")}
            className="w-full text-left text-xs text-ink-faint hover:text-ink-dim font-mono px-2 py-1.5 rounded-md hover:bg-base-800 transition-colors"
          >
            ← Analyze another repository
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        <Outlet context={{ repoId, repo }} />
      </main>
    </div>
  );
}
