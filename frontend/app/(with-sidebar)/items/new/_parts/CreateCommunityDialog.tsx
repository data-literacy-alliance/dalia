'use client';
import React, { FC, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import Button from '@/components/Button';
import TextBox from '@/components/Textbox/Textbox';
import { saveCommunity } from '@/app/(with-sidebar)/items/new/_parts/AddContentData/utils';
import { useAuthLogin } from '@/lib/auth/clientAuth';

const CreateCommunityDialog: FC<CreateCommunityDialogProps> = ({
  open,
  onClose,
}) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { access } = useAuthLogin();

  const resetForm = () => {
    setTitle('');
    setDescription('');
    setError('');
  };

  const handleSave = async () => {
    if (!title.trim()) {
      setError('Title is required.');
      return;
    }
    if (!access) return;
    setLoading(true);
    setError('');
    const result = await saveCommunity(title.trim(), description.trim(), access);
    setLoading(false);
    if (result) {
      resetForm();
      onClose({ label: result.title, value: String(result.id) });
    } else {
      setError('Failed to create community. The title may already be in use.');
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(newOpen) => {
        if (!newOpen) {
          resetForm();
          onClose();
        }
      }}
    >
      <DialogContent className={'w-full sm:max-w-xl md:max-w-2xl'}>
        <DialogHeader>
          <DialogTitle>Create Community</DialogTitle>
        </DialogHeader>
        <div>
          <TextBox
            label={'Title'}
            priority={'Mandatory'}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className={'mb-4'}
          />
          <TextBox
            label={'Description'}
            priority={'Optional'}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            numberOfLines={8}
          />
          {error && (
            <p className={'mt-2 text-sm text-red-500'}>{error}</p>
          )}
        </div>
        <DialogFooter>
          <Button
            type="button"
            dark
            onClick={handleSave}
            disabled={loading}
          >
            {loading ? 'Creating…' : 'Create Community'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export type CreateCommunityDialogProps = {
  open: boolean;
  onClose: (newCommunity?: { label: string; value: string }) => void;
};

export default CreateCommunityDialog;
