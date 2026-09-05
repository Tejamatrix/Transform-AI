import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: "#EEF3ED",
        surface: "#FFFFFF",
        elevated: "#E3EEE6",
        cream: "#F4EEDC",
        line: "#D8E2D8",
        "line-subtle": "#E4E9E1",
        input: "#FFFFFF",
        ink: "#3F4743",
        "ink-2": "#6A726C",
        "ink-3": "#98A099",
        accent: "#18B7A5",
        "accent-strong": "#0F9C8C",
        mint: "#59B99B",
        "mint-soft": "#DFF0E7",
        turquoise: "#18B7A5",
        highlight: "#F5EFCF",
        error: "#D2544A",
        success: "#3E8E5C",
        warn: "#C08A2D",
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
