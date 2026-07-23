import { NextResponse } from "next/server";
import {
  fetchTenantSettings,
  parseTenantParams,
  upsertTenantSettings,
} from "@/lib/settings/server";

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const { tenantType, tenantId } = parseTenantParams(
      url.searchParams.get("tenant_type"),
      url.searchParams.get("tenant_id"),
    );
    const settings = await fetchTenantSettings(tenantType, tenantId);
    return NextResponse.json(settings);
  } catch (error) {
    if (error instanceof Response) {
      return NextResponse.json(
        { error: await error.text() },
        { status: error.status },
      );
    }
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}

export async function PUT(request: Request) {
  try {
    const body = await request.json();
    const tenantType = String(body.tenant_type ?? "");
    const tenantId = String(body.tenant_id ?? "");
    parseTenantParams(tenantType, tenantId);

    const settings = await upsertTenantSettings(tenantType, tenantId, {
      fiscal_start_day: Number(body.fiscal_start_day),
      bot_persona_preset: body.bot_persona_preset ?? null,
      bot_persona_custom_text: body.bot_persona_custom_text ?? null,
      bot_persona_emoji_level: body.bot_persona_emoji_level ?? null,
      confirmation_show_item_details: Boolean(body.confirmation_show_item_details),
      reply_language: body.reply_language ?? null,
    });
    return NextResponse.json(settings);
  } catch (error) {
    if (error instanceof Response) {
      return NextResponse.json(
        { error: await error.text() },
        { status: error.status },
      );
    }
    return NextResponse.json({ error: "Internal error" }, { status: 500 });
  }
}
