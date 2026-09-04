"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { API_URL } from "@/lib/api";

type Item = { id: string; user_query: string; created_at: string; status: string };

export function HistorySidebar() {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/council/sessions?limit=20`)
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data.items)) setItems(data.items);
        else if (Array.isArray(data)) setItems(data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <aside className="relative overflow-hidden rounded-[20px] p-[1px] lg:sticky lg:top-6 self-start">
      <div className="absolute inset-0 rounded-[20px] bg-gradient-to-b from-white/10 to-white/5 opacity-60" />
      <div className="relative rounded-[19px] glass p-4 backdrop-blur-[16px]">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent" />
        <div className="flex items-center justify-between">
          <span className="font-display text-[13px] font-semibold tracking-tight text-white">History</span>
          <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 font-mono text-[10px] tracking-wide text-white/40">{items.length} sessions</span>
        </div>
        {loading ? (
          <div className="mt-4 space-y-2">
            <div className="h-12 animate-pulse rounded-[12px] bg-white/5" />
            <div className="h-12 animate-pulse rounded-[12px] bg-white/5" />
          </div>
        ) : items.length === 0 ? (
          <div className="mt-6 rounded-[14px] border border-dashed border-white/10 bg-white/[0.02] p-6 text-center">
            <div className="mx-auto flex h-8 w-8 items-center justify-center rounded-full bg-white/5 text-white/30">◯</div>
            <p className="mt-2 font-mono text-xs text-white/30">No history yet.</p>
            <p className="mt-1 text-xs leading-4 text-white/20">Your councils will appear here as frosted traces.</p>
          </div>
        ) : (
          <ul className="mt-3 space-y-2">
            {items.map((it) => (
              <li key={it.id}>
                <Link href={`/council/${it.id}`} className="group block rounded-[14px] border border-white/8 bg-white/[0.04] p-3 backdrop-blur-md transition hover:border-white/15 hover:bg-white/[0.07]">
                  <div className="line-clamp-2 text-sm leading-5 text-white/80 group-hover:text-white">{it.user_query}</div>
                  <div className="mt-1.5 flex items-center gap-1.5 font-mono text-[11px] text-white/30">
                    <span className={`h-1.5 w-1.5 rounded-full ${it.status === "done" ? "bg-emerald-400" : it.status === "error" ? "bg-red-400" : "bg-white/30"}`} />
                    <span>{new Date(it.created_at).toLocaleString()} • {it.status}</span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
