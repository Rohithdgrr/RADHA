"use client";
import { useEffect, useRef } from "react";
import { useCouncilStore, ModelId } from "@/lib/store";
import { useCouncilStream } from "@/hooks/useCouncilStream";

const ALL = ["claude", "chatgpt", "gemini", "deepseek", "qwen", "kimi", "kimi-k3"] as const;
const LABELS: Record<string, string> = {
  claude: "Claude Sonnet 4",
  chatgpt: "GPT-5.5 Instant",
  gemini: "Gemini 3 Pro",
  deepseek: "DeepSeek V3.1",
  qwen: "Qwen3 Max",
  kimi: "Kimi K2.5 Instant",
  "kimi-k3": "Kimi K3 (preview)",
};

export function HeroSearch() {
  const { query, setQuery, models, toggleModel, mode, setMode, depth, setDepth, showReasoning, setShowReasoning, chairman, setChairman } = useCouncilStore();
  const { start, status, error } = useCouncilStream();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
      if (e.key === "Escape") inputRef.current?.blur();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    start();
  };

  return (
    <form onSubmit={onSubmit} className="relative rounded-[24px] glass-strong shine-top p-[1px]">
      <div className="hero-glow" aria-hidden />
      <div className="relative rounded-[23px] glass-strong p-5">
        {/* inner highlight */}
        <div className="pointer-events-none absolute inset-0 rounded-[23px] bg-gradient-to-b from-white/[0.07] to-transparent" />

        <div className="relative flex gap-3">
          <div className="relative flex-1">
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask anything… (Ctrl+K)"
              className="w-full rounded-[16px] border border-white/10 bg-white/[0.06] px-4 py-3.5 pr-12 text-[15px] text-white placeholder:text-white/40 outline-none backdrop-blur-md transition focus:border-white/15 focus:bg-white/[0.08] focus:ring-1 focus:ring-white/10"
            />
            <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 rounded-full border border-white/10 bg-white/5 px-2 py-1 font-mono text-[10px] tracking-wide text-white/40">⌘K</span>
          </div>
          <button
            type="submit"
            disabled={status === "streaming" || !query.trim() || models.length < 2}
            className="relative inline-flex items-center justify-center rounded-[16px] bg-white px-7 py-3.5 text-sm font-semibold tracking-tight text-black shadow-[0_4px_24px_rgba(255,255,255,0.18),inset_0_1px_0_rgba(255,255,255,0.6)] transition hover:bg-white/95 disabled:opacity-40 disabled:shadow-none"
          >
            <span className="relative">{status === "streaming" ? "Streaming…" : "Search"}</span>
          </button>
        </div>

        <div className="relative mt-4 flex flex-wrap gap-2">
          {ALL.map((m) => {
            const active = models.includes(m as ModelId);
            return (
              <button
                key={m}
                type="button"
                onClick={() => toggleModel(m as ModelId)}
                title={m}
                className={`group relative rounded-full px-3.5 py-1.5 text-xs font-medium backdrop-blur-md transition ${
                  active
                    ? "bg-white text-black shadow-[0_2px_16px_rgba(255,255,255,0.22)]"
                    : "border border-white/12 bg-white/[0.05] text-white/70 hover:bg-white/[0.08] hover:text-white"
                }`}
              >
                {active && <span className="absolute inset-0 rounded-full bg-gradient-to-b from-white to-white/90 opacity-0 group-hover:opacity-100 transition" />}
                <span className="relative">{LABELS[m] || m}</span>
              </button>
            );
          })}
        </div>
        <div className="relative mt-2 font-mono text-[11px] tracking-wide text-white/30">Kimi K2.5 default • Kimi K3 for 256k preview • All versions in docs/API-CONFIG.md</div>

        <div className="relative mt-4 grid gap-3 md:grid-cols-4">
          {[
            { label: "Mode", value: mode, onChange: (v: string) => setMode(v as any), options: ["consensus","debate","specialist","weighted"] },
            { label: "Depth", value: depth, onChange: (v: string) => setDepth(v as any), options: ["brief","standard","detailed"] },
            { label: "Chairman", value: chairman, onChange: (v: string) => setChairman(v as any), options: [...ALL] },
          ].map((f) => (
            <label key={f.label} className="flex flex-col gap-1.5">
              <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-white/40">{f.label}</span>
              <select
                value={f.value}
                onChange={(e) => f.onChange(e.target.value)}
                className="rounded-[12px] border border-white/10 bg-white/[0.06] px-3 py-2.5 text-sm text-white/90 backdrop-blur-md outline-none focus:border-white/15"
              >
                {f.options.map((o) => (
                  <option key={o} value={o} className="bg-[#0B1224]">{o}</option>
                ))}
              </select>
            </label>
          ))}
          <label className="flex items-end gap-2 pb-2">
            <input type="checkbox" checked={showReasoning} onChange={(e) => setShowReasoning(e.target.checked)} className="h-4 w-4 rounded border-white/20 bg-white/10 accent-white" />
            <span className="text-sm text-white/70">Show reasoning</span>
          </label>
        </div>

        {error && <div className="relative mt-3 rounded-[12px] border border-red-400/20 bg-red-500/[0.08] px-3 py-2 text-sm text-red-200 backdrop-blur-md">{error}</div>}
        <div className="relative mt-3 flex items-center gap-2 font-mono text-[11px] text-white/30">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400/70 shadow-[0_0_8px_rgba(52,211,153,0.6)]" />
          Selected {models.length} (min 2, max 8) • <span className="capitalize text-white/50">{status}</span>
        </div>
      </div>
    </form>
  );
}
