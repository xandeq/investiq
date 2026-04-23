"use client";
import { useState } from "react";
import { useProfile, useUpsertProfile } from "@/features/profile/hooks/useProfile";
import type { InvestorProfileUpsert } from "@/features/profile/types";
import { EmailPrefsCard } from "./EmailPrefsCard";
import { AIModeCard } from "./AIModeCard";

const OBJETIVO_LABELS: Record<string, string> = {
  aposentadoria: "Aposentadoria",
  renda_passiva: "Renda Passiva",
  crescimento: "Crescimento de Patrimônio",
  reserva: "Reserva de Emergência",
};

const RISCO_LABELS: Record<string, { label: string; desc: string }> = {
  conservador: { label: "Conservador", desc: "Prefiro segurança. Aceito retornos menores para dormir tranquilo." },
  moderado: { label: "Moderado", desc: "Equilíbrio entre risco e retorno. Aceito oscilações razoáveis." },
  arrojado: { label: "Arrojado", desc: "Busco máximo retorno. Aceito volatilidade no curto prazo." },
};

const STEPS = ["Dados pessoais", "Objetivo", "Risco"];

function fmtBRL(v: string | null) {
  if (!v) return "—";
  return Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

const INPUT_CLS = "w-full rounded-md bg-gray-100 px-3 py-2.5 text-sm border-2 border-transparent focus:outline-none focus:bg-white focus:border-blue-500 transition-all duration-200";

function Step1({ form, onChange }: { form: Partial<InvestorProfileUpsert>; onChange: (k: keyof InvestorProfileUpsert, v: unknown) => void }) {
  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">Dados básicos para contextualizar sua situação financeira.</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Idade</label>
          <input type="number" min={18} max={120} value={form.idade ?? ""} onChange={(e) => onChange("idade", e.target.value ? Number(e.target.value) : null)} placeholder="Ex: 35" className={INPUT_CLS} />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Renda mensal líquida (R$)</label>
          <input type="number" min={0} step="100" value={form.renda_mensal ?? ""} onChange={(e) => onChange("renda_mensal", e.target.value ? Number(e.target.value) : null)} placeholder="Ex: 8000" className={INPUT_CLS} />
        </div>
        <div className="flex flex-col gap-1 sm:col-span-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Patrimônio total investido (R$)</label>
          <input type="number" min={0} step="1000" value={form.patrimonio_total ?? ""} onChange={(e) => onChange("patrimonio_total", e.target.value ? Number(e.target.value) : null)} placeholder="Ex: 150000" className={INPUT_CLS} />
        </div>
      </div>
    </div>
  );
}

function Step2({ form, onChange }: { form: Partial<InvestorProfileUpsert>; onChange: (k: keyof InvestorProfileUpsert, v: unknown) => void }) {
  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">Qual é o seu principal objetivo de investimento?</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {Object.entries(OBJETIVO_LABELS).map(([key, label]) => (
          <button key={key} type="button" onClick={() => onChange("objetivo", key)}
            className={`rounded-md px-4 py-3 text-sm text-left transition-all duration-200 ${
              form.objetivo === key
                ? "bg-blue-500 text-white font-semibold"
                : "bg-gray-100 hover:bg-gray-200 font-medium"
            }`}>
            {label}
          </button>
        ))}
      </div>
      <div className="flex flex-col gap-1 mt-2">
        <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Horizonte de investimento (anos)</label>
        <input type="number" min={1} max={50} value={form.horizonte_anos ?? ""} onChange={(e) => onChange("horizonte_anos", e.target.value ? Number(e.target.value) : null)} placeholder="Ex: 20" className={`${INPUT_CLS} w-40`} />
      </div>
    </div>
  );
}

function Step3({ form, onChange }: { form: Partial<InvestorProfileUpsert>; onChange: (k: keyof InvestorProfileUpsert, v: unknown) => void }) {
  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">Como você reage a oscilações no valor da sua carteira?</p>
      <div className="flex flex-col gap-3">
        {Object.entries(RISCO_LABELS).map(([key, { label, desc }]) => (
          <button key={key} type="button" onClick={() => onChange("tolerancia_risco", key)}
            className={`rounded-md px-4 py-3 text-left transition-all duration-200 ${
              form.tolerancia_risco === key
                ? "bg-blue-500 text-white"
                : "bg-gray-100 hover:bg-gray-200"
            }`}>
            <p className={`text-sm font-semibold ${form.tolerancia_risco === key ? "text-white" : ""}`}>{label}</p>
            <p className={`text-xs mt-0.5 ${form.tolerancia_risco === key ? "text-blue-100" : "text-muted-foreground"}`}>{desc}</p>
          </button>
        ))}
      </div>
      <div className="flex flex-col gap-1 mt-2">
        <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Alocação alvo em renda fixa (%)</label>
        <div className="flex items-center gap-3">
          <input type="range" min={0} max={100} step={5} value={form.percentual_renda_fixa_alvo ?? 30} onChange={(e) => onChange("percentual_renda_fixa_alvo", Number(e.target.value))} className="w-full accent-blue-500" />
          <span className="text-sm font-bold w-10 text-right">{form.percentual_renda_fixa_alvo ?? 30}%</span>
        </div>
        <p className="text-xs text-muted-foreground">Renda fixa: {form.percentual_renda_fixa_alvo ?? 30}% · Renda variável: {100 - (form.percentual_renda_fixa_alvo ?? 30)}%</p>
      </div>
    </div>
  );
}

function ProfileSummary({ profile, onEdit }: { profile: ReturnType<typeof useProfile>["data"]; onEdit: () => void }) {
  if (!profile) return null;
  return (
    <div className="space-y-6">
      {/* Completion */}
      <div className="rounded-lg bg-gray-100 p-5">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-semibold">Perfil configurado</span>
          <span className="text-sm font-bold text-blue-500">{profile.completion_pct}%</span>
        </div>
        <div className="h-2 rounded-full bg-gray-200 overflow-hidden">
          <div className="h-full rounded-full bg-blue-500 transition-all duration-500" style={{ width: `${profile.completion_pct}%` }} />
        </div>
        {profile.completion_pct < 100 && (
          <p className="text-xs text-muted-foreground mt-2">
            Complete seu perfil para análises de IA mais personalizadas.
          </p>
        )}
      </div>

      {/* Data */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {[
          { label: "Idade", value: profile.idade ? `${profile.idade} anos` : null },
          { label: "Renda mensal", value: fmtBRL(profile.renda_mensal) },
          { label: "Patrimônio total", value: fmtBRL(profile.patrimonio_total) },
          { label: "Objetivo", value: profile.objetivo ? OBJETIVO_LABELS[profile.objetivo] : null },
          { label: "Horizonte", value: profile.horizonte_anos ? `${profile.horizonte_anos} anos` : null },
          { label: "Tolerância ao risco", value: profile.tolerancia_risco ? RISCO_LABELS[profile.tolerancia_risco]?.label : null },
          { label: "Alvo renda fixa", value: profile.percentual_renda_fixa_alvo ? `${profile.percentual_renda_fixa_alvo}%` : null },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-md bg-gray-100 p-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</p>
            <p className="text-sm font-semibold mt-0.5">{value ?? "—"}</p>
          </div>
        ))}
      </div>

      <button onClick={onEdit} className="px-4 py-2 text-sm rounded-md bg-gray-100 hover:bg-gray-200 font-medium transition-all duration-200 hover:scale-105">
        Editar perfil
      </button>
    </div>
  );
}

export function ProfileContent() {
  const { data: profile, isLoading, error } = useProfile();
  const upsertMut = useUpsertProfile();
  const [step, setStep] = useState(0);
  const [editing, setEditing] = useState(false);
  // Pre-seed percentual_renda_fixa_alvo so the slider always submits a value
  // even if the user never interacts with it (slider visually defaults to 30).
  const [form, setForm] = useState<Partial<InvestorProfileUpsert>>({ percentual_renda_fixa_alvo: 30 });
  const [saveError, setSaveError] = useState("");

  const profileExists = !!profile && !error;
  const showForm = editing || !profileExists;

  const handleChange = (k: keyof InvestorProfileUpsert, v: unknown) => {
    setForm((f) => ({ ...f, [k]: v }));
  };

  const handleStartEdit = () => {
    if (profile) {
      setForm({
        idade: profile.idade,
        renda_mensal: profile.renda_mensal ? Number(profile.renda_mensal) : null,
        patrimonio_total: profile.patrimonio_total ? Number(profile.patrimonio_total) : null,
        objetivo: profile.objetivo,
        horizonte_anos: profile.horizonte_anos,
        tolerancia_risco: profile.tolerancia_risco,
        // Default to 30 if null so the slider shows a meaningful value and
        // the field is always submitted (not null) when user reaches step 3.
        percentual_renda_fixa_alvo: profile.percentual_renda_fixa_alvo
          ? Number(profile.percentual_renda_fixa_alvo)
          : 30,
      });
    }
    setStep(0);
    setEditing(true);
  };

  const handleSave = async () => {
    setSaveError("");
    try {
      await upsertMut.mutateAsync(form);
      setEditing(false);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Erro ao salvar perfil");
    }
  };

  if (isLoading) {
    return <div className="text-sm text-muted-foreground py-8 text-center">Carregando...</div>;
  }

  if (!showForm) {
    return (
      <div className="space-y-6 max-w-xl">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Meu Perfil de Investidor</h2>
          <p className="text-sm text-muted-foreground mt-1">Contexto usado pela IA para personalizar análises</p>
        </div>
        <ProfileSummary profile={profile} onEdit={handleStartEdit} />
        <AIModeCard />
        <EmailPrefsCard />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-xl">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">
          {profileExists ? "Editar Perfil" : "Configure seu Perfil de Investidor"}
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Seu copiloto usa essas informações para personalizar análises de IA.
        </p>
      </div>

      {/* Step indicators */}
      <div className="flex items-center gap-2">
        {STEPS.map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-200 ${
              i < step ? "bg-blue-500 text-white" :
              i === step ? "bg-blue-500 text-white" :
              "bg-gray-200 text-muted-foreground"
            }`}>
              {i < step ? "✓" : i + 1}
            </div>
            <span className={`text-xs font-medium hidden sm:block ${i === step ? "text-foreground" : "text-muted-foreground"}`}>{s}</span>
            {i < STEPS.length - 1 && <div className="h-px w-6 bg-gray-200" />}
          </div>
        ))}
      </div>

      {/* Step content */}
      <div className="rounded-lg bg-gray-50 p-5">
        {step === 0 && <Step1 form={form} onChange={handleChange} />}
        {step === 1 && <Step2 form={form} onChange={handleChange} />}
        {step === 2 && <Step3 form={form} onChange={handleChange} />}
      </div>

      {saveError && (
        <p className="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2">{saveError}</p>
      )}

      {/* Navigation */}
      <div className="flex justify-between">
        <button
          type="button"
          onClick={() => {
            if (step === 0) { setEditing(false); }
            else setStep((s) => s - 1);
          }}
          className="px-4 py-2 text-sm rounded-md bg-gray-100 hover:bg-gray-200 font-medium transition-all duration-200"
        >
          {step === 0 ? "Cancelar" : "Anterior"}
        </button>
        {step < STEPS.length - 1 ? (
          <button
            type="button"
            onClick={() => setStep((s) => s + 1)}
            className="px-4 py-2 text-sm rounded-md bg-blue-500 text-white hover:bg-blue-600 font-semibold hover:scale-105 transition-all duration-200"
          >
            Próximo
          </button>
        ) : (
          <button
            type="button"
            onClick={handleSave}
            disabled={upsertMut.isPending}
            className="px-4 py-2 text-sm rounded-md bg-blue-500 text-white hover:bg-blue-600 font-semibold hover:scale-105 disabled:opacity-60 transition-all duration-200"
          >
            {upsertMut.isPending ? "Salvando..." : "Salvar perfil"}
          </button>
        )}
      </div>
    </div>
  );
}
