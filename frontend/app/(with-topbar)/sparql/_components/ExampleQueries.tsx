'use client';

import React from 'react';
import { exampleQueries, getQueryLabel } from '@/lib/sparql/exampleQueries';
import styles from './ExampleQueries.module.css';

interface ExampleQueriesProps {
  language: 'en' | 'de';
  onExampleClick: (id: string) => void;
}

export default function ExampleQueries({ language, onExampleClick }: ExampleQueriesProps) {
  return (
    <div className={styles.card}>
      <h2 className={styles.title}>
        {language === 'en' ? 'Example Queries' : 'Beispielabfragen'}
      </h2>
      <div className={styles.examples}>
        {exampleQueries.map((example) => (
          <div
            key={example.id}
            className={styles.exampleQuery}
            onClick={() => onExampleClick(example.id)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onExampleClick(example.id);
              }
            }}
            role="button"
            tabIndex={0}
          >
            <div className={styles.exampleIcon}>{example.icon}</div>
            <div className={styles.exampleText}>
              {getQueryLabel(example, language)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
