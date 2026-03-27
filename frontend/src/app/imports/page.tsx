import { AppNav } from "@/components/AppNav";
import { ImportContent } from "@/features/imports/components/ImportContent";

export default function ImportsPage() {
  return (
    <main className="min-h-screen bg-background">
      <AppNav />
      <div className="container mx-auto px-4 py-8">
        <ImportContent />
      </div>
    </main>
  );
}
