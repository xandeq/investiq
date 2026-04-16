"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Mail, BellOff } from "lucide-react";

interface EmailPrefs {
  email_digest_enabled: boolean;
}

async function fetchEmailPrefs(): Promise<EmailPrefs> {
  return apiClient<EmailPrefs>("/profile/email-prefs");
}

async function updateEmailPrefs(prefs: EmailPrefs): Promise<EmailPrefs> {
  return apiClient<EmailPrefs>("/profile/email-prefs", {
    method: "PATCH",
    body: JSON.stringify(prefs),
  });
}

export function EmailPrefsCard() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery<EmailPrefs>({
    queryKey: ["profile", "email-prefs"],
    queryFn: fetchEmailPrefs,
    staleTime: 60_000,
    retry: false,
  });

  const mutation = useMutation({
    mutationFn: updateEmailPrefs,
    onSuccess: (updated) => {
      queryClient.setQueryData(["profile", "email-prefs"], updated);
    },
  });

  const toggle = () => {
    if (!data) return;
    mutation.mutate({ email_digest_enabled: !data.email_digest_enabled });
  };

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="flex items-center gap-2 mb-4">
        <Mail className="h-4 w-4 text-gray-500" />
        <h3 className="text-sm font-semibold text-gray-900">Preferências de Email</h3>
      </div>

      {isLoading ? (
        <div className="h-12 rounded-lg bg-gray-100 animate-pulse" />
      ) : (
        <div className="space-y-3">
          {/* Weekly digest toggle */}
          <div className="flex items-center justify-between gap-4 py-2">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">Resumo semanal da carteira</p>
              <p className="text-xs text-gray-500 mt-0.5">
                Receba toda segunda-feira um resumo do patrimônio, variação da semana e maiores movimentações.
              </p>
            </div>
            <button
              onClick={toggle}
              disabled={mutation.isPending}
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent
                transition-colors duration-200 ease-in-out focus:outline-none
                disabled:opacity-60 disabled:cursor-not-allowed
                ${data?.email_digest_enabled ? "bg-blue-500" : "bg-gray-200"}`}
              role="switch"
              aria-checked={data?.email_digest_enabled ?? true}
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow-sm
                  transform transition duration-200 ease-in-out
                  ${data?.email_digest_enabled ? "translate-x-5" : "translate-x-0"}`}
              />
            </button>
          </div>

          {/* Note on price alerts */}
          <div className="flex items-start gap-2 rounded-lg bg-gray-50 px-3 py-2.5">
            <BellOff className="h-3.5 w-3.5 text-gray-400 mt-0.5 shrink-0" />
            <p className="text-xs text-gray-500 leading-relaxed">
              Emails de <strong>alerta de preço</strong> são transacionais e sempre enviados quando um alerta dispara.
              Para remover um alerta, acesse a Watchlist e limpe o campo "Alerta".
            </p>
          </div>

          {mutation.isError && (
            <p className="text-xs text-red-600 bg-red-50 rounded px-3 py-2">
              Erro ao salvar preferências. Tente novamente.
            </p>
          )}

          {mutation.isSuccess && (
            <p className="text-xs text-emerald-700 bg-emerald-50 rounded px-3 py-2">
              Preferências salvas.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
