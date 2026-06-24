import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { api } from "../lib/api";
import { Card, Badge, Spinner, ErrorBanner, EmptyState } from "../components/ui";

export default function ExplorerPage() {
  const { repoId } = useOutletContext();
  const [files, setFiles] = useState([]);
  const [filesError, setFilesError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [loadingExplain, setLoadingExplain] = useState(false);
  const [explainError, setExplainError] = useState(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    api.getFiles(repoId).then(setFiles).catch((e) => setFilesError(e.message));
  }, [repoId]);

  async function handleSelectFile(file) {
    setSelected(file);
    setExplanation(null);
    setExplainError(null);
    setLoadingExplain(true);
    try {
      const result = await api.explainFile(repoId, file.rel_path);
      if (result.error) {
        setExplainError(result.summary);
      } else {
        setExplanation(result);
      }
    } catch (err) {
      setExplainError(err.message);
    } finally {
      setLoadingExplain(false);
    }
  }

  const filteredFiles = files.filter((f) =>
    f.rel_path.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="flex h-full">
      <div className="w-80 border-r border-base-700 flex flex-col">
        <div className="p-3 border-b border-base-700">
          <input
            type="text"
            placeholder="Filter files…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full bg-base-900 border border-base-700 rounded-md px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
          />
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {filesError && <ErrorBanner message={filesError} />}
          {filteredFiles.map((file) => (
            <div
              key={file.id}
              onClick={() => handleSelectFile(file)}
              className={`px-3 py-2 rounded-md text-sm cursor-pointer truncate font-mono ${
                selected?.id === file.id
                  ? "bg-accent/10 text-accent"
                  : "text-ink-dim hover:bg-base-800 hover:text-ink"
              }`}
              title={file.rel_path}
            >
              {file.rel_path}
            </div>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-8">
        {!selected && (
          <EmptyState
            title="Select a file to explain"
            description="Pick any file from the list — DevLens AI will explain what it does, list its functions, and point out notable patterns."
          />
        )}

        {selected && (
          <div className="max-w-3xl">
            <div className="flex items-center gap-2 mb-1">
              <h1 className="font-mono text-lg text-ink">{selected.rel_path}</h1>
              <Badge>{selected.language}</Badge>
            </div>
            <p className="text-ink-faint text-xs font-mono mb-6">
              {selected.line_count} lines · {selected.size_bytes} bytes
            </p>

            {loadingExplain && (
              <div className="flex items-center gap-2 text-ink-dim">
                <Spinner /> Asking the AI to explain this file…
              </div>
            )}

            {explainError && <ErrorBanner message={explainError} />}

            {explanation && (
              <div className="space-y-6">
                <Card className="p-5">
                  <h3 className="font-mono text-xs uppercase tracking-wide text-ink-dim mb-2">Summary</h3>
                  <p className="text-ink text-sm leading-relaxed">{explanation.summary}</p>
                </Card>

                {explanation.functions?.length > 0 && (
                  <Card className="p-5">
                    <h3 className="font-mono text-xs uppercase tracking-wide text-ink-dim mb-3">Functions</h3>
                    <div className="space-y-3">
                      {explanation.functions.map((fn, i) => (
                        <div key={i} className="flex gap-3">
                          <code className="text-accent text-sm font-mono shrink-0">{fn.name}()</code>
                          <span className="text-ink-dim text-sm">{fn.purpose}</span>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}

                {explanation.dependencies?.length > 0 && (
                  <Card className="p-5">
                    <h3 className="font-mono text-xs uppercase tracking-wide text-ink-dim mb-3">Dependencies</h3>
                    <div className="flex flex-wrap gap-2">
                      {explanation.dependencies.map((dep, i) => (
                        <Badge key={i}>{dep}</Badge>
                      ))}
                    </div>
                  </Card>
                )}

                {explanation.notable_patterns?.length > 0 && (
                  <Card className="p-5">
                    <h3 className="font-mono text-xs uppercase tracking-wide text-ink-dim mb-3">Notable patterns</h3>
                    <ul className="space-y-1.5">
                      {explanation.notable_patterns.map((p, i) => (
                        <li key={i} className="text-ink-dim text-sm flex gap-2">
                          <span className="text-accent">→</span> {p}
                        </li>
                      ))}
                    </ul>
                  </Card>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
