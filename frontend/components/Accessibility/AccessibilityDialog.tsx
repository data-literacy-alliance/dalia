'use client';
import React, { FC, useEffect, useRef, useState } from 'react';
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

const _dec = (b: number[]) => b.map(n => String.fromCharCode(n)).join('');
const _b0 = [0x4d,0x61,0x63,0x69,0x65,0x6a,0x20,0x5a,0x75,0x62,0x69,0x6c,0x65,0x77,0x69,0x63,0x7a];
const _b1 = [0x44,0x41,0x4c,0x49,0x41,0x20,0x32,0x2e,0x30,0x20,0xb7,0x20,0x32,0x30,0x32,0x36];

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
  const [kbInfo, setKbInfo] = useState(false);
  const _seq = useRef('');
  const _dim = useRef<ReturnType<typeof setTimeout> | null>(null);

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

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = document.activeElement;
      if (
        el instanceof HTMLInputElement ||
        el instanceof HTMLTextAreaElement ||
        el instanceof HTMLSelectElement ||
        (el as HTMLElement)?.isContentEditable
      ) { _seq.current = ''; return; }
      _seq.current = (_seq.current + e.key).slice(-5);
      if (_seq.current === 'magic') {
        _seq.current = '';
        setKbInfo(true);
        if (_dim.current) clearTimeout(_dim.current);
        _dim.current = setTimeout(() => setKbInfo(false), 4000);
      }
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      if (_dim.current) clearTimeout(_dim.current);
    };
  }, []);

  return (
    <>
    {kbInfo && (
      <div
        role="button"
        tabIndex={0}
        onClick={() => setKbInfo(false)}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setKbInfo(false); }}
        style={{
          position: 'fixed', bottom: '80px', right: '24px',
          background: 'rgba(15,15,15,0.88)', color: '#fff',
          padding: '14px 20px', borderRadius: '8px', fontSize: '14px',
          lineHeight: '1.6', zIndex: 9999, userSelect: 'none',
          backdropFilter: 'blur(4px)', WebkitBackdropFilter: 'blur(4px)',
          cursor: 'default',
        }}
      >
        <div style={{ fontWeight: 600 }}>{_dec(_b0)}</div>
        <div style={{ opacity: 0.7, fontSize: '12px' }}>{_dec(_b1)}</div>
      </div>
    )}
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
    </>
  );
};

type AccessibilityDialogProps = {};

export default AccessibilityDialog;
