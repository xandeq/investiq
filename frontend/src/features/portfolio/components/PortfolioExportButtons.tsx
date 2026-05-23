"use client";
import { useState, useRef, useEffect } from "react";
import { FileCsv, FileXls, Printer, Copy, Check, X, CaretDown, DownloadSimple } from "@phosphor-icons/react";
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

const FORMAT_ICONS: Record<ExportFormat, React.ElementType> = {
  csv: FileCsv,
  xls: FileXls,
  pdf: Printer,
};

export function PortfolioExportButtons({ pnl }: PortfolioExportButtonsProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");
  const [exporting, setExporting] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

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
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setDropdownOpen((v) => !v)}
          disabled={exporting}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-zinc-200 bg-white hover:bg-zinc-50 text-zinc-700 active:scale-[0.97] transition-all duration-150 disabled:opacity-50 shadow-sm"
          title="Exportar carteira"
        >
          <DownloadSimple size={13} weight="bold" />
          {exporting ? "Exportando…" : "Exportar"}
          <CaretDown size={10} className="text-zinc-400 ml-0.5" />
        </button>

        {dropdownOpen && (
          <div className="absolute right-0 top-full mt-1 z-50 min-w-[160px] rounded-lg border border-zinc-200 bg-white shadow-lg py-1">
            {(["csv", "xls", "pdf"] as ExportFormat[]).map((fmt) => {
              const Icon = FORMAT_ICONS[fmt];
              return (
                <button
                  key={fmt}
                  onClick={() => handleExport(fmt)}
                  className="w-full text-left flex items-center gap-2 px-4 py-2 text-xs text-zinc-700 hover:bg-zinc-50 active:scale-[0.97] transition-all duration-150"
                >
                  <Icon size={14} className="text-zinc-400" />
                  <span>{FORMAT_LABELS[fmt]}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      <button
        onClick={handleCopy}
        disabled={copyState !== "idle"}
        title="Copiar para área de transferência (formato tabela)"
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border active:scale-[0.97] transition-all duration-150 shadow-sm ${
          copyState === "copied"
            ? "border-emerald-300 bg-emerald-50 text-emerald-700"
            : copyState === "error"
            ? "border-red-300 bg-red-50 text-red-700"
            : "border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50"
        }`}
      >
        {copyState === "copied" ? (
          <><Check size={12} weight="bold" /> Copiado!</>
        ) : copyState === "error" ? (
          <><X size={12} weight="bold" /> Erro</>
        ) : (
          <><Copy size={12} /> Copiar</>
        )}
      </button>
    </div>
  );
}
