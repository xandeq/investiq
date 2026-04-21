import { useEffect, useState } from "react";
import { getAdvisorJob } from "../api";
import type { AdvisorJobResponse } from "../types";

export function useAdvisorJob(jobId: string | null) {
  const [data, setData] = useState<AdvisorJobResponse | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;

    const poll = async () => {
      try {
        const result = await getAdvisorJob(jobId);
        if (!cancelled) {
          setData(result);
          if (result.status !== "pending" && result.status !== "running") return;
          setTimeout(poll, 3000);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err : new Error(String(err)));
      }
    };

    poll();
    return () => { cancelled = true; };
  }, [jobId]);

  return { data, error };
}
