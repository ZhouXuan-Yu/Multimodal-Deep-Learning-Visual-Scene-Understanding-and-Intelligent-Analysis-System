/** @type {import('tailwindcss').Config} */
export default {
    content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
    theme: {
        extend: {
            colors: {
                primary: "#0082fc",
                secondary: "#00c6ff",
                dark: "#111827",
                light: "#f9fafb",
            },
            fontFamily: {
                sans: ["Inter", "sans-serif"],
            },
        },
    },
    plugins: [],
};