"use client";
import { useState, useRef, useEffect } from "react";
import { PnLResponse } from "@/features/portfolio/types";
import {
  exportPortfolioCsv,
  exportPortfolioXls,
  exportPortfolioPdf,
  copyPortfolioToClipboard,
} from "@/features/portfolio/utils/portfolioExport";

interface PortfolioExportButtonsProps {
  pnl: PnLResponse;
}

type ExportFormat = "csv" | "xls" | "pdf";

const FORMAT_LABELS: Record<ExportFormat, string> = {
  csv: "CSV (.csv)",
  xls: "Excel (.xls)",
  pdf: "PDF (imprimir)",
};

const FORMAT_ICONS: Record<ExportFormat, string> = {
  csv: "📄",
  xls: "📊",
  pdf: "🖨️",
};

export function PortfolioExportButtons({ pnl }: PortfolioExportButtonsProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");
  const [exporting, setExporting] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    if (dropdownOpen) document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, [dropdownOpen]);

  async function handleExport(fmt: ExportFormat) {
    setDropdownOpen(false);
    setExporting(true);
    try {
      if (fmt === "csv") exportPortfolioCsv(pnl);
      else if (fmt === "xls") exportPortfolioXls(pnl);
      else if (fmt === "pdf") exportPortfolioPdf(pnl);
    } finally {
      setExporting(false);
    }
  }

  async function handleCopy() {
    try {
      const count = await copyPortfolioToClipboard(pnl);
      setCopyState("copied");
      setTimeout(() => setCopyState("idle"), 2000);
      void count;
    } catch {
      setCopyState("error");
      setTimeout(() => setCopyState("idle"), 2500);
    }
  }

  if (!pnl.positions.length) return null;

  return (
    <div className="flex items-center gap-2">
      {/* ── Export dropdown ── */}
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setDropdownOpen((v) => !v)}
          disabled={exporting}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-gray-200 bg-white hover:bg-gray-50 text-gray-700 transition-colors disabled:opacity-50 shadow-sm"
          title="Exportar carteira"
        >
          <span className="text-sm">↓</span>
          {exporting ? "Exportando…" : "Exportar"}
          <span className="text-[10px] text-gray-400 ml-0.5">▾</span>
        </button>

        {dropdownOpen && (
          <div className="absolute right-0 top-full mt-1 z-50 min-w-[160px] rounded-lg border border-gray-200 bg-white shadow-lg py-1">
            {(["csv", "xls", "pdf"] as ExportFormat[]).map((fmt) => (
              <button
                key={fmt}
                onClick={() => handleExport(fmt)}
                className="w-full text-left flex items-center gap-2 px-4 py-2 text-xs text-gray-700 hover:bg-gray-50 transition-colors"
              >
                <span>{FORMAT_ICONS[fmt]}</span>
                <span>{FORMAT_LABELS[fmt]}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ── Copy to clipboard ── */}
      <button
        onClick={handleCopy}
        disabled={copyState !== "idle"}
        title="Copiar para área de transferência (formato tabela)"
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border transition-colors shadow-sm ${
          copyState === "copied"
            ? "border-emerald-300 bg-emerald-50 text-emerald-700"
            : copyState === "error"
            ? "border-red-300 bg-red-50 text-red-700"
            : "border-gray-200 bg-white text-gray-700 hover:bg-gray-50"
        }`}
      >
        {copyState === "copied" ? (
          <>✓ Copiado!</>
        ) : copyState === "error" ? (
          <>✗ Erro</>
        ) : (
          <>
            <span className="text-sm">⧉</span>
            Copiar
          </>
        )}
      </button>
    </div>
  );
}
