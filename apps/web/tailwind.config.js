/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        studio: {
          dark: "#090A0F",
          card: "#12141F",
          border: "#202436",
          accent: "#6366F1",
          accentHover: "#4F46E5",
          purple: "#8B5CF6",
          cyan: "#06B6D4"
        }
      }
    },
  },
  plugins: [],
}
