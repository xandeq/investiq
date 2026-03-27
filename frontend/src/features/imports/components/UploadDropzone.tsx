"use client";
import { useState, useRef } from "react";
import { ImportJob } from "../types";
import { uploadPdf, uploadCsv, uploadXlsx, getCsvTemplateUrl } from "../api";
import { isLimitError } from "@/lib/api-client";
import { UpgradeBanner } from "@/features/billing/components/UpgradeBanner";
import { useUsage } from "@/features/billing/hooks/useUsage";

interface UploadDropzoneProps {
  onJobCreated: (job: ImportJob) => void;
}

type TabId = "pdf" | "csv" | "json" | "b3" | "xp" | "clear";

const TABS: { id: TabId; label: string; sub: string }[] = [
  { id: "pdf",   label: "PDF",            sub: "Nota de corretagem" },
  { id: "csv",   label: "CSV",            sub: "Planilha InvestIQ" },
  { id: "json",  label: "JSON",           sub: "Formato estruturado" },
  { id: "b3",    label: "B3 Investidor",  sub: "Canal Eletrônico" },
  { id: "xp",    label: "XP",            sub: "Extrato XP" },
  { id: "clear", label: "Clear",          sub: "Extrato Clear" },
];

const JSON_EXAMPLE = `[
  {
    "data": "2024-01-15",
    "ticker": "PETR4",
    "tipo": "compra",
    "quantidade": 100,
    "preco": 36.50,
    "taxas": 4.90,
    "corretora": "Clear"
  },
  {
    "data": "2024-02-03",
    "ticker": "XPML11",
    "tipo": "compra",
    "quantidade": 10,
    "preco": 98.20,
    "taxas": 0,
    "corretora": "XP"
  }
]`;

function jsonToCsvBlob(rows: Record<string, unknown>[]): Blob {
  const typeMap: Record<string, string> = {
    compra: "buy", venda: "sell", dividendo: "dividend",
    jscp: "jscp", amortizacao: "amortization", amortização: "amortization",
  };
  const today = new Date().toISOString().split("T")[0];
  const headers = ["ticker","asset_class","transaction_type","transaction_date","quantity","unit_price","brokerage_fee","irrf_withheld","notes"];
  const lines = [
    headers.join(","),
    ...rows.map((r) => {
      const ticker = String(r.ticker ?? "").toUpperCase();
      const assetClass = r.asset_class ?? (ticker.match(/11$/) ? "FII" : "acao");
      const tipo = String(r.tipo ?? r.transaction_type ?? "compra").toLowerCase();
      const txnType = typeMap[tipo] ?? "buy";
      const date = r.data ?? r.date ?? r.transaction_date ?? today;
      const qty = r.quantidade ?? r.quantity ?? 0;
      const price = r.preco ?? r.price ?? r.unit_price ?? 0;
      const fees = r.taxas ?? r.brokerage_fee ?? 0;
      const irrf = r.irrf ?? r.irrf_withheld ?? 0;
      const notes = String(r.corretora ?? r.notes ?? "").replace(/,/g, " ");
      return [ticker, assetClass, txnType, date, qty, price, fees, irrf, notes].join(",");
    }),
  ];
  return new Blob([lines.join("\n")], { type: "text/csv" });
}

function GuideStep({ n, text }: { n: number; text: string }) {
  return (
    <div className="flex gap-3">
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
        {n}
      </span>
      <p className="text-sm text-muted-foreground leading-snug pt-0.5">{text}</p>
    </div>
  );
}

function UploadArea({
  accept,
  label,
  uploading,
  onChange,
}: {
  accept: string;
  label: string;
  uploading: boolean;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}) {
  return (
    <label className="block mt-4 cursor-pointer">
      <div className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-6 text-center hover:border-primary/50 hover:bg-muted/20 transition-colors">
        {uploading ? (
          <div className="flex flex-col items-center gap-2">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <span className="text-sm text-muted-foreground">Enviando...</span>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-1.5">
            <svg className="h-8 w-8 text-muted-foreground/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="text-sm font-medium">{label}</p>
          </div>
        )}
      </div>
      <input type="file" accept={accept} className="sr-only" disabled={uploading} onChange={onChange} />
    </label>
  );
}

export function UploadDropzone({ onJobCreated }: UploadDropzoneProps) {
  const [activeTab, setActiveTab] = useState<TabId>("pdf");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [limitError, setLimitError] = useState<{ message: string; upgradeUrl: string } | null>(null);
  const [jsonPasteText, setJsonPasteText] = useState("");
  const { usage } = useUsage();

  async function handleUpload(file: File, type: "pdf" | "csv" | "xlsx") {
    setUploading(true);
    setError(null);
    setLimitError(null);
    try {
      const job = type === "pdf"
        ? await uploadPdf(file)
        : type === "xlsx"
        ? await uploadXlsx(file)
        : await uploadCsv(file);
      onJobCreated(job);
    } catch (err) {
      if (isLimitError(err)) {
        setLimitError({ message: err.message, upgradeUrl: err.upgradeUrl });
      } else {
        setError(err instanceof Error ? err.message : "Falha ao enviar arquivo");
      }
    } finally {
      setUploading(false);
    }
  }

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>, type: "pdf" | "csv" | "xlsx") {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    handleUpload(file, type);
  }

  async function handleJsonInput(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    setError(null);
    setLimitError(null);
    try {
      const text = await file.text();
      await processJsonText(text, file.name.replace(/\.json$/, ".csv"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao processar JSON");
      setUploading(false);
    }
  }

  async function processJsonText(text: string, filename = "colado.csv") {
    setError(null);
    setLimitError(null);
    try {
      const parsed = JSON.parse(text);
      const rows: Record<string, unknown>[] = Array.isArray(parsed)
        ? parsed
        : parsed.transacoes ?? parsed.data ?? [];
      if (!rows.length) throw new Error("Nenhuma transação encontrada no JSON");
      const csvBlob = jsonToCsvBlob(rows);
      const csvFile = new File([csvBlob], filename, { type: "text/csv" });
      await handleUpload(csvFile, "csv");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao processar JSON");
      setUploading(false);
    }
  }

  async function handleJsonPasteSubmit() {
    if (!jsonPasteText.trim()) {
      setError("Cole o JSON acima antes de enviar");
      return;
    }
    await processJsonText(jsonPasteText.trim(), "colado.csv");
  }

  return (
    <div className="rounded-lg border bg-card p-6">
      <h2 className="text-lg font-semibold mb-4">Importar Transações</h2>

      {/* Usage bar */}
      {usage && usage.plan === "free" && (
        <div className="mb-4 space-y-1">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Importações este mês</span>
            <span>{usage.imports_this_month}/{usage.imports_limit}</span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${Math.min((usage.imports_this_month / usage.imports_limit) * 100, 100)}%` }}
            />
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex flex-wrap gap-1 mb-6 border-b">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => { setActiveTab(t.id); setError(null); setLimitError(null); }}
            className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === t.id
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <span>{t.label}</span>
            <span className="hidden sm:inline text-xs text-muted-foreground ml-1">· {t.sub}</span>
          </button>
        ))}
      </div>

      {/* PDF Tab */}
      {activeTab === "pdf" && (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Envie sua nota de corretagem em PDF. Suporte para <strong>Clear, XP, BTG, Rico, Nubank e outras</strong>.
          </p>
          <UploadArea accept=".pdf,application/pdf" label="Clique para enviar PDF" uploading={uploading}
            onChange={(e) => handleFileInput(e, "pdf")} />
        </div>
      )}

      {/* CSV Tab */}
      {activeTab === "csv" && (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Preencha o template e envie. Ideal para importar histórico completo de uma vez.
          </p>
          <UploadArea accept=".csv,text/csv" label="Clique para enviar CSV" uploading={uploading}
            onChange={(e) => handleFileInput(e, "csv")} />
          <div className="text-center">
            <a href={getCsvTemplateUrl()} download="template_investiq.csv"
              className="text-sm text-primary hover:underline">
              Baixar template CSV
            </a>
          </div>
        </div>
      )}

      {/* JSON Tab */}
      {activeTab === "json" && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Envie um arquivo <code className="bg-muted px-1 rounded text-xs">.json</code> ou cole o JSON diretamente.
            O conteúdo é convertido automaticamente para o formato InvestIQ.
          </p>
          <div className="rounded-md bg-muted/50 p-3">
            <p className="text-xs font-semibold text-muted-foreground mb-2">Formato esperado:</p>
            <pre className="text-xs text-foreground overflow-x-auto whitespace-pre">{JSON_EXAMPLE}</pre>
          </div>
          <div className="text-xs text-muted-foreground space-y-1">
            <p><strong>tipo:</strong> <code>compra</code> ou <code>venda</code></p>
            <p><strong>taxas:</strong> soma de corretagem + emolumentos (pode ser 0)</p>
            <p><strong>Também aceito:</strong> objeto com chave <code>transacoes</code> ou <code>data</code></p>
          </div>

          {/* Paste area */}
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Colar JSON</p>
            <textarea
              className="w-full h-32 rounded-md border bg-muted/30 px-3 py-2 text-xs font-mono text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/50 resize-y"
              placeholder={`Cole seu JSON aqui...\n[\n  { "data": "2024-01-15", "ticker": "PETR4", ... }\n]`}
              value={jsonPasteText}
              onChange={(e) => setJsonPasteText(e.target.value)}
              disabled={uploading}
            />
            <button
              onClick={handleJsonPasteSubmit}
              disabled={uploading || !jsonPasteText.trim()}
              className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {uploading ? "Enviando..." : "Importar JSON colado"}
            </button>
          </div>

          <div className="relative flex items-center gap-2 text-xs text-muted-foreground">
            <div className="flex-1 border-t" />
            <span>ou envie o arquivo</span>
            <div className="flex-1 border-t" />
          </div>

          <UploadArea accept=".json,application/json" label="Clique para enviar arquivo JSON" uploading={uploading}
            onChange={handleJsonInput} />
        </div>
      )}

      {/* B3 Tab */}
      {activeTab === "b3" && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            O portal B3 consolida posições de <strong>todas as corretoras</strong> (XP, Clear, BTG, etc.) em um só lugar.
          </p>
          <div className="space-y-2.5">
            <GuideStep n={1} text="Acesse investidor.b3.com.br e faça login com sua conta gov.br" />
            <GuideStep n={2} text="No menu, vá em Extrato → Negociação → Movimentações" />
            <GuideStep n={3} text="Selecione o período desejado e clique em Exportar → Excel ou CSV" />
            <GuideStep n={4} text="Renomeie as colunas conforme o template InvestIQ e importe abaixo" />
          </div>
          <div className="rounded-md bg-blue-50 border border-blue-100 px-3 py-2 text-xs text-blue-700">
            Dica: baixe o template CSV para ver as colunas esperadas antes de ajustar o arquivo da B3.
          </div>
          <UploadArea accept=".csv,text/csv,.xlsx" label="Enviar extrato da B3 (CSV / Excel)" uploading={uploading}
            onChange={(e) => handleFileInput(e, "csv")} />
          <div className="text-center">
            <a href={getCsvTemplateUrl()} download="template_investiq.csv"
              className="text-sm text-primary hover:underline">
              Baixar template CSV
            </a>
          </div>
        </div>
      )}

      {/* XP Tab */}
      {activeTab === "xp" && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Exporte suas notas de corretagem ou extrato diretamente do portal XP.
          </p>
          <div className="space-y-2.5">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Opção 1 — Nota de corretagem (PDF)</p>
            <GuideStep n={1} text="Acesse portal.xpi.com.br e faça login" />
            <GuideStep n={2} text="Vá em Extrato → Notas de Corretagem" />
            <GuideStep n={3} text="Selecione o período e baixe o PDF" />
            <GuideStep n={4} text="Envie o PDF abaixo — o InvestIQ extrai as transações automaticamente" />
          </div>
          <UploadArea accept=".pdf,application/pdf" label="Enviar nota de corretagem XP (PDF)" uploading={uploading}
            onChange={(e) => handleFileInput(e, "pdf")} />

          <div className="border-t pt-4 space-y-2.5">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Opção 2 — Posição consolidada (CSV)</p>
            <GuideStep n={1} text="No portal XP, vá em Minha Conta → Extrato → Posição Consolidada" />
            <GuideStep n={2} text="Exporte para Excel, ajuste as colunas conforme o template e envie como CSV" />
          </div>
          <UploadArea accept=".csv,text/csv" label="Enviar extrato XP (CSV)" uploading={uploading}
            onChange={(e) => handleFileInput(e, "csv")} />
        </div>
      )}

      {/* Clear Tab */}
      {activeTab === "clear" && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Importe sua carteira Clear via nota de corretagem (PDF) ou posição consolidada (XLSX).
          </p>

          <div className="space-y-2.5">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Opção 1 — Posição consolidada (XLSX)</p>
            <GuideStep n={1} text="Acesse clear.com.br/plataforma e faça login" />
            <GuideStep n={2} text="Vá em Extrato → Posição Detalhada" />
            <GuideStep n={3} text="Clique em Exportar → Excel (.xlsx)" />
            <GuideStep n={4} text="Envie o arquivo PosicaoDetalhada.xlsx abaixo" />
          </div>
          <div className="rounded-md bg-amber-50 border border-amber-100 px-3 py-2 text-xs text-amber-700">
            <strong>Atenção:</strong> a posição consolidada é um snapshot do dia, não histórico de transações.
            Cada ativo será importado como uma compra única pelo preço médio.
          </div>
          <UploadArea accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" label="Enviar PosicaoDetalhada.xlsx (Clear)" uploading={uploading}
            onChange={(e) => handleFileInput(e, "xlsx")} />

          <div className="border-t pt-4 space-y-2.5">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Opção 2 — Nota de corretagem (PDF)</p>
            <GuideStep n={1} text="No portal Clear, vá em Extrato → Notas de Corretagem" />
            <GuideStep n={2} text="Selecione o período e baixe o PDF" />
            <GuideStep n={3} text="Envie o PDF abaixo — o InvestIQ extrai as transações automaticamente" />
          </div>
          <UploadArea accept=".pdf,application/pdf" label="Enviar nota de corretagem Clear (PDF)" uploading={uploading}
            onChange={(e) => handleFileInput(e, "pdf")} />
        </div>
      )}

      {/* Errors */}
      {limitError && (
        <div className="mt-3">
          <UpgradeBanner message={limitError.message} upgradeUrl={limitError.upgradeUrl} />
        </div>
      )}
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
    </div>
  );
}
