"use client";

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function inlineFormat(text: string): string {
  // Escape first, then apply inline markdown
  let t = escapeHtml(text);
  // inline code `code`
  t = t.replace(/`([^`]+?)`/g, '<code class="rounded bg-white/10 px-1.5 py-0.5 font-mono text-xs text-white/90">$1</code>');
  // bold **text**
  t = t.replace(/\*\*([^*]+?)\*\*/g, '<strong class="font-semibold text-white">$1</strong>');
  // italic *text* (avoid **)
  t = t.replace(/(?<!\*)\*([^*]+?)\*(?!\*)/g, '<em class="italic text-white/80">$1</em>');
  // also _italic_
  t = t.replace(/_([^_]+?)_/g, '<em class="italic text-white/80">$1</em>');
  // links [text](url)
  t = t.replace(/\[([^\]]+?)\]\(([^)]+?)\)/g, '<a href="$2" target="_blank" rel="noopener" class="text-sky-300 underline decoration-sky-300/30 underline-offset-2 hover:text-sky-200">$1</a>');
  return t;
}

function renderTable(lines: string[], start: number): { html: string; next: number } {
  // Header row
  const header = lines[start].trim();
  const sep = lines[start + 1]?.trim() || "";
  if (!header.includes("|") || !sep.includes("|") || !sep.includes("-")) {
    return { html: `<p class="my-2 leading-6 text-white/85">${inlineFormat(header)}</p>`, next: start + 1 };
  }
  const headers = header.split("|").map((c) => c.trim()).filter(Boolean);
  let html = '<div class="my-3 overflow-x-auto rounded-[12px] border border-white/10"><table class="w-full text-sm"><thead><tr>';
  headers.forEach((h) => { html += `<th class="bg-white/5 px-3 py-2 text-left font-mono text-xs font-semibold tracking-wide text-white/60 border-b border-white/10">${inlineFormat(h)}</th>`; });
  html += '</tr></thead><tbody>';
  let i = start + 2;
  while (i < lines.length && lines[i].includes("|") && lines[i].trim() !== "") {
    const cells = lines[i].split("|").map((c) => c.trim()).filter(Boolean);
    if (cells.length === 0) { i++; continue; }
    html += '<tr>';
    cells.forEach((c) => { html += `<td class="px-3 py-2 text-white/75 border-b border-white/5">${inlineFormat(c)}</td>`; });
    // pad if row shorter than header
    for (let k = cells.length; k < headers.length; k++) html += `<td class="px-3 py-2 border-b border-white/5"></td>`;
    html += '</tr>';
    i++;
  }
  html += '</tbody></table></div>';
  return { html, next: i };
}

function markdownToHtml(md: string): string {
  const lines = md.split("\n");
  let html = "";
  let i = 0;
  let inCodeBlock = false;
  let codeLang = "";
  let codeBuf: string[] = [];
  let inList = false;
  let listType: "ul" | "ol" | null = null;

  const flushList = () => {
    if (inList) {
      html += listType === "ol" ? '</ol>' : '</ul>';
      inList = false;
      listType = null;
    }
  };

  while (i < lines.length) {
    let line = lines[i];
    const trimmed = line.trim();

    // Code fence
    if (trimmed.startsWith("```")) {
      if (!inCodeBlock) {
        inCodeBlock = true;
        codeLang = trimmed.slice(3).trim();
        codeBuf = [];
        flushList();
      } else {
        inCodeBlock = false;
        const code = escapeHtml(codeBuf.join("\n"));
        html += `<pre class="my-3 overflow-x-auto rounded-[12px] border border-white/10 bg-[#0B1224]/60 p-3"><code class="font-mono text-xs leading-5 text-white/80">${code}</code></pre>`;
        codeBuf = [];
      }
      i++;
      continue;
    }
    if (inCodeBlock) {
      codeBuf.push(line);
      i++;
      continue;
    }

    // Empty line -> close list if needed, add break
    if (trimmed === "") {
      flushList();
      i++;
      continue;
    }

    // Table detection (look ahead)
    if (trimmed.includes("|") && i + 1 < lines.length && lines[i + 1].includes("|") && lines[i + 1].includes("-")) {
      flushList();
      const res = renderTable(lines, i);
      html += res.html;
      i = res.next;
      continue;
    }

    // Headings
    if (trimmed.startsWith("### ")) {
      flushList();
      html += `<h3 class="font-display text-base font-semibold tracking-tight text-white mt-4 mb-2">${inlineFormat(trimmed.slice(4))}</h3>`;
      i++; continue;
    }
    if (trimmed.startsWith("## ")) {
      flushList();
      html += `<h2 class="font-display text-lg font-semibold tracking-tight text-white mt-4 mb-2">${inlineFormat(trimmed.slice(3))}</h2>`;
      i++; continue;
    }
    if (trimmed.startsWith("# ")) {
      flushList();
      html += `<h1 class="font-display text-xl font-semibold tracking-tight text-white mt-4 mb-2">${inlineFormat(trimmed.slice(2))}</h1>`;
      i++; continue;
    }
    if (trimmed.startsWith("#### ")) {
      flushList();
      html += `<h4 class="font-display text-sm font-semibold tracking-tight text-white mt-3 mb-1.5">${inlineFormat(trimmed.slice(5))}</h4>`;
      i++; continue;
    }

    // Horizontal rule
    if (/^---+$/.test(trimmed) || /^\*\*\*+$/.test(trimmed)) {
      flushList();
      html += '<hr class="my-4 border-white/10" />';
      i++; continue;
    }

    // Blockquote
    if (trimmed.startsWith("> ")) {
      flushList();
      let bqLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith("> ")) {
        bqLines.push(lines[i].trim().slice(2));
        i++;
      }
      html += `<blockquote class="my-3 border-l-2 border-white/15 bg-white/[0.04] pl-4 py-2 italic text-white/70">${bqLines.map(inlineFormat).join("<br/>")}</blockquote>`;
      continue;
    }

    // List item
    const ulMatch = trimmed.match(/^[-*]\s+(.*)/);
    const olMatch = trimmed.match(/^\d+\.\s+(.*)/);
    if (ulMatch || olMatch) {
      const isOl = !!olMatch;
      const content = ulMatch ? ulMatch[1] : olMatch![1];
      const curType = isOl ? "ol" : "ul";
      if (!inList || listType !== curType) {
        flushList();
        html += curType === "ol" ? '<ol class="my-2 list-decimal pl-5 space-y-1 text-white/80">' : '<ul class="my-2 list-disc pl-5 space-y-1 text-white/80">';
        inList = true;
        listType = curType;
      }
      html += `<li class="leading-6">${inlineFormat(content)}</li>`;
      i++;
      continue;
    } else {
      flushList();
    }

    // Paragraph (collect consecutive non-empty non-special lines as one paragraph, but our mock often has single line paragraphs)
    // If next line is not special and not empty, we could join, but for simplicity each line as paragraph
    // However for markdown like "**What it is:** ..." we want paragraph
    html += `<p class="my-2 leading-6 text-white/85">${inlineFormat(trimmed)}</p>`;
    i++;
  }
  flushList();
  // Close any remaining code block (should not happen)
  if (inCodeBlock) {
    const code = escapeHtml(codeBuf.join("\n"));
    html += `<pre class="my-3 overflow-x-auto rounded-[12px] border border-white/10 bg-[#0B1224]/60 p-3"><code class="font-mono text-xs leading-5 text-white/80">${code}</code></pre>`;
  }
  return html;
}

export function Markdown({ children }: { children: string }) {
  const html = markdownToHtml(children || "");
  return <div className="markdown" dangerouslySetInnerHTML={{ __html: html }} />;
}
