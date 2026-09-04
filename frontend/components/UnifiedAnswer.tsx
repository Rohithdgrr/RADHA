"use client";
import { useCouncilStore } from "@/lib/store";
import { Markdown } from "@/components/Markdown";

export function UnifiedAnswer() {
  const { synthesis, agreements, divergences, uniqueInsights, status, totalLatency } = useCouncilStore();
  if (status === "idle") return null;
  if (status === "streaming" && !synthesis) {
    return (
      <div className="relative overflow-hidden rounded-[20px] p-[1px]">
        <div className="absolute inset-0 rounded-[20px] bg-gradient-to-b from-white/12 to-transparent" />
        <div className="relative rounded-[19px] glass p-6">
          <div className="flex items-center gap-3 font-mono text-sm text-white/60">
            <span className="h-2 w-2 animate-pulse rounded-full bg-sky-300 shadow-[0_0_10px_rgba(125,211,252,0.7)]" />
            Chairman is synthesizing…
          </div>
          <div className="mt-4 h-2 w-3/4 animate-pulse rounded-full bg-white/10" />
          <div className="mt-2 h-2 w-1/2 animate-pulse rounded-full bg-white/5" />
        </div>
      </div>
    );
  }
  if (!synthesis) return null;
  return (
    <div className="relative overflow-hidden rounded-[24px] p-[1px]">
      <div className="absolute inset-0 rounded-[24px] bg-gradient-to-b from-sky-200/20 via-violet-200/12 to-transparent opacity-80" />
      <div className="absolute inset-[1px] rounded-[23px] bg-gradient-to-b from-white/[0.06] to-transparent pointer-events-none" />
      <div className="relative rounded-[23px] glass-strong shine-top p-6">
        <div className="flex items-start justify-between gap-4">
          <h2 className="font-display flex items-center gap-2.5 text-[18px] font-semibold tracking-tight text-white">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-white text-[14px] text-black shadow-[0_2px_12px_rgba(255,255,255,0.25)]">✦</span>
            Answer
            <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 font-mono text-[10px] font-normal tracking-[0.12em] text-white/50">SYNTHESIS</span>
          </h2>
          {totalLatency && <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 font-mono text-[11px] text-white/40">{totalLatency.toFixed(2)}s</span>}
        </div>

        <div className="mt-4">
          <Markdown>{synthesis}</Markdown>
        </div>

        {(agreements || divergences || (uniqueInsights && uniqueInsights.length > 0)) && (
          <div className="mt-6 grid gap-3 md:grid-cols-3">
            {agreements && (
              <div className="rounded-[16px] border border-emerald-300/15 bg-emerald-400/[0.06] p-3.5 backdrop-blur-md">
                <div className="flex items-center gap-1.5 font-mono text-[11px] font-medium tracking-wide text-emerald-300"> <span>◆</span> Where models agree</div>
                <div className="mt-2 text-sm leading-5 text-white/70">
                  <Markdown>{agreements}</Markdown>
                </div>
              </div>
            )}
            {divergences && (
              <div className="rounded-[16px] border border-amber-300/15 bg-amber-400/[0.06] p-3.5 backdrop-blur-md">
                <div className="flex items-center gap-1.5 font-mono text-[11px] font-medium tracking-wide text-amber-300"> <span>◇</span> Where they diverge</div>
                <div className="mt-2 text-sm leading-5 text-white/70">
                  <Markdown>{divergences}</Markdown>
                </div>
              </div>
            )}
            {uniqueInsights && uniqueInsights.length > 0 && (
              <div className="rounded-[16px] border border-sky-300/15 bg-sky-400/[0.06] p-3.5 backdrop-blur-md">
                <div className="flex items-center gap-1.5 font-mono text-[11px] font-medium tracking-wide text-sky-300"> <span>✦</span> Unique insights</div>
                <ul className="mt-2 list-disc space-y-1 pl-4 text-sm leading-5 text-white/70">
                  {uniqueInsights.map((u, i) => (
                    <li key={i}><Markdown>{u}</Markdown></li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
