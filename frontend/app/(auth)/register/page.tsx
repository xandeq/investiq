import type { Metadata } from "next";
import { RegisterForm } from "@/features/auth/components/RegisterForm";

export const metadata: Metadata = {
  title: "Criar conta — InvestIQ",
};

export default function RegisterPage() {
  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-6">Criar sua conta</h2>
      <RegisterForm />
    </div>
  );
}
