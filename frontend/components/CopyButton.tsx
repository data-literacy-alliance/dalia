'use client';
import React, { FC, useState } from 'react';
import Button from '@/components/Button';
import { CopyCheckIcon, CopyIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

const CopyButton: FC<CopyButtonProps> = ({ text, className }) => {
  const [recentlyCopied, setRecentlyCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setRecentlyCopied(true);
      setTimeout(() => {
        setRecentlyCopied(false);
      }, 3000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  return (
    <Button
      small
      className={cn('size-8 p-0 2xl:p-0', className)}
      onClick={!recentlyCopied ? handleCopy : undefined}
    >
      {recentlyCopied ? <CopyCheckIcon size={14} /> : <CopyIcon size={14} />}
    </Button>
  );
};

export type CopyButtonProps = {
  text: string;
  className?: string;
};

export default CopyButton;
