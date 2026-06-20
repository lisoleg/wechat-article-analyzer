import axios, { type AxiosInstance } from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API响应类型定义
export interface StatusResponse {
  total_articles: number;
  crawled: number;
  pending: number;
  analyzed: number;
  db_size_mb: number;
}

export interface StatsSummaryResponse {
  total_articles: number;
  crawled: number;
  analyzed: number;
  total_concepts: number;
  total_relations: number;
  pillar_distribution: Record<string, number>;
  last_analysis_time: string | null;
}

export interface ConceptGraphNode {
  id: string;
  label: string;
  frequency: number;
}

export interface ConceptGraphEdge {
  source: string;
  target: string;
  weight: number;
}

export interface ConceptGraphResponse {
  nodes: ConceptGraphNode[];
  edges: ConceptGraphEdge[];
  metadata: Record<string, any>;
}

export interface EvolutionData {
  tracked_concepts: string[];
  timeline: Array<{
    time: string;
    article_count: number;
    concept_counts: Record<string, number>;
  }>;
  summary: string;
}

export interface ConceptFrequency {
  concept: string;
  frequency: number;
}

export interface ConceptRelation {
  related_concept: string;
  weight: number;
}

export interface TheorySystem {
  id: string;
  system_name: string;
  description: string;
  pillars: string[];
  color_code: string;
}

export interface CrossTheorySystem {
  name: string;
  description: string;
  color_code: string;
  pillars: string[];
  pillar_distribution: Record<string, number>;
  top_concepts: ConceptFrequency[];
  unique_concepts: string[];
}

export interface CrossTheoryResponse {
  systems: CrossTheorySystem[];
  shared_concepts: string[];
  all_concepts_count: number;
}

export interface Article {
  id: string;
  title: string;
  url: string;
  publish_time: string;
  crawl_status: string;
  has_analysis: boolean;
  content_summary?: string;
  concepts?: string[];
  keywords?: string[];
  theory_pillars?: string[];
  convergence_analysis?: any;
  content_text?: string;
}

export interface ArticlesResponse {
  articles: Article[];
  total: number;
  page: number;
  page_size: number;
}

export interface SynonymMapping {
  id: string;
  original_concept: string;
  standardized_concept: string;
  mapping_type: string;
  confidence: number;
}

export interface IncrementalLog {
  id: string;
  last_article_id: string;
  last_analysis_time: string;
  new_articles_count: number;
  new_concepts_count: number;
  executed_at: string;
}

export interface MultiModelStats {
  total_results: number;
  total_articles: number;
  avg_consistency: number;
  model_counts: Record<string, number>;
}

export interface PillarDistribution {
  pillar: string;
  count: number;
}

// API函数
export const api = {
  // 状态相关
  getStatus: () => apiClient.get<StatusResponse>('/api/status'),
  
  getStatsSummary: () => apiClient.get<StatsSummaryResponse>('/api/stats/summary'),
  
  // 概念图谱相关
  getConceptGraph: (topN: number = 100) => 
    apiClient.get<ConceptGraphResponse>(`/api/concept-graph?top_n=${topN}`),
  
  getConceptGraphFull: (limit: number = 500) =>
    apiClient.get<ConceptGraphResponse>(`/api/concept-graph/full?limit=${limit}`),
  
  // 演化相关
  getEvolution: (topN: number = 10) =>
    apiClient.get<EvolutionData>(`/api/evolution?top_n=${topN}`),
  
  getEvolutionByConcepts: (concepts: string[]) => {
    const params = new URLSearchParams();
    concepts.forEach(c => params.append('concepts', c));
    return apiClient.get<EvolutionData>(`/api/evolution?${params.toString()}`);
  },
  
  // 概念相关
  getTopConcepts: (n: number = 50) =>
    apiClient.get<ConceptFrequency[]>(`/api/concepts/top?n=${n}`),
  
  searchConcepts: (q: string, limit: number = 20) =>
    apiClient.get<ConceptFrequency[]>(`/api/concepts/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  
  getConceptRelations: (concept: string, limit: number = 50) =>
    apiClient.get<ConceptRelation[]>(`/api/concepts/${encodeURIComponent(concept)}/relations?limit=${limit}`),
  
  standardizeConcept: (q: string) =>
    apiClient.get<{original: string, standardized: string, method: string}>(`/api/concepts/standardize?q=${encodeURIComponent(q)}`),
  
  // 跨理论相关
  getCrossTheory: () => apiClient.get<CrossTheoryResponse>('/api/cross-theory'),
  
  getTheorySystems: () => apiClient.get<TheorySystem[]>('/api/theory-systems'),
  
  // 文章相关
  getArticles: (page: number = 1, pageSize: number = 20) =>
    apiClient.get<ArticlesResponse>(`/api/articles?page=${page}&page_size=${pageSize}`),
  
  getArticle: (id: string) => apiClient.get<Article>(`/api/articles/${id}`),
  
  searchArticles: (q: string, limit: number = 20) =>
    apiClient.get<Article[]>(`/api/articles/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  
  // 同义词相关
  getSynonyms: () => apiClient.get<SynonymMapping[]>('/api/synonyms'),
  
  // 概念列表（分页）
  getConcepts: (page: number = 1, pageSize: number = 20, search: string = '') => {
    let url = `/api/concepts?page=${page}&page_size=${pageSize}`;
    if (search && search.trim()) {
      url += `&search=${encodeURIComponent(search.trim())}`;
    }
    return apiClient.get<{items: ConceptFrequency[], total: number, page: number, page_size: number}>(url);
  },

  // 增量分析相关
  getIncrementalLog: () => apiClient.get<IncrementalLog | null>('/api/incremental/log'),
  
  // 多模型相关
  getMultiModelStats: () => apiClient.get<MultiModelStats>('/api/multi-model/stats'),
  
  // 理论支柱相关
  getPillarDistribution: () => apiClient.get<PillarDistribution[]>('/api/pillars/distribution'),
};

export default api;
