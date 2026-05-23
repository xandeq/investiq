"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChatCircle, Link, LinkBreak } from "@phosphor-icons/react";
import { ShimmerSkeleton } from "@/components/ui/ShimmerSkeleton";
import {
  getTelegramPrefs,
  updateTelegramPrefs,
  type TelegramPrefsData,
} from "@/features/profile/api";

const CHAT_ID_RE = /^-?\d{1,20}$/;

function maskChatId(id: string): string {
  if (id.length <= 4) return id;
  return "••••" + id.slice(-4);
}

interface ServerError {
  status?: number;
  detail?: { code?: string; message?: string; upgrade_url?: string } | string;
}

function getErrorKind(err: unknown): "requires_pro" | "invalid" | "other" {
  const e = err as ServerError & { message?: string; type?: string; code?: string };
  const type = e?.type ?? "";
  const code = e?.code ?? "";
  const msg = (e?.message || "").toLowerCase();
  const detail = e?.detail;
  const detailCode =
    typeof detail === "object" && detail !== null ? detail.code : undefined;

  if (
    type === "LIMIT" ||
    detailCode === "REQUIRES_PRO" ||
    code === "REQUIRES_PRO" ||
    msg.includes("requires_pro") ||
    msg.includes("plano pro")
  ) {
    return "requires_pro";
  }
  if (e?.status === 422 || msg.includes("422")) {
    return "invalid";
  }
  return "other";
}

export function TelegramCard() {
  const queryClient = useQueryClient();
  const [input, setInput] = useState("");
  const [clientError, setClientError] = useState<string | null>(null);

  const { data, isLoading } = useQuery<TelegramPrefsData>({
    queryKey: ["profile", "telegram"],
    queryFn: getTelegramPrefs,
    staleTime: 60_000,
    retry: false,
  });

  const mutation = useMutation({
    mutationFn: (chat_id: string | null) => updateTelegramPrefs(chat_id),
    onSuccess: (updated) => {
      queryClient.setQueryData(["profile", "telegram"], updated);
      setInput("");
      setClientError(null);
    },
  });

  const isConnected = !!data?.telegram_chat_id;
  const errKind = mutation.isError ? getErrorKind(mutation.error) : null;

  const handleConnect = () => {
    const trimmed = input.trim();
    if (!CHAT_ID_RE.test(trimmed)) {
      setClientError("Formato inválido — use apenas números (ex: 721438452)");
      return;
    }
    setClientError(null);
    mutation.mutate(trimmed);
  };

  const handleDisconnect = () => {
    setClientError(null);
    mutation.mutate(null);
  };

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-5" data-testid="telegram-card">
      <div className="flex items-center gap-2 mb-4">
        <ChatCircle className="h-4 w-4 text-blue-500" weight="fill" />
        <h3 className="text-sm font-semibold text-zinc-900">Notificações Telegram</h3>
        {isConnected && (
          <span className="ml-auto inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">
            <Link className="h-3 w-3" weight="bold" /> Conectado
          </span>
        )}
      </div>

      {isLoading ? (
        <ShimmerSkeleton className="h-20 rounded-lg" data-testid="telegram-loading" />
      ) : isConnected ? (
        <div className="space-y-3" data-testid="telegram-connected">
          <p className="text-sm text-zinc-700">
            Recebendo alertas no chat <strong>{maskChatId(data!.telegram_chat_id!)}</strong>
          </p>
          <button
            type="button"
            onClick={handleDisconnect}
            disabled={mutation.isPending}
            data-testid="telegram-disconnect-btn"
            className="inline-flex items-center gap-2 rounded-md bg-zinc-100 px-3 py-2 text-sm font-medium hover:bg-zinc-200 disabled:opacity-60 active:scale-[0.97] transition-all duration-150"
          >
            <LinkBreak className="h-3.5 w-3.5" />
            {mutation.isPending ? "Desconectando..." : "Desconectar"}
          </button>
        </div>
      ) : (
        <div className="space-y-3" data-testid="telegram-disconnected">
          <div className="rounded-lg bg-blue-50 px-3 py-2.5 text-xs text-blue-700 leading-relaxed">
            <strong>Como obter seu chat_id:</strong>
            <ol className="mt-1 ml-4 list-decimal space-y-0.5">
              <li>Abra o Telegram e busque por <code className="bg-white px-1 rounded">@userinfobot</code></li>
              <li>Inicie uma conversa e envie qualquer mensagem</li>
              <li>Copie o número exibido em <code className="bg-white px-1 rounded">Id</code> e cole abaixo</li>
            </ol>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              inputMode="numeric"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ex: 721438452"
              data-testid="telegram-chat-id-input"
              className="flex-1 rounded-md bg-zinc-100 px-3 py-2 text-sm border-2 border-transparent focus:outline-none focus:bg-white focus:border-blue-500 transition-all duration-200"
            />
            <button
              type="button"
              onClick={handleConnect}
              disabled={mutation.isPending || !input.trim()}
              data-testid="telegram-connect-btn"
              className="rounded-md bg-blue-500 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-600 disabled:opacity-60 active:scale-[0.97] transition-all duration-150"
            >
              {mutation.isPending ? "Conectando..." : "Conectar"}
            </button>
          </div>
        </div>
      )}

      {clientError && (
        <p className="mt-3 text-xs text-red-600 bg-red-50 rounded px-3 py-2" data-testid="telegram-client-error">
          {clientError}
        </p>
      )}

      {errKind === "requires_pro" && (
        <p className="mt-3 text-xs text-zinc-700 bg-zinc-50 rounded-lg px-3 py-2.5" data-testid="telegram-pro-required">
          Notificações Telegram disponíveis no <strong>Plano Pro</strong>.{" "}
          <a href="/planos" className="text-blue-500 hover:underline font-medium">Fazer upgrade</a>
        </p>
      )}

      {errKind === "invalid" && (
        <p className="mt-3 text-xs text-red-600 bg-red-50 rounded px-3 py-2" data-testid="telegram-invalid-error">
          Formato inválido — use apenas números.
        </p>
      )}

      {errKind === "other" && (
        <p className="mt-3 text-xs text-red-600 bg-red-50 rounded px-3 py-2" data-testid="telegram-error">
          Erro ao salvar. Tente novamente.
        </p>
      )}

      {mutation.isSuccess && !isConnected && (
        <p className="mt-3 text-xs text-emerald-700 bg-emerald-50 rounded px-3 py-2" data-testid="telegram-success-disconnect">
          Telegram desconectado com sucesso.
        </p>
      )}
    </div>
  );
}
