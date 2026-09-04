export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const WS_URL = process.env.NEXT_PUBLIC_WEBSOCKET_URL || "ws://localhost:8000/ws";

export async function getSession(id: string) {
  const r = await fetch(`${API_URL}/council/session/${id}`);
  if (!r.ok) throw new Error(`GET session ${r.status}`);
  return r.json();
}
export async function getSessions(limit = 20, offset = 0, token?: string) {
  const headers: Record<string,string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const r = await fetch(`${API_URL}/council/sessions?limit=${limit}&offset=${offset}`, { headers });
  if (!r.ok) throw new Error(`GET sessions ${r.status}`);
  return r.json();
}
export async function getModels() {
  const r = await fetch(`${API_URL}/models`);
  if (!r.ok) throw new Error(`GET models ${r.status}`);
  return r.json();
}
