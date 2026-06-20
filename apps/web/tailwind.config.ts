import type { Config } from "tailwindcss";

// Brand colors are from design/gbif_dark_atlas.md. The interface now uses a
// light surface (matching gbif.org) while keeping the same brand hues and the
// same type system. Light-theme semantic tokens are added below.
const config: Config = {
  content: ["./src/**/*.{ts,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        primary: "#61A350", // nature green accent
        secondary: "#0079B5", // institutional blue
        tertiary: "#94A3B8", // muted slate
        info: "#0B84C6",
        error: "#D64545",
        // Light-theme semantic tokens
        ink: "#121212", // primary text
        muted: "#475569", // secondary text
        panel: "#ECEEF6", // hero panel background
        hairline: "#E2E8F0", // borders and dividers
      },
      borderRadius: {
        sm: "3px",
        md: "4px",
        lg: "8px",
        xl: "12px",
      },
      fontFamily: {
        sans: [
          "Helvetica Neue",
          "Helvetica",
          "Arial",
          "system-ui",
          "-apple-system",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};

export default config;
