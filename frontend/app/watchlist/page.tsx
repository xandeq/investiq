import { AppNav } from "@/components/AppNav";
import { WatchlistContent } from "@/features/watchlist/components/WatchlistContent";

export default function WatchlistPage() {
  return (
    <main className="min-h-screen bg-background">
      <AppNav />
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
        <WatchlistContent />
      </div>
    </main>
  );
}
