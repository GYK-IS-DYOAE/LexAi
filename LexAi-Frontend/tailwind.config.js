/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx,js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        lex: {
          primary: "#7A1622",
          "primary-dark": "#5E0F19",
          grad1: "#7A1622",
          grad2: "#9C2734",
          light: "#F4F5F7",
          gray: "#18191C",
          "gray-soft": "#1E1F23",
          "gray-hover": "#222327",
        },
        primary: "#7A1622",          
        "primary-dark": "#5E0F19",    
        border: "hsl(var(--border) / <alpha-value>)",
        input: "hsl(var(--input) / <alpha-value>)",
        ring: "hsl(var(--ring) / <alpha-value>)",
        background: "hsl(var(--background) / <alpha-value>)",
        foreground: "hsl(var(--foreground) / <alpha-value>)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
