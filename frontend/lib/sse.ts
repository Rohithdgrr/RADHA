// SSE parser for POST /council/query text/event-stream
// Contract: event: <type>\ndata: <json>\n\n per contracts/sse-events.md

export type SSEEvent = {
  event: string;
  data: any;
};

export function parseSSEChunk(buffer: string): { events: SSEEvent[]; rest: string } {
  const events: SSEEvent[] = [];
  const parts = buffer.split("\n\n");
  const rest = parts.pop() || "";
  for (const part of parts) {
    if (!part.trim()) continue;
    const lines = part.split("\n");
    let event = "";
    let dataStr = "";
    for (const line of lines) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) dataStr += line.slice(5).trim();
    }
    if (!event) continue;
    let data: any = dataStr;
    try {
      data = JSON.parse(dataStr);
    } catch {}
    events.push({ event, data });
  }
  return { events, rest };
}

export async function* sseReader(res: Response): AsyncGenerator<SSEEvent, void, unknown> {
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const { events, rest } = parseSSEChunk(buffer);
    buffer = rest;
    for (const ev of events) yield ev;
  }
  // flush
  if (buffer.trim()) {
    const { events } = parseSSEChunk(buffer + "\n\n");
    for (const ev of events) yield ev;
  }
}
