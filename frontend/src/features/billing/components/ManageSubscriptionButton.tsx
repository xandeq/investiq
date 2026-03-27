"use client";
import { useState } from "react";
import { createPortalSession } from "../api";

interface Props {
  className?: string;
}

export function ManageSubscriptionButton({ className }: Props) {
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    setLoading(true);
    try {
      const { portal_url } = await createPortalSession();
      window.location.href = portal_url;
    } catch {
      setLoading(false);
    }
  };

  return (
    <button onClick={handleClick} disabled={loading} className={className}>
      {loading ? "Aguarde..." : "Gerenciar assinatura"}
    </button>
  );
}
