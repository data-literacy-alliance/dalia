'use client';
import React, { FC, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import Button from '@/components/Button';
import { ContrastIcon } from 'lucide-react';
import AccessibilityButton from '@/components/Accessibility/AccessibilityButton';
import { AccessibilityState } from '@/components/Accessibility/utils';
import { usePathname } from 'next/navigation';

const fontSizeName = 'font-size-accessibility';
const textSpacingName = 'spacing-accessibility';
const lineSpacingName = 'line-accessibility';
const bigCursorName = 'big-cursor-accessibility';

const accessibilityStates: AccessibilityState[] = [
  {
    name: fontSizeName,
    states: [
      {
        label: 'Change Font Size',
        point: 0,
        onAction: () => {
          document.documentElement.classList.remove('font-1', 'font-2');
          document.documentElement.classList.add('font-1');
        },
      },
      {
        label: 'Change Font Size',
        point: 50,
        onAction: () => {
          document.documentElement.classList.remove('font-1', 'font-2');
          document.documentElement.classList.add('font-2');
        },
      },
      {
        label: 'Change Font Size',
        point: 100,
        onAction: () => {
          document.documentElement.classList.remove('font-1', 'font-2');
        },
      },
    ],
  },
  {
    name: textSpacingName,
    states: [
      {
        label: 'Change Text Spacing',
        point: 0,
        onAction: () => {
          document.body.classList.add('spacing-1');
        },
      },
      {
        label: 'Change Text Spacing',
        point: 100,
        onAction: () => {
          document.body.classList.remove('spacing-1');
        },
      },
    ],
  },
  {
    name: lineSpacingName,
    states: [
      {
        label: 'Change Line Spacing',
        point: 0,
        onAction: () => {
          document.body.classList.add('leading-relaxed');
        },
      },
      {
        label: 'Change Line Spacing',
        point: 50,
        onAction: () => {
          document.body.classList.remove('leading-relaxed');
          document.body.classList.add('leading-loose');
        },
      },
      {
        label: 'Change Line Spacing',
        point: 100,
        onAction: () => {
          document.body.classList.remove('leading-relaxed', 'leading-loose');
        },
      },
    ],
  },
  {
    name: bigCursorName,
    // disable on touch screens
    disabled:
      typeof window !== 'undefined' &&
      window.matchMedia('(pointer: coarse)').matches,
    states: [
      {
        label: 'Increase Cursor Size',
        point: 0,
        onAction: () => {
          document.documentElement.classList.add('big-cursor', bigCursorName);
        },
      },
      {
        label: 'Reset Cursor Size',
        point: 100,
        onAction: () => {
          document.documentElement.classList.remove(
            'big-cursor',
            bigCursorName
          );
        },
      },
    ],
  },
];

const AccessibilityDialog: FC<AccessibilityDialogProps> = () => {
  // change on url change
  const pathname = usePathname();

  useEffect(() => {
    for (const state of accessibilityStates) {
      const keyIndexStr = localStorage.getItem(state.name);
      if (keyIndexStr) {
        const keyIndex = Number(keyIndexStr);
        if (!isNaN(keyIndex) && keyIndex >= 0) {
          state.states[keyIndex % state.states.length]?.onAction();
        }
      }
    }
  }, [pathname]);

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button
          className={'fixed bottom-4 right-4 z-10 w-14 px-1 2xl:px-1'}
          small
        >
          <ContrastIcon size={24} />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Accessibility Features</DialogTitle>
          <DialogDescription className="sr-only">
            Adjust visual accessibility settings for the site.
          </DialogDescription>
        </DialogHeader>
        <div className={'grid grid-cols-1 gap-4 md:grid-cols-2'}>
          {accessibilityStates.map((state) => (
            <AccessibilityButton
              states={state.states}
              name={state.name}
              key={state.name}
              disabled={state.disabled}
            />
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
};

type AccessibilityDialogProps = {};

export default AccessibilityDialog;
