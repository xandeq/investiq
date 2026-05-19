import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

export interface PatternWeight {
  weight: number;
  status: "default" | "boosted" | "disabled";
  n: number;
  expectancy: number | null;
  win_rate: number | null;
}

export interface GradeStats {
  n: number;
  winrate: number;
  avg_r: number;
}

export interface CalibrationResponse {
  data_sufficient: boolean;
  total_outcomes: number;
  thresholds: { min_to_adjust: number; min_to_disable: number };
  pattern_weights: Record<string, PatternWeight>;
  grade_performance: Record<string, GradeStats>;
}

export function useCalibration() {
  return useQuery<CalibrationResponse>({
    queryKey: ["signals-calibration"],
    queryFn: () => apiClient<CalibrationResponse>("/signals/calibration"),
    staleTime: 10 * 60 * 1000,
  });
}
