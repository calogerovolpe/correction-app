import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';

/** Frontend Svelte 5 — build dirigé vers app/static/spa/ (servi par FastAPI,
 *  local-first : aucune ressource distante). base '/static/spa/' : les assets
 *  sont référencés sous /static/spa/assets/*, servis par le mount FastAPI
 *  `/static` (app/main.py). */
export default defineConfig({
  plugins: [svelte()],
  base: '/static/spa/',
  resolve: {
    // Svelte 5 : force la variante CLIENT du runtime (index-browser), sinon
    // Vitest résout `svelte` vers index-server → `mount()` indisponible.
    conditions: ['browser'],
  },
  build: {
    outDir: '../app/static/spa',
    emptyOutDir: true,
    sourcemap: true,
  },
  test: {
    environment: 'jsdom',
    include: ['tests/**/*.test.ts'],
  },
});