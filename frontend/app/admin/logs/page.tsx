import { AppNav } from "@/components/AppNav";
import { LogsContent } from "@/features/logs/components/LogsContent";

export default function AdminLogsPage() {
  return (
    <main className="min-h-screen bg-background">
      <AppNav />
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <LogsContent />
      </div>
    </main>
  );
}
