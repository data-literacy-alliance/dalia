'use client';

import React from 'react';
import { SparqlResult } from '../../page';
import { transformDaliaUri, getUriDisplayName } from '@/lib/sparql/uriTransform';
import styles from './TableView.module.css';

interface TableViewProps {
  language: 'en' | 'de';
  results: SparqlResult | null;
}

export default function TableView({ language, results }: TableViewProps) {
  if (!results || results.results.bindings.length === 0) {
    return (
      <div className={styles.emptyState}>
        <div className={styles.emptyIcon}>🔍</div>
        <div className={styles.emptyTitle}>
          {language === 'en' ? 'No results yet' : 'Noch keine Ergebnisse'}
        </div>
        <div className={styles.emptyText}>
          {language === 'en' ? 'Execute a query to see results' : 'Führen Sie eine Abfrage aus, um Ergebnisse zu sehen'}
        </div>
      </div>
    );
  }

  const vars = results.head.vars;
  const bindings = results.results.bindings;

  return (
    <div className={styles.tableContainer}>
      <table className={styles.resultsTable}>
        <thead>
          <tr>
            {vars.map((v) => (
              <th key={v}>{v}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {bindings.map((binding, idx) => (
            <tr key={idx}>
              {vars.map((v) => {
                const value = binding[v];
                if (!value) {
                  return (
                    <td key={v} className={styles.emptyCell}>
                      —
                    </td>
                  );
                }

                if (value.type === 'uri') {
                  const displayValue = getUriDisplayName(value.value);
                  const transformedUri = transformDaliaUri(value.value);
                  return (
                    <td key={v}>
                      <a
                        href={transformedUri}
                        className={styles.uriLink}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {displayValue}
                      </a>
                    </td>
                  );
                }

                return (
                  <td key={v} title={value.value}>
                    {value.value}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
