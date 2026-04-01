/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                dark: {
                    900: '#0B0C10',
                    800: '#1F2833',
                },
                neon: {
                    blue: '#66FCF1',
                    teal: '#45A29E',
                    purple: '#B026FF',
                    green: '#39FF14',
                    brand: '#FF4655' // A cool gaming red tone
                }
            },
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
                mono: ['Fira Code', 'monospace']
            }
        },
    },
    plugins: [],
}
