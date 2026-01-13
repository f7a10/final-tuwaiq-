/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{vue,js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: '#0F766E', // Teal 700
                secondary: '#334155', // Slate 700
                accent: '#F59E0B',    // Amber 500
            },
            fontFamily: {
                sans: ['Cairo', 'sans-serif'],
            },
        },
    },
    plugins: [],
}
