import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { api } from "../lib/api";
import { Card, Badge, Spinner, ErrorBanner } from "../components/ui";
import FileTree from "../components/FileTree";

const CATEGORY_COLORS = {
  Frontend: "#5B8DEF",
  Backend: "#22C55E",
  Database: "#F59E0B",
  Services: "#A855F7",
  Tests: "#94A3B8",
  Config: "#64748B",
  Documentation: "#94A3B8",
  Other: "#475569",
};

export default function StructurePage() {
  const { repoId } = useOutletContext();
  const [structure, setStructure] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getStructure(repoId).then(setStructure).catch((e) => setError(e.message));
  }, [repoId]);

  if (error) return <div className="p-8"><ErrorBanner message={error} /></div>;
  if (!structure) return <div className="p-8 flex items-center gap-2 text-ink-dim"><Spinner /> Loading structure…</div>;

  const totalFiles = structure.total_files || 1;

  return (
    <div className="p-8 max-w-5xl">
      <h1 className="font-mono text-xl text-ink mb-1">Project Structure</h1>
      <p className="text-ink-dim text-sm mb-6">
        {structure.total_files} files analyzed across {Object.keys(structure.categories || {}).length} categories.
      </p>

      <div className="grid grid-cols-2 gap-6 mb-8">
        <Card className="p-5">
          <h3 className="font-mono text-xs uppercase tracking-wide text-ink-dim mb-4">By category</h3>
          <div className="space-y-2.5">
            {Object.entries(structure.categories || {}).map(([cat, count]) => (
              <div key={cat}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-ink">{cat}</span>
                  <span className="text-ink-faint font-mono">{count}</span>
                </div>
                <div className="h-1.5 bg-base-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${(count / totalFiles) * 100}%`,
                      backgroundColor: CATEGORY_COLORS[cat] || "#475569",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-5">
          <h3 className="font-mono text-xs uppercase tracking-wide text-ink-dim mb-4">Languages</h3>
          <div className="flex flex-wrap gap-2">
            {Object.entries(structure.languages || {}).map(([lang, count]) => (
              <Badge key={lang} tone="default">
                {lang} · {count}
              </Badge>
            ))}
          </div>
        </Card>
      </div>

      <Card className="p-5">
        <h3 className="font-mono text-xs uppercase tracking-wide text-ink-dim mb-3">File tree</h3>
        <div className="max-h-[480px] overflow-y-auto">
          <FileTree tree={structure.tree} />
        </div>
      </Card>
    </div>
  );
}
