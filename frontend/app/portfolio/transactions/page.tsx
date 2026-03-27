import { AppNav } from "@/components/AppNav";
import { TransactionsContent } from "@/features/portfolio/components/TransactionsContent";

export default function TransactionsPage() {
  return (
    <main className="min-h-screen bg-background">
      <AppNav />
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
        <TransactionsContent />
      </div>
    </main>
  );
}
