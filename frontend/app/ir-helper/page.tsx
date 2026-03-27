import { AppNav } from "@/components/AppNav";
import { IrHelperContent } from "@/features/ir_helper/IrHelperContent";

export const metadata = { title: "IR Helper — InvestIQ" };

export default function IrHelperPage() {
  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-background">
        <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
          <IrHelperContent />
        </div>
      </main>
    </>
  );
}
