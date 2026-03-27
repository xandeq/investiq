import { AppNav } from "@/components/AppNav";
import { ImportContent } from "@/features/imports/components/ImportContent";

export default function ImportsPage() {
  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-background">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <ImportContent />
        </div>
      </main>
    </>
  );
}
