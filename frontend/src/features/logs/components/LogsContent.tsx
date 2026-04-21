"use client";
import { useState, useEffect, useCallback } from "react";
import { getLogs, deleteLog, clearAllLogs, LogEntry } from "@/features/logs/api";
import { useSortedData } from "@/hooks/useSort";
import { SortableHeader } from "@/components/ui/SortableHeader";

const LEVEL_BADGE: Record<string, string> = {
  ERROR: "bg-red-100 text-red-700 border border-red-200",
  WARNING: "bg-yellow-100 text-yellow-700 border border-yellow-200",
  INFO: "bg-blue-100 text-blue-700 border border-blue-200",
  DEBUG: "bg-gray-100 text-gray-600 border border-gray-200",
};

function formatDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function buildPrompt(type: "analyze" | "fix" | "refactor", log: LogEntry): string {
  const header = [
    `Título: ${log.title}`,
    log.module ? `Módulo: ${log.module}` : null,
    log.request_method && log.request_path
      ? `Rota: ${log.request_method} ${log.request_path}`
      : null,
    `Nível: ${log.level}`,
  ]
    .filter(Boolean)
    .join("\n");

  const tb = log.traceback ? `\nTraceback:\n\`\`\`\n${log.traceback}\n\`\`\`` : "";
  const msg = log.message !== log.title ? `\nMensagem:\n${log.message}` : "";

  if (type === "analyze") {
    return `Analise este erro da aplicação InvestIQ (FastAPI + Next.js):\n\n${header}${msg}${tb}\n\nExplique o que causou este erro, o impacto potencial e onde exatamente ocorreu no código.`;
  }
  if (type === "fix") {
    return `Corrija este erro da aplicação InvestIQ (FastAPI + Next.js):\n\n${header}${msg}${tb}\n\nForneça o código corrigido com explicação da causa raiz e da solução aplicada.`;
  }
  return `Refatore o código da aplicação InvestIQ para prevenir este tipo de erro:\n\n${header}${msg}${tb}\n\nSugira melhorias de código, tratamento de exceções e boas práticas para tornar o sistema mais robusto.`;
}

function CopyButton({ label, text }: { label: string; text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <button
      onClick={copy}
      className="px-3 py-1 text-xs rounded border border-border bg-background hover:bg-muted transition-colors font-medium"
    >
      {copied ? "Copiado!" : label}
    </button>
  );
}

function LogRow({
  log,
  onDelete,
}: {
  log: LogEntry;
  onDelete: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr
        className="border-b border-border hover:bg-muted/40 cursor-pointer select-none"
        onClick={() => setExpanded((v) => !v)}
      >
        <td className="px-4 py-3 w-24">
          <span
            className={`inline-block text-xs font-semibold px-2 py-0.5 rounded-full ${LEVEL_BADGE[log.level] ?? LEVEL_BADGE.DEBUG}`}
          >
            {log.level}
          </span>
        </td>
        <td className="px-4 py-3 text-sm text-foreground font-medium truncate max-w-xs">
          {log.title}
        </td>
        <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">
          {log.module ?? "—"}
        </td>
        <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">
          {formatDate(log.created_at)}
        </td>
        <td className="px-4 py-3 text-right">
          <span className="text-xs text-muted-foreground">{expanded ? "▲" : "▼"}</span>
        </td>
      </tr>

      {expanded && (
        <tr className="bg-muted/20 border-b border-border">
          <td colSpan={5} className="px-4 pb-4 pt-2">
            <div className="space-y-3">
              {/* Meta */}
              <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                {log.request_method && log.request_path && (
                  <span>
                    <span className="font-semibold">Rota:</span>{" "}
                    {log.request_method} {log.request_path}
                  </span>
                )}
                {log.user_id && (
                  <span>
                    <span className="font-semibold">User:</span> {log.user_id}
                  </span>
                )}
              </div>

              {/* Message */}
              {log.message && log.message !== log.title && (
                <div>
                  <p className="text-xs font-semibold text-muted-foreground mb-1">Mensagem</p>
                  <p className="text-sm text-foreground whitespace-pre-wrap">{log.message}</p>
                </div>
              )}

              {/* Traceback */}
              {log.traceback && (
                <div>
                  <p className="text-xs font-semibold text-muted-foreground mb-1">Traceback</p>
                  <pre className="text-xs bg-background border border-border rounded p-3 overflow-x-auto whitespace-pre-wrap text-red-600 font-mono max-h-64 overflow-y-auto">
                    {log.traceback}
                  </pre>
                </div>
              )}

              {/* Extra JSON */}
              {log.extra && Object.keys(log.extra).length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-muted-foreground mb-1">Extra</p>
                  <pre className="text-xs bg-background border border-border rounded p-3 overflow-x-auto font-mono">
                    {JSON.stringify(log.extra, null, 2)}
                  </pre>
                </div>
              )}

              {/* Prompt buttons + delete */}
              <div className="flex items-center gap-2 pt-1 flex-wrap">
                <span className="text-xs text-muted-foreground font-semibold">Gerar prompt:</span>
                <CopyButton label="Analisar" text={buildPrompt("analyze", log)} />
                <CopyButton label="Corrigir" text={buildPrompt("fix", log)} />
                <CopyButton label="Refatorar" text={buildPrompt("refactor", log)} />
                <div className="ml-auto">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(log.id);
                    }}
                    className="px-3 py-1 text-xs rounded border border-red-200 text-red-600 hover:bg-red-50 transition-colors"
                  >
                    Remover
                  </button>
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

const FILTERS = ["ALL", "ERROR", "WARNING", "INFO"] as const;

export function LogsContent() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("ALL");
  const [clearing, setClearing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getLogs(filter === "ALL" ? undefined : filter);
      setLogs(data);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (id: string) => {
    await deleteLog(id);
    setLogs((prev) => prev.filter((l) => l.id !== id));
  };

  const handleClearAll = async () => {
    if (!confirm("Apagar todos os logs?")) return;
    setClearing(true);
    try {
      await clearAllLogs();
      setLogs([]);
    } finally {
      setClearing(false);
    }
  };

  const { sorted: sortedLogs, col, dir, toggle } = useSortedData(
    logs as Record<string, unknown>[],
    "created_at",
    "desc"
  );

  const errorCount = logs.filter((l) => l.level === "ERROR").length;
  const warnCount = logs.filter((l) => l.level === "WARNING").length;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold text-foreground">Logs do Sistema</h1>
          {errorCount > 0 && (
            <span className="text-xs bg-red-100 text-red-700 border border-red-200 px-2 py-0.5 rounded-full font-semibold">
              {errorCount} error{errorCount !== 1 ? "s" : ""}
            </span>
          )}
          {warnCount > 0 && (
            <span className="text-xs bg-yellow-100 text-yellow-700 border border-yellow-200 px-2 py-0.5 rounded-full font-semibold">
              {warnCount} warning{warnCount !== 1 ? "s" : ""}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            className="text-xs px-3 py-1.5 border border-border rounded hover:bg-muted transition-colors"
          >
            Atualizar
          </button>
          <button
            onClick={handleClearAll}
            disabled={clearing || logs.length === 0}
            className="text-xs px-3 py-1.5 border border-red-200 text-red-600 rounded hover:bg-red-50 transition-colors disabled:opacity-40"
          >
            {clearing ? "Limpando…" : "Limpar tudo"}
          </button>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 border-b border-border">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              filter === f
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center py-16 text-muted-foreground text-sm">
          Carregando…
        </div>
      ) : logs.length === 0 ? (
        <div className="flex items-center justify-center py-16 text-muted-foreground text-sm">
          Nenhum log encontrado.
        </div>
      ) : (
        <div className="rounded-lg border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 border-b border-border">
              <tr>
                <SortableHeader col="level" label="Nível" activeCol={col} dir={dir} onSort={toggle} className="px-4 py-2.5 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide w-24" />
                <SortableHeader col="title" label="Título" activeCol={col} dir={dir} onSort={toggle} className="px-4 py-2.5 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide" />
                <SortableHeader col="module" label="Módulo" activeCol={col} dir={dir} onSort={toggle} className="px-4 py-2.5 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide" />
                <SortableHeader col="created_at" label="Horário" activeCol={col} dir={dir} onSort={toggle} className="px-4 py-2.5 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide whitespace-nowrap" />
                <th className="w-8" />
              </tr>
            </thead>
            <tbody>
              {sortedLogs.map((log_) => {
                const log = log_ as LogEntry;
                return <LogRow key={log.id} log={log} onDelete={handleDelete} />;
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
