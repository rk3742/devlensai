import { useState } from "react";
import { useOutletContext } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { api } from "../lib/api";
import { Card, Spinner, ErrorBanner, EmptyState } from "../components/ui";

export default function BugInvestigationPage() {
  const { repoId } = useOutletContext();
  const [description, setDescription] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!description.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await api.investigateBug(repoId, description.trim());
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-3xl">
      <h1 className="font-mono text-xl text-ink mb-1">Bug Investigation Assistant</h1>
      <p className="text-ink-dim text-sm mb-6">
        Describe a bug or unexpected behavior. DevLens AI will search the relevant code and suggest likely causes.
      </p>

      <form onSubmit={handleSubmit} className="mb-6">
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="e.g. Why is login failing for some users but not others?"
          rows={3}
          className="w-full bg-base-900 border border-base-700 rounded-lg px-4 py-3 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50 resize-none"
        />
        <button
          type="submit"
          disabled={loading || !description.trim()}
          className="mt-3 px-4 py-2 rounded-lg bg-accent text-base-950 font-semibold text-sm disabled:opacity-40 hover:bg-accent-dim transition-colors"
        >
          Investigate
        </button>
      </form>

      {loading && (
        <div className="flex items-center gap-2 text-ink-dim">
          <Spinner /> Searching the codebase for relevant logic…
        </div>
      )}

      {error && <ErrorBanner message={error} />}

      {!result && !loading && !error && (
        <EmptyState
          title="No investigation yet"
          description="Describe the bug above to get started."
        />
      )}

      {result && (
        <Card className="p-5">
          <div className="markdown-body text-sm">
            <ReactMarkdown>{result.analysis}</ReactMarkdown>
          </div>
          {result.sources?.length > 0 && (
            <div className="mt-4 pt-4 border-t border-base-700">
              <h4 className="font-mono text-xs uppercase tracking-wide text-ink-dim mb-2">
                Relevant files examined
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {result.sources.map((s, i) => (
                  <span
                    key={i}
                    className="text-xs font-mono text-accent bg-accent/5 px-2 py-0.5 rounded border border-accent/20"
                    title={s.snippet}
                  >
                    {s.file_path}
                  </span>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
