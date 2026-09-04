# ⚙️ How the AI Council Works

This document explains the **step-by-step orchestration** of the AI Council – from user query to final synthesized answer.

## 🔄 The Three-Stage Pipeline

### Stage 1: Parallel Generation (Fan-Out)

1.  User submits a query via the frontend Search Bar.
2.  Backend receives the query and the list of selected models (e.g., Claude, ChatGPT, Gemini).
3.  For each selected model, the backend creates an asynchronous task.
4.  All tasks are executed concurrently using `asyncio.gather()` to minimize total latency.
5.  Each task sends a request to LMArenaBridge (which translates it to LMArena's format and streams the response).
6.  The backend collects **the full, unabridged response** from each model, along with metadata (latency, confidence, token count).

**Prompt Engineering for Thinking:**

Each model receives a system prompt instructing it to output its reasoning inside an XML `<reasoning>` tag before the final `<answer>` tag. This simulates "chain-of-thought" visibility.

### Stage 2: Peer Review & Critique (Optional)

If "Debate Mode" is enabled:

1.  After all responses are collected, the backend randomly assigns each model to review another model's answer.
2.  A dedicated critic prompt is sent: *"Review the answer from [Model X]. Provide strengths, weaknesses, missing context, and a score out of 10."*
3.  Critiques are collected and stored alongside the original responses.

### Stage 3: Synthesis (Chairman / Fan-In)

1.  A designated "Chairman" model (configurable – defaults to Claude) receives a synthesis prompt:
    > *"You are the chair of an AI council. Here are responses from [Model A, B, C] regarding: '[User Query]'. Synthesize a unified final answer. Explicitly state: (1) Where all models agree, (2) Where they diverge and why, (3) Any unique insights from individual models."*
2.  The Chairman model generates the final unified answer.
3.  The backend packages everything – the unified answer, agreements/divergences, unique insights, and each model's full response – into a single JSON payload.
4.  This payload is streamed back to the frontend via Server-Sent Events (SSE).

## 📡 Real-Time Event Streaming

The backend emits the following event types to the frontend:

| Event Type | Description |
| :--- | :--- |
| `model_start` | A model has begun processing. |
| `model_stream` | A token chunk from a model's response. |
| `model_done` | A model's full response is complete. |
| `critique_done` | A peer review/critique is complete. |
| `synthesis_start` | Chairman synthesis has begun. |
| `synthesis_stream` | Token chunk from the synthesized answer. |
| `done` | Entire council process is complete. |

## 🧮 Consensus Algorithms

| Mode | Logic |
| :--- | :--- |
| **Consensus (Default)** | Chairman synthesizes based on all responses. |
| **Majority Voting** | Simple textual overlap – the most common answer is chosen. |
| **Confidence Weighting** | Each model self-reports confidence (0-100). Weighted average determines final answer. |
| **Debate** | Models critique each other; Chairman uses critiques to refine the final answer. |

## 🔗 LMArenaBridge Integration

- The backend communicates with LMArenaBridge via its OpenAI-compatible `/v1/chat/completions` endpoint.
- WebSockets are used for low-latency streaming.
- Each model is assigned a **unique session ID** to prevent context leakage.
- Authentication is handled via the `arena-auth-prod-v1` cookie token, stored securely in environment variables.
