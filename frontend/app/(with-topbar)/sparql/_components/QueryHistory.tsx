'use client';

import React from 'react';
import { QueryHistoryItem } from '../page';
import styles from './QueryHistory.module.css';

interface QueryHistoryProps {
  language: 'en' | 'de';
  history: QueryHistoryItem[];
  onLoadQuery: (item: QueryHistoryItem) => void;
  onDeleteQuery: (index: number) => void;
  onClearHistory: () => void;
}

export default function QueryHistory({
  language,
  history,
  onLoadQuery,
  onDeleteQuery,
  onClearHistory,
}: QueryHistoryProps) {
  if (history.length === 0) {
    return (
      <div className={styles.card}>
        <h2 className={styles.title}>
          {language === 'en' ? 'Query History' : 'Abfrageverlauf'}
        </h2>
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon}>⏱️</div>
          <div className={styles.emptyText}>
            {language === 'en' ? 'No history yet' : 'Noch kein Verlauf'}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <h2 className={styles.title}>
          {language === 'en' ? 'Query History' : 'Abfrageverlauf'}
        </h2>
        <button className={styles.clearBtn} onClick={onClearHistory} title="Clear history">
          🗑️
        </button>
      </div>
      <div className={styles.historyList}>
        {history.map((item, index) => {
          const date = new Date(item.timestamp);
          const timeStr = date.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          });

          return (
            <div
              key={item.timestamp}
              className={styles.historyItem}
              onClick={() => onLoadQuery(item)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onLoadQuery(item);
                }
              }}
              role="button"
              tabIndex={0}
            >
              <div className={styles.historyContent}>
                <div className={styles.historyPreview}>{item.preview}</div>
                <div className={styles.historyTime}>{timeStr}</div>
              </div>
              <button
                className={styles.deleteBtn}
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteQuery(index);
                }}
                title="Delete"
              >
                ×
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
