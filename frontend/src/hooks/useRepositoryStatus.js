import { useEffect, useState, useRef } from "react";
import { api } from "../lib/api";

/**
 * Polls a repository's status until it reaches 'ready' or 'failed'.
 * Returns the latest repository record plus loading/error state.
 */
export function useRepositoryStatus(repoId) {
  const [repo, setRepo] = useState(null);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (!repoId) return;

    let cancelled = false;

    async function poll() {
      try {
        const data = await api.getRepository(repoId);
        if (cancelled) return;
        setRepo(data);
        if (data.status === "ready" || data.status === "failed") {
          clearInterval(intervalRef.current);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
          clearInterval(intervalRef.current);
        }
      }
    }

    poll();
    intervalRef.current = setInterval(poll, 2000);

    return () => {
      cancelled = true;
      clearInterval(intervalRef.current);
    };
  }, [repoId]);

  return { repo, error };
}
