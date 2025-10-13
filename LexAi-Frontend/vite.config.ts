import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths"; // ✅ EKLENECEK

export default defineConfig({
  plugins: [
    react(),
    tsconfigPaths(), // ✅ EKLENECEK
  ],
});
