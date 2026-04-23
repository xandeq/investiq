"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Sparkles, Zap } from "lucide-react";

interface AIModeData {
  ai_mode: "standard" | "ultra";
  plan: string;
}

async function fetchAIMode(): Promise<AIModeData> {
  return apiClient<AIModeData>("/profile/ai-mode");
}

async function updateAIMode(ai_mode: string): Promise<AIModeData> {
  return apiClient<AIModeData>("/profile/ai-mode", {
    method: "PATCH",
    body: JSON.stringify({ ai_mode }),
  });
}

export function AIModeCard() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery<AIModeData>({
    queryKey: ["profile", "ai-mode"],
    queryFn: fetchAIMode,
    staleTime: 60_000,
    retry: false,
  });

  const mutation = useMutation({
    mutationFn: (mode: string) => updateAIMode(mode),
    onSuccess: (updated) => {
      queryClient.setQueryData(["profile", "ai-mode"], updated);
    },
  });

  const isUltra = data?.ai_mode === "ultra";
  const isPro = data?.plan === "pro";

  const toggle = () => {
    if (!data || !isPro) return;
    mutation.mutate(isUltra ? "standard" : "ultra");
  };

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="h-4 w-4 text-blue-500" />
        <h3 className="text-sm font-semibold text-gray-900">Modo de Análise IA</h3>
        {isUltra && (
          <span className="ml-auto inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-600">
            <Zap className="h-3 w-3" /> Ultra ativo
          </span>
        )}
      </div>

      {isLoading ? (
        <div className="h-20 rounded-lg bg-gray-100 animate-pulse" />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            {/* Standard option */}
            <button
              type="button"
              onClick={() => isPro && !isUltra ? undefined : isPro ? mutation.mutate("standard") : undefined}
              disabled={mutation.isPending || !isPro}
              className={`rounded-lg border-2 p-3 text-left transition-all duration-200 disabled:opacity-60
                ${!isUltra
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200 bg-white hover:border-gray-300"
                }`}
            >
              <p className="text-sm font-semibold text-gray-900">Standard</p>
              <p className="text-xs text-gray-500 mt-1">GPT-4o-mini · DeepSeek</p>
              <p className="text-xs text-gray-400 mt-1">Rápido e econômico</p>
            </button>

            {/* Ultra option */}
            <button
              type="button"
              onClick={() => isPro && !isUltra ? mutation.mutate("ultra") : isPro ? undefined : undefined}
              disabled={mutation.isPending || !isPro}
              className={`rounded-lg border-2 p-3 text-left transition-all duration-200 disabled:opacity-60
                ${isUltra
                  ? "border-blue-500 bg-blue-50"
                  : isPro
                    ? "border-gray-200 bg-white hover:border-blue-300 hover:bg-blue-50/30"
                    : "border-gray-100 bg-gray-50 cursor-not-allowed"
                }`}
            >
              <div className="flex items-center gap-1">
                <p className="text-sm font-semibold text-gray-900">Ultra</p>
                {!isPro && (
                  <span className="ml-1 rounded-full bg-amber-100 px-1.5 py-0.5 text-xs font-semibold text-amber-700">Pro</span>
                )}
              </div>
              <p className="text-xs text-gray-500 mt-1">Claude · GPT-4o · Perplexity</p>
              <p className="text-xs text-gray-400 mt-1">Máxima qualidade</p>
            </button>
          </div>

          {isUltra && (
            <div className="rounded-lg bg-blue-50 px-3 py-2.5 text-xs text-blue-700 leading-relaxed">
              <strong>Ultra ativo:</strong> suas análises usam Claude Sonnet → GPT-4o → Perplexity Sonar Pro → DeepSeek-R1 → Gemini 2.5 Pro, com fallback automático.
            </div>
          )}

          {!isPro && (
            <p className="text-xs text-gray-500 bg-gray-50 rounded-lg px-3 py-2.5">
              Modo Ultra disponível no <strong>Plano Pro</strong>.{" "}
              <a href="/planos" className="text-blue-500 hover:underline font-medium">Fazer upgrade</a>
            </p>
          )}

          {mutation.isError && (
            <p className="text-xs text-red-600 bg-red-50 rounded px-3 py-2">
              Erro ao salvar. Tente novamente.
            </p>
          )}

          {mutation.isSuccess && (
            <p className="text-xs text-emerald-700 bg-emerald-50 rounded px-3 py-2">
              Modo {isUltra ? "Ultra" : "Standard"} ativado.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
