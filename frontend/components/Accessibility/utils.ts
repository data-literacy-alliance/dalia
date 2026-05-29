import { AccessibilityButtonState } from '@/components/Accessibility/AccessibilityButton';

export type AccessibilityState = {
  name: string;
  states: AccessibilityButtonState[];
  disabled?: boolean;
};
