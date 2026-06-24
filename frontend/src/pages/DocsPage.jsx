import { useState } from "react";
import { useOutletContext } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { api } from "../lib/api";
import { Card, Spinner, ErrorBanner, Button } from "../components/ui";

const TABS = [
  { key: "readme", label: "README.md", fetcher: "getReadme" },
  { key: "api", label: "API Docs", fetcher: "getApiDocs" },
  { key: "install", label: "Install Guide", fetcher: "getInstallGuide" },
];

export default function DocsPage() {
  const { repoId } = useOutletContext();
  const [activeTab, setActiveTab] = useState(null);
  const [content, setContent] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function loadTab(tab) {
    setActiveTab(tab.key);
    if (content[tab.key]) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api[tab.fetcher](repoId);
      setContent((prev) => ({ ...prev, [tab.key]: result.content }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function downloadCurrent() {
    const tab = TABS.find((t) => t.key === activeTab);
    const text = content[activeTab] || "";
    const blob = new Blob([text], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${tab.key}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="p-8 max-w-4xl">
      <h1 className="font-mono text-xl text-ink mb-1">Documentation Generator</h1>
      <p className="text-ink-dim text-sm mb-6">
        Generate a README, API reference, or install guide grounded in this repository's actual code.
      </p>

      <div className="flex gap-2 mb-6">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => loadTab(tab)}
            className={`px-4 py-2 rounded-lg text-sm font-mono transition-colors ${
              activeTab === tab.key
                ? "bg-accent/10 text-accent border border-accent/30"
                : "bg-base-900 text-ink-dim border border-base-700 hover:text-ink"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {!activeTab && (
        <p className="text-ink-faint text-sm">Pick a document type above to generate it.</p>
      )}

      {loading && (
        <div className="flex items-center gap-2 text-ink-dim">
          <Spinner /> Generating documentation…
        </div>
      )}

      {error && <ErrorBanner message={error} />}

      {activeTab && content[activeTab] && !loading && (
        <Card className="p-6">
          <div className="flex justify-end mb-3">
            <Button variant="secondary" onClick={downloadCurrent}>Download .md</Button>
          </div>
          <div className="markdown-body">
            <ReactMarkdown>{content[activeTab]}</ReactMarkdown>
          </div>
        </Card>
      )}
    </div>
  );
}
