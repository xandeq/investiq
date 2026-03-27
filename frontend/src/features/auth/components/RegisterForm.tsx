"use client";

import { useState } from "react";
import Link from "next/link";
import { register } from "@/features/auth/api";
import { Eye, EyeOff, ArrowRight, CheckCircle } from "lucide-react";

export function RegisterForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [showConfirmPw, setShowConfirmPw] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("As senhas não coincidem.");
      return;
    }

    if (password.length < 8) {
      setError("A senha deve ter pelo menos 8 caracteres.");
      return;
    }

    setIsLoading(true);

    try {
      await register(email, password);
      setSuccess(true);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro ao criar conta";
      if (message.toLowerCase().includes("already registered")) {
        setError("Este email já está cadastrado.");
      } else {
        setError(message);
      }
    } finally {
      setIsLoading(false);
    }
  }

  if (success) {
    return (
      <div className="text-center space-y-4">
        <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center mx-auto">
          <CheckCircle className="w-6 h-6 text-emerald-600" />
        </div>
        <h3 className="text-lg font-bold tracking-tight">Verifique seu email</h3>
        <p className="text-sm text-muted-foreground">
          Enviamos um link de verificação para <strong>{email}</strong>.
          Clique no link para ativar sua conta.
        </p>
        <p className="text-xs text-muted-foreground">
          Não recebeu?{" "}
          <Link href="/login" className="text-blue-500 font-medium hover:text-blue-600 transition-colors">
            Voltar ao login
          </Link>
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1">
        <label htmlFor="email" className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Email
        </label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
          placeholder="seu@email.com"
          className="w-full bg-gray-100 text-gray-900 rounded-md px-4 py-3 text-sm font-medium border-2 border-transparent focus:outline-none focus:bg-white focus:border-blue-500 transition-all duration-200"
        />
      </div>

      <div className="space-y-1">
        <label htmlFor="password" className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Senha
        </label>
        <div className="relative">
          <input
            id="password"
            type={showPw ? "text" : "password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="new-password"
            minLength={8}
            placeholder="Mínimo 8 caracteres"
            className="w-full bg-gray-100 text-gray-900 rounded-md px-4 py-3 pr-11 text-sm font-medium border-2 border-transparent focus:outline-none focus:bg-white focus:border-blue-500 transition-all duration-200"
          />
          <button
            type="button"
            onClick={() => setShowPw(!showPw)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
          >
            {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
      </div>

      <div className="space-y-1">
        <label htmlFor="confirmPassword" className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Confirmar senha
        </label>
        <div className="relative">
          <input
            id="confirmPassword"
            type={showConfirmPw ? "text" : "password"}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            autoComplete="new-password"
            className="w-full bg-gray-100 text-gray-900 rounded-md px-4 py-3 pr-11 text-sm font-medium border-2 border-transparent focus:outline-none focus:bg-white focus:border-blue-500 transition-all duration-200"
          />
          <button
            type="button"
            onClick={() => setShowConfirmPw(!showConfirmPw)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
          >
            {showConfirmPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 rounded-md px-4 py-3 text-sm text-red-600 font-medium">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={isLoading}
        className="w-full h-11 bg-blue-500 hover:bg-blue-600 text-white font-semibold rounded-md flex items-center justify-center gap-2 transition-all duration-200 hover:scale-[1.02] disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:scale-100"
      >
        {isLoading ? (
          <span className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        ) : (
          <>Criar conta <ArrowRight className="h-4 w-4" /></>
        )}
      </button>

      <p className="text-center text-sm text-muted-foreground">
        Já tem uma conta?{" "}
        <Link href="/login" className="text-blue-500 font-medium hover:text-blue-600 transition-colors">
          Entrar
        </Link>
      </p>
    </form>
  );
}
