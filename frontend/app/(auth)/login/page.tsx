import type { Metadata } from "next";
import { Suspense } from "react";
import { LoginForm } from "@/features/auth/components/LoginForm";

export const metadata: Metadata = {
  title: "Entrar — InvestIQ",
};

export default function LoginPage() {
  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-6">Entrar na sua conta</h2>
      <Suspense fallback={<div>Carregando...</div>}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
