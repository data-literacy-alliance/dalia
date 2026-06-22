import { test, expect, Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Test data constants
// ---------------------------------------------------------------------------
const TEST_RESOURCE = {
  title: 'E2E Test Resource — Playwright Automated',
  url: 'https://example.com/e2e-test-resource',
  description: 'Automated E2E test resource created by Playwright. Safe to delete.',
  publicationDate: '2024-01-15',
  version: '1.0',
  sizeMb: '2',
  keywords: 'e2e-test, playwright, automated',
  language: 'English',
  lrt: 'tutorial',
  license: 'CC0-1.0',
  proficiency: 'novice',
  targetGroup: 'researcher',
  fileFormat: '.pdf',
  mediaType: 'text',
} as const;

// ---------------------------------------------------------------------------
// Shared state between test cases
// ---------------------------------------------------------------------------
interface SharedState {
  rcUuid: string | null;
  resourceUuid: string | null;
}

const state: SharedState = {
  rcUuid: null,
  resourceUuid: null,
};

// ---------------------------------------------------------------------------
// Helper: select a value from an MSelect2 (shadcn/ui Command/Popover) dropdown
// MSelect2 trigger is a <button> that contains a floating <label> with the field name.
// ---------------------------------------------------------------------------
async function selectFromDropdown(
  page: Page,
  labelText: string,
  optionText: string
): Promise<void> {
  const trigger = page.locator('button').filter({ hasText: labelText }).first();
  await trigger.scrollIntoViewIfNeeded();
  await trigger.click();

  const searchInput = page.locator('[placeholder="Search..."]').last();
  await searchInput.waitFor({ state: 'visible' });
  await searchInput.fill(optionText);

  // Items load from API — wait for the option to appear before clicking
  const option = page.getByRole('option', { name: optionText }).first();
  await option.waitFor({ state: 'visible', timeout: 15_000 });
  await option.click();

  await page.keyboard.press('Escape');
}

// ---------------------------------------------------------------------------
// Helper: API GET via browser session
// ---------------------------------------------------------------------------
async function apiGet<T = unknown>(page: Page, path: string): Promise<T> {
  return page.evaluate(async (url: string) => {
    const res = await fetch(url, { credentials: 'include' });
    if (!res.ok) throw new Error(`GET ${url} → ${res.status}`);
    return res.json();
  }, `https://search.dalia.education${path}`) as Promise<T>;
}

// ---------------------------------------------------------------------------
// Helper: API POST via browser session
// ---------------------------------------------------------------------------
async function apiPost<T = unknown>(
  page: Page,
  path: string,
  body: Record<string, unknown> = {}
): Promise<T> {
  const csrfToken = await page.evaluate((): string => {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
  });

  return page.evaluate(
    async ({ url, csrf, payload }) => {
      const res = await fetch(url, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrf,
        },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`POST ${url} → ${res.status}: ${text}`);
      }
      return res.json();
    },
    { url: `https://search.dalia.education${path}`, csrf: csrfToken, payload: body }
  ) as Promise<T>;
}

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------
test.describe('Items new form — full workflow', () => {

  // -------------------------------------------------------------------------
  // Test 1: Create a new resource with all fields filled
  // -------------------------------------------------------------------------
  test('01 — create new resource with all fields', async ({ page }) => {
    await page.goto('/items/new/');

    // Wait for the form to be ready — Suspense + useLogin hydration
    // TextBox renders as floating label over the input; use [name=] selectors
    // throughout since getByLabel cannot resolve through the overlay.
    await page.locator('input[name="title"]').waitFor({ state: 'visible' });

    // --- Basic fields -----------------------------------------------------------
    await page.locator('input[name="title"]').fill(TEST_RESOURCE.title);
    await page.locator('input[name="url"]').fill(TEST_RESOURCE.url);

    // --- Author -----------------------------------------------------------------
    // ContentAuthors "Add" is a DropdownMenuTrigger — Radix sets aria-haspopup="menu"
    // which makes it unique on this form (MSelect2 uses Popover, not DropdownMenu).
    await page.locator('button[aria-haspopup="menu"]').filter({ hasText: 'Add' }).click();
    await page.getByRole('menuitem', { name: 'Person' }).click();

    // Dialog opens in 'search' mode — click "Add Person" to switch to form mode
    await page.getByRole('button', { name: 'Add Person' }).click();

    await page.locator('input[name="people.0.firstname"]').fill('E2E');
    await page.locator('input[name="people.0.lastname"]').fill('Testauthor');

    await page.getByRole('button', { name: 'Save Changes' }).click();

    // --- Classification ---------------------------------------------------------
    await page.locator('input[name="publicationDate"]').fill(TEST_RESOURCE.publicationDate);

    await selectFromDropdown(page, 'Language', TEST_RESOURCE.language);
    await selectFromDropdown(page, 'Learning Resource Type', TEST_RESOURCE.lrt);
    await selectFromDropdown(page, 'License', TEST_RESOURCE.license);

    await page.locator('textarea[name="description"]').fill(TEST_RESOURCE.description);

    await selectFromDropdown(page, 'Proficiency Level', TEST_RESOURCE.proficiency);
    await selectFromDropdown(page, 'Target Group', TEST_RESOURCE.targetGroup);
    await selectFromDropdown(page, 'File Format', TEST_RESOURCE.fileFormat);
    await selectFromDropdown(page, 'Media Type', TEST_RESOURCE.mediaType);

    await page.locator('input[name="version"]').fill(TEST_RESOURCE.version);
    await page.locator('input[name="size"]').fill(TEST_RESOURCE.sizeMb);
    await page.locator('input[name="keywords"]').fill(TEST_RESOURCE.keywords);

    // --- Terms ------------------------------------------------------------------
    // The label prop is a ReactNode <div>, so there is no <label> element.
    // Click the Radix UI checkbox button directly.
    await page.getByRole('checkbox').click();

    // --- Submit -----------------------------------------------------------------
    // New submissions call router.refresh() — URL stays at /items/new/.
    await page.getByRole('button', { name: 'Send', exact: true }).click();
    await expect(
      page.getByText(/Your data is saved and will be available after review/i)
    ).toBeVisible({ timeout: 30_000 });

    // --- Contributions list: extract RC UUID ------------------------------------
    await page.goto('/profile/contributions');

    const contributionLink = page
      .getByRole('link', { name: TEST_RESOURCE.title })
      .first();
    await expect(contributionLink).toBeVisible();

    // Resolve the ResourceContent uuid from the contributions API by title.
    // The contribution link points to the public detail page via the RESOURCE
    // uuid (not the content uuid), so it can't be scraped for the content uuid.
    const contributions = await apiGet<{
      results: Array<{ uuid: string; resource_uuid: string; title: string }>;
    }>(page, '/api/curation/resource-contents/?filter=my-resources');
    const created = contributions.results.find(
      (c) => c.title === TEST_RESOURCE.title
    );
    expect(created, 'created resource not found in contributions API').toBeTruthy();
    state.rcUuid = created!.uuid;

    // Regression guard for the contributions-link fix: the title link must point
    // to the resource detail page via the RESOURCE uuid, so it resolves on the
    // public items endpoint instead of 404ing (issue: clicking a contribution).
    const href = await contributionLink.getAttribute('href');
    expect(href).toContain(`/items/${created!.resource_uuid}/`);

    // --- API verification -------------------------------------------------------
    interface ResourceContentResponse {
      uuid: string;
      resource_uuid: string;
      title: string;
      main_url: string;
      description: string;
      publication_date: string;
      keywords: string[];
      people: unknown[];
      is_active: boolean;
    }

    const data = await apiGet<ResourceContentResponse>(
      page,
      `/api/curation/resource-contents/${state.rcUuid}/`
    );

    expect(data.title).toBe(TEST_RESOURCE.title);
    expect(data.main_url).toBe(TEST_RESOURCE.url);
    expect(data.description).toBe(TEST_RESOURCE.description);
    expect(data.publication_date).toBe(TEST_RESOURCE.publicationDate);

    expect(data.resource_uuid).toBeTruthy();
    expect(Array.isArray(data.people)).toBe(true);
    expect(data.people.length).toBeGreaterThanOrEqual(1);

    // Keywords are sent by the frontend and stored via django-taggit.
    // The API returns them sorted alphabetically as an array of strings.
    const expectedKeywords = TEST_RESOURCE.keywords
      .split(',')
      .map((k) => k.trim())
      .sort();
    expect(data.keywords).toEqual(expectedKeywords);

    state.resourceUuid = data.resource_uuid;
  });

  // -------------------------------------------------------------------------
  // Test 2: Edit resource — patches in place, no duplicate resource grouper
  // -------------------------------------------------------------------------
  test('02 — edit resource: patches in place, no duplicate resource grouper', async ({ page }) => {
    expect(state.rcUuid).toBeTruthy();
    expect(state.resourceUuid).toBeTruthy();

    // Record the contribution count BEFORE the edit — verifying no new resource is created
    await page.goto('/profile/contributions');
    const linksBefore = page.getByRole('link', { name: TEST_RESOURCE.title });
    const countBefore = await linksBefore.count();

    await page.goto(`/items/new?id=${state.rcUuid}`);

    // Wait for edit form to load
    await page.locator('input[name="title"]').waitFor({ state: 'visible' });

    // Verify edit mode heading and pre-filled title
    await expect(page.getByText('Edit Content').first()).toBeVisible();
    await expect(page.locator('input[name="title"]')).toHaveValue(TEST_RESOURCE.title);

    // Click checkbox first — in edit mode setAcceptedRules(false) only runs in the
    // else branch (no item), so this state is never reset by the useEffect.
    await page.getByRole('checkbox').click();

    // The page arrives with SSR data already in the HTML. React hydrates asynchronously
    // and then useEffect runs form.reset(formValues) — which resets isDirty to false.
    // If the reset runs AFTER our fill, the Send button stays disabled.
    // Strategy: fill in a retry loop. After each fill, check whether Send is enabled
    // (isDirty=true). If not, the effect won the race — wait for the form to re-settle
    // and try again. Once useEffect fires once (item?.id is stable), it won't fire
    // again and the fill will stick.
    const descriptionField = page.locator('textarea[name="description"]');
    const sendButton = page.getByRole('button', { name: 'Send', exact: true });

    await expect(descriptionField).toHaveValue(TEST_RESOURCE.description, { timeout: 15_000 });

    let filled = false;
    for (let attempt = 0; attempt < 6 && !filled; attempt++) {
      await descriptionField.fill('Updated by E2E test');
      try {
        await expect(sendButton).toBeEnabled({ timeout: 2_000 });
        filled = true;
      } catch {
        // useEffect form.reset() ran after our fill — wait for form to settle and retry
        await expect(descriptionField).toHaveValue(TEST_RESOURCE.description, { timeout: 5_000 });
      }
    }
    expect(filled, 'Send button never became enabled — form.reset() keeps resetting isDirty').toBe(true);

    // submitted_for_review=true means PATCH in-place — success message appears at same URL
    await sendButton.click();
    await expect(
      page.getByText(/Your data is saved and will be available after review/i)
    ).toBeVisible({ timeout: 30_000 });

    // --- Contributions: count must not increase (no new resource grouper created) ---
    await page.goto('/profile/contributions');
    const linksAfter = page.getByRole('link', { name: TEST_RESOURCE.title });
    await expect(linksAfter).toHaveCount(countBefore);

    // --- API: description updated, keywords preserved, resource grouper intact ---
    interface ResourceContentResponse {
      uuid: string;
      resource_uuid: string;
      description: string;
      keywords: string[];
    }

    const data = await apiGet<ResourceContentResponse>(
      page,
      `/api/curation/resource-contents/${state.rcUuid}/`
    );

    expect(data.description).toBe('Updated by E2E test');
    expect(data.resource_uuid).toBe(state.resourceUuid);

    // Edit re-sends the same keywords loaded from the form — verify they're preserved
    const expectedKeywords = TEST_RESOURCE.keywords
      .split(',')
      .map((k) => k.trim())
      .sort();
    expect(data.keywords).toEqual(expectedKeywords);
  });

  // -------------------------------------------------------------------------
  // Cleanup: soft-delete the test resource after all tests
  // -------------------------------------------------------------------------
  test.afterAll(async ({ browser }) => {
    if (!state.rcUuid) return;

    const context = await browser.newContext({ storageState: '/session/auth.json' });
    const page = await context.newPage();
    // Must navigate to a same-origin page before reading document.cookie
    await page.goto('https://search.dalia.education/');

    try {
      interface SoftDeleteResponse { ok: boolean; removed: boolean; }

      const result = await apiPost<SoftDeleteResponse>(
        page,
        `/api/curation/resource-contents/${state.rcUuid}/soft-delete/`
      );
      expect(result.ok).toBe(true);
    } finally {
      await context.close();
    }
  });
});
