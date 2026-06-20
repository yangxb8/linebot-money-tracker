export type LineProfile = {
  sub: string;
  name?: string;
  picture?: string;
};

export async function verifyLineIdToken(idToken: string): Promise<LineProfile> {
  const body = new URLSearchParams({
    id_token: idToken,
    client_id: process.env.LINE_LOGIN_CHANNEL_ID!,
  });

  const response = await fetch("https://api.line.me/oauth2/v2.1/verify", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString(),
  });

  if (!response.ok) {
    throw new Error(`LINE ID token verification failed: ${response.status}`);
  }

  const payload = await response.json();
  if (!payload.sub) {
    throw new Error("LINE ID token missing sub claim");
  }

  return {
    sub: payload.sub,
    name: payload.name,
    picture: payload.picture,
  };
}
