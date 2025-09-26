import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/frontend/setup.ts'],
    include: ['tests/frontend/**/*.test.{ts,tsx}'],
    coverage: {
      reporter: ['text', 'json', 'html'],
      include: ['frontend/src/**/*'],
      exclude: [
        'frontend/src/**/*.d.ts',
        'frontend/src/main.tsx',
        'frontend/src/vite-env.d.ts'
      ]
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, '../../frontend/src'),
      '@/components': path.resolve(__dirname, '../../frontend/src/components'),
      '@/hooks': path.resolve(__dirname, '../../frontend/src/hooks'),
      '@/services': path.resolve(__dirname, '../../frontend/src/services'),
      '@/types': path.resolve(__dirname, '../../frontend/src/types')
    }
  }
});