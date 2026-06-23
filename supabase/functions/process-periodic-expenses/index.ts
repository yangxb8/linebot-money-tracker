import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";
import { runPeriodicCron } from "../_shared/periodic/cron.ts";

function isAuthorized(request: Request): boolean {
  const cronSecret = Deno.env.get("CRON_SECRET");
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  const authHeader = request.headers.get("authorization");
  const apiKey = request.headers.get("apikey");

  if (cronSecret && authHeader === `Bearer ${cronSecret}`) {
    return true;
  }
  if (serviceRoleKey && apiKey === serviceRoleKey) {
    return true;
  }
  return false;
}

Deno.serve(async (request: Request) => {
  if (request.method !== "POST" && request.method !== "GET") {
    return new Response(JSON.stringify({ error: "Method not allowed" }), {
      status: 405,
      headers: { "Content-Type": "application/json" },
    });
  }

  if (!isAuthorized(request)) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (!supabaseUrl || !serviceRoleKey) {
    return new Response(JSON.stringify({ error: "Missing Supabase env" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }

  try {
    const admin = createClient(supabaseUrl, serviceRoleKey);
    const result = await runPeriodicCron(admin);
    console.info(
      "[process-periodic-expenses] processed=%d inserted=%d skipped=%d ended=%d",
      result.processed,
      result.inserted,
      result.skipped,
      result.ended,
    );
    return new Response(JSON.stringify(result), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } catch (error) {
    console.error("[process-periodic-expenses] failed", error);
    return new Response(JSON.stringify({ error: "Internal error" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
});
