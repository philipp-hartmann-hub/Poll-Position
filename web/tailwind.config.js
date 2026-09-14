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
        ink: "#e8eaed",
        paper: "#17191d",
        mist: "#23262b",
        accent: "#d77842",
        sea: "#26d997",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      backgroundImage: {
        "grid-fade":
          "radial-gradient(ellipse at 20% 0%, rgba(38,217,151,0.10), transparent 50%), radial-gradient(ellipse at 90% 20%, rgba(215,120,66,0.10), transparent 45%)",
      },
    },
  },
  plugins: [],
};
