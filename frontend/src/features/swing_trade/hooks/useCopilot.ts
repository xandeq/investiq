import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchCopilot } from "../api";

export function useCopilot() {
  const qc = useQueryClient();

  const query = useQuery({
    queryKey: ["swing-trade-copilot"],
    queryFn: () => fetchCopilot(),
    staleTime: 1000 * 60 * 30, // 30 min — backend caches 4h
    retry: 1,
  });

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["swing-trade-copilot"] });
    return fetchCopilot(true).then((data) => {
      qc.setQueryData(["swing-trade-copilot"], data);
      return data;
    });
  };

  return { ...query, refresh };
}
