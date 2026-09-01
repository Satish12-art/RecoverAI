import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0f1117",
        surface: "#1a1d27",
        "surface-border": "#2a2d3a",
        primary: "#6366f1",
        "primary-hover": "#4f46e5",
        success: "#10b981",
        warning: "#f59e0b",
        danger: "#ef4444",
      },
    },
  },
  plugins: [],
};
export default config;
