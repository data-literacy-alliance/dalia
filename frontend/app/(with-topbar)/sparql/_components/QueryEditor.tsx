'use client';

import React from 'react';
import styles from './QueryEditor.module.css';

interface QueryEditorProps {
  query: string;
  onChange: (query: string) => void;
  disabled?: boolean;
}

export default function QueryEditor({ query, onChange, disabled }: QueryEditorProps) {
  return (
    <textarea
      className={styles.codeEditor}
      value={query}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      placeholder="Enter your SPARQL query here..."
      spellCheck={false}
    />
  );
}
