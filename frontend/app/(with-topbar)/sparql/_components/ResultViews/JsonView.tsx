'use client';

import React from 'react';
import { SparqlResult } from '../../page';
import styles from './JsonView.module.css';

interface JsonViewProps {
  language: 'en' | 'de';
  results: SparqlResult | null;
}

export default function JsonView({ language, results }: JsonViewProps) {
  if (!results) {
    return (
      <div className={styles.jsonViewer}>
        <pre>
          <code className={styles.emptyMessage}>
            {JSON.stringify(
              {
                message:
                  language === 'en'
                    ? 'Execute a query to see JSON output'
                    : 'Führen Sie eine Abfrage aus, um die JSON-Ausgabe zu sehen',
              },
              null,
              2
            )}
          </code>
        </pre>
      </div>
    );
  }

  // Use JSON.stringify which safely escapes HTML entities
  const formatted = JSON.stringify(results, null, 2);

  // Safe rendering - just display the JSON without HTML injection
  // CSS will handle basic syntax highlighting via the jsonViewer styles
  return (
    <div className={styles.jsonViewer}>
      <pre>
        <code>{formatted}</code>
      </pre>
    </div>
  );
}
