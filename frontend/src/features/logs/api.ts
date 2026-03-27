import { apiClient } from "@/lib/api-client";

export interface LogEntry {
  id: string;
  level: "ERROR" | "WARNING" | "INFO" | "DEBUG";
  title: string;
  message: string;
  traceback: string | null;
  module: string | null;
  request_path: string | null;
  request_method: string | null;
  user_id: string | null;
  extra: Record<string, unknown> | null;
  created_at: string;
}

export async function getLogs(level?: string): Promise<LogEntry[]> {
  const qs = level ? `?level=${level}` : "";
  return apiClient<LogEntry[]>(`/admin/logs${qs}`);
}

export async function deleteLog(id: string): Promise<void> {
  await apiClient(`/admin/logs/${id}`, { method: "DELETE" });
}

export async function clearAllLogs(): Promise<void> {
  await apiClient("/admin/logs", { method: "DELETE" });
}
