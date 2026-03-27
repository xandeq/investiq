"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { verifyEmail } from "@/features/auth/api";

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("Link de verificação inválido ou expirado.");
      return;
    }

    verifyEmail(token)
      .then((res) => {
        setStatus("success");
        setMessage(res.message);
      })
      .catch((err) => {
        setStatus("error");
        const msg = err instanceof Error ? err.message : "Erro na verificação";
        if (msg.toLowerCase().includes("expired")) {
          setMessage("O link de verificação expirou. Solicite um novo.");
        } else {
          setMessage("Link inválido ou já utilizado.");
        }
      });
  }, [token]);

  return (
    <div className="text-center space-y-4">
      {status === "loading" && (
        <>
          <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-gray-600">Verificando seu email...</p>
        </>
      )}

      {status === "success" && (
        <>
          <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto">
            <svg
              className="w-6 h-6 text-green-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900">Email verificado!</h2>
          <p className="text-gray-600">Sua conta está ativa. Você pode fazer login agora.</p>
          <Link
            href="/login"
            className="inline-block mt-2 py-2 px-6 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 transition-colors"
          >
            Fazer login
          </Link>
        </>
      )}

      {status === "error" && (
        <>
          <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto">
            <svg
              className="w-6 h-6 text-red-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900">Verificação falhou</h2>
          <p className="text-gray-600">{message}</p>
          <Link
            href="/login"
            className="inline-block mt-2 text-sm text-blue-600 hover:underline"
          >
            Voltar ao login
          </Link>
        </>
      )}
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<div className="text-center text-gray-500">Carregando...</div>}>
      <VerifyEmailContent />
    </Suspense>
  );
}
