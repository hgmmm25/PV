/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        sidebar: {
          bg: "#1e1e2e",
          hover: "#313244",
          active: "#45475a",
          text: "#cdd6f4",
          muted: "#a6adc8",
        },
        status: {
          running: "#a6e3a1",
          stopped: "#f38ba8",
          starting: "#f9e2af",
        },
        content: {
          bg: "#181825",
        },
      },
    },
  },
  plugins: [],
};
