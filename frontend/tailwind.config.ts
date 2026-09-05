import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: "#EEF3ED",
        surface: "#FFFFFF",
        elevated: "#E3EDE4",
        cream: "#F4EEDC",
        line: "#DCE5DC",
        "line-subtle": "#E6E9E0",
        input: "#FFFFFF",
        ink: "#3F4743",
        "ink-2": "#6A726C",
        "ink-3": "#98A099",
        accent: "#18B7A5",
        "accent-strong": "#0F9D8C",
        mint: "#59B99B",
        "mint-soft": "#DFF0E9",
        turquoise: "#2FC6B2",
        highlight: "#F5EFCF",
        error: "#DC2626",
        success: "#3E7D4E",
        warn: "#B08115",
      },
      borderRadius: {
        card: "16px",
        btn: "14px",
      },
      boxShadow: {
        soft: "0 4px 24px rgba(63, 71, 67, 0.08)",
        lift: "0 14px 36px rgba(24, 183, 165, 0.18)",
      },
    },
  },
  plugins: [],
};
export default config;
