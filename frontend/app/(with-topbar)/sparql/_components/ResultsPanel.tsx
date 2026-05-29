'use client';

import React, { useState } from 'react';
import { SparqlResult } from '../page';
import TableView from './ResultViews/TableView';
import CardsView from './ResultViews/CardsView';
import GraphView from './ResultViews/GraphView';
import JsonView from './ResultViews/JsonView';
import styles from './ResultsPanel.module.css';

interface ResultsPanelProps {
  language: 'en' | 'de';
  results: SparqlResult | null;
  onShare: () => void;
}

type ViewTab = 'table' | 'cards' | 'graph' | 'json';

export default function ResultsPanel({ language, results, onShare }: ResultsPanelProps) {
  const [activeTab, setActiveTab] = useState<ViewTab>('table');

  const exportCSV = () => {
    if (!results) return;

    const vars = results.head.vars;
    const bindings = results.results.bindings;

    let csv = vars.join(',') + '\n';
    bindings.forEach((binding) => {
      const row = vars.map((v) => {
        const value = binding[v]?.value || '';
        return `"${value.replace(/"/g, '""')}"`;
      });
      csv += row.join(',') + '\n';
    });

    downloadFile(csv, 'sparql-results.csv', 'text/csv');
  };

  const exportJSON = () => {
    if (!results) return;

    const json = JSON.stringify(results, null, 2);
    downloadFile(json, 'sparql-results.json', 'application/json');
  };

  const downloadFile = (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const resultsCount = results?.results.bindings.length || 0;

  return (
    <section className={styles.resultsSection}>
      <div className={styles.resultsHeader}>
        <div>
          <h2 className={styles.resultsTitle}>
            {language === 'en' ? 'Query Results' : 'Abfrageergebnisse'}
          </h2>
          <div className={styles.resultsCount}>
            {resultsCount} {language === 'en' ? 'results' : 'Ergebnisse'}
          </div>
        </div>
        <div className={styles.exportControls}>
          <button
            className={styles.btnSecondary}
            onClick={exportCSV}
            disabled={!results}
          >
            <span className={styles.btnIcon}>📊</span>
            CSV
          </button>
          <button
            className={styles.btnSecondary}
            onClick={exportJSON}
            disabled={!results}
          >
            <span className={styles.btnIcon}>📄</span>
            JSON-LD
          </button>
          <button
            className={styles.btnSecondary}
            onClick={onShare}
            disabled={!results}
          >
            <span className={styles.btnIcon}>🔗</span>
            {language === 'en' ? 'Share' : 'Teilen'}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === 'table' ? styles.active : ''}`}
          onClick={() => setActiveTab('table')}
        >
          {language === 'en' ? 'Table' : 'Tabelle'}
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'cards' ? styles.active : ''}`}
          onClick={() => setActiveTab('cards')}
        >
          {language === 'en' ? 'Cards' : 'Karten'}
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'graph' ? styles.active : ''}`}
          onClick={() => setActiveTab('graph')}
        >
          {language === 'en' ? 'Graph' : 'Graph'}
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'json' ? styles.active : ''}`}
          onClick={() => setActiveTab('json')}
        >
          JSON
        </button>
      </div>

      {/* Tab Content */}
      <div className={styles.tabContent}>
        {activeTab === 'table' && <TableView language={language} results={results} />}
        {activeTab === 'cards' && <CardsView language={language} results={results} />}
        {activeTab === 'graph' && <GraphView language={language} results={results} />}
        {activeTab === 'json' && <JsonView language={language} results={results} />}
      </div>
    </section>
  );
}
