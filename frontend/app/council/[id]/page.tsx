"use client";
import { useEffect, useState } from "react";
import { getSession } from "@/lib/api";
import { useCouncilStore, ModelId } from "@/lib/store";
import { UnifiedAnswer } from "@/components/UnifiedAnswer";
import { ModelCard } from "@/components/ModelCard";

export default function CouncilPage({ params }: { params: { id: string } }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSession(params.id)
      .then((data) => {
        const store: any = useCouncilStore.getState();
        useCouncilStore.setState({
          query: data.user_query || data.userQuery || "",
          models: data.selected_models || data.selectedModels || [],
          chairman: data.chairman_model || data.chairmanModel || "claude",
          mode: data.mode || "consensus",
          depth: data.depth || "detailed",
          showReasoning: data.show_reasoning ?? true,
          sessionId: data.id,
          synthesis: data.synthesis,
          agreements: data.agreements,
          divergences: data.divergences,
          uniqueInsights: data.unique_insights || data.uniqueInsights || null,
          totalLatency: data.total_latency || data.totalLatency || null,
          status: data.synthesis ? "done" : "idle",
          responses: (() => {
            const map: any = {};
            for (const r of data.responses || []) {
              map[r.model_name || r.modelName] = {
                status: r.status === "done" ? "done" : r.status === "timeout" ? "timeout" : r.status === "error" ? "error" : "done",
                reasoning: r.reasoning || null,
                final_answer: r.final_answer || r.finalAnswer || "",
                confidence: r.confidence ?? null,
                latency: r.latency ?? null,
                token_count: r.token_count ?? null,
              };
            }
            return map;
          })(),
        });
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [params.id]);

  const { models, synthesis, query } = useCouncilStore();
  if (loading) return <div className="mx-auto max-w-4xl p-6 text-gray-400">Loading session {params.id}…</div>;
  if (error) return <div className="mx-auto max-w-4xl p-6 text-red-300">{error}</div>;

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <a href="/" className="text-sm text-cyan-400">← Back to Council</a>
      <h1 className="mt-4 text-xl font-semibold">Session {params.id}</h1>
      <p className="mt-1 text-sm text-gray-400">{query}</p>
      <div className="mt-6">
        <UnifiedAnswer />
      </div>
      <div className="mt-6 flex gap-4 overflow-x-auto">
        {models.map((m) => (
          <ModelCard key={m} model={m as ModelId} />
        ))}
      </div>
      {synthesis && (
        <button
          onClick={() => {
            const { synthesis: s, responses, query: q } = useCouncilStore.getState();
            const html = `<html><body><h1>${q}</h1><pre>${s}</pre>${Object.entries(responses).map(([k, v]: any) => `<h2>${k}</h2><pre>${v.final_answer}</pre>`).join("")}</body></html>`;
            const blob = new Blob([html], { type: "text/html" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `report-${params.id}.html`;
            a.click();
            URL.revokeObjectURL(url);
          }}
          className="mt-6 rounded-full bg-cyan-500 px-4 py-2 text-sm font-semibold text-black"
        >
          Download Full Report
        </button>
      )}
    </main>
  );
}
