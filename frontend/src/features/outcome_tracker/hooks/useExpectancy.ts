"use client";
import { useQuery } from "@tanstack/react-query";
import { fetchExpectancy } from "../api";

export function useExpectancy() {
  return useQuery({
    queryKey: ["outcome-expectancy"],
    queryFn: fetchExpectancy,
    staleTime: 5 * 60 * 1000,
  });
}
