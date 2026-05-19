import { useQuery } from "@tanstack/react-query";
import { getGoals } from "../api";
import type { GoalResponse } from "../types";

export function useGoals() {
  return useQuery<GoalResponse[]>({
    queryKey: ["goals"],
    queryFn: getGoals,
    staleTime: 5 * 60 * 1000,
  });
}
