'use client';
import React, { FormEventHandler, useState } from 'react';
import TopBar from '@/app/_parts/TopBar';
import { HFlex, VFlex } from '@/components/Flex';
import Textbox from '@/components/Textbox';
import Button from '@/components/Button';
import Text from '@/components/Text';
import { FeedbackFormEndpoint } from '@/lib/settings.mjs';
import Alert from '@/components/Alert';
import { FeedbackSchema } from '@/app/(blueBg)/feedback-form/_parts/validation';

const FeedbackForm = () => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [comment, setComment] = useState('');
  const [message, setMessage] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const doSubmission = async (body: string) => {
    await fetch(FeedbackFormEndpoint, {
      method: 'POST',
      body,
    });
  };

  const handleSubmit: FormEventHandler<HTMLFormElement> = (e) => {
    e.preventDefault();
    try {
      const rawData = {
        name: name,
        email: email,
        userInput: comment,
        submittedAt: new Date().toISOString(),
        formMode: 'production',
      };

      FeedbackSchema.parse(rawData);
      setLoading(true);

      doSubmission(JSON.stringify(rawData))
        .then(() => {
          setSubmitted(true);
          setMessage('Feedback submitted successfully.');
        })
        .catch(() => {
          setMessage('Failed to submit. Please try again later.');
        });
    } catch (error) {
      setMessage('Failed to submit. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <TopBar activePage={'feedback'} />
      <HFlex className="h-full items-center justify-center">
        <div className={'min-w-96 bg-daliaGray-100 p-10'}>
          <form method={'POST'} onSubmit={handleSubmit}>
            <VFlex>
              <Text variant={'subheader'} className={'mb-4'}>
                Feedback Form
              </Text>
              {message && (
                <div className={'mb-2'}>
                  <Alert>{message}</Alert>
                </div>
              )}
              {!submitted && (
                <>
                  <Textbox
                    inputClassname={'min-w-72 mb-2'}
                    label={'Name'}
                    value={name}
                    disabled={loading}
                    onChange={(e) => setName(e.target.value)}
                  />
                  <Textbox
                    inputClassname={'min-w-72 mb-2'}
                    label={'Email *'}
                    required
                    type={'email'}
                    value={email}
                    disabled={loading}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                  <Textbox
                    numberOfLines={4}
                    className={'mb-2'}
                    label={'Comment *'}
                    required
                    value={comment}
                    disabled={loading}
                    onChange={(e) => setComment(e.target.value)}
                  />
                  <Button
                    className={'mb-5 w-full'}
                    small={false}
                    dark={true}
                    disabled={loading}
                    type={'submit'}
                  >
                    Submit Feedback
                  </Button>
                </>
              )}
            </VFlex>
          </form>
        </div>
      </HFlex>
    </>
  );
};

export default FeedbackForm;
