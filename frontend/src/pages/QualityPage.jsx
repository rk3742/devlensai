import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { api } from "../lib/api";
import { Card, Badge, Spinner, ErrorBanner, EmptyState } from "../components/ui";

const SEVERITY_TONE = { high: "danger", medium: "warn", low: "default" };

function FindingCard({ finding, kind }) {
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3 mb-1.5">
        <h4 className="font-mono text-sm text-ink">{finding.title}</h4>
        {kind === "dead_code" ? (
          <Badge tone="warn">{finding.confidence}% confidence</Badge>
        ) : (
          <Badge tone={SEVERITY_TONE[finding.severity] || "default"}>{finding.severity}</Badge>
        )}
      </div>
      <p className="text-ink-faint text-xs font-mono mb-2">{finding.file_path}</p>
      {finding.detail && <p className="text-ink-dim text-sm leading-relaxed">{finding.detail}</p>}
    </Card>
  );
}

export default function QualityPage() {
  const { repoId } = useOutletContext();
  const [tab, setTab] = useState("dead_code");
  const [deadCode, setDeadCode] = useState(null);
  const [techDebt, setTechDebt] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([api.getDeadCode(repoId), api.getTechDebt(repoId)])
      .then(([dc, td]) => { setDeadCode(dc); setTechDebt(td); })
      .catch((e) => setError(e.message));
  }, [repoId]);

  if (error) return <div className="p-8"><ErrorBanner message={error} /></div>;
  if (!deadCode || !techDebt) {
    return <div className="p-8 flex items-center gap-2 text-ink-dim"><Spinner /> Loading findings…</div>;
  }

  const activeData = tab === "dead_code" ? deadCode : techDebt;

  return (
    <div className="p-8 max-w-3xl">
      <h1 className="font-mono text-xl text-ink mb-1">Dead Code & Technical Debt</h1>
      <p className="text-ink-dim text-sm mb-6">
        Static analysis findings — not pure AI guesses. Each finding comes from measurable signals
        (cross-reference counts, function length, duplicate names) so confidence scores mean something.
      </p>

      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setTab("dead_code")}
          className={`px-4 py-2 rounded-lg text-sm font-mono transition-colors ${
            tab === "dead_code" ? "bg-accent/10 text-accent border border-accent/30" : "bg-base-900 text-ink-dim border border-base-700"
          }`}
        >
          Dead Code ({deadCode.length})
        </button>
        <button
          onClick={() => setTab("tech_debt")}
          className={`px-4 py-2 rounded-lg text-sm font-mono transition-colors ${
            tab === "tech_debt" ? "bg-accent/10 text-accent border border-accent/30" : "bg-base-900 text-ink-dim border border-base-700"
          }`}
        >
          Technical Debt ({techDebt.length})
        </button>
      </div>

      {activeData.length === 0 ? (
        <EmptyState
          title={tab === "dead_code" ? "No likely dead code found" : "No technical debt found"}
          description={
            tab === "dead_code"
              ? "Every function in this repository appears to be referenced, exported, or registered somewhere. That's a good sign — or it means this scan's heuristics didn't have enough cross-references to work with on a small repo."
              : "No long functions, duplicate logic, or TODO/FIXME markers were detected."
          }
        />
      ) : (
        <div className="space-y-3">
          {activeData.map((f) => (
            <FindingCard key={f.id} finding={f} kind={tab} />
          ))}
        </div>
      )}
    </div>
  );
}
