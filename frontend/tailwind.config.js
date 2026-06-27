/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-noto-thai)", "var(--font-inter)", "sans-serif"],
      },
      colors: {
        navy: {
          DEFAULT: "#050B24",
          deep:    "#0B1B4D",
          600:     "#0D2260",
          400:     "#1A3A8F",
        },
        gold: {
          DEFAULT: "#C8963E",
          soft:    "#F4E4C1",
          light:   "#FDF6E8",
        },
        surface: "#F7F8FB",
        card:    "#FFFFFF",
        risk: {
          red:    "#DC2626",
          yellow: "#F59E0B",
          green:  "#16A34A",
          blue:   "#2563EB",
        },
        "risk-bg": {
          red:    "#FEE2E2",
          yellow: "#FEF3C7",
          green:  "#DCFCE7",
          blue:   "#DBEAFE",
        },
        ink: {
          DEFAULT: "#1F2937",
          muted:   "#6B7280",
          faint:   "#9CA3AF",
        },
      },
      borderRadius: {
        card: "16px",
        pill: "9999px",
      },
      boxShadow: {
        card:        "0 2px 12px 0 rgba(5,11,36,0.07)",
        "card-hover":"0 4px 20px 0 rgba(5,11,36,0.12)",
        gold:        "0 4px 14px 0 rgba(200,150,62,0.30)",
      },
    },
  },
  plugins: [],
};
