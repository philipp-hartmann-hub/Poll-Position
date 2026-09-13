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
        mist: "#cfc3ab",
        accent: "#8f5510",
        sea: "#06563f",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      backgroundImage: {
        "grid-fade":
          "radial-gradient(ellipse at 20% 0%, rgba(6,86,63,0.14), transparent 50%), radial-gradient(ellipse at 90% 20%, rgba(143,85,16,0.12), transparent 45%)",
      },
    },
  },
  plugins: [],
};
