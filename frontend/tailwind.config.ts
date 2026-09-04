import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0B0B0C",
        surface: "#121214",
        elevated: "#1A1A1D",
        line: "#232326",
        "line-subtle": "#1F1F23",
        input: "#0F0F11",
        ink: "#FFFFFF",
        "ink-2": "#A1A1AA",
        "ink-3": "#6B7280",
        accent: "#3B82F6",
        error: "#DC2626",
        success: "#16A34A",
        warn: "#D97706",
      },
      borderRadius: {
        card: "12px",
        btn: "10px",
      },
    },
  },
  plugins: [],
};
export default config;
