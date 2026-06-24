/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        base: {
          950: "#0B0E14",
          900: "#10141D",
          850: "#141925",
          800: "#1A2030",
          700: "#252C3F",
          600: "#3A4358",
        },
        accent: {
          DEFAULT: "#5EEAD4",
          dim: "#2DD4BF",
        },
        warn: {
          DEFAULT: "#F0B25C",
          dim: "#D89A45",
        },
        danger: {
          DEFAULT: "#F0746A",
        },
        ink: {
          DEFAULT: "#E6E9EF",
          dim: "#9AA3B5",
          faint: "#5B6478",
        },
      },
      fontFamily: {
        mono: [
          "JetBrains Mono", "ui-monospace", "SFMono-Regular", "Menlo",
          "Consolas", "Liberation Mono", "monospace",
        ],
        sans: [
          "Inter", "ui-sans-serif", "-apple-system", "BlinkMacSystemFont",
          "Segoe UI", "Roboto", "Helvetica Neue", "Arial", "sans-serif",
        ],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(45,212,191,0.15), 0 0 24px rgba(45,212,191,0.12)",
      },
    },
  },
  plugins: [],
};
