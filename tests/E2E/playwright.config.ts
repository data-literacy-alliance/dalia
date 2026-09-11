import { defineConfig, devices } from '@playwright/test';

// Set E2E_BASE_URL in your environment or .env file to target a specific deployment.
// Example: E2E_BASE_URL=https://your-domain.example.com
const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost';

export default defineConfig({
  testDir: './tests',
  timeout: 180_000,
  expect: { timeout: 10_000 },
  retries: 1,
  reporter: [['html', { open: 'never', outputFolder: '/reports' }], ['list']],
  use: {
    baseURL: BASE_URL,
    storageState: '/session/auth.json',
    headless: true,
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
