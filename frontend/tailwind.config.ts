import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#3b5bdb",
          dark: "#2f4ab8",
        },
      },
    },
  },
  plugins: [],
};

export default config;
