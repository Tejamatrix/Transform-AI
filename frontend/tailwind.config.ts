import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: "#F5F6F8",
        surface: "#FFFFFF",
        elevated: "#EEF1F5",
        cream: "#EDF0FB",
        line: "#DFE4EB",
        "line-subtle": "#E7EAF0",
        input: "#FFFFFF",
        ink: "#2E3440",
        "ink-2": "#646B7A",
        "ink-3": "#969DAB",
        accent: "#5B8DEF",
        "accent-strong": "#3D74E0",
        mint: "#7BE0D3",
        "mint-soft": "#E0F5F1",
        turquoise: "#2DD4BF",
        violet: "#A78BFA",
        highlight: "#ECEAFE",
        error: "#DC2626",
        success: "#16A34A",
        warn: "#D97706",
      },
      borderRadius: {
        card: "16px",
        btn: "14px",
      },
      boxShadow: {
        soft: "0 4px 24px rgba(46, 52, 64, 0.08)",
        lift: "0 14px 36px rgba(91, 141, 239, 0.2)",
      },
    },
  },
  plugins: [],
};
export default config;
