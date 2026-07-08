import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef1fd",
          100: "#dde3fb",
          200: "#b8c4f5",
          300: "#8fa0ee",
          400: "#6178e5",
          500: "#3b5bdb",
          DEFAULT: "#3b5bdb",
          600: "#2f4ab8",
          dark: "#2f4ab8",
          700: "#263c94",
          800: "#1e2f74",
          900: "#182658",
        },
      },
      boxShadow: {
        soft: "0 1px 2px rgba(15, 23, 42, 0.04), 0 4px 16px rgba(15, 23, 42, 0.06)",
        softer: "0 1px 2px rgba(15, 23, 42, 0.03), 0 2px 8px rgba(15, 23, 42, 0.04)",
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(2px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.15s ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
