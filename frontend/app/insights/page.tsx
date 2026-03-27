import { AppNav } from "@/components/AppNav";
import { InsightsContent } from "@/features/insights/components/InsightsContent";
export default function InsightsPage() {
  return (
    <main className="min-h-screen bg-background">
      <AppNav />
      <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8 py-8">
        <InsightsContent />
      </div>
    </main>
  );
}
