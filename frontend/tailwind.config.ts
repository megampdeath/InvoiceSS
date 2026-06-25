import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172033",
        line: "#D8DEE8",
        panel: "#F7F9FC",
        signal: "#0F766E",
        berry: "#9F1239",
        sun: "#B7791F"
      },
      boxShadow: {
        soft: "0 10px 30px rgba(23, 32, 51, 0.08)"
      }
    }
  },
  plugins: []
};

export default config;
