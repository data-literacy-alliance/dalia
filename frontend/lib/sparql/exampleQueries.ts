/**
 * Example SPARQL Queries for DALIA Education
 * Based on the DALIA ontology and data structure
 */

export interface ExampleQuery {
  id: string;
  icon: string;
  label: {
    en: string;
    de: string;
  };
  query: string;
}

export const exampleQueries: ExampleQuery[] = [
  {
    id: 'basic',
    icon: '📚',
    label: {
      en: 'All Resources',
      de: 'Alle Ressourcen'
    },
    query: `PREFIX ec: <https://github.com/tibonto/educor#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX schema: <https://schema.org/>

SELECT ?res ?title ?description ?url
WHERE {
  ?res a ec:EducationalResource .
  OPTIONAL { ?res dcterms:title ?title . }
  OPTIONAL { ?res dcterms:description ?description . }
  OPTIONAL { ?res schema:url ?url . }
}
LIMIT 10`
  },
  {
    id: 'videos',
    icon: '🎥',
    label: {
      en: 'Video Resources',
      de: 'Video-Ressourcen'
    },
    query: `PREFIX ec: <https://github.com/tibonto/educor#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX schema: <https://schema.org/>
PREFIX modalia: <https://purl.org/ontology/modalia#>

SELECT ?res ?title ?url ?datePublished
WHERE {
  ?res a ec:EducationalResource ;
       modalia:hasMediaType <https://schema.org/VideoObject> .
  OPTIONAL { ?res dcterms:title ?title . }
  OPTIONAL { ?res schema:url ?url . }
  OPTIONAL { ?res schema:datePublished ?datePublished . }
}
LIMIT 20`
  },
  {
    id: 'authors',
    icon: '👥',
    label: {
      en: 'By Author',
      de: 'Nach Autor'
    },
    query: `PREFIX schema: <https://schema.org/>
PREFIX dalia: <https://dalia.education/>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?resource ?title ?givenName ?familyName
WHERE {
  ?resource dalia:authorUnordered ?author .
  OPTIONAL { ?author schema:givenName ?givenName . }
  OPTIONAL { ?author schema:familyName ?familyName . }
  OPTIONAL { ?resource dcterms:title ?title . }
}
LIMIT 15`
  },
  {
    id: 'recent',
    icon: '🔥',
    label: {
      en: 'Recently Published',
      de: 'Kürzlich veröffentlicht'
    },
    query: `PREFIX ec: <https://github.com/tibonto/educor#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX schema: <https://schema.org/>

SELECT ?res ?title ?datePublished
WHERE {
  ?res a ec:EducationalResource ;
       schema:datePublished ?datePublished .
  OPTIONAL { ?res dcterms:title ?title . }
}
ORDER BY DESC(?datePublished)
LIMIT 15`
  },
  {
    id: 'disciplines',
    icon: '🔬',
    label: {
      en: 'By Discipline',
      de: 'Nach Disziplin'
    },
    query: `PREFIX ec: <https://github.com/tibonto/educor#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX fabio: <https://purl.org/spar/fabio/>

SELECT ?res ?title ?discipline
WHERE {
  ?res a ec:EducationalResource ;
       fabio:hasDiscipline ?discipline .
  OPTIONAL { ?res dcterms:title ?title . }
}
LIMIT 20`
  }
];

/**
 * Get an example query by ID
 * @param id - The query ID
 * @returns The example query or undefined
 */
export function getExampleQuery(id: string): ExampleQuery | undefined {
  return exampleQueries.find(q => q.id === id);
}

/**
 * Get example query label by language
 * @param query - The example query
 * @param language - The language code (en or de)
 * @returns The localized label
 */
export function getQueryLabel(query: ExampleQuery, language: 'en' | 'de'): string {
  return query.label[language] || query.label.en;
}
