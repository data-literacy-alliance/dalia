'use client';

import React from 'react';
import { SparqlResult } from '../../page';
import { transformDaliaUri } from '@/lib/sparql/uriTransform';
import styles from './CardsView.module.css';

interface CardsViewProps {
  language: 'en' | 'de';
  results: SparqlResult | null;
}

type SparqlBinding = Record<string, {
  type: 'uri' | 'literal' | 'bnode';
  value: string;
  datatype?: string;
  'xml:lang'?: string;
}>;

export default function CardsView({ language, results }: CardsViewProps) {
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

  const bindings = results.results.bindings;

  const inferResourceType = (binding: SparqlBinding): string => {
    const url = binding.url?.value?.toLowerCase() || '';
    if (url.includes('youtube') || url.includes('video')) return 'video';
    if (url.includes('pdf') || url.includes('doc')) return 'text';
    return 'interactive';
  };

  return (
    <div className={styles.cardsContainer}>
      {bindings.map((binding, idx) => {
        const title = binding.title?.value || binding.res?.value?.split('/').pop() || 'Untitled Resource';
        const description = binding.description?.value || 'No description available';
        const rawUrl = binding.url?.value || binding.res?.value || '#';
        const url = transformDaliaUri(rawUrl);
        const type = inferResourceType(binding);

        return (
          <div
            key={idx}
            className={styles.resourceCard}
            onClick={() => window.open(url, '_blank')}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                window.open(url, '_blank');
              }
            }}
            role="button"
            tabIndex={0}
          >
            <div className={styles.cardHeader}>
              <span className={`${styles.typeBadge} ${styles[type]}`}>
                {type}
              </span>
            </div>
            <h3 className={styles.cardTitle}>{title}</h3>
            <p className={styles.cardDescription}>{description}</p>
            <div className={styles.cardMeta}>
              <div className={styles.metaItem}>
                <span>🔗</span>
                <span>{language === 'en' ? 'Open Resource' : 'Ressource öffnen'}</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
