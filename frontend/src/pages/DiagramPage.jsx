import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { api } from "../lib/api";
import { Card, Spinner, ErrorBanner } from "../components/ui";

export default function DiagramPage() {
  const { repoId } = useOutletContext();
  const [diagram, setDiagram] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getDiagram(repoId).then(setDiagram).catch((e) => setError(e.message));
  }, [repoId]);

  if (error) return <div className="p-8"><ErrorBanner message={error} /></div>;
  if (!diagram) return <div className="p-8 flex items-center gap-2 text-ink-dim"><Spinner /> Generating diagram…</div>;

  return (
    <div className="p-8 max-w-3xl">
      <h1 className="font-mono text-xl text-ink mb-1">Architecture Diagram</h1>
      <p className="text-ink-dim text-sm mb-6">{diagram.description}</p>

      <Card className="p-8 flex justify-center">
        <div
          className="w-full max-w-md"
          dangerouslySetInnerHTML={{ __html: diagram.svg }}
        />
      </Card>
    </div>
  );
}
