"use client";
import { create } from "zustand";

export type ModelId = "claude" | "chatgpt" | "gemini" | "deepseek" | "qwen" | "kimi" | "kimi-k2.5" | "kimi-k3" | "grok" | "llama";
export type CouncilMode = "consensus" | "debate" | "specialist" | "weighted";
export type Depth = "brief" | "standard" | "detailed";

export type ModelState = {
  status: "idle" | "generating" | "done" | "error" | "timeout";
  reasoning: string | null;
  final_answer: string;
  confidence: number | null;
  latency: number | null;
  token_count?: number | null;
};

type CouncilState = {
  query: string;
  models: ModelId[];
  mode: CouncilMode;
  depth: Depth;
  showReasoning: boolean;
  chairman: ModelId;
  status: "idle" | "streaming" | "done" | "error";
  sessionId: string | null;
  synthesis: string | null;
  agreements: string | null;
  divergences: string | null;
  uniqueInsights: string[] | null;
  totalLatency: number | null;
  responses: Record<string, ModelState>;
  error: string | null;
  setQuery: (q: string) => void;
  toggleModel: (m: ModelId) => void;
  setMode: (m: CouncilMode) => void;
  setDepth: (d: Depth) => void;
  setShowReasoning: (b: boolean) => void;
  setChairman: (m: ModelId) => void;
  resetForNewQuery: () => void;
  startStreaming: () => void;
  setDone: (data: any) => void;
  setError: (msg: string) => void;
  upsertModel: (model: ModelId, patch: Partial<ModelState>) => void;
};

export const useCouncilStore = create<CouncilState>((set, get) => ({
  query: "",
  models: ["claude", "chatgpt"],
  mode: "consensus",
  depth: "detailed",
  showReasoning: true,
  chairman: "claude",
  status: "idle",
  sessionId: null,
  synthesis: null,
  agreements: null,
  divergences: null,
  uniqueInsights: null,
  totalLatency: null,
  responses: {},
  error: null,
  setQuery: (query) => set({ query }),
  toggleModel: (m) =>
    set((s) => {
      const has = s.models.includes(m);
      if (has) {
        if (s.models.length <= 2) return s;
        return { models: s.models.filter((x) => x !== m) };
      } else {
        if (s.models.length >= 8) return s;
        return { models: [...s.models, m] };
      }
    }),
  setMode: (mode) => set({ mode }),
  setDepth: (depth) => set({ depth }),
  setShowReasoning: (showReasoning) => set({ showReasoning }),
  setChairman: (chairman) => set({ chairman }),
  resetForNewQuery: () =>
    set({
      status: "idle",
      sessionId: null,
      synthesis: null,
      agreements: null,
      divergences: null,
      uniqueInsights: null,
      totalLatency: null,
      responses: {},
      error: null,
    }),
  startStreaming: () => set({ status: "streaming", error: null }),
  setDone: (data) =>
    set({
      status: "done",
      sessionId: data.session_id || data.sessionId || null,
      synthesis: data.synthesis || null,
      agreements: data.agreements || null,
      divergences: data.divergences || null,
      uniqueInsights: data.unique_insights || data.uniqueInsights || null,
      totalLatency: data.total_latency || data.totalLatency || null,
    }),
  setError: (msg) => set({ status: "error", error: msg }),
  upsertModel: (model, patch) =>
    set((s) => ({
      responses: {
        ...s.responses,
        [model]: { ...(s.responses[model] || { status: "idle", reasoning: null, final_answer: "", confidence: null, latency: null }), ...patch },
      },
    })),
}));
