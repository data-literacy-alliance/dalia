'use client';

import React, { useState } from 'react';
import styles from './ShareModal.module.css';

interface ShareModalProps {
  language: 'en' | 'de';
  query: string;
  onClose: () => void;
}

export default function ShareModal({ language, query, onClose }: ShareModalProps) {
  const [copied, setCopied] = useState(false);

  const shareUrl = typeof window !== 'undefined'
    ? `${window.location.origin}${window.location.pathname}?query=${encodeURIComponent(query)}`
    : '';

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div
      className={styles.modal}
      onClick={onClose}
      onKeyDown={(e) => {
        if (e.key === 'Escape') {
          onClose();
        }
      }}
      role="presentation"
    >
      {/* eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions, jsx-a11y/click-events-have-key-events */}
      <div
        className={styles.modalContent}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className={styles.modalHeader}>
          <h3 className={styles.modalTitle}>
            {language === 'en' ? 'Share Query' : 'Abfrage teilen'}
          </h3>
          <button className={styles.modalClose} onClick={onClose}>
            ×
          </button>
        </div>
        <div className={styles.shareUrlContainer}>
          <input
            type="text"
            className={styles.shareUrlInput}
            value={shareUrl}
            readOnly
          />
          <button
            className={styles.copyBtn}
            onClick={() => {
              void copyToClipboard();
            }}
          >
            <span className={styles.btnIcon}>{copied ? '✓' : '📋'}</span>
            {copied
              ? (language === 'en' ? 'Copied!' : 'Kopiert!')
              : (language === 'en' ? 'Copy' : 'Kopieren')}
          </button>
        </div>
        <p className={styles.shareInfo}>
          {language === 'en'
            ? 'Share this URL to let others view and execute this query'
            : 'Teilen Sie diese URL, damit andere diese Abfrage ansehen und ausführen können'}
        </p>
      </div>
    </div>
  );
}
