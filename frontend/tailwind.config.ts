import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: "#FAF8F3",
        surface: "#FFFFFF",
        elevated: "#F1F7F3",
        cream: "#F6F1E7",
        line: "#E2E8E2",
        "line-subtle": "#ECE9E1",
        input: "#FFFFFF",
        ink: "#232620",
        "ink-2": "#5C6259",
        "ink-3": "#8B9187",
        accent: "#0D9488",
        "accent-strong": "#0B7C72",
        mint: "#BFEAD9",
        "mint-soft": "#E6F6EF",
        turquoise: "#14B8A6",
        error: "#DC2626",
        success: "#15803D",
        warn: "#B45309",
      },
      borderRadius: {
        card: "16px",
        btn: "14px",
      },
      boxShadow: {
        soft: "0 4px 24px rgba(35, 38, 32, 0.07)",
        lift: "0 14px 36px rgba(13, 148, 136, 0.16)",
      },
    },
  },
  plugins: [],
};
export default config;
