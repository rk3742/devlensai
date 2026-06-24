import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { api } from "../lib/api";
import { Card, Spinner, ErrorBanner, Badge } from "../components/ui";

export default function OnboardingPage() {
  const { repoId } = useOutletContext();
  const [path, setPath] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getOnboarding(repoId)
      .then((result) => {
        if (result.error) setError(result.error);
        else setPath(result);
      })
      .catch((e) => setError(e.message));
  }, [repoId]);

  if (error) return <div className="p-8"><ErrorBanner message={error} /></div>;
  if (!path) return <div className="p-8 flex items-center gap-2 text-ink-dim"><Spinner /> Building your onboarding path…</div>;

  return (
    <div className="p-8 max-w-3xl">
      <h1 className="font-mono text-xl text-ink mb-1">Onboarding Assistant</h1>
      <p className="text-ink-dim text-sm mb-6">
        A suggested learning order for a new developer joining this project — what to read first, and why.
      </p>

      <div className="space-y-4">
        {(path.steps || []).map((step) => (
          <Card key={step.order} className="p-5 flex gap-4">
            <div className="shrink-0 w-8 h-8 rounded-full bg-accent/10 border border-accent/30 flex items-center justify-center font-mono text-accent text-sm">
              {step.order}
            </div>
            <div>
              <h3 className="font-mono text-sm text-ink mb-1">{step.topic}</h3>
              <p className="text-ink-dim text-sm mb-2">{step.reason}</p>
              {step.files?.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {step.files.map((f, i) => (
                    <Badge key={i}>{f}</Badge>
                  ))}
                </div>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
