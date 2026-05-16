"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

// ── Types ───────────────────────────────────────────────────────────────────

interface TickerHeat {
  ticker: string;
  mention_count: number;
  score: number;
  snapshot_count: number;
  last_updated: string | null;
  sources: string[];
}

interface RedditTop {
  ticker: string;
  mentions: number;
}

interface MarketHeat {
  hours: number;
  ticker_count: number;
  tickers: TickerHeat[];
  reddit_top10: RedditTop[];
}

interface NewsItem {
  headline: string;
  url: string | null;
  source: string;
  tickers: string[];
  sentiment: number | null;
  published_at: string | null;
}

interface NewsFeed {
  ticker_filter: string | null;
  hours: number;
  count: number;
  items: NewsItem[];
}

// ── Hooks ───────────────────────────────────────────────────────────────────

function useMarketHeat() {
  return useQuery<MarketHeat>({
    queryKey: ["market-heat"],
    queryFn: () => apiClient<MarketHeat>("/briefing/market-heat?limit=40&hours=24"),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });
}

function useNewsFeed() {
  return useQuery<NewsFeed>({
    queryKey: ["news-feed-intel"],
    queryFn: () => apiClient<NewsFeed>("/briefing/news-feed?hours=24"),
    staleTime: 10 * 60 * 1000,
    refetchInterval: 10 * 60 * 1000,
  });
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function scoreToColor(score: number, mentions: number): string {
  if (mentions === 0) return "bg-gray-100 text-gray-500";
  if (score > 0.1) return "bg-emerald-100 text-emerald-800 border-emerald-200";
  if (score < -0.1) return "bg-red-100 text-red-800 border-red-200";
  return "bg-amber-50 text-amber-800 border-amber-200";
}

function scoreLabel(score: number): string {
  if (score > 0.3) return "Muito positivo";
  if (score > 0.1) return "Positivo";
  if (score < -0.3) return "Muito negativo";
  if (score < -0.1) return "Negativo";
  return "Neutro";
}

function formatScore(score: number): string {
  const sign = score > 0 ? "+" : "";
  return `${sign}${(score * 100).toFixed(0)}%`;
}

function relativeTime(iso: string | null): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 60) return `${m}min atrás`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h atrás`;
  return `${Math.floor(h / 24)}d atrás`;
}

// ── Sub-components ──────────────────────────────────────────────────────────

function SentimentHeatMap({ data }: { data: MarketHeat }) {
  if (data.ticker_count === 0) {
    return (
      <div className="text-center py-12 text-gray-500 text-sm">
        <p className="font-medium mb-1">Nenhum dado de sentimento disponível ainda.</p>
        <p>A coleta roda a cada 30min durante o pregão. Volte mais tarde.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
      {data.tickers.map((t) => {
        const colorClass = scoreToColor(t.score, t.mention_count);
        return (
          <div
            key={t.ticker}
            className={`rounded-xl border p-3 flex flex-col gap-1 ${colorClass}`}
            title={`${scoreLabel(t.score)} — ${t.mention_count} menções`}
          >
            <span className="font-bold text-sm">{t.ticker}</span>
            <span className="text-xs font-mono">{formatScore(t.score)}</span>
            <span className="text-xs opacity-70">{t.mention_count} menções</span>
            {t.last_updated && (
              <span className="text-xs opacity-50">{relativeTime(t.last_updated)}</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

function RedditRanking({ items }: { items: RedditTop[] }) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-gray-500 py-4">
        Nenhuma menção coletada ainda — coleta inicia durante o pregão.
      </p>
    );
  }

  const max = items[0]?.mentions ?? 1;

  return (
    <div className="space-y-2">
      {items.map((item, idx) => (
        <div key={item.ticker} className="flex items-center gap-3">
          <span className="text-xs w-5 text-gray-400 text-right">{idx + 1}</span>
          <span className="font-mono font-semibold text-sm w-16">{item.ticker}</span>
          <div className="flex-1 bg-gray-100 rounded-full h-2">
            <div
              className="bg-orange-400 h-2 rounded-full transition-all"
              style={{ width: `${(item.mentions / max) * 100}%` }}
            />
          </div>
          <span className="text-xs text-gray-500 w-14 text-right">{item.mentions} posts</span>
        </div>
      ))}
    </div>
  );
}

function NewsFeedList({ items }: { items: NewsItem[] }) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-gray-500 py-4">
        Nenhuma notícia nas últimas 24h. A coleta roda a cada 2h.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {items.slice(0, 20).map((item, idx) => {
        const sentColor =
          item.sentiment === null
            ? "text-gray-400"
            : item.sentiment > 0
            ? "text-emerald-600"
            : item.sentiment < 0
            ? "text-red-500"
            : "text-gray-400";

        return (
          <div key={idx} className="border-b pb-3 last:border-0">
            <div className="flex items-start gap-2">
              <div className="flex-1 min-w-0">
                {item.url ? (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-gray-900 hover:text-blue-600 leading-snug"
                  >
                    {item.headline}
                  </a>
                ) : (
                  <span className="text-sm font-medium text-gray-900 leading-snug">
                    {item.headline}
                  </span>
                )}
                <div className="flex items-center gap-2 mt-1 flex-wrap">
                  <span className="text-xs text-gray-400">{item.source}</span>
                  {item.published_at && (
                    <span className="text-xs text-gray-400">
                      {relativeTime(item.published_at)}
                    </span>
                  )}
                  {item.tickers.length > 0 && (
                    <div className="flex gap-1 flex-wrap">
                      {item.tickers.slice(0, 4).map((t) => (
                        <span
                          key={t}
                          className="text-xs bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded font-mono"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              {item.sentiment !== null && (
                <span className={`text-xs font-mono shrink-0 ${sentColor}`}>
                  {item.sentiment > 0 ? "▲" : item.sentiment < 0 ? "▼" : "—"}
                  {Math.abs(item.sentiment * 100).toFixed(0)}%
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Main ─────────────────────────────────────────────────────────────────────

export function IntelligenceContent() {
  const { data: heat, isLoading: heatLoading, error: heatError } = useMarketHeat();
  const { data: news, isLoading: newsLoading } = useNewsFeed();

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Inteligência de Mercado</h1>
        <p className="text-sm text-gray-500 mt-1">
          Sentimento social, menções no Reddit e notícias com impacto — atualizado automaticamente.
        </p>
      </div>

      {/* Heat Map */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-800">Mapa de Sentimento — B3</h2>
          {heat && (
            <span className="text-xs text-gray-400">
              {heat.ticker_count} ticker{heat.ticker_count !== 1 ? "s" : ""} · últimas {heat.hours}h
            </span>
          )}
        </div>

        {/* Legend */}
        <div className="flex gap-3 mb-3 text-xs flex-wrap">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-sm bg-emerald-100 border border-emerald-200 inline-block" />
            Positivo
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-sm bg-amber-50 border border-amber-200 inline-block" />
            Neutro
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-sm bg-red-100 border border-red-200 inline-block" />
            Negativo
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-sm bg-gray-100 border inline-block" />
            Sem dados
          </span>
        </div>

        <div className="bg-white rounded-2xl border p-4">
          {heatLoading ? (
            <div className="text-sm text-gray-400 py-8 text-center">Carregando...</div>
          ) : heatError ? (
            <div className="text-sm text-red-500 py-4">Erro ao carregar sentimento.</div>
          ) : heat ? (
            <SentimentHeatMap data={heat} />
          ) : null}
        </div>
      </section>

      {/* Two columns: Reddit + News */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Reddit Top 10 */}
        <section>
          <h2 className="text-lg font-semibold text-gray-800 mb-3">
            🔴 Top Mencionados — Reddit
          </h2>
          <div className="bg-white rounded-2xl border p-4">
            {heatLoading ? (
              <div className="text-sm text-gray-400 py-4">Carregando...</div>
            ) : heat ? (
              <RedditRanking items={heat.reddit_top10} />
            ) : null}
          </div>
        </section>

        {/* News Feed */}
        <section>
          <h2 className="text-lg font-semibold text-gray-800 mb-3">
            📰 Notícias — Últimas 24h
          </h2>
          <div className="bg-white rounded-2xl border p-4 max-h-96 overflow-y-auto">
            {newsLoading ? (
              <div className="text-sm text-gray-400 py-4">Carregando...</div>
            ) : news ? (
              <NewsFeedList items={news.items} />
            ) : null}
          </div>
        </section>
      </div>
    </div>
  );
}
