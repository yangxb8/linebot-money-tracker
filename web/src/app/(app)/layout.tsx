import { AppAuthProvider } from "@/components/AppAuthProvider";
import { AppShell } from "@/components/AppShell";
import { fetchUserLocaleServer } from "@/lib/dashboard/tenants-server";
import { createClient } from "@/lib/supabase/server";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  let initialLocale: string | null = null;
  if (user) {
    initialLocale = await fetchUserLocaleServer();
  }

  return (
    <AppAuthProvider initialLocale={initialLocale}>
      <AppShell>{children}</AppShell>
    </AppAuthProvider>
  );
}
