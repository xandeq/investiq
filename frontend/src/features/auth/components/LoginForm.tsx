"use client";
import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Eye, EyeSlash, ArrowRight } from "@phosphor-icons/react";
import { login } from "@/features/auth/api";

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      await login(email, password);
      const redirect = searchParams.get("redirect");
      const destination = redirect && redirect.startsWith("/") ? redirect : "/dashboard";
      router.push(destination);
    } catch (err) {
      const message = err instanceof Error ? err.message : "";
      if (message.toLowerCase().includes("not verified") || message.includes("is_verified")) {
        setError("Email não verificado. Verifique sua caixa de entrada.");
      } else {
        setError("Email ou senha incorretos.");
      }
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1">
        <label htmlFor="email" className="block text-xs font-semibold uppercase tracking-wider text-zinc-400">
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
          className="w-full bg-zinc-100 text-zinc-900 rounded-md px-4 py-3 text-sm font-medium border-2 border-transparent focus:outline-none focus:bg-white focus:border-blue-500 transition-all duration-200"
        />
      </div>

      <div className="space-y-1">
        <label htmlFor="password" className="block text-xs font-semibold uppercase tracking-wider text-zinc-400">
          Senha
        </label>
        <div className="relative">
          <input
            id="password"
            type={showPw ? "text" : "password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            className="w-full bg-zinc-100 text-zinc-900 rounded-md px-4 py-3 pr-11 text-sm font-medium border-2 border-transparent focus:outline-none focus:bg-white focus:border-blue-500 transition-all duration-200"
          />
          <button
            type="button"
            onClick={() => setShowPw(!showPw)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600 active:scale-[0.97] transition-all duration-150"
          >
            {showPw ? <EyeSlash className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
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
        className="w-full h-11 bg-blue-500 hover:bg-blue-600 text-white font-semibold rounded-md flex items-center justify-center gap-2 transition-all duration-150 active:scale-[0.97] disabled:opacity-60 disabled:cursor-not-allowed"
      >
        {isLoading ? (
          <span className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        ) : (
          <>Entrar <ArrowRight className="h-4 w-4" /></>
        )}
      </button>

      <div className="flex justify-between text-sm">
        <Link href="/register" className="text-blue-500 font-medium hover:text-blue-600 transition-colors">
          Criar conta
        </Link>
        <Link href="/forgot-password" className="text-zinc-400 hover:text-zinc-700 transition-colors">
          Esqueci a senha
        </Link>
      </div>
    </form>
  );
}
