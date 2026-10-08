import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        mint: {
          50: "#ECFDF5",
          100: "#D1FAE5",
          200: "#A7F3D0",
          300: "#6EE7B7",
          400: "#34D399",
          500: "#00E599",
          600: "#05CD8B",
          700: "#047857",
          800: "#065F46",
          900: "#064E3B",
          DEFAULT: "#00E599"
        }
      },
      boxShadow: {
        glass: "0 12px 36px 0 rgba(31, 38, 135, 0.06)",
        "glass-lg": "0 20px 48px 0 rgba(15, 23, 42, 0.08)"
      }
    },
  },
  plugins: [],
};

export default config;
