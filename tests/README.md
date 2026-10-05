# E2E Tests — Playwright / Podman

End-to-end tests for the DALIA 2.0 frontend at **https://search.dalia.education**.

All tests run inside Podman containers. No Node.js, no browsers, and no npm are required on the host.

---

## Overview

The suite tests the full lifecycle of the `/items/new/` resource submission form:

- filling every field (title, URL, description, publication date, keywords, authors, vocabulary dropdowns)
- submitting the form and verifying the success state
- confirming the created record via the REST API (`/api/curation/resource-contents/`)
- editing the resource and asserting that no duplicate Resource grouper is created
- cleaning up by soft-deleting the test resource after all tests finish

The site uses **NFDI AAI OpenID Connect** for authentication. Because OIDC flows cannot be automated headlessly, login is done once through a browser session captured via noVNC, and the resulting cookies are stored in a named Podman volume (`e2e-session`). The test container reuses those cookies on every run.

---

## Prerequisites

- `podman` >= 4.x
- `podman-compose` >= 1.x

Nothing else. Chromium, Node.js, and Playwright are bundled inside the container image.

---

## Quick start

```bash
cd dalia20/tests/E2E

# 1. Build both container images (capture + test)
make build

# 2. Capture a login session (one-time, or after expiry — see below)
make capture-session

# 3. Run the tests
make test

# 4. Open the HTML report
make report
```

---

## Session capture

Because the site authenticates through NFDI AAI OpenID Connect, automated login is not possible. The capture step opens a real browser inside the container, lets you log in manually, and then saves the session cookies to the `e2e-session` Podman volume as `auth.json`.

**Step-by-step:**

1. Run `make capture-session`. The terminal prints:

   ```
   Starting session capture — open http://localhost:6080 in your browser
   ```

2. Open **http://localhost:6080** in any browser on your machine. This connects to a noVNC session running inside the container — you will see a Chromium window.

3. In that Chromium window, navigate to **https://search.dalia.education** and complete the NFDI AAI login flow as you normally would (institution selector, credentials, MFA if required).

4. Once you are fully logged in and the site loads, return to the terminal and **press Enter**.

5. The script saves `auth.json` to the `e2e-session` named volume and exits.

The `auth.json` file lives inside a Podman-managed volume and is **not committed to git**.

---

## Test suite

File: `tests/items-new-form.spec.ts`

### Test 01 — create new resource with all fields

1. Navigates to `/items/new/` and asserts the "Add New Content" heading is visible.
2. Fills all form fields: title, link, author (Person — first name "E2E", last name "Testauthor"), publication date, language, learning resource type, license, description, proficiency level, target group, file format, media type, version, size, keywords.
3. Accepts terms and conditions, submits the form.
4. Asserts redirect to `/items/new?id=<uuid>` and the success message.
5. Navigates to `/profile/contributions` and extracts the RC UUID from the contribution link.
6. Calls `GET /api/curation/resource-contents/<rc_uuid>/` and verifies:
   - `title`, `main_url`, `description`, `publication_date` match the submitted values
   - `keywords` contain all three submitted tags
   - `resource_uuid` is non-empty (the Resource grouper)
   - `people` array has at least one entry (the author)

The `rc_uuid` and `resource_uuid` are stored in shared state for use by test 02 and the cleanup hook.

### Test 02 — edit resource, no duplicate grouper

1. Navigates to `/items/new?id=<rc_uuid>` (edit mode) and asserts the "Edit Content" heading and pre-filled title.
2. Clears the description field and fills it with `Updated by E2E test`.
3. Re-accepts terms and submits.
4. Asserts redirect to `/items/new?id=<new_uuid>`.
5. Navigates to `/profile/contributions` and asserts exactly **one** link with the test title (no duplicate entry visible on the contributions page).
6. Calls `GET /api/curation/resource-contents/?filter=my-resources` and verifies:
   - exactly **2** ResourceContent records share the test title (original + edited version)
   - both records have the same `resource_uuid` (the grouper was not duplicated)
   - exactly **1** of the two records has `is_active = true`

### afterAll — cleanup

After both tests complete, the hook soft-deletes the latest ResourceContent via `POST /api/curation/resource-contents/<latest_rc_uuid>/soft-delete/` and asserts `{ ok: true, removed: true }`. This keeps the database clean regardless of test outcome.

---

## Make targets

| Target | Description |
|---|---|
| `make build` | Builds both the `capture` and `test` container images |
| `make capture-session` | Runs the interactive session capture (noVNC on port 6080); implies `build` |
| `make test` | Runs Playwright tests inside the `test` container; fails fast if no session volume exists |
| `make report` | Opens `reports/index.html` in the system browser (`xdg-open` / `open`) |
| `make clean` | Stops and removes containers, deletes the `e2e-session` volume, and clears `reports/` |

---

## Session expiry

`auth.json` stores the OIDC session cookies. When the session expires the tests will fail with authentication or redirect errors.

Re-capture the session:

```bash
make capture-session
```

There is no fixed expiry period — it depends on the NFDI AAI session lifetime for your identity provider. As a rule of thumb, re-capture if tests start failing with HTTP 401 or unexpected redirects to the login page.

---

## Known limitations and risks

- **Vocabulary label mismatches.** Dropdown options (Language, Learning Resource Type, License, etc.) are matched by partial label text against the production vocabulary. If a label is renamed or removed in the vocabulary service the relevant `selectFromDropdown` call will time out. Update the constants in `TEST_RESOURCE` to match the new label.

- **Session expiry.** The `auth.json` session has a finite lifetime. There is no automatic renewal; a manual `make capture-session` run is required when it expires.

- **Contributions page pagination.** Test 02 checks for exactly one link with the test title on `/profile/contributions`. If the contributions list is paginated and older test artefacts from previous failed runs appear on page 1, the count assertion may fail. Run `make capture-session` on a clean account or manually soft-delete stale test resources via the admin if this occurs.

- **Shared state between tests.** Tests 01 and 02 share state via a module-level object. Running test 02 in isolation (without test 01 having run first in the same process) will cause it to skip due to a missing `rcUuid`.
