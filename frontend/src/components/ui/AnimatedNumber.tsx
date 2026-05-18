"use client";
import { useEffect, useRef } from "react";
import { useMotionValue, useSpring, useTransform, motion } from "framer-motion";

interface AnimatedNumberProps {
  value: number;
  formatter?: (v: number) => string;
  className?: string;
}

/**
 * Spring-animated number counter.
 * Uses Framer Motion useSpring — no setState, no re-renders on each frame.
 * Formatter defaults to pt-BR BRL currency.
 */
export function AnimatedNumber({ value, formatter, className }: AnimatedNumberProps) {
  const motionVal = useMotionValue(value);
  const spring = useSpring(motionVal, { stiffness: 80, damping: 22, mass: 0.8 });
  const displayRef = useRef<HTMLSpanElement>(null);

  const defaultFormatter = (v: number) =>
    v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

  const fmt = formatter ?? defaultFormatter;

  useEffect(() => {
    motionVal.set(value);
  }, [value, motionVal]);

  useEffect(() => {
    const unsubscribe = spring.on("change", (latest) => {
      if (displayRef.current) {
        displayRef.current.textContent = fmt(latest);
      }
    });
    return unsubscribe;
  }, [spring, fmt]);

  return (
    <span ref={displayRef} className={className}>
      {fmt(value)}
    </span>
  );
}
