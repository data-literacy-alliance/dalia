'use client';

import React, { useEffect, useRef } from 'react';
import { SparqlResult } from '../../page';
import styles from './GraphView.module.css';

interface GraphViewProps {
  language: 'en' | 'de';
  results: SparqlResult | null;
}

interface GraphNode {
  id: string;
  label: string;
  type: 'resource' | 'author' | 'center';
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
}

interface GraphLink {
  source: string | GraphNode;
  target: string | GraphNode;
  label?: string;
}

type SparqlBinding = Record<string, {
  type: 'uri' | 'literal' | 'bnode';
  value: string;
  datatype?: string;
  'xml:lang'?: string;
}>;

export default function GraphView({ language, results }: GraphViewProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!results || !svgRef.current) return;

    // Store the ref in a const to satisfy TypeScript
    const svgElement = svgRef.current;

    // Import D3.js dynamically
    void import('d3').then((d3Module) => {
      const d3 = d3Module;
      const svg = d3.select(svgElement);
      svg.selectAll('*').remove();

      const bindings = results.results.bindings;
      if (bindings.length === 0) return;

      const width = svgElement.clientWidth;
      const height = svgElement.clientHeight;

      // Create a group element for zoom/pan
      const g = svg.append('g');

      // Add zoom behavior
      const zoom = d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 4])
        .on('zoom', (event: d3.D3ZoomEvent<SVGSVGElement, unknown>) => {
          g.attr('transform', event.transform.toString());
        });

      svg.call(zoom);

      // Create nodes and links from SPARQL results
      const nodes: GraphNode[] = [];
      const links: GraphLink[] = [];
      const nodeMap = new Map<string, number>();

      bindings.forEach((binding: SparqlBinding, i: number) => {
        // Main resource node
        const resUri = binding.res?.value || `resource-${i}`;
        if (!nodeMap.has(resUri)) {
          nodes.push({
            id: resUri,
            label: binding.title?.value || resUri.split('/').pop() || 'Resource',
            type: 'resource',
          });
          nodeMap.set(resUri, nodes.length - 1);
        }

        // Create connected nodes for other properties
        if (binding.author) {
          const authorId = binding.author.value;
          if (!nodeMap.has(authorId)) {
            nodes.push({
              id: authorId,
              label: binding.authorName?.value || 'Author',
              type: 'author',
            });
            nodeMap.set(authorId, nodes.length - 1);
          }
          links.push({
            source: resUri,
            target: authorId,
            label: 'author',
          });
        }
      });

      // If we don't have connected data, create a simple cluster
      if (links.length === 0 && nodes.length > 0) {
        nodes.push({
          id: 'center',
          label: language === 'en' ? 'Educational Resources' : 'Bildungsressourcen',
          type: 'center',
        });

        bindings.forEach((binding: SparqlBinding, i: number) => {
          const resUri = binding.res?.value || `resource-${i}`;
          links.push({
            source: 'center',
            target: resUri,
          });
        });
      }

      // Create force simulation
      const simulation = d3
        .forceSimulation<GraphNode>(nodes)
        .force(
          'link',
          d3.forceLink<GraphNode, GraphLink>(links).id((d) => d.id).distance(100)
        )
        .force('charge', d3.forceManyBody<GraphNode>().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide<GraphNode>().radius(40));

      // Create links
      const link = g
        .append('g')
        .selectAll('line')
        .data(links)
        .enter()
        .append('line')
        .attr('class', styles.graphLink)
        .attr('stroke-width', 1.5);

      // Create nodes
      const node = g
        .append('g')
        .selectAll('g')
        .data(nodes)
        .enter()
        .append('g')
        .attr('class', styles.graphNode)
        .call(
          d3.drag<SVGGElement, GraphNode>()
            .on('start', (event: d3.D3DragEvent<SVGGElement, GraphNode, GraphNode>, d: GraphNode) => {
              if (!event.active) simulation.alphaTarget(0.3).restart();
              d.fx = d.x;
              d.fy = d.y;
            })
            .on('drag', (event: d3.D3DragEvent<SVGGElement, GraphNode, GraphNode>, d: GraphNode) => {
              d.fx = event.x;
              d.fy = event.y;
            })
            .on('end', (event: d3.D3DragEvent<SVGGElement, GraphNode, GraphNode>, d: GraphNode) => {
              if (!event.active) simulation.alphaTarget(0);
              d.fx = null;
              d.fy = null;
            })
        );

      // Node circles with colors based on type
      node
        .append('circle')
        .attr('r', (d) => (d.type === 'center' ? 20 : 15))
        .attr('fill', (d) => {
          switch (d.type) {
            case 'center':
              return '#06b6d4';
            case 'author':
              return '#8b5cf6';
            default:
              return '#10b981';
          }
        })
        .attr('stroke-width', 2);

      // Node labels
      node
        .append('text')
        .text((d) => (d.label.length > 20 ? d.label.substring(0, 17) + '...' : d.label))
        .attr('dy', 30)
        .attr('text-anchor', 'middle')
        .attr('font-size', '12px');

      // Update positions on simulation tick
      simulation.on('tick', () => {
        link
          .attr('x1', (d) => {
            const source = d.source as GraphNode;
            return source.x || 0;
          })
          .attr('y1', (d) => {
            const source = d.source as GraphNode;
            return source.y || 0;
          })
          .attr('x2', (d) => {
            const target = d.target as GraphNode;
            return target.x || 0;
          })
          .attr('y2', (d) => {
            const target = d.target as GraphNode;
            return target.y || 0;
          });

        node.attr('transform', (d) => `translate(${d.x || 0},${d.y || 0})`);
      });
    });
  }, [results, language]);

  if (!results || results.results.bindings.length === 0) {
    return (
      <div className={styles.emptyState}>
        <div className={styles.emptyIcon}>🕸️</div>
        <div className={styles.emptyTitle}>
          {language === 'en' ? 'No Graph Data' : 'Keine Graphdaten'}
        </div>
        <div className={styles.emptyText}>
          {language === 'en' ? 'Execute a query to see the knowledge graph' : 'Führen Sie eine Abfrage aus, um den Wissensgraphen zu sehen'}
        </div>
      </div>
    );
  }

  return (
    <div className={styles.graphContainer}>
      <svg ref={svgRef} className={styles.graphSvg}></svg>
    </div>
  );
}
