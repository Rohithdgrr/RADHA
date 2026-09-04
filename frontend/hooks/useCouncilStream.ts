"use client";
import { useCallback } from "react";
import { useCouncilStore } from "@/lib/store";
import { API_URL } from "@/lib/api";
import { sseReader } from "@/lib/sse";

export function useCouncilStream() {
  const store = useCouncilStore();

  const start = useCallback(async () => {
    const { query, models, mode, depth, showReasoning, chairman } = useCouncilStore.getState();
    if (!query.trim() || models.length < 2) {
      store.setError("Need query and at least 2 models");
      return;
    }
    store.resetForNewQuery();
    store.startStreaming();
    // initialize model cards as generating on model_start, but we can pre-seed idle
    for (const m of models) {
      store.upsertModel(m as any, { status: "generating", final_answer: "", reasoning: null, confidence: null, latency: null });
    }

    try {
      const res = await fetch(`${API_URL}/council/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          models,
          mode,
          depth,
          show_reasoning: showReasoning,
          chairman,
        }),
      });
      if (!res.ok || !res.body) {
        const txt = await res.text();
        throw new Error(`query failed ${res.status}: ${txt.slice(0, 300)}`);
      }
      // optional token: attach if exists in localStorage
      // For now, auth optional — if token in localStorage, retry with it? Keep simple.

      for await (const ev of sseReader(res)) {
        const { event, data } = ev;
        if (event === "model_start") {
          store.upsertModel(data.model, { status: "generating" });
        } else if (event === "model_stream") {
          // Phase 1 may not emit; handle append
          const prev = useCouncilStore.getState().responses[data.model];
          store.upsertModel(data.model, { final_answer: (prev?.final_answer || "") + (data.delta || "") });
        } else if (event === "model_done") {
          store.upsertModel(data.model, {
            status: data.status === "done" ? "done" : data.status === "timeout" ? "timeout" : "error",
            final_answer: data.final_answer || "",
            reasoning: data.reasoning || null,
            confidence: data.confidence ?? null,
            latency: data.latency ?? null,
            token_count: data.token_count ?? null,
          });
        } else if (event === "synthesis_start") {
          // show spinner — store synthesis null until stream
        } else if (event === "synthesis_stream") {
          const cur = useCouncilStore.getState().synthesis || "";
          useCouncilStore.setState({ synthesis: cur + (data.delta || "") });
        } else if (event === "done") {
          store.setDone(data as any);
          // also ensure synthesis already set; if not, set from data.synthesis
          if (data.synthesis && !useCouncilStore.getState().synthesis) {
            useCouncilStore.setState({ synthesis: data.synthesis });
          }
        } else if (event === "error") {
          store.setError(data.message || data.detail || "council error");
        }
      }
      // if still streaming but no done/error, mark done
      const s = useCouncilStore.getState();
      if (s.status === "streaming") {
        // fallback: mark done if we have synthesis
        if (s.synthesis) store.setDone({ session_id: s.sessionId, synthesis: s.synthesis } as any);
      }
    } catch (e: any) {
      store.setError(e.message || String(e));
    }
  }, []);

  return { start, status: store.status, error: store.error };
}
