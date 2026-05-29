'use client';
import * as RadixAlertDialog from '@radix-ui/react-alert-dialog';
import React, { FC, ReactNode } from 'react';
import Button from '@/components/Button';

const AlertDialog: FC<DialogProps> = ({
  children,
  title,
  content,
  open,
  onOpenChange,
  onConfirm,
  confirmText,
  cancelText,
  confirmDisabled,
}) => {
  return (
    <RadixAlertDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixAlertDialog.Trigger asChild>{children}</RadixAlertDialog.Trigger>
      <RadixAlertDialog.Portal>
        <RadixAlertDialog.Overlay className="fixed inset-0 z-50 bg-daliaGray-A6 data-[state=open]:animate-overlayShow" />
        <RadixAlertDialog.Content className="fixed left-[50%] top-[50%] z-[51] max-h-[85vh] w-[90vw] max-w-[31.25rem] translate-x-[-50%] translate-y-[-50%] rounded-[6px] bg-white p-[25px] shadow-[hsl(206_22%_7%_/_35%)_0px_10px_38px_-10px,_hsl(206_22%_7%_/_20%)_0px_10px_20px_-15px] focus:outline-none data-[state=open]:animate-contentShow">
          <RadixAlertDialog.Title className="text-mauve12 m-0 text-[1.06rem] font-medium">
            {title}
          </RadixAlertDialog.Title>
          <RadixAlertDialog.Description className="mb-5 mt-4 text-[0.9375rem] leading-normal text-primary">
            {content}
          </RadixAlertDialog.Description>
          <span className="flex justify-end gap-[25px]">
            {onConfirm ? (
              <>
                <RadixAlertDialog.Cancel asChild>
                  <Button small>{cancelText || 'Cancel'}</Button>
                </RadixAlertDialog.Cancel>
                <RadixAlertDialog.Action asChild>
                  <Button
                    small
                    dark
                    onClick={onConfirm}
                    disabled={confirmDisabled}
                  >
                    {confirmText || 'Confirm'}
                  </Button>
                </RadixAlertDialog.Action>
              </>
            ) : (
              <RadixAlertDialog.Cancel asChild>
                <Button small>Ok</Button>
              </RadixAlertDialog.Cancel>
            )}
          </span>
        </RadixAlertDialog.Content>
      </RadixAlertDialog.Portal>
    </RadixAlertDialog.Root>
  );
};

export type DialogProps = {
  children: ReactNode;
  title: ReactNode;
  content: ReactNode;
  open?: boolean;
  onOpenChange?: (newValue: boolean) => void;
  onConfirm?: () => void | Promise<void>;
  confirmText?: string;
  cancelText?: string;
  confirmDisabled?: boolean;
};

export default AlertDialog;
