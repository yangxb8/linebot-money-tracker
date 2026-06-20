import { createClient } from "@/lib/supabase/server";
import { DashboardClient } from "@/app/dashboard/DashboardClient";
import { fetchUserLocaleServer } from "@/lib/dashboard/tenants-server";

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  let initialLocale: string | null = null;
  if (user) {
    initialLocale = await fetchUserLocaleServer();
  }

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="sticky top-0 z-10 bg-white border-b border-gray-100 px-4 py-3">
        <h1 className="text-lg font-semibold text-gray-900">家計簿</h1>
      </header>
      <div className="max-w-lg mx-auto px-4 py-4">
        <DashboardClient initialLocale={initialLocale} />
      </div>
    </main>
  );
}
