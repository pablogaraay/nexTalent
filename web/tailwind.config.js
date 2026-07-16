/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  safelist: [
    "nt-button--sm",
    "nt-button--md",
    "nt-button--lg",
    "nt-button--primary",
    "nt-button--dark",
    "nt-button--secondary",
    "nt-button--outline",
    "nt-button--ghost",
    "nt-card--default",
    "nt-card--subtle",
    "nt-card--dark",
    "nt-card--elevated",
    "nt-badge--accent",
    "nt-badge--neutral",
    "nt-badge--success",
    "nt-badge--warning",
    "nt-progress__fill--accent",
    "nt-progress__fill--success",
    "nt-progress__fill--dark",
    "nt-status--error",
    "nt-status--info",
    "nt-status--success",
  ],
  theme: {
    extend: {}
  },
  plugins: []
};
