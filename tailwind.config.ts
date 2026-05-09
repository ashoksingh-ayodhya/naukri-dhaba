import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#eef2ff",
          100: "#e0e7ff",
          200: "#c7d2fe",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca",
          800: "#3730a3",
          900: "#1e3a8a",
          950: "#172554",
        },
        accent: {
          400: "#fb923c",
          500: "#f97316",
          600: "#ea580c",
        },
        // New vibrant palette for homepage
        brand: {
          purple: "#7c3aed",
          "purple-light": "#a855f7",
          orange: "#f97316",
          "orange-light": "#fb923c",
          cyan: "#06b6d4",
          "cyan-light": "#22d3ee",
          pink: "#ec4899",
          hero: "#06060f",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        heading: ["var(--font-heading)", "Space Grotesk", "Poppins", "ui-sans-serif", "sans-serif"],
      },
      backgroundImage: {
        "hero-radial":
          "radial-gradient(ellipse 90% 60% at 50% 50%, rgba(124,58,237,0.13) 0%, transparent 70%)",
      },
      animation: {
        "gradient-shift": "gradient-shift 5s ease-in-out infinite",
        "float-up": "float-up 3s ease-in-out infinite",
        "pulse-glow": "pulse-glow 2.5s ease-in-out infinite",
      },
      keyframes: {
        "gradient-shift": {
          "0%, 100%": { "background-position": "0% 50%" },
          "50%": { "background-position": "100% 50%" },
        },
        "float-up": {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-8px)" },
        },
        "pulse-glow": {
          "0%, 100%": { opacity: "0.6" },
          "50%": { opacity: "1" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
