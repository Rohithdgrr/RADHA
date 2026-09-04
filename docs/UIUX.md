# 🎨 UI/UX Design Philosophy

The AI Council website is designed to be **minimalist, research-focused, and transparent** – heavily inspired by Perplexity AI.

## Design Principles

1.  **Clarity Over Complexity**: The user's primary action is to search. Everything else is secondary.
2.  **Transparency**: Show the user exactly what each model produced. No black boxes.
3.  **Dark Theme**: Reduces eye strain during extended research sessions.
4.  **Responsive**: Works flawlessly on desktop, tablet, and mobile.

## Color Palette

| Element | Color (Tailwind) | Hex |
| :--- | :--- | :--- |
| Background | `gray-900` | `#111827` |
| Surface (cards) | `gray-800` | `#1F2937` |
| Primary Accent | `cyan-500` | `#00BFFF` |
| Text (primary) | `gray-100` | `#F3F4F6` |
| Text (muted) | `gray-400` | `#9CA3AF` |
| Success | `emerald-500` | `#10B981` |
| Warning | `amber-500` | `#F59E0B` |
| Danger | `red-500` | `#EF4444` |

## Typography

- **Headings**: Inter (sans-serif), bold, large.
- **Body**: Inter, regular, 16px.
- **Monospace**: JetBrains Mono (for code snippets and reasoning blocks).

## Layout Components

### 1. Search Bar (Hero)
- Centered on the page.
- Large input field with rounded corners and subtle glow on focus.
- Below: Model selector toggles (horizontal pill buttons).

### 2. Unified Answer Section
- Positioned at the top of the results.
- Headed by a "Sparkle" icon (`✨`) and the word "Answer".
- Uses a **slightly larger font** to distinguish from model cards.
- Bulleted lists for "Agree", "Diverge", "Unique Insights".

### 3. Model Cards
- Horizontal scroll (desktop) / vertical stack (mobile).
- Each card has a **header** with model name, latency, and status (done/generating).
- A **scrollable text area** for the full response.
- If reasoning is enabled, an expandable `<details>` element reveals the reasoning block.

### 4. Status Indicators
- **Spinning dots** (`...`) while a model is generating.
- **Green checkmark** (`✅`) when done.
- **Red exclamation** (`❌`) if failed (with retry button).

## User Flows

### Flow 1: New Query
1.  User types query → presses Enter.
2.  Search bar collapses slightly; model cards begin to appear with loading spinners.
3.  As each model finishes, its card populates.
4.  Once all models finish, the Chairman synthesis starts.
5.  The unified answer section appears at the top.
6.  The user can scroll down to inspect individual model responses.

### Flow 2: Revisiting History
1.  User clicks "History" sidebar icon.
2.  List of past sessions appears (chronological).
3.  Clicking a session reloads the entire council view with all responses and the synthesis.

## Accessibility (WCAG 2.1 AA)

- All interactive elements are keyboard-navigable (tab order).
- Color contrast ratios are above 4.5:1 for all text.
- ARIA labels on buttons and dynamic content.
- Support for screen readers (VoiceOver, NVDA).

## Responsive Breakpoints

| Breakpoint | Layout |
| :--- | :--- |
| < 640px (mobile) | Single column, model cards stacked vertically. |
| 640px - 1024px (tablet) | Model cards in 2-column grid. |
| > 1024px (desktop) | Model cards in horizontal scroll (up to 8 visible). |
