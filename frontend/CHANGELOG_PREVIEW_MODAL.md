# Changelog: Preview Modal Implementation

**Date:** 2025-11-14
**Feature:** Convert preview from new window to full-screen modal

## Summary
Replaced the "open in new window" preview functionality with a full-screen modal dialog. This allows users to preview and submit content without leaving the form page.

## Changes Made

### 1. DetailsBody.tsx
**File:** `/home/mzubilewicz/daliaproject/dev/frontend/app/(with-sidebar)/items/[id]/[slug]/_parts/DetailsBody.tsx`

#### Added onPreviewClose Prop (Lines 23-34)
- Added optional `onPreviewClose?: () => void` prop to DetailsBodyProps
- Updated "Back to resource form" button to call onPreviewClose if provided, otherwise falls back to window.close()
- Maintains backward compatibility with old preview route (if still used elsewhere)

**Button Logic (Lines 69-75):**
```typescript
onClick={() => {
  if (onPreviewClose) {
    onPreviewClose();
  } else {
    window.close();
  }
}}
```

### 2. AddContentData.tsx
**File:** `/home/mzubilewicz/daliaproject/dev/frontend/app/(with-sidebar)/items/new/_parts/AddContentData/AddContentData.tsx`

#### Imports Added (Lines 20, 56)
- Added `DialogFooter` to dialog imports
- Added `import DetailsBody from '@/app/(with-sidebar)/items/[id]/[slug]/_parts/DetailsBody'`

#### State Variables Added (Lines 130-131)
```typescript
const [previewOpen, setPreviewOpen] = useState(false);
const [previewData, setPreviewData] = useState<ResourceItem | null>(null);
```

#### Preview Button Updated (Line 832)
**Before:** `disabled={isLoading}`
**After:** `disabled={isLoading || !acceptedRules}`
- Preview button now requires confirmation checkbox to be checked
- Button remains `type={'submit'}` to properly validate form before preview

#### handlePreview Function Updated (Lines 309-311)
**Before:**
```typescript
const tempKey = randomString();
window.sessionStorage.setItem(tempKey, JSON.stringify(resource));
window.open(`/items/new/preview?item=${tempKey}`);
```

**After:**
```typescript
// Open preview in modal instead of new window
setPreviewData(resource);
setPreviewOpen(true);
```
- Removed sessionStorage usage
- Removed window.open call
- Opens modal instead

#### Full-Screen Dialog Added (Lines 877-912)
- Added Dialog component with full-screen styling
- Uses DetailsBody component to display preview with `onPreviewClose` callback
- DetailsBody's "Back to resource form" button closes modal via callback (line 886)
- Includes sticky footer with "Back to Form" and "Send" buttons
- Send button in modal uses **same enable/disable logic** as main Send button:
  - Disabled when `isLoading` (form is submitting)
  - Disabled when `!acceptedRules` (confirmation not checked)
  - Disabled when `isEdit && !state.isDirty` (edit mode with no changes)
- Both "Back to resource form" (top banner) and "Back to Form" (footer) buttons close the modal

**Key styling classes:**
- `max-w-full h-screen max-h-screen p-0 m-0 rounded-none border-0` - Makes dialog full-screen
- `sticky bottom-0` - Keeps buttons visible while scrolling
- `z-50` - Ensures buttons stay above content

**Send Button Disable Logic (Line 903-905):**
```typescript
disabled={
  isLoading || !acceptedRules || (isEdit && !state.isDirty)
}
```
This matches exactly with the main form Send button logic, ensuring consistent behavior.

## Behavior Changes

### Before
1. User checks confirmation checkbox
2. Send button becomes enabled (Preview always enabled)
3. User clicks Preview
4. Preview opens in new browser window
5. User closes preview window
6. User returns to form and clicks Send

### After
1. User checks confirmation checkbox
2. Both Preview and Send buttons become enabled
3. User clicks Preview
4. Preview opens in full-screen modal (same tab)
5. User can:
   - Click "Back to resource form" (top banner) to close modal and continue editing
   - Click "Back to Form" (footer button) to close modal and continue editing
   - Click "Send" (footer button) to submit directly from preview
6. All buttons respect confirmation checkbox state
7. In edit mode, Send button requires changes to be made (isDirty check)

## Files NOT Modified
The following components remain unchanged and continue to work:
- `/components/ui/dialog.tsx` - No custom styling added, uses inline classes
- `/app/(with-sidebar)/items/new/_parts/AddContentData/utils.ts` - Submit functions unchanged
- `/app/(with-sidebar)/items/[id]/[slug]/_parts/DetailsBody.tsx` - Preview display unchanged

## Deprecated Files
The following files are no longer used but preserved in backup:
- `/app/(with-sidebar)/items/new/preview/page.tsx` - Preview route (moved to backup)
- `/app/(with-sidebar)/items/new/_parts/PreviewDetailsBody.tsx` - Preview wrapper (moved to backup)

**Location:** `/home/mzubilewicz/daliaproject/backup/`

## Rollback Instructions

To revert these changes:

1. Restore modified files from git:
   ```bash
   git checkout HEAD -- app/(with-sidebar)/items/new/_parts/AddContentData/AddContentData.tsx
   git checkout HEAD -- app/(with-sidebar)/items/[id]/[slug]/_parts/DetailsBody.tsx
   ```

2. Restore preview route files from backup:
   ```bash
   cp /home/mzubilewicz/daliaproject/backup/preview_route_backup/* app/(with-sidebar)/items/new/
   ```

3. Rebuild frontend:
   ```bash
   npm run build
   ```

## Testing Checklist
- [ ] Confirmation checkbox controls both Preview and Send buttons
- [ ] Preview opens in full-screen modal
- [ ] Preview displays correct content with all fields
- [ ] "Back to resource form" button (top banner) closes modal and returns to form
- [ ] "Back to Form" button (footer) closes modal and returns to form
- [ ] Send button in modal submits form correctly
- [ ] Send button shows loading spinner during submission
- [ ] Send button disabled in edit mode when no changes made
- [ ] Send button enabled in edit mode after making changes
- [ ] Form data persists when closing preview modal
- [ ] Edit mode: Send requires changes to be made
- [ ] Add mode: Send works without requiring changes
- [ ] Modal closes on ESC key
- [ ] Success/error messages work correctly after submission

## Bug Fixes

### Stale Data After Saving from Preview Modal (Fixed: 2025-11-14)
**Issue:** Data was being saved successfully when using Send button in preview modal, but when clicking Edit again, the old/stale data was loaded into the form instead of the updated data.

**Root Cause:** After successful save, Next.js was serving cached page data. The router cache wasn't being invalidated, so subsequent page loads returned stale data.

**Fix:**
1. Added `useRouter` import from `next/navigation`
2. Added `router.refresh()` call after successful save in both edit and add modes
3. This invalidates Next.js cache and triggers server-side data refetch
4. Now when you edit a resource after saving, you get fresh data from the database

**Files Modified:**
- `/app/(with-sidebar)/items/new/_parts/AddContentData/AddContentData.tsx`
  - Line 3: Added `import { useRouter } from 'next/navigation'`
  - Line 62: Added `const router = useRouter()`
  - Line 264: Added `router.refresh()` after successful edit save
  - Line 283: Added `router.refresh()` after successful add save

**Code Example (Line 260-265):**
```typescript
} else if ('id' in result) {
  // success - result is ResourceItem
  setSaved(true);
  // Refresh router to invalidate cache and fetch updated data
  router.refresh();
}
```

### ORCID/ROR Validation Error When Editing (Fixed: 2025-11-14)
**Issue:** When editing existing resources, clicking Preview showed "There are some errors in the data" with ORCID validation error "Invalid ORCID link."

**Root Cause:** Backend stores ORCID as just the ID (e.g., `0000-0002-0363-3837`), but frontend schema expects full URL format (e.g., `https://orcid.org/0000-0002-0363-3837`). When loading edit data, ORCIDs weren't converted to URL format.

**Fix:** Convert ORCID IDs and ROR IDs to full URLs when loading form data for editing:
- Check if ORCID/ROR already starts with `http`
- If not, prepend `https://orcid.org/` or `https://ror.org/`
- Applied in both initial defaultValues and in reset useEffect

**Files Modified:**
- `/app/(with-sidebar)/items/new/_parts/AddContentData/AddContentData.tsx`
  - Lines 67-88 (defaultValues)
  - Lines 151-170 (reset useEffect)

**Error Display:**
- ORCID/ROR validation errors are shown in EditPersonDialog/EditOrganizationDialog via FormMessage component
- Top-level author errors shown in ContentAuthors component

## Known Limitations
None identified. All existing functionality preserved.

## Dependencies
- No new package dependencies added
- Uses existing Dialog component from shadcn/ui
- Uses existing DetailsBody component

## Performance Impact
- **Improved:** No longer creates new browser window/tab
- **Improved:** No sessionStorage operations
- **Improved:** Faster preview loading (no page navigation)
- **Same:** Preview rendering performance (uses same DetailsBody component)
