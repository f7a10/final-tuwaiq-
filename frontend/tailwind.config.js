/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{vue,js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: '#176B5B',
                secondary: '#3F4943',
                accent: '#E9F3EF',
            },
            fontFamily: {
                sans: ['IBM Plex Sans Arabic', 'Segoe UI', 'Tahoma', 'Arial', 'sans-serif'],
            },
        },
    },
    plugins: [],
}
