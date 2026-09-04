import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#070B16",
        surface: "rgba(255,255,255,0.06)",
        ink: "#070B16",
        fog: "#E2E8F0",
        mist: "#94A3B8",
        prism: {
          cyan: "#7DD3FC",
          violet: "#C4B5FD",
          amber: "#FCD34D",
        },
      },
      fontFamily: {
        display: ["Space Grotesk", "Instrument Sans", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      backdropBlur: {
        glass: "18px",
      },
      boxShadow: {
        glass: "0 8px 32px rgba(0,0,0,0.34), inset 0 1px 0 rgba(255,255,255,0.12)",
        "glass-strong": "0 12px 40px rgba(0,0,0,0.42), inset 0 1px 0 rgba(255,255,255,0.15)",
      },
      borderRadius: {
        glass: "20px",
        "glass-lg": "24px",
      },
      animation: {
        shimmer: "shimmer 2.2s ease-in-out infinite",
      },
      keyframes: {
        shimmer: {
          "0%": { opacity: "0.55" },
          "50%": { opacity: "1" },
          "100%": { opacity: "0.55" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
