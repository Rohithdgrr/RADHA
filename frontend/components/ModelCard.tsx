"use client";
import { useState, useEffect } from "react";
import { useCouncilStore, ModelId } from "@/lib/store";
import { Markdown } from "@/components/Markdown";

function ConfidenceBar({ value }: { value: number | null }) {
  if (value == null) return <span className="font-mono text-[11px] tracking-wide text-white/30">confidence —</span>;
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-white/10 p-[2px] backdrop-blur">
        <div className="h-full rounded-full bg-gradient-to-r from-emerald-400 to-cyan-300 transition-all" style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-[11px] text-white/50">{pct}%</span>
    </div>
  );
}

function FullscreenModal({ model, final_answer, reasoning, confidence, latency, onClose }: { model: string; final_answer: string; reasoning: string | null; confidence: number | null; latency: number | null; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", onKey); document.body.style.overflow = prev; };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex flex-col p-4 md:p-8" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-[#070B16]/70 backdrop-blur-[12px]" onClick={onClose} />
      <div className="relative mx-auto flex max-h-[92vh] w-full max-w-4xl flex-col overflow-hidden rounded-[20px] p-[1px]">
        <div className="absolute inset-0 rounded-[20px] bg-gradient-to-b from-white/15 via-white/8 to-transparent" />
        <div className="relative flex flex-col overflow-hidden rounded-[19px] glass-strong">
          <div className="flex items-center justify-between border-b border-white/10 px-6 py-4">
            <div className="flex items-center gap-3">
              <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.7)]" />
              <h2 className="font-display text-lg font-semibold tracking-tight text-white">{model}</h2>
              <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-0.5 font-mono text-xs text-white/50">{confidence != null ? `${Math.round(confidence*100)}%` : "—"} • {latency != null ? `${latency.toFixed(2)}s` : "—"}</span>
            </div>
            <button onClick={onClose} aria-label="Close fullscreen" className="rounded-full border border-white/10 bg-white/5 p-2 text-white/60 hover:bg-white/10 hover:text-white transition">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12" /></svg>
            </button>
          </div>
          <div className="flex-1 overflow-auto p-6 md:p-8">
            {reasoning && (
              <details className="mb-6 rounded-[12px] border border-white/8 bg-white/[0.04] p-3" open>
                <summary className="cursor-pointer font-mono text-xs tracking-wide text-sky-200/70">Reasoning</summary>
                <div className="mt-3 rounded-[10px] bg-[#0B1224]/40 p-3 font-mono text-xs leading-4 text-white/60 whitespace-pre-wrap">{reasoning}</div>
              </details>
            )}
            <div className="prose prose-invert max-w-none">
              <Markdown>{final_answer || "_No content_"}</Markdown>
            </div>
          </div>
          <div className="border-t border-white/10 px-6 py-3 flex justify-end gap-2">
            <button onClick={() => { navigator.clipboard?.writeText(final_answer); }} className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 font-mono text-xs text-white/60 hover:bg-white/10">Copy markdown</button>
            <button onClick={onClose} className="rounded-full bg-white px-4 py-1.5 text-sm font-semibold text-black">Close</button>
          </div>
        </div>
      </div>
    </div>
  );
}

export function ModelCard({ model }: { model: ModelId }) {
  const { responses, showReasoning } = useCouncilStore();
  const r = responses[model] || { status: "idle", final_answer: "", reasoning: null, confidence: null, latency: null };
  const isError = r.status === "error";
  const isDone = r.status === "done";
  const isGen = r.status === "generating";
  const [fs, setFs] = useState(false);

  return (
    <>
      <div className="group relative flex min-w-[320px] max-w-[420px] snap-start flex-col overflow-hidden rounded-[20px] p-[1px]">
        <div className={`absolute inset-0 rounded-[20px] ${isError ? "bg-gradient-to-b from-red-300/30 via-white/5 to-transparent" : isDone ? "bg-gradient-to-b from-white/18 via-white/6 to-transparent" : "bg-gradient-to-b from-white/12 via-white/5 to-transparent"} opacity-80`} />
        <div className="absolute inset-[1px] rounded-[19px] bg-gradient-to-b from-white/[0.04] to-transparent pointer-events-none" />
        <div className="relative flex flex-1 flex-col rounded-[19px] glass p-4 backdrop-blur-[16px]">
          <div className="pointer-events-none absolute inset-x-0 top-0 h-[1px] bg-gradient-to-r from-transparent via-white/30 to-transparent opacity-60" />
          <div className="absolute -top-10 left-1/2 h-20 w-40 -translate-x-1/2 rounded-full bg-white/5 blur-2xl" />

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className={`h-2 w-2 rounded-full ${isDone ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.7)]" : isGen ? "animate-pulse bg-sky-300 shadow-[0_0_8px_rgba(125,211,252,0.7)]" : isError ? "bg-red-400 shadow-[0_0_8px_rgba(248,113,113,0.6)]" : "bg-white/20"}`} />
              <span className="font-display text-[13px] font-semibold tracking-tight text-white">{model}</span>
            </div>
            <div className="flex items-center gap-1.5 font-mono text-[11px] text-white/40">
              <span className={`${isDone ? "text-emerald-300" : isError ? "text-red-300" : "text-white/40"}`}>{r.status}</span>
              {r.latency != null && <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5">{r.latency.toFixed(2)}s</span>}
              <button
                onClick={() => setFs(true)}
                disabled={!r.final_answer}
                title="Fullscreen"
                aria-label={`Open ${model} fullscreen`}
                className="ml-1 rounded-full border border-white/10 bg-white/5 p-1.5 text-white/50 hover:bg-white/10 hover:text-white disabled:opacity-30 transition"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M8 3H5a2 2 0 0 0-2 2v3m0 8v3a2 2 0 0 0 2 2h3m8-16h3a2 2 0 0 1 2 2v3m0 8v3a2 2 0 0 1-2 2h-3" /></svg>
              </button>
            </div>
          </div>

          <div className="mt-3">
            <ConfidenceBar value={r.confidence} />
          </div>

          {showReasoning && r.reasoning && (
            <details className="group/reason mt-3 rounded-[12px] border border-white/8 bg-white/[0.04] p-2 backdrop-blur-md open:bg-white/[0.06]">
              <summary className="flex cursor-pointer list-none items-center gap-1.5 font-mono text-[11px] tracking-wide text-sky-200/70">
                <span className="transition group-open/reason:rotate-90">▸</span> Reasoning
              </summary>
              <pre className="mt-2 whitespace-pre-wrap break-words font-mono text-[11px] leading-4 text-white/60">{r.reasoning}</pre>
            </details>
          )}

          <div className="relative mt-3 max-h-[320px] flex-1 overflow-auto rounded-[14px] border border-white/8 bg-[#0B1224]/40 p-3.5 backdrop-blur-md">
            {r.status === "generating" && !r.final_answer ? (
              <span className="inline-flex items-center gap-2 font-mono text-xs text-white/40">
                <span className="h-3 w-3 animate-spin rounded-full border-2 border-white/20 border-t-white/60" /> generating…
              </span>
            ) : r.final_answer ? (
              <div className="prose prose-invert max-w-none prose-sm prose-p:my-1.5 prose-headings:font-display prose-headings:tracking-tight">
                <Markdown>{r.final_answer}</Markdown>
              </div>
            ) : r.status === "error" ? (
              <span className="text-sm text-red-300">Failed to generate.</span>
            ) : (
              <span className="font-mono text-xs text-white/20">Awaiting…</span>
            )}
          </div>

          {r.final_answer && (
            <button onClick={() => setFs(true)} className="mt-2 self-end rounded-full border border-white/10 bg-white/5 px-2.5 py-1 font-mono text-[11px] text-white/50 hover:bg-white/10 hover:text-white transition">
              ⛶ Fullscreen
            </button>
          )}
        </div>
      </div>
      {fs && r.final_answer && (
        <FullscreenModal model={model} final_answer={r.final_answer} reasoning={r.reasoning} confidence={r.confidence} latency={r.latency} onClose={() => setFs(false)} />
      )}
    </>
  );
}

export function ModelCards() {
  const { models } = useCouncilStore();
  return (
    <div className="flex gap-4 overflow-x-auto pb-3 snap-x snap-mandatory scrollbar-thin max-lg:grid max-lg:grid-cols-1">
      {models.map((m) => (
        <ModelCard key={m} model={m} />
      ))}
    </div>
  );
}
