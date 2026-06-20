import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  ToggleButton,
  ToggleButtonGroup,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
} from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { useAppStore } from '../store/useAppStore';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';

const Evolution: React.FC = () => {
  const {
    evolution,
    topConcepts,
    loading,
    error,
    fetchEvolution,
    fetchTopConcepts,
    clearError,
  } = useAppStore();

  const [selectedConcepts, setSelectedConcepts] = useState<string[]>([]);
  const [timeGranularity, setTimeGranularity] = useState<'month' | 'quarter'>('month');

  useEffect(() => {
    fetchTopConcepts(10);
    fetchEvolution(5);
  }, [fetchTopConcepts, fetchEvolution]);

  useEffect(() => {
    if (topConcepts.length > 0 && selectedConcepts.length === 0) {
      setSelectedConcepts(topConcepts.slice(0, 5).map(c => c.concept));
    }
  }, [topConcepts, selectedConcepts]);

  const handleConceptToggle = (concept: string) => {
    setSelectedConcepts(prev => {
      if (prev.includes(concept)) {
        return prev.filter(c => c !== concept);
      } else {
        return [...prev, concept];
      }
    });
  };

  const handleFetchEvolution = () => {
    if (selectedConcepts.length > 0) {
      // 这里需要调用API获取指定概念的演化数据
      // 暂时使用默认的fetchEvolution
      fetchEvolution(10);
    }
  };

  // 准备图表数据
  const chartData = React.useMemo(() => {
    if (!evolution) return [];
    
    return evolution.timeline.map((point: any) => {
      const dataPoint: any = {
        time: point.time,
        article_count: point.article_count,
      };
      
      selectedConcepts.forEach((concept: any) => {
        dataPoint[concept] = point.concept_counts[concept] || 0;
      });
      
      return dataPoint;
    });
  }, [evolution, selectedConcepts]);

  // 计算趋势
  const calculateTrend = (concept: string) => {
    if (!evolution || evolution.timeline.length < 2) return null;
    
    const recent = evolution.timeline.slice(-3);
    const older = evolution.timeline.slice(-6, -3);
    
    const recentAvg = recent.reduce((sum: any, p: any) => sum + (p.concept_counts[concept] || 0), 0) / recent.length;
    const olderAvg = older.reduce((sum: any, p: any) => sum + (p.concept_counts[concept] || 0), 0) / older.length;
    
    if (olderAvg === 0) return recentAvg > 0 ? 'up' : 'stable';
    const change = ((recentAvg - olderAvg) / olderAvg) * 100;
    
    if (change > 10) return 'up';
    if (change < -10) return 'down';
    return 'stable';
  };

  const getTrendIcon = (trend: string | null) => {
    if (!trend) return '-';
    switch (trend) {
      case 'up': return '↑';
      case 'down': return '↓';
      case 'stable': return '→';
      default: return '-';
    }
  };

  if (loading && !evolution) {
    return <LoadingSpinner message="加载演化数据..." />;
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        概念演化时间线
      </Typography>
      
      <ErrorAlert error={error} onClose={clearError} />
      
      {/* 控制栏 */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
          {/* 概念选择 */}
          <Box sx={{ flex: 1, minWidth: '300px' }}>
            <Typography variant="subtitle2" gutterBottom>
              选择概念 (多选):
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {topConcepts.slice(0, 20).map((concept: any) => (
                <ToggleButton
                  key={concept.concept}
                  value={concept.concept}
                  selected={selectedConcepts.includes(concept.concept)}
                  onChange={() => handleConceptToggle(concept.concept)}
                  size="small"
                >
                  {concept.concept} ({concept.frequency})
                </ToggleButton>
              ))}
            </Box>
          </Box>
          
          {/* 时间粒度切换 */}
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              时间粒度:
            </Typography>
            <ToggleButtonGroup
              value={timeGranularity}
              exclusive
              onChange={(_, value) => value && setTimeGranularity(value)}
              size="small"
            >
              <ToggleButton value="month">按月</ToggleButton>
              <ToggleButton value="quarter">按季度</ToggleButton>
            </ToggleButtonGroup>
          </Box>
          
          {/* 加载按钮 */}
          <Box>
            <ToggleButton
              value="load"
              selected={false}
              onChange={handleFetchEvolution}
              disabled={loading}
            >
              {loading ? <CircularProgress size={20} /> : '加载数据'}
            </ToggleButton>
          </Box>
        </Box>
      </Paper>
      
      {/* 时间线折线图 */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          概念演化趋势
        </Typography>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="article_count"
                stroke="#1a73e8"
                name="文章数"
                strokeWidth={2}
              />
              {selectedConcepts.map((concept, index) => (
                <Line
                  key={concept}
                  type="monotone"
                  dataKey={concept}
                  stroke={`hsl(${index * 60}, 70%, 50%)`}
                  name={concept}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <Typography sx={{ color: 'text.secondary' }}>暂无数据</Typography>
        )}
      </Paper>
      
      {/* 摘要表 */}
      {selectedConcepts.length > 0 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            概念摘要
          </Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>概念</TableCell>
                  <TableCell>首次出现</TableCell>
                  <TableCell>峰值时间</TableCell>
                  <TableCell>峰值次数</TableCell>
                  <TableCell>近期趋势</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {selectedConcepts.map(concept => {
                  const trend = calculateTrend(concept);
                  return (
                    <TableRow key={concept}>
                      <TableCell>{concept}</TableCell>
                      <TableCell>
                        {evolution?.timeline.find((p: any) => (p.concept_counts[concept] || 0) > 0)?.time || '-'}
                      </TableCell>
                      <TableCell>
                        {(() => {
                          if (!evolution) return '-';
                          let maxCount = 0;
                          let maxTime = '-';
                          evolution.timeline.forEach((p: any) => {
                            const count = p.concept_counts[concept] || 0;
                            if (count > maxCount) {
                              maxCount = count;
                              maxTime = p.time;
                            }
                          });
                          return maxTime;
                        })()}
                      </TableCell>
                      <TableCell>
                        {(() => {
                          if (!evolution) return 0;
                          let maxCount = 0;
                          evolution.timeline.forEach((p: any) => {
                            const count = p.concept_counts[concept] || 0;
                            if (count > maxCount) {
                              maxCount = count;
                            }
                          });
                          return maxCount;
                        })()}
                      </TableCell>
                      <TableCell>
                        <span style={{ 
                          color: trend === 'up' ? 'green' : trend === 'down' ? 'red' : 'gray',
                          fontWeight: 'bold'
                        }}>
                          {getTrendIcon(trend)}
                        </span>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}
    </Box>
  );
};

export default Evolution;
