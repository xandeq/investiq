"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { Check } from "@phosphor-icons/react";
import { useProfile, useUpsertProfile } from "@/features/profile/hooks/useProfile";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";
import type { InvestorProfileUpsert } from "@/features/profile/types";
import { EmailPrefsCard } from "./EmailPrefsCard";
import { AIModeCard } from "./AIModeCard";
import { TelegramCard } from "./TelegramCard";

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

const INPUT_CLS = "w-full rounded-md bg-zinc-100 px-3 py-2.5 text-sm border-2 border-transparent focus:outline-none focus:bg-white focus:border-blue-500 transition-all duration-200";

function Step1({ form, onChange }: { form: Partial<InvestorProfileUpsert>; onChange: (k: keyof InvestorProfileUpsert, v: unknown) => void }) {
  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-zinc-500">Dados básicos para contextualizar sua situação financeira.</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Idade</label>
          <input type="number" min={18} max={120} value={form.idade ?? ""} onChange={(e) => onChange("idade", e.target.value ? Number(e.target.value) : null)} placeholder="Ex: 35" className={INPUT_CLS} />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Renda mensal líquida (R$)</label>
          <input type="number" min={0} step="100" value={form.renda_mensal ?? ""} onChange={(e) => onChange("renda_mensal", e.target.value ? Number(e.target.value) : null)} placeholder="Ex: 8000" className={INPUT_CLS} />
        </div>
        <div className="flex flex-col gap-1 sm:col-span-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Patrimônio total investido (R$)</label>
          <input type="number" min={0} step="1000" value={form.patrimonio_total ?? ""} onChange={(e) => onChange("patrimonio_total", e.target.value ? Number(e.target.value) : null)} placeholder="Ex: 150000" className={INPUT_CLS} />
        </div>
      </div>
    </div>
  );
}

function Step2({ form, onChange }: { form: Partial<InvestorProfileUpsert>; onChange: (k: keyof InvestorProfileUpsert, v: unknown) => void }) {
  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-zinc-500">Qual é o seu principal objetivo de investimento?</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {Object.entries(OBJETIVO_LABELS).map(([key, label]) => (
          <button key={key} type="button" onClick={() => onChange("objetivo", key)}
            className={`rounded-md px-4 py-3 text-sm text-left active:scale-[0.97] transition-all duration-150 ${
              form.objetivo === key
                ? "bg-blue-500 text-white font-semibold"
                : "bg-zinc-100 hover:bg-zinc-200 font-medium"
            }`}>
            {label}
          </button>
        ))}
      </div>
      <div className="flex flex-col gap-1 mt-2">
        <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Horizonte de investimento (anos)</label>
        <input type="number" min={1} max={50} value={form.horizonte_anos ?? ""} onChange={(e) => onChange("horizonte_anos", e.target.value ? Number(e.target.value) : null)} placeholder="Ex: 20" className={`${INPUT_CLS} w-40`} />
      </div>
    </div>
  );
}

function Step3({ form, onChange }: { form: Partial<InvestorProfileUpsert>; onChange: (k: keyof InvestorProfileUpsert, v: unknown) => void }) {
  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-zinc-500">Como você reage a oscilações no valor da sua carteira?</p>
      <div className="flex flex-col gap-3">
        {Object.entries(RISCO_LABELS).map(([key, { label, desc }]) => (
          <button key={key} type="button" onClick={() => onChange("tolerancia_risco", key)}
            className={`rounded-md px-4 py-3 text-left active:scale-[0.97] transition-all duration-150 ${
              form.tolerancia_risco === key
                ? "bg-blue-500 text-white"
                : "bg-zinc-100 hover:bg-zinc-200"
            }`}>
            <p className={`text-sm font-semibold ${form.tolerancia_risco === key ? "text-white" : ""}`}>{label}</p>
            <p className={`text-xs mt-0.5 ${form.tolerancia_risco === key ? "text-blue-100" : "text-zinc-400"}`}>{desc}</p>
          </button>
        ))}
      </div>
      <div className="flex flex-col gap-1 mt-2">
        <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Alocação alvo em renda fixa (%)</label>
        <div className="flex items-center gap-3">
          <input type="range" min={0} max={100} step={5} value={form.percentual_renda_fixa_alvo ?? 30} onChange={(e) => onChange("percentual_renda_fixa_alvo", Number(e.target.value))} className="w-full accent-blue-500" />
          <span className="text-sm font-bold w-10 text-right">{form.percentual_renda_fixa_alvo ?? 30}%</span>
        </div>
        <p className="text-xs text-zinc-400">Renda fixa: {form.percentual_renda_fixa_alvo ?? 30}% · Renda variável: {100 - (form.percentual_renda_fixa_alvo ?? 30)}%</p>
      </div>
    </div>
  );
}

function ProfileSummary({ profile, onEdit }: { profile: ReturnType<typeof useProfile>["data"]; onEdit: () => void }) {
  if (!profile) return null;
  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-zinc-200 bg-white p-5">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-semibold">Perfil configurado</span>
          <span className="text-sm font-bold text-blue-500">{profile.completion_pct}%</span>
        </div>
        <div className="h-2 rounded-full bg-zinc-100 overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-blue-500"
            initial={{ width: 0 }}
            animate={{ width: `${profile.completion_pct}%` }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          />
        </div>
        {profile.completion_pct < 100 && (
          <p className="text-xs text-zinc-400 mt-2">
            Complete seu perfil para análises de IA mais personalizadas.
          </p>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {[
          { label: "Idade", value: profile.idade ? `${profile.idade} anos` : null },
          { label: "Renda mensal", value: fmtBRL(profile.renda_mensal) },
          { label: "Patrimônio total", value: fmtBRL(profile.patrimonio_total) },
          { label: "Objetivo", value: profile.objetivo ? OBJETIVO_LABELS[profile.objetivo] : null },
          { label: "Horizonte", value: profile.horizonte_anos ? `${profile.horizonte_anos} anos` : null },
          { label: "Tolerância ao risco", value: profile.tolerancia_risco ? RISCO_LABELS[profile.tolerancia_risco]?.label : null },
          { label: "Alvo renda fixa", value: profile.percentual_renda_fixa_alvo ? `${profile.percentual_renda_fixa_alvo}%` : null },
        ].map(({ label, value }, i) => (
          <motion.div
            key={label}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.22, delay: i * 0.04 }}
            className="rounded-md bg-zinc-50 border border-zinc-100 p-3"
          >
            <p className="text-xs font-semibold uppercase tracking-wider text-zinc-400">{label}</p>
            <p className="text-sm font-semibold mt-0.5 text-zinc-900">{value ?? "—"}</p>
          </motion.div>
        ))}
      </div>

      <button onClick={onEdit} className="px-4 py-2 text-sm rounded-md bg-zinc-100 hover:bg-zinc-200 font-medium hover:scale-105 active:scale-[0.97] transition-all duration-150">
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
    return (
      <div className="space-y-4 max-w-xl py-4">
        <ShimmerSkeleton className="h-8 w-48 rounded" />
        <ShimmerSkeleton className="h-24 w-full rounded-xl" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {[0,1,2,3,4,5].map(i => <ShimmerSkeleton key={i} className="h-14 rounded-md" />)}
        </div>
      </div>
    );
  }

  if (!showForm) {
    return (
      <div className="space-y-6 max-w-xl">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Meu Perfil de Investidor</h2>
          <p className="text-sm text-zinc-400 mt-1">Contexto usado pela IA para personalizar análises</p>
        </div>
        <ProfileSummary profile={profile} onEdit={handleStartEdit} />
        <AIModeCard />
        <EmailPrefsCard />
        <TelegramCard />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-xl">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">
          {profileExists ? "Editar Perfil" : "Configure seu Perfil de Investidor"}
        </h2>
        <p className="text-sm text-zinc-400 mt-1">
          Seu copiloto usa essas informações para personalizar análises de IA.
        </p>
      </div>

      {/* Step indicators */}
      <div className="flex items-center gap-2">
        {STEPS.map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            <motion.div
              initial={{ scale: 0.85 }}
              animate={{ scale: 1 }}
              transition={{ duration: 0.2, delay: i * 0.06 }}
              className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold active:scale-[0.97] transition-all duration-150 ${
                i < step ? "bg-blue-500 text-white" :
                i === step ? "bg-blue-500 text-white" :
                "bg-zinc-200 text-zinc-400"
              }`}
            >
              {i < step ? <Check size={12} weight="bold" /> : i + 1}
            </motion.div>
            <span className={`text-xs font-medium hidden sm:block ${i === step ? "text-zinc-900" : "text-zinc-400"}`}>{s}</span>
            {i < STEPS.length - 1 && <div className="h-px w-6 bg-zinc-200" />}
          </div>
        ))}
      </div>

      {/* Step content */}
      <div className="rounded-xl bg-zinc-50 border border-zinc-100 p-5">
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
          className="px-4 py-2 text-sm rounded-md bg-zinc-100 hover:bg-zinc-200 font-medium active:scale-[0.97] transition-all duration-150"
        >
          {step === 0 ? "Cancelar" : "Anterior"}
        </button>
        {step < STEPS.length - 1 ? (
          <button
            type="button"
            onClick={() => setStep((s) => s + 1)}
            className="px-4 py-2 text-sm rounded-md bg-blue-500 text-white hover:bg-blue-600 font-semibold hover:scale-105 active:scale-[0.97] transition-all duration-150"
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
