import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box,
  Grid,
  Typography,
  Slider,
  Button,
  Paper,
  CircularProgress,
  List,
  ListItemButton,
  ListItemText,
} from '@mui/material';
import { Network } from 'vis-network/standalone';
import { useAppStore } from '../store/useAppStore';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';
import PillarBadge from '../components/PillarBadge';

// vis-network CSS
import 'vis-network/styles/vis-network.css';

const ConceptGraph: React.FC = () => {
  const {
    conceptGraph,
    theorySystems,
    conceptRelations,
    selectedConcept,
    loading,
    error,
    fetchConceptGraph,
    fetchTheorySystems,
    fetchConceptRelations,
    setSelectedConcept,
    clearError,
  } = useAppStore();

  const [topN, setTopN] = useState<number>(100);
  const [minWeight, setMinWeight] = useState<number>(1);
  const [selectedNodeRelations, setSelectedNodeRelations] = useState<any[]>([]);
  const [articleId, setArticleId] = useState<string | undefined>(() => {
    const hash = window.location.hash;
    const qIndex = hash.indexOf('?');
    if (qIndex >= 0) {
      const params = new URLSearchParams(hash.substring(qIndex));
      return params.get('articleId') || undefined;
    }
    return undefined;
  });

  // 监听 hash 变化，更新 articleId
  useEffect(() => {
    const onHashChange = () => {
      const hash = window.location.hash;
      const qIndex = hash.indexOf('?');
      if (qIndex >= 0) {
        const params = new URLSearchParams(hash.substring(qIndex));
        setArticleId(params.get('articleId') || undefined);
      } else {
        setArticleId(undefined);
      }
    };
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  // vis-network 实例 ref
  const networkRef = useRef<Network | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    fetchTheorySystems();
  }, [fetchTheorySystems]);

  const handleLoadGraph = useCallback(() => {
    fetchConceptGraph(topN, articleId);
  }, [fetchConceptGraph, topN, articleId]);

  // 自动加载图谱（支持 articleId）
  useEffect(() => {
    if (articleId || !conceptGraph) {
      fetchConceptGraph(topN, articleId);
    }
  }, [articleId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (selectedConcept) {
      fetchConceptRelations(selectedConcept);
    } else {
      setSelectedNodeRelations([]);
    }
  }, [selectedConcept, fetchConceptRelations]);

  useEffect(() => {
    setSelectedNodeRelations(conceptRelations || []);
  }, [conceptRelations]);

  // 获取节点颜色
  const getNodeColor = (concept: string): string => {
    for (const system of theorySystems) {
      if (system.pillars.some((pillar: string) => concept.includes(pillar))) {
        return system.color_code;
      }
    }
    return '#1a73e8';
  };

  // 当 conceptGraph 或 minWeight 变化时，更新图谱
  useEffect(() => {
    if (!conceptGraph || !containerRef.current) return;

    const filteredEdges = conceptGraph.edges.filter(edge => edge.weight >= minWeight);

    // 收集出现在边中的节点 ID
    const connectedNodeIds = new Set<string>();
    for (const edge of filteredEdges) {
      connectedNodeIds.add(edge.source);
      connectedNodeIds.add(edge.target);
    }

    const nodes = conceptGraph.nodes
      .filter(node => connectedNodeIds.has(node.id))
      .map(node => ({
        id: node.id,
        label: node.label,
        value: node.frequency,
        title: `${node.label}\n频次: ${node.frequency}`,
        color: {
          background: getNodeColor(node.label),
          border: '#333',
          highlight: { background: '#fff176', border: '#f57c00' },
        },
        size: Math.max(10, Math.min(50, node.frequency / 2)),
        font: { size: 12, color: '#333' },
      }));

    const edges = filteredEdges.map(edge => ({
      from: edge.source,
      to: edge.target,
      value: edge.weight,
      width: Math.max(1, Math.min(5, edge.weight / 2)),
      title: `权重: ${edge.weight}`,
      color: { color: '#848484', highlight: '#1a73e8' },
    }));

    const data = { nodes, edges };

    const options = {
      nodes: {
        shape: 'dot',
        scaling: {
          min: 10,
          max: 50,
          label: { enabled: true, min: 10, max: 24 },
        },
      },
      edges: {
        color: { color: '#848484', highlight: '#1a73e8' },
        smooth: { enabled: true, type: 'continuous', roundness: 0.5 },
      },
      physics: {
        enabled: true,
        stabilization: { enabled: true, iterations: 1000 },
        barnesHut: { gravitationalConstant: -8000, springLength: 200 },
      },
      interaction: { hover: true, tooltipDelay: 200 },
      height: '100%',
      width: '100%',
    };

    // 销毁旧实例
    if (networkRef.current) {
      networkRef.current.destroy();
      networkRef.current = null;
    }

    const network = new Network(containerRef.current, data, options);
    networkRef.current = network;

    // 节点点击事件
    network.on('click', (params: any) => {
      if (params.nodes && params.nodes.length > 0) {
        setSelectedConcept(params.nodes[0] as string);
      }
    });

    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
        networkRef.current = null;
      }
    };
  }, [conceptGraph, minWeight, setSelectedConcept]);

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        概念图谱可视化
      </Typography>

      <ErrorAlert error={error} onClose={clearError} />

      <Grid container spacing={3}>
        {/* 左侧控制面板 */}
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              控制面板
            </Typography>

            {/* Top N 滑块 */}
            <Box sx={{ mb: 3 }}>
              <Typography gutterBottom>Top N 概念: {topN}</Typography>
              <Slider
                value={topN}
                onChange={(_, value) => setTopN(value as number)}
                min={10}
                max={200}
                step={10}
                valueLabelDisplay="auto"
              />
            </Box>

            {/* 最小权重过滤 */}
            <Box sx={{ mb: 3 }}>
              <Typography gutterBottom>最小权重: {minWeight}</Typography>
              <Slider
                value={minWeight}
                onChange={(_, value) => setMinWeight(value as number)}
                min={1}
                max={10}
                step={1}
                valueLabelDisplay="auto"
              />
            </Box>

            {/* 加载图谱按钮 */}
            <Button
              fullWidth
              variant="contained"
              onClick={handleLoadGraph}
              disabled={loading}
              sx={{ mb: 2 }}
            >
              {loading ? <CircularProgress size={24} /> : '重新加载图谱'}
            </Button>
          </Paper>
        </Grid>

        {/* 中央图谱区域 */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 0, height: '600px', overflow: 'hidden' }}>
            {loading ? (
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                <LoadingSpinner message="加载图谱数据..." />
              </Box>
            ) : conceptGraph ? (
              <div
                ref={containerRef}
                style={{ width: '100%', height: '100%' }}
              />
            ) : (
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                }}
              >
                <Typography sx={{ color: 'text.secondary' }}>
                  正在加载图谱数据...
                </Typography>
              </Box>
            )}
          </Paper>
        </Grid>

        {/* 右侧概念详情面板 */}
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 3, height: '100%', overflow: 'auto' }}>
            <Typography variant="h6" gutterBottom>
              概念详情
            </Typography>

            {selectedConcept ? (
              <Box>
                <Typography variant="h6" gutterBottom>
                  {selectedConcept}
                </Typography>

                {/* 概念频次 */}
                {conceptGraph && (
                  <Typography sx={{ mb: 2 }}>
                    频次: {conceptGraph.nodes.find((n: any) => n.id === selectedConcept)?.frequency || 0}
                  </Typography>
                )}

                {/* 关联理论支柱 */}
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    关联理论支柱:
                  </Typography>
                  {theorySystems.map((system: any) => {
                    const hasPillar = system.pillars.some((pillar: string) =>
                      selectedConcept.includes(pillar)
                    );
                    return hasPillar ? (
                      <PillarBadge
                        key={system.id}
                        pillar={system.system_name}
                        color={system.color_code}
                        size="small"
                      />
                    ) : null;
                  })}
                </Box>

                {/* 关联概念列表 */}
                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    关联概念 (Top 10):
                  </Typography>
                  <List dense>
                    {selectedNodeRelations.slice(0, 10).map((rel: any, index: number) => (
                      <ListItemButton
                        key={index}
                        onClick={() => setSelectedConcept(rel.related_concept)}
                      >
                        <ListItemText
                          primary={rel.related_concept}
                          secondary={`权重: ${rel.weight}`}
                        />
                      </ListItemButton>
                    ))}
                  </List>
                </Box>
              </Box>
            ) : (
              <Typography sx={{ color: 'text.secondary' }}>
                点击图谱中的节点查看详情
              </Typography>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default ConceptGraph;
