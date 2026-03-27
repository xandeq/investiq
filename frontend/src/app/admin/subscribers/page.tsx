import { AppNav } from "@/components/AppNav";
import { AdminSubscribersContent } from "./AdminSubscribersContent";

export default function AdminSubscribersPage() {
  return (
    <main className="min-h-screen bg-background">
      <AppNav />
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <h1 className="text-2xl font-bold text-foreground mb-6">Assinantes</h1>
        <AdminSubscribersContent />
      </div>
    </main>
  );
}
