import { AppNav } from "@/components/AppNav";
import { ProfileContent } from "@/features/profile/components/ProfileContent";

export default function ProfilePage() {
  return (
    <main className="min-h-screen bg-background">
      <AppNav />
      <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8 py-8">
        <ProfileContent />
      </div>
    </main>
  );
}
