/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,jsx,ts,tsx}',
    './public/index.html',
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(214, 32%, 91%)",
        input: "hsl(214, 32%, 91%)",
        ring: "hsl(215, 20.2%, 65.1%)",
        background: "hsl(226, 71%, 4%)",
        foreground: "hsl(213, 31%, 91%)",
        primary: {
          DEFAULT: "hsl(210, 100%, 66%)",
          foreground: "hsl(210, 40%, 98%)",
        },
        secondary: {
          DEFAULT: "hsl(222.2, 47.4%, 11.2%)",
          foreground: "hsl(210, 40%, 98%)",
        },
        muted: {
          DEFAULT: "hsl(223, 47%, 11%)",
          foreground: "hsl(215, 20%, 65%)",
        },
        accent: {
          DEFAULT: "hsl(216, 34%, 17%)",
          foreground: "hsl(210, 40%, 98%)",
        },
        destructive: {
          DEFAULT: "hsl(0, 63%, 31%)",
          foreground: "hsl(210, 40%, 98%)",
        },
      },
      borderRadius: {
        lg: "0.5rem",
        md: "calc(0.5rem - 2px)",
        sm: "calc(0.5rem - 4px)",
      },
    },
  },
  plugins: [],
}