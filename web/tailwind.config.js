/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#0f1c2e",
        paper: "#f3efe6",
        mist: "#d9e2ec",
        accent: "#c45c26",
        sea: "#1a5f7a",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      backgroundImage: {
        "grid-fade":
          "radial-gradient(ellipse at 20% 0%, rgba(26,95,122,0.12), transparent 50%), radial-gradient(ellipse at 90% 20%, rgba(196,92,38,0.1), transparent 45%)",
      },
    },
  },
  plugins: [],
};
