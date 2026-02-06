import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';

export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: '../destiin/public/js',
    emptyOutDir: false,
    lib: {
      entry: path.resolve(__dirname, 'src_overrides/index.js'),
      name: 'DestiinCRMOverride',
      fileName: 'destiin_crm_override',
      formats: ['iife']
    },
    rollupOptions: {
      external: ['vue', 'frappe-ui'],
      output: {
        globals: {
          vue: 'Vue',
          'frappe-ui': 'FrappeUI'
        }
      }
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src_overrides')
    }
  }
});
