'use client';
import React, { FC, useEffect, useRef, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import Button from '@/components/Button';
import Icon from '@/components/Icon';
import Checkbox from '@/components/Checkbox';
import { CheckedState } from '@radix-ui/react-checkbox';
import { Loader2Icon } from 'lucide-react';
import {
  DaliaDeletionRequestEmail,
  NEXT_PUBLIC_BACKEND_ROOT,
} from '@/lib/settings.mjs';
import { useAuthLogin } from '@/lib/auth/clientAuth';
import { useUserInfo } from '@/lib/auth/authApi';
import { getCsrfTokenClient } from '@/lib/auth/csrfToken';

const DeletionRequestDialog: FC<DeletionRequestDialogProps> = () => {
  const [remainingTime, setRemainingTime] = useState(5);
  const timer = useRef<NodeJS.Timeout>();
  const [understand, setUnderstand] = useState<CheckedState>(false);
  const [open, setOpen] = useState(false);
  const { access } = useAuthLogin();
  const { userInfo, isLoading } = useUserInfo();
  const [deletionToken, setDeletionToken] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleStartDeletion = async () => {
    if (!userInfo || isSubmitting) return;

    setIsSubmitting(true);

    try {
      const csrfToken = getCsrfTokenClient();

      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };

      if (access) {
        headers['Authorization'] = `Bearer ${access}`;
      }

      if (csrfToken) {
        headers['X-CSRFToken'] = csrfToken;
      }

      console.log('[DeletionRequest] Sending request with:', {
        hasAccess: !!access,
        hasCsrfToken: !!csrfToken,
        url: NEXT_PUBLIC_BACKEND_ROOT + '/api/account/deletion-requests/create/',
        headers: Object.keys(headers),
      });

      const result = await fetch(
        NEXT_PUBLIC_BACKEND_ROOT + '/api/account/deletion-requests/create/',
        {
          method: 'POST',
          credentials: 'include',
          headers,
          // Empty body for self-deletion - backend uses request.user automatically
          body: JSON.stringify({}),
        }
      );

      console.log('[DeletionRequest] Response status:', result.status);

      if (result.ok) {
        const data = (await result.json()) as {
          confirmation_token: string;
        };
        setDeletionToken(data.confirmation_token);
      } else {
        const error = await result
          .json()
          .catch(() => ({ detail: 'Failed to create deletion request' })) as { detail?: string };
        console.error('[DeletionRequest] Error response:', error);
        alert(`Error: ${error.detail || 'Failed to create deletion request'}\n\nStatus: ${result.status}`);
      }
    } catch (error) {
      console.error('Deletion request error:', error);
      alert('An error occurred. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  useEffect(() => {
    if (open) {
      setRemainingTime(5);
      timer.current = setInterval(() => {
        setRemainingTime((t) => {
          if (t - 1 === 0) {
            clearInterval(timer.current);
          }
          return t - 1;
        });
      }, 1000);

      return () => {
        clearInterval(timer.current);
      };
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button small className={'w-full border-dalia4 text-dalia4'}>
          <Icon source={'close'} size={10} /> Request Data Deletion
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Data Deletion</DialogTitle>
        </DialogHeader>
        <p>
          <strong>Deletion is permanent.</strong> If you request account
          deletion, all personal data, account preferences, created content, and
          any other information stored in our system will be removed or
          anonymized according to legal requirements. <br />
          After you submit your request, you will have 7 days to confirm the
          procedure.{' '}
          <i>
            If you do not confirm within 7 days, the request will be cancelled
            automatically.
          </i>{' '}
          Once confirmed, a 30-day grace period begins. During this period, you
          may still cancel the deletion request. After the grace period ends,
          your request will proceed to final processing and can no longer be
          reversed. At that point, your account will be permanently deleted and
          any recoverable data will be irreversibly removed.
        </p>
        {deletionToken ? (
          <div className={'border border-primary p-2'}>
            Your request has been submitted. In order to proceed please send us
            an email with the following information: <br />
            <div className={'my-3 grid grid-cols-3 gap-2'}>
              <div>Recipient:</div>
              <div className={'col-span-2'}>{DaliaDeletionRequestEmail}</div>
              <div>Request Token:</div>
              <div className={'col-span-2'}>{deletionToken}</div>
            </div>
            <i>This token will expire in 7 days.</i>
          </div>
        ) : (
          <Checkbox
            label={
              'I understand and agree to the terms.' +
              (remainingTime > 0 ? ` (${remainingTime}s)` : '')
            }
            checked={understand}
            onCheckedChange={setUnderstand}
            disabled={remainingTime > 0 || isLoading}
          />
        )}
        {!deletionToken && (
          <DialogFooter>
            <Button
              disabled={!understand || isSubmitting}
              onClick={handleStartDeletion}
            >
              {isSubmitting && <Loader2Icon className={'animate-spin mr-2'} size={16} />}
              I Request Deletion
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
};

export type DeletionRequestDialogProps = {};

export default DeletionRequestDialog;
