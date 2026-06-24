import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { Button, Card, ErrorBanner, Spinner } from "../components/ui";

const TYPED_LINES = [
  "$ devlens analyze --repo .",
  "> reading 245 files...",
  "> mapping architecture...",
  "> indexing for natural-language search...",
  "> ready. ask me anything about this codebase.",
];

function TerminalHero() {
  const [displayed, setDisplayed] = useState([]);
  const [currentText, setCurrentText] = useState("");
  const lineIndex = useRef(0);
  const charIndex = useRef(0);

  useEffect(() => {
    const interval = setInterval(() => {
      if (lineIndex.current >= TYPED_LINES.length) {
        clearInterval(interval);
        return;
      }
      const line = TYPED_LINES[lineIndex.current];
      if (charIndex.current <= line.length) {
        setCurrentText(line.slice(0, charIndex.current));
        charIndex.current += 1;
      } else {
        setDisplayed((prev) => [...prev, line]);
        setCurrentText("");
        lineIndex.current += 1;
        charIndex.current = 0;
      }
    }, 28);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-base-900 border border-base-700 rounded-xl p-5 font-mono text-sm shadow-glow">
      <div className="flex gap-1.5 mb-4">
        <div className="w-3 h-3 rounded-full bg-danger/60" />
        <div className="w-3 h-3 rounded-full bg-warn/60" />
        <div className="w-3 h-3 rounded-full bg-accent/60" />
      </div>
      <div className="space-y-1.5 min-h-[140px]">
        {displayed.map((line, i) => (
          <div key={i} className={line.startsWith("$") ? "text-ink" : "text-accent"}>
            {line}
          </div>
        ))}
        {lineIndex.current < TYPED_LINES.length && (
          <div className={TYPED_LINES[lineIndex.current]?.startsWith("$") ? "text-ink" : "text-accent"}>
            {currentText}
            <span className="cursor-blink">▌</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ImportPage() {
  const [githubUrl, setGithubUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  async function handleGithubImport(e) {
    e.preventDefault();
    if (!githubUrl.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.importGithub(githubUrl.trim());
      navigate(`/repo/${result.id}`);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }

  async function handleZipUpload(file) {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.importZip(file);
      navigate(`/repo/${result.id}`);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-12">
      <div className="max-w-2xl w-full">
        <div className="text-center mb-8">
          <h1 className="font-mono text-3xl font-bold text-ink mb-2 tracking-tight">
            DevLens <span className="text-accent">AI</span>
          </h1>
          <p className="text-ink-dim text-sm">
            Point it at a repository. It reads everything so you don't have to.
          </p>
        </div>

        <TerminalHero />

        <div className="mt-8">
          <Card className="p-6">
            <form onSubmit={handleGithubImport} className="space-y-3">
              <label className="block text-xs font-mono text-ink-dim uppercase tracking-wide">
                GitHub repository URL
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  placeholder="https://github.com/owner/repo"
                  disabled={loading}
                  className="flex-1 bg-base-950 border border-base-700 rounded-lg px-4 py-2.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/30"
                />
                <Button type="submit" disabled={loading || !githubUrl.trim()}>
                  {loading ? <Spinner size={16} /> : "Import"}
                </Button>
              </div>
            </form>

            <div className="flex items-center gap-3 my-5">
              <div className="flex-1 h-px bg-base-700" />
              <span className="text-xs text-ink-faint font-mono">or</span>
              <div className="flex-1 h-px bg-base-700" />
            </div>

            <div
              onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
              onDragLeave={() => setDragActive(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragActive(false);
                const file = e.dataTransfer.files?.[0];
                if (file) handleZipUpload(file);
              }}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-lg py-8 text-center cursor-pointer transition-colors ${
                dragActive ? "border-accent bg-accent/5" : "border-base-700 hover:border-base-600"
              }`}
            >
              <p className="text-sm text-ink-dim">
                Drop a <span className="text-ink font-mono">.zip</span> of your project here, or click to browse
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".zip"
                className="hidden"
                onChange={(e) => handleZipUpload(e.target.files?.[0])}
              />
            </div>

            {error && (
              <div className="mt-4">
                <ErrorBanner message={error} />
              </div>
            )}
          </Card>

          <p className="text-center text-xs text-ink-faint mt-6 font-mono">
            Runs on free-tier AI. No data leaves your machine except what's sent to your configured AI provider.
          </p>
        </div>
      </div>
    </div>
  );
}
