'use client';

import React, { useState, useEffect } from 'react';
import { exampleQueries, getQueryLabel } from '@/lib/sparql/exampleQueries';
import { validateReadOnlyQuery, formatSparqlQuery } from '@/lib/sparql/queryValidator';
import QueryEditor from './_components/QueryEditor';
import ExampleQueries from './_components/ExampleQueries';
import QueryHistory from './_components/QueryHistory';
import ResultsPanel from './_components/ResultsPanel';
import ShareModal from './_components/ShareModal';
import styles from './sparql.module.css';

export interface SparqlResult {
  head: {
    vars: string[];
  };
  results: {
    bindings: Array<Record<string, {
      type: 'uri' | 'literal' | 'bnode';
      value: string;
      datatype?: string;
      'xml:lang'?: string;
    }>>;
  };
}

export interface QueryHistoryItem {
  query: string;
  timestamp: string;
  preview: string;
}

export default function SparqlExplorerPage() {
  const [query, setQuery] = useState<string>('');
  const [results, setResults] = useState<SparqlResult | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [queryHistory, setQueryHistory] = useState<QueryHistoryItem[]>([]);
  const [shareModalOpen, setShareModalOpen] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [language, setLanguage] = useState<'en' | 'de'>('en');

  // Load query history from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem('queryHistory');
    if (stored) {
      try {
        setQueryHistory(JSON.parse(stored) as QueryHistoryItem[]);
      } catch (e) {
        console.error('Failed to parse query history', e);
      }
    }

    // Load theme preference
    const storedTheme = localStorage.getItem('theme');
    if (storedTheme === 'light' || storedTheme === 'dark') {
      setTheme(storedTheme);
    }

    // Check URL for shared query
    const params = new URLSearchParams(window.location.search);
    const sharedQuery = params.get('query');
    if (sharedQuery) {
      setQuery(decodeURIComponent(sharedQuery));
      showSuccess('Query loaded from shared URL');
    } else {
      // Set default query
      setQuery(exampleQueries[0].query);
    }
  }, []);

  // Save query history to localStorage
  useEffect(() => {
    if (queryHistory.length > 0) {
      localStorage.setItem('queryHistory', JSON.stringify(queryHistory));
    }
  }, [queryHistory]);

  // Save theme preference
  useEffect(() => {
    localStorage.setItem('theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const showError = (message: string) => {
    setError(message);
    setSuccess(null);
    setTimeout(() => setError(null), 5000);
  };

  const showSuccess = (message: string) => {
    setSuccess(message);
    setError(null);
    setTimeout(() => setSuccess(null), 4000);
  };

  const executeQuery = async () => {
    if (!query.trim()) {
      showError('Please enter a SPARQL query');
      return;
    }

    // Validate query
    const validation = validateReadOnlyQuery(query);
    if (!validation.valid) {
      showError(validation.error || 'Invalid query');
      return;
    }

    setIsExecuting(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch('/sparql-api', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
      });

      const data = await response.json() as SparqlResult | { error?: string };

      if (!response.ok) {
        const errorData = data as { error?: string };
        showError(errorData.error || `Query failed with status ${response.status}`);
        return;
      }

      const resultData = data as SparqlResult;
      setResults(resultData);
      addToHistory(query);
      showSuccess(`Query executed successfully. ${resultData.results.bindings.length} results found.`);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to execute query';
      showError(`Error: ${errorMessage}`);
    } finally {
      setIsExecuting(false);
    }
  };

  const addToHistory = (executedQuery: string) => {
    const timestamp = new Date().toISOString();
    const preview = executedQuery.substring(0, 50).replace(/\n/g, ' ') + '...';

    const newItem: QueryHistoryItem = {
      query: executedQuery,
      timestamp,
      preview,
    };

    setQueryHistory(prev => {
      const updated = [newItem, ...prev];
      return updated.slice(0, 10); // Keep only last 10
    });
  };

  const loadHistoryQuery = (item: QueryHistoryItem) => {
    setQuery(item.query);
    showSuccess('Query loaded from history');
  };

  const deleteHistoryItem = (index: number) => {
    setQueryHistory(prev => {
      const updated = [...prev];
      updated.splice(index, 1);
      return updated;
    });
  };

  const clearHistory = () => {
    setQueryHistory([]);
    localStorage.removeItem('queryHistory');
    showSuccess('Query history cleared');
  };

  const handleExampleClick = (exampleId: string) => {
    const example = exampleQueries.find(q => q.id === exampleId);
    if (example) {
      setQuery(example.query);
    }
  };

  const clearQuery = () => {
    setQuery('');
    showSuccess('Query cleared');
  };

  const formatQuery = () => {
    const formatted = formatSparqlQuery(query);
    setQuery(formatted);
    showSuccess('Query formatted');
  };

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  const toggleLanguage = () => {
    setLanguage(prev => prev === 'en' ? 'de' : 'en');
  };

  return (
    <div className={styles.container} data-theme={theme}>
      <div className={styles.backgroundGradient}></div>

      <div className={styles.content}>
        {/* Header */}
        <header className={styles.header}>
          <div className={styles.logo}>
            <div className={styles.logoIcon}>🎓</div>
            <div className={styles.logoText}>
              <span className={styles.logoHighlight}>DALIA</span> Education
            </div>
          </div>
          <h1 className={styles.title}>
            {language === 'en' ? 'SPARQL Explorer' : 'SPARQL-Explorer'}
          </h1>
          <p className={styles.subtitle}>
            {language === 'en'
              ? 'Discover the interconnected universe of open educational resources'
              : 'Entdecken Sie das vernetzte Universum offener Bildungsressourcen'}
          </p>
        </header>

        {/* Language Selector */}
        <div className={styles.languageSelector}>
          <button
            className={`${styles.languageBtn} ${language === 'en' ? styles.active : ''}`}
            onClick={() => setLanguage('en')}
          >
            English
          </button>
          <button
            className={`${styles.languageBtn} ${language === 'de' ? styles.active : ''}`}
            onClick={() => setLanguage('de')}
          >
            Deutsch
          </button>
        </div>

        {/* Main Layout */}
        <div className={styles.mainLayout}>
          {/* Sidebar */}
          <aside className={styles.sidebar}>
            <ExampleQueries
              language={language}
              onExampleClick={handleExampleClick}
            />
            <QueryHistory
              language={language}
              history={queryHistory}
              onLoadQuery={loadHistoryQuery}
              onDeleteQuery={deleteHistoryItem}
              onClearHistory={clearHistory}
            />
          </aside>

          {/* Main Content */}
          <main className={styles.mainContent}>
            {/* Editor Section */}
            <section className={styles.editorSection}>
              <div className={styles.editorHeader}>
                <h2 className={styles.editorTitle}>
                  {language === 'en' ? 'SPARQL Query Editor' : 'SPARQL-Abfrage-Editor'}
                </h2>
                <div className={styles.editorControls}>
                  <button
                    className={styles.btnSecondary}
                    onClick={clearQuery}
                    disabled={isExecuting}
                  >
                    <span className={styles.btnIcon}>🗑️</span>
                    {language === 'en' ? 'Clear' : 'Löschen'}
                  </button>
                  <button
                    className={styles.btnSecondary}
                    onClick={formatQuery}
                    disabled={isExecuting}
                  >
                    <span className={styles.btnIcon}>✨</span>
                    {language === 'en' ? 'Format' : 'Formatieren'}
                  </button>
                  <button
                    className={styles.btnPrimary}
                    onClick={() => {
                      void executeQuery();
                    }}
                    disabled={isExecuting}
                  >
                    {isExecuting ? (
                      <>
                        <span className={styles.spinner}></span>
                        {language === 'en' ? 'Executing...' : 'Wird ausgeführt...'}
                      </>
                    ) : (
                      <>
                        <span className={styles.btnIcon}>▶️</span>
                        {language === 'en' ? 'Execute Query' : 'Abfrage ausführen'}
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Status Messages */}
              {error && (
                <div className={`${styles.statusMessage} ${styles.error}`}>
                  <span>✕</span>
                  <span>{error}</span>
                </div>
              )}
              {success && (
                <div className={`${styles.statusMessage} ${styles.success}`}>
                  <span>✓</span>
                  <span>{success}</span>
                </div>
              )}

              <QueryEditor
                query={query}
                onChange={setQuery}
                disabled={isExecuting}
              />
            </section>

            {/* Results Section */}
            <ResultsPanel
              language={language}
              results={results}
              onShare={() => setShareModalOpen(true)}
            />
          </main>
        </div>
      </div>

      {/* Share Modal */}
      {shareModalOpen && (
        <ShareModal
          language={language}
          query={query}
          onClose={() => setShareModalOpen(false)}
        />
      )}

      {/* Theme Switcher */}
      <div className={styles.themeSwitcher}>
        <button
          className={styles.themeToggleBtn}
          onClick={toggleTheme}
          aria-label="Toggle theme"
        >
          <span className={styles.themeIcon}>
            {theme === 'dark' ? '🌙' : '☀️'}
          </span>
        </button>
      </div>
    </div>
  );
}
