import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Grid,
  Typography,
  Slider,
  TextField,
  Button,
  FormControlLabel,
  Switch,
  Paper,
  CircularProgress,
  List,
  ListItemButton,
  ListItemText,
} from '@mui/material';
import { Graph } from 'react-vis-network-graph';
import { useAppStore } from '../store/useAppStore';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';
import PillarBadge from '../components/PillarBadge';

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
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [standardize, setStandardize] = useState<boolean>(false);
  const [selectedNodeRelations, setSelectedNodeRelations] = useState<any[]>([]);
  const [graphKey, setGraphKey] = useState<number>(0);

  useEffect(() => {
    fetchTheorySystems();
  }, [fetchTheorySystems]);

  const handleLoadGraph = useCallback(() => {
    fetchConceptGraph(topN);
    setGraphKey(prev => prev + 1);
  }, [fetchConceptGraph, topN]);

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

  // 准备vis-network数据
  const graphData = React.useMemo(() => {
    if (!conceptGraph) return { nodes: [], edges: [] };

    const filteredEdges = conceptGraph.edges.filter(edge => edge.weight >= minWeight);

    const nodes = conceptGraph.nodes
      .filter(node => 
        filteredEdges.some(edge => edge.source === node.id || edge.target === node.id) ||
        filteredEdges.some(edge => edge.source === node.id || edge.target === node.id)
      )
      .map(node => ({
        id: node.id,
        label: node.label,
        value: node.frequency,
        title: `${node.label}\n频次: ${node.frequency}`,
        color: getNodeColor(node.label),
        size: Math.max(10, Math.min(50, node.frequency / 2)),
      }));

    const edges = filteredEdges.map(edge => ({
      from: edge.source,
      to: edge.target,
      value: edge.weight,
      width: Math.max(1, Math.min(5, edge.weight / 2)),
      title: `权重: ${edge.weight}`,
    }));

    return { nodes, edges };
  }, [conceptGraph, minWeight]);

  const getNodeColor = (concept: string): string => {
    // 根据概念所属理论体系确定颜色
    for (const system of theorySystems) {
      if (system.pillars.some(pillar => concept.includes(pillar))) {
        return system.color_code;
      }
    }
    return '#1a73e8'; // 默认颜色
  };

  const graphOptions = {
    nodes: {
      shape: 'dot',
      scaling: {
        min: 10,
        max: 50,
        label: {
          enabled: true,
          min: 14,
          max: 30,
        },
      },
    },
    edges: {
      color: {
        color: '#848484',
        highlight: '#1a73e8',
      },
      smooth: {
        type: 'continuous',
      },
    },
    physics: {
      enabled: true,
      stabilization: {
        enabled: true,
        iterations: 1000,
      },
      barnesHut: {
        gravitationalConstant: -8000,
        springLength: 200,
      },
    },
    interaction: {
      hover: true,
      tooltipDelay: 200,
    },
    height: '600px',
  };

  const handleNodeClick = (event: any) => {
    const nodeId = event.nodes[0];
    if (nodeId) {
      setSelectedConcept(nodeId);
    }
  };

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
            
            {/* 搜索概念 */}
            <Box sx={{ mb: 3 }}>
              <TextField
                fullWidth
                label="搜索概念"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                size="small"
              />
            </Box>
            
            {/* 标准化模式开关 */}
            <Box sx={{ mb: 3 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={standardize}
                    onChange={(e) => setStandardize(e.target.checked)}
                  />
                }
                label="标准化模式"
              />
            </Box>
            
            {/* 加载图谱按钮 */}
            <Button
              fullWidth
              variant="contained"
              onClick={handleLoadGraph}
              disabled={loading}
            >
              {loading ? <CircularProgress size={24} /> : '加载图谱'}
            </Button>
          </Paper>
        </Grid>
        
        {/* 中央图谱区域 */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '600px' }}>
            {loading ? (
              <LoadingSpinner message="加载图谱数据..." />
            ) : conceptGraph ? (
              <Graph
                key={graphKey}
                graph={graphData}
                options={graphOptions}
                events={{
                  click: handleNodeClick,
                }}
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
                  点击"加载图谱"按钮开始可视化
                </Typography>
              </Box>
            )}
          </Paper>
        </Grid>
        
        {/* 右侧概念详情面板 */}
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 3, height: '100%' }}>
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
                    频次: {conceptGraph.nodes.find(n => n.id === selectedConcept)?.frequency || 0}
                  </Typography>
                )}
                
                {/* 关联理论支柱 */}
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    关联理论支柱:
                  </Typography>
                  {theorySystems.map(system => {
                    const hasPillar = system.pillars.some(pillar =>
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
                    {selectedNodeRelations.slice(0, 10).map((rel, index) => (
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
                
                {/* 在文章中查看按钮 */}
                <Button
                  fullWidth
                  variant="outlined"
                  sx={{ mt: 2 }}
                  onClick={() => {
                    // 跳转到文章搜索页面，搜索该概念
                    window.location.href = `/articles?search=${encodeURIComponent(selectedConcept)}`;
                  }}
                >
                  在文章中查看
                </Button>
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
