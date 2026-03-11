import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  base: '/ecostance-ui/',
  plugins: [react()],
  server: {
    port: 9008,
    host: '0.0.0.0', // Allow accessibility from network/cloud
    // Allowed hosts configuration (supported in Vite 6+, adding as placeholder/preparation)
    // @ts-ignore - allowedHosts is for Newer Vite/Preview
    allowedHosts: ['idp.securitycentric.net', 'sc-api-us-v2.securitycentric.net'],
    proxy: {
      '/api': {
        target: 'http://localhost:9007', // Updated to match new agent port 9007
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
