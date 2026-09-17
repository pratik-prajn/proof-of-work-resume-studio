import { test, expect } from '@playwright/test';

test('age and processing consent precede input', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Open studio' })).toBeDisabled();
  await expect(page.getByLabel('Your resume', { exact: true })).toHaveCount(0);
  await page.getByLabel('I confirm that I am 18 or older.').check();
  await expect(page.getByRole('button', { name: 'Open studio' })).toBeDisabled();
});

test('source -> coverage -> refusal -> verified PDF', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('I confirm that I am 18 or older.').check();
  await page.getByLabel(/I agree to send my inputs/).check();
  await page.getByRole('button', { name: 'Open studio' }).click();
  await page.getByRole('button', { name: 'Load fictional example' }).click();
  await page.getByRole('button', { name: 'Analyze skill coverage' }).click();
  await expect(page.getByText('62.5%', { exact: true })).toBeVisible();
  await expect(page.getByText('PROVISIONAL SKILL COVERAGE')).toBeVisible();
  await page.getByRole('button', { name: 'Refine safely', exact: true }).click();
  await page.getByRole('button', { name: 'Find safe improvements' }).click();
  await page.getByRole('button', { name: 'Apply change', exact: true }).first().click();
  await page.getByRole('button', { name: 'Insert an unsupported example' }).click();
  await page.getByRole('button', { name: 'Check rewrite', exact: true }).click();
  await expect(page.getByText('Rejected. Your original stays.')).toBeVisible();
  await page.getByRole('button', { name: 'Preview and export' }).click();
  const received = page.waitForResponse(response => response.url().endsWith('/api/backend/export/pdf'));
  const downloaded = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export checked PDF' }).click();
  const response = await received;
  expect(response.status()).toBe(200);
  expect(response.headers()['x-text-verified']).toBe('true');
  expect((await downloaded).suggestedFilename()).toBe('resume.pdf');
  await expect(page.getByText('PDF text check passed')).toBeVisible();
});
