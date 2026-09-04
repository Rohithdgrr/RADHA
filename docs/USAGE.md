# 🧑‍💻 Usage Guide

This guide explains how to use the AI Council website effectively.

## Getting Started

1.  Navigate to `http://localhost:3000` (or your deployed URL).
2.  You'll see a hero search bar with a dark theme and cyan accents.
3.  **Select Council Members**: Below the search bar, toggle which models you want to include (minimum 2, maximum 8).
4.  **Choose a Mode**: Select from Consensus (default), Debate, Specialist, or Weighted Voting.
5.  **Optional Settings**: Enable "Show Reasoning" to see each model's `<reasoning>` block, and set "Analysis Depth" to Brief, Standard, or Detailed.
6.  Type your query and hit **Enter** or click the **Search** button.

## Understanding the Results Page

After submission, the page transitions to a results layout:

### 1. Unified Answer (Top Section)
- **Sparkle Icon** ✨ + "Answer" heading.
- The Chairman's synthesized final answer is displayed here.
- Below the answer, you will see:
  - ✅ **Where models agree** – A bulleted list of common points.
  - ⚠️ **Where models diverge** – Explanations of disagreements and why they occurred.
  - 💡 **Unique insights** – Points raised by only one model.

### 2. Model Response Cards (Bottom Section)
- Each selected model is displayed in a horizontally scrollable grid (or vertical stack on mobile).
- Each card contains:
  - Model name and icon.
  - Latency (time to respond).
  - **Full, unabridged response** – Scrollable inside the card.
  - If "Show Reasoning" is enabled, a dedicated `<reasoning>` section appears above the final answer.
  - If "Debate Mode" is enabled, a **Critique** section is appended.
- **Confidence Score** – A visual progress bar indicating the model's self-reported confidence.

### 3. Transcript Download
- A **"Download Full Report"** button at the top exports the entire session as a `.txt` or `.html` file, containing all responses, critiques, and the synthesis.

## Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Ctrl + K` | Focus the search bar (global). |
| `Esc` | Close modals / clear selection. |
| `Enter` | Submit query. |

## Managing Sessions (no login required)

- All sessions are stored anonymously and appear automatically in the **"History"** sidebar (recent 20, `GET /council/sessions`).
- No account needed — history is per-browser + server-persisted via `sqlite` (or PG). Clear via `DELETE /council/session/{id}`.
- You can share a session via a unique URL (e.g., `/council/abc-123`) — anyone with the link can replay.
- **Login needed only at `arena.ai`** to refresh `arena-auth-prod-v1` if `Token expired`.

## Troubleshooting

| Issue | Solution |
| :--- | :--- |
| "Model unavailable" | The model is offline or rate-limited. The system will retry automatically. |
| "Token expired" | Your LMArena auth token has expired. Follow the [SETUP.md](./SETUP.md) guide to refresh it. |
| "Slow responses" | Some models (e.g., Gemini) are inherently slower. You can disable them in the model selector. |
