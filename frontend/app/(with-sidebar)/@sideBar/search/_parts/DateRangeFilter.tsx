'use client';
import React, { FC, useState, useEffect } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import { useRouter } from 'nextjs-toploader/app';
import { VFlex } from '@/components/Flex';
import { useMainContext } from '@/app/Providers';

const DateRangeFilter: FC = () => {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const { setSidebarOpen } = useMainContext();

  // Read current date filter values from URL
  const afterParam = params.get('datePublished_after');
  const beforeParam = params.get('datePublished_before');

  // Derive filter type from URL params
  const getFilterTypeFromURL = () =>
    afterParam && beforeParam ? 'between' :
    afterParam ? 'after' :
    beforeParam ? 'before' :
    'none';

  // Use local state for dropdown selection (UX), but URL is source of truth for filtering
  const [selectedFilterType, setSelectedFilterType] = useState(getFilterTypeFromURL());

  // Local state for date inputs (while typing) - prevents immediate navigation on keystroke
  const [localAfterDate, setLocalAfterDate] = useState(afterParam || '');
  const [localBeforeDate, setLocalBeforeDate] = useState(beforeParam || '');

  // Sync dropdown and local dates with URL when URL changes (e.g., when filter is cleared)
  useEffect(() => {
    const urlFilterType =
      afterParam && beforeParam ? 'between' :
      afterParam ? 'after' :
      beforeParam ? 'before' :
      'none';
    setSelectedFilterType(urlFilterType);
    setLocalAfterDate(afterParam || '');
    setLocalBeforeDate(beforeParam || '');
  }, [afterParam, beforeParam]);

  const updateDateFilter = (
    newFilterType: string,
    newAfter: string,
    newBefore: string
  ) => {
    const newParams = new URLSearchParams(params);

    // Remove existing date params
    newParams.delete('datePublished_after');
    newParams.delete('datePublished_before');

    // Add new params based on filter type
    if (newFilterType === 'after' && newAfter) {
      newParams.set('datePublished_after', newAfter);
    } else if (newFilterType === 'before' && newBefore) {
      newParams.set('datePublished_before', newBefore);
    } else if (newFilterType === 'between' && newAfter && newBefore) {
      newParams.set('datePublished_after', newAfter);
      newParams.set('datePublished_before', newBefore);
    }

    // Reset pagination
    newParams.set('offset', '0');

    setSidebarOpen(false);
    router.push(`${pathname}?${newParams.toString()}`);
  };

  const handleFilterTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newType = e.target.value;

    // Update dropdown immediately for UX
    setSelectedFilterType(newType);

    // Only trigger search when clearing (none) - this removes the filter
    if (newType === 'none') {
      updateDateFilter('none', '', '');
    }
    // For other types, just show the inputs - search will trigger when dates are entered
  };

  // Only update local state - filter is applied via Apply button
  const handleAfterDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLocalAfterDate(e.target.value);
  };

  const handleBeforeDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLocalBeforeDate(e.target.value);
  };

  // Check if filter can be applied (required dates are entered)
  const isValidFilter = () => {
    if (selectedFilterType === 'after') return !!localAfterDate;
    if (selectedFilterType === 'before') return !!localBeforeDate;
    if (selectedFilterType === 'between') return !!localAfterDate && !!localBeforeDate;
    return false;
  };

  // Apply the filter when button is clicked
  const handleApplyFilter = () => {
    updateDateFilter(selectedFilterType, localAfterDate, localBeforeDate);
  };

  return (
    <VFlex className="gap-3 px-5 py-4">
      {/* Filter Type Dropdown */}
      <div>
        <label
          htmlFor="date-filter-type"
          className="mb-2 block text-sm font-medium text-gray-700"
        >
          Filter by:
        </label>
        <select
          id="date-filter-type"
          value={selectedFilterType}
          onChange={handleFilterTypeChange}
          className="w-full rounded border border-primary bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="none">No filter</option>
          <option value="after">After date</option>
          <option value="before">Before date</option>
          <option value="between">Between dates</option>
        </select>
      </div>

      {/* Conditional Date Inputs */}
      {(selectedFilterType === 'after' || selectedFilterType === 'between') && (
        <div>
          <label
            htmlFor="date-after"
            className="mb-2 block text-sm font-medium text-gray-700"
          >
            From:
          </label>
          <input
            type="date"
            id="date-after"
            value={localAfterDate}
            onChange={handleAfterDateChange}
            className="w-full rounded border border-primary bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      )}

      {(selectedFilterType === 'before' || selectedFilterType === 'between') && (
        <div>
          <label
            htmlFor="date-before"
            className="mb-2 block text-sm font-medium text-gray-700"
          >
            To:
          </label>
          <input
            type="date"
            id="date-before"
            value={localBeforeDate}
            onChange={handleBeforeDateChange}
            className="w-full rounded border border-primary bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      )}

      {/* Apply Button - only show when a filter type is selected */}
      {selectedFilterType !== 'none' && (
        <button
          onClick={handleApplyFilter}
          disabled={!isValidFilter()}
          className="w-full rounded bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90 disabled:cursor-not-allowed disabled:bg-gray-300"
        >
          Apply Filter
        </button>
      )}
    </VFlex>
  );
};

export default DateRangeFilter;
