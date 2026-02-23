import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  base: '/ecostance-ui/',
  plugins: [react()],
  server: {
    port: 9002,
    host: '0.0.0.0', // Allow accessibility from network/cloud
    // Allowed hosts configuration (supported in Vite 6+, adding as placeholder/preparation)
    // @ts-ignore - allowedHosts is for Newer Vite/Preview
    allowedHosts: ['idp.securitycentric.net', 'sc-api-us-v2.securitycentric.net'],
    proxy: {
      '/api': {
        target: 'http://localhost:9000', // Updated from 8000 to match current setup
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
