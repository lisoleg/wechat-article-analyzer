import { create } from 'zustand';
import * as api from '../api/client';

// 类型定义
interface AppState {
  // 数据状态
  status: api.StatusResponse | null;
  statsSummary: api.StatsSummaryResponse | null;
  conceptGraph: api.ConceptGraphResponse | null;
  evolution: api.EvolutionData | null;
  crossTheory: api.CrossTheoryResponse | null;
  theorySystems: api.TheorySystem[];
  topConcepts: api.ConceptFrequency[];
  pillarDistribution: api.PillarDistribution[];
  multiModelStats: api.MultiModelStats | null;
  incrementalLog: api.IncrementalLog | null;
  synonyms: api.SynonymMapping[];
  conceptRelations: api.ConceptRelation[];
  articles: api.Article[];
  totalArticles: number;
  currentPage: number;
  pageSize: number;
  
  // UI状态
  selectedConcept: string | null;
  loading: boolean;
  error: string | null;
  
  // Actions
  fetchStatus: () => Promise<void>;
  fetchStatsSummary: () => Promise<void>;
  fetchConceptGraph: (topN?: number) => Promise<void>;
  fetchEvolution: (topN?: number) => Promise<void>;
  fetchCrossTheory: () => Promise<void>;
  fetchTheorySystems: () => Promise<void>;
  fetchTopConcepts: (n?: number) => Promise<void>;
  fetchPillarDistribution: () => Promise<void>;
  fetchMultiModelStats: () => Promise<void>;
  fetchIncrementalLog: () => Promise<void>;
  fetchSynonyms: () => Promise<void>;
  fetchArticles: (page?: number, pageSize?: number) => Promise<void>;
  fetchArticle: (id: string) => Promise<void>;
  fetchConceptRelations: (concept: string) => Promise<void>;
  setSelectedConcept: (concept: string | null) => void;
  clearError: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  // 初始状态
  status: null,
  statsSummary: null,
  conceptGraph: null,
  evolution: null,
  crossTheory: null,
  theorySystems: [],
  topConcepts: [],
  pillarDistribution: [],
  multiModelStats: null,
  incrementalLog: null,
  synonyms: [],
  conceptRelations: [],
  articles: [],
  totalArticles: 0,
  currentPage: 1,
  pageSize: 20,
  
  selectedConcept: null,
  loading: false,
  error: null,
  
  // Actions
  fetchStatus: async () => {
    set({ loading: true, error: null });
    try {
      const response = await api.api.getStatus();
      set({ status: response.data, loading: false });
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch status', loading: false });
    }
  },
  
  fetchStatsSummary: async () => {
    set({ loading: true, error: null });
    try {
      const response = await api.api.getStatsSummary();
      set({ statsSummary: response.data, loading: false });
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch stats summary', loading: false });
    }
  },
  
  fetchConceptGraph: async (topN = 100) => {
    set({ loading: true, error: null });
    try {
      const response = await api.api.getConceptGraph(topN);
      set({ conceptGraph: response.data, loading: false });
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch concept graph', loading: false });
    }
  },
  
  fetchEvolution: async (topN = 10) => {
    set({ loading: true, error: null });
    try {
      const response = await api.api.getEvolution(topN);
      set({ evolution: response.data, loading: false });
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch evolution data', loading: false });
    }
  },
  
  fetchCrossTheory: async () => {
    set({ loading: true, error: null });
    try {
      const response = await api.api.getCrossTheory();
      set({ crossTheory: response.data, loading: false });
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch cross theory data', loading: false });
    }
  },
  
  fetchTheorySystems: async () => {
    set({ loading: true, error: null });
    try {
      const response = await api.api.getTheorySystems();
      set({ theorySystems: response.data, loading: false });
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch theory systems', loading: false });
    }
  },
  
  fetchTopConcepts: async (n = 50) => {
    set({ loading: true, error: null });
    try {
      const response = await api.api.getTopConcepts(n);
      set({ topConcepts: response.data, loading: false });
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch top concepts', loading: false });
    }
  },
  
  fetchPillarDistribution: async () => {
    set({ loading: true, error: null });
    try {
      const response = await api.api.getPillarDistribution();
      set({ pillarDistribution: response.data, loading: false });
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch pillar distribution', loading: false });
    }
  },
  
  fetchMultiModelStats: async () => {
    set({ loading: true, error: null });
    try {
      const response = await api.api.getMultiModelStats();
      set({ multiModelStats: response.data, loading: false });
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch multi-model stats', loading: false });
    }
  },
  
  fetchIncrementalLog: async () => {
    set({ loading: true, error: null });
    try {
      const response = await api.api.getIncrementalLog();
      set({ incrementalLog: response.data, loading: false });
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch incremental log', loading: false });
    }
  },
  
  fetchSynonyms: async () => {
    set({ loading: true, error: null });
    try {
      const response = await api.api.getSynonyms();
      set({ synonyms: response.data, loading: false });
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch synonyms', loading: false });
    }
  },
  
  fetchArticles: async (page = 1, pageSize = 20) => {
    set({ loading: true, error: null });
    try {
      const response = await api.api.getArticles(page, pageSize);
      set({ 
        articles: response.data.articles, 
        totalArticles: response.data.total,
        currentPage: page,
        pageSize: pageSize,
        loading: false 
      });
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch articles', loading: false });
    }
  },

  fetchArticle: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const response = await api.api.getArticle(id);
      const data = response.data as any;
      // 将 analysis 中的字段扁平化到 article 顶层，方便前端组件使用
      const analysis = data.analysis;
      if (analysis) {
        data.concepts = analysis.concepts || null;
        data.keywords = analysis.keywords || null;
        data.theory_pillars = analysis.theory_pillars || null;
        data.content_summary = analysis.summary || null;
        data.convergence_analysis = analysis.convergence_analysis || null;
      }
      // 保留 content_text 字段（文章全文）
      if (data.content_text) {
        data.content_text = data.content_text;
      }
      set((state) => ({
        articles: state.articles.map((a) => (a.id === id ? data : a)),
        loading: false,
      }));
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch article', loading: false });
    }
  },

  fetchConceptRelations: async (concept: string) => {
    set({ loading: true, error: null });
    try {
      const response = await api.api.getConceptRelations(concept, 50);
      set({ conceptRelations: response.data, loading: false });
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch concept relations', loading: false });
    }
  },

  setSelectedConcept: (concept: string | null) => {
    set({ selectedConcept: concept });
  },
  
  clearError: () => {
    set({ error: null });
  },
}));
