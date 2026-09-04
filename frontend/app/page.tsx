"use client";
import { HeroSearch } from "@/components/HeroSearch";
import { UnifiedAnswer } from "@/components/UnifiedAnswer";
import { ModelCards } from "@/components/ModelCard";
import { HistorySidebar } from "@/components/HistorySidebar";
import { useCouncilStore } from "@/lib/store";

function DownloadReport() {
  const { sessionId, query, synthesis, responses } = useCouncilStore();
  if (!sessionId || !synthesis) return null;
  const onDownload = () => {
    const html = `<html><head><meta charset="utf-8"><style>body{font-family: 'Space Grotesk', sans-serif; background:#070B16; color:#E2E8F0; padding:32px} h1{font-size:28px} pre{white-space:pre-wrap; background:rgba(255,255,255,0.06); padding:16px; border-radius:12px; border:1px solid rgba(255,255,255,0.08)}</style></head><body><h1>AI Council Report</h1><p><b>Query:</b> ${query}</p><h2>Synthesis</h2><pre>${synthesis}</pre><h2>Models</h2>${Object.entries(responses)
      .map(([m, r]: any) => `<h3>${m}</h3><pre>${r.final_answer || ""}</pre>`)
      .join("")}</body></html>`;
    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `report-${sessionId}.html`;
    a.click();
    URL.revokeObjectURL(url);
  };
  return (
    <button onClick={onDownload} className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.06] px-4 py-2 text-sm font-medium text-white backdrop-blur-md transition hover:bg-white/10 hover:border-white/18">
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-white text-black text-xs">↓</span>
      Download Full Report
    </button>
  );
}

export default function Home() {
  const { status } = useCouncilStore();
  const showResults = status !== "idle";
  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <header className="flex items-end justify-between gap-6">
        <div>
          <h1 className="font-display text-[32px] font-bold tracking-tight text-white">
            AI Council<span className="ml-2 align-super rounded-full border border-white/10 bg-white/5 px-2 py-0.5 font-mono text-[10px] font-medium tracking-[0.12em] text-white/40">PERPLEXITY STYLE</span>
          </h1>
          <p className="mt-1 max-w-[560px] text-sm leading-5 text-white/50">A frosted council chamber — six models deliberate in parallel, light passes through each pane.</p>
        </div>
        <div className="hidden md:flex items-center gap-2 rounded-full border border-white/8 bg-white/[0.04] px-3 py-1.5 backdrop-blur-md">
          <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]" />
          <span className="font-mono text-[11px] tracking-wide text-white/40">{process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}</span>
        </div>
      </header>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-6">
          <HeroSearch />
          {showResults && (
            <>
              <div className="flex justify-end"><DownloadReport /></div>
              <UnifiedAnswer />
              <ModelCards />
            </>
          )}
        </div>
        <HistorySidebar />
      </div>

      <footer className="mx-auto mt-12 max-w-xl text-center font-mono text-[11px] leading-4 text-white/20">
        Frosted glass partitions • shining edges encode state • backdrop blur 18px • reduced-motion respected
      </footer>
    </main>
  );
}
