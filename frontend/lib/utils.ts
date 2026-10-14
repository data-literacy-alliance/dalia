import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { LabelValuePair } from '@/lib/types/Common';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Joins the array with the separator in-between
 * @param array
 * @param callback
 * @param separator
 */
export function mapJoin<T1, T2, S>(
  array: T1[],
  callback: (value: T1, index: number, array: T1[]) => T2,
  separator: S
) {
  if (array.length === 0) {
    return [];
  }

  const newArr: (T2 | S)[] = [callback(array[0], 0, array)];
  array.slice(1).map((value, index, arr) => {
    newArr.push(separator);
    newArr.push(callback(value, index + 1, arr));
  });
  return newArr;
}

export function isLabelValuePair(obj: unknown): obj is LabelValuePair {
  return !!obj && 'label' in (obj as {});
}

/**
 * Formats file size string by removing trailing zeros and ensuring proper spacing.
 * Automatically converts small MB values to KB for better readability.
 * @param size - File size string (e.g., "1.500 MB", "1.5MB", "558.4KB", "0.1505 MB")
 * @returns Formatted file size string (e.g., "1.5 MB", "558.4 KB", "150.5 KB")
 * @example
 * formatFileSize("0.1505 MB") // "150.5 KB"
 * formatFileSize("1.500 MB")  // "1.5 MB"
 * formatFileSize("1024 KB")   // "1 MB"
 */
export function formatFileSize(size: string): string {
  // Remove spaces and convert to uppercase to normalize
  const normalized = size.replace(/\s+/g, '').toUpperCase();

  // Extract number and unit
  const match = normalized.match(/^([\d.]+)(MB|KB|GB)?$/i);
  if (!match) return size;

  const numberStr = match[1];
  let unit = match[2] || 'MB';
  let number = parseFloat(numberStr);

  // Convert units for better readability
  if (unit === 'MB' && number < 1 && number > 0) {
    // Convert small MB values to KB (e.g., 0.1505 MB → 150.5 KB)
    number = number * 1000;
    unit = 'KB';
  } else if (unit === 'KB' && number >= 1000) {
    // Convert large KB values to MB (e.g., 1024 KB → 1 MB)
    number = number / 1000;
    unit = 'MB';
  } else if (unit === 'GB' && number < 1 && number > 0) {
    // Convert small GB values to MB (e.g., 0.5 GB → 500 MB)
    number = number * 1000;
    unit = 'MB';
  }

  // Format number to remove trailing zeros
  const formatted = number % 1 === 0 ? number.toString() : number.toFixed(1).replace(/\.0$/, '');

  return `${formatted} ${unit.toUpperCase()}`;
}
