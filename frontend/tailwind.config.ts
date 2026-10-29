import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: "#07090e",
          secondary: "#0d1117",
          tertiary: "#161b22",
          elevated: "#1c2128",
        },
        border: {
          subtle: "#21262d",
          muted: "#30363d",
          glow: "rgba(239, 68, 68, 0.2)",
        },
        crimson: {
          DEFAULT: "#dc2626",
          glow: "#ef4444",
          dark: "#991b1b",
          light: "#f87171",
        },
        severity: {
          critical: "#ef4444",
          high: "#f97316",
          medium: "#eab308",
          low: "#3b82f6",
          info: "#6b7280",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "Courier New", "monospace"],
      },
      boxShadow: {
        "crimson-glow": "0 0 20px -5px rgba(220, 38, 38, 0.3)",
        "card-subtle": "0 1px 3px 0 rgba(0, 0, 0, 0.4), 0 1px 2px -1px rgba(0, 0, 0, 0.4)",
      },
    },
  },
  plugins: [],
};

export default config;
