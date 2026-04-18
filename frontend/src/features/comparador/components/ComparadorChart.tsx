"use client";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  ResponsiveContainer,
} from "recharts";
import type { ProjectionPoint } from "../types";

interface Props {
  data: ProjectionPoint[];
  produtoRfLabel: string; // e.g. "CDB" | "LCI" | "Tesouro IPCA+" — from ComparadorContent
}

// BRL formatter for axis ticks and tooltip values (compact).
function formatBRL(value: number): string {
  if (!Number.isFinite(value)) return "—";
  return value.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  });
}

function formatBRLFull(value: number): string {
  if (!Number.isFinite(value)) return "—";
  return value.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function ComparadorChart({ data, produtoRfLabel }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-6 text-center text-sm text-gray-500">
        Sem dados para o gráfico.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="text-sm font-bold mb-3">Evolução do patrimônio (R$)</h3>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="mes"
            tick={{ fontSize: 11 }}
            label={{ value: "Meses", position: "insideBottom", offset: -4, style: { fontSize: 11 } }}
          />
          <YAxis
            tick={{ fontSize: 11 }}
            tickFormatter={formatBRL}
            width={80}
            domain={["auto", "auto"]}
          />
          <Tooltip
            formatter={(value: number, name: string) => [formatBRLFull(value), name]}
            labelFormatter={(label: number) => `Mês ${label}`}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line
            type="monotone"
            dataKey="produto_rf"
            name={produtoRfLabel}
            stroke="#2563eb"
            strokeWidth={2.5}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="cdi"
            name="CDI"
            stroke="#64748b"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="selic"
            name="SELIC"
            stroke="#10b981"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="ipca"
            name="IPCA+"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
      <p className="mt-2 text-xs text-gray-400 text-center">
        Projeção linear com taxa líquida constante — estimativa educacional.
      </p>
    </div>
  );
}
