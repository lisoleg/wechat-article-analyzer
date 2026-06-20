import React, { useEffect } from 'react';
import {
  Box,
  Grid,
  Typography,
  Paper,
  Card,
  CardContent,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  Chip,
} from '@mui/material';
import {
  Article as ArticleIcon,
  Psychology as ConceptIcon,
  AccountTree as RelationIcon,
  CheckCircle as AnalyzedIcon,
} from '@mui/icons-material';
import { useAppStore } from '../store/useAppStore';
import StatCard from '../components/StatCard';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';

const Dashboard: React.FC = () => {
  const {
    status,
    statsSummary,
    topConcepts,
    pillarDistribution,
    multiModelStats,
    incrementalLog,
    loading,
    error,
    fetchStatus,
    fetchStatsSummary,
    fetchTopConcepts,
    fetchPillarDistribution,
    fetchMultiModelStats,
    fetchIncrementalLog,
    clearError,
  } = useAppStore();

  useEffect(() => {
    fetchStatus();
    fetchStatsSummary();
    fetchTopConcepts(10);
    fetchPillarDistribution();
    fetchMultiModelStats();
    fetchIncrementalLog();
  }, []);

  if (loading && !status && !statsSummary) {
    return <LoadingSpinner message="加载仪表盘数据..." />;
  }

  // 安全辅助函数：确保是数组（避免 .map() 崩溃）
  const safeArray = (val: any): any[] =>
    Array.isArray(val) ? val : [];

  // 计算支柱分布最大值（用于进度条比例）
  const pDist = safeArray(pillarDistribution);
  const tConcepts = safeArray(topConcepts);
  const maxPillarCount = Math.max(...pDist.map((item: any) => item?.count || 0), 1);
  const maxConceptFreq = Math.max(...tConcepts.map((item: any) => item?.frequency || 0), 1);

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        仪表盘
      </Typography>
      
      <ErrorAlert error={error} onClose={clearError} />
      
      {/* 统计卡片 */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="文章总数"
            value={status?.total_articles || 0}
            icon={<ArticleIcon />}
            color="#1a73e8"
            clickable
            onClick={() => { window.location.hash = '#/articles'; }}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="已分析"
            value={status?.analyzed || 0}
            icon={<AnalyzedIcon />}
            color="#34a853"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="概念总数"
            value={statsSummary?.total_concepts || 0}
            icon={<ConceptIcon />}
            color="#ea4335"
            clickable
            onClick={() => { window.location.hash = '#/concepts'; }}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="关系总数"
            value={statsSummary?.total_relations || 0}
            icon={<RelationIcon />}
            color="#fbbc04"
            clickable
            onClick={() => { window.location.hash = '#/relations'; }}
          />
        </Grid>
      </Grid>
      
      {/* 图表区域 - 用纯 MUI 代替 recharts */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {/* 理论支柱分布 */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              理论支柱分布
            </Typography>
            {pDist.length > 0 ? (
              <List>
                {pDist.map((item: any) => (
                  <ListItem key={item.pillar} sx={{ flexDirection: 'column', alignItems: 'stretch' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <ListItemText primary={item.pillar} />
                      <Typography variant="body2">{item.count}</Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={(item.count / maxPillarCount) * 100}
                      sx={{ height: 8, borderRadius: 4 }}
                    />
                  </ListItem>
                ))}
              </List>
            ) : (
              <Typography sx={{ color: 'text.secondary' }}>暂无数据</Typography>
            )}
          </Paper>
        </Grid>
        
        {/* Top 10 概念频次 */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Top 10 概念频次
            </Typography>
            {tConcepts.length > 0 ? (
              <List>
                {tConcepts.map((item: any, idx: number) => (
                  <ListItem key={item.concept} sx={{ flexDirection: 'column', alignItems: 'stretch' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Chip label={idx + 1} size="small" color="primary" />
                        <Typography variant="body2">{item.concept}</Typography>
                      </Box>
                      <Typography variant="body2">{item.frequency}</Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={(item.frequency / maxConceptFreq) * 100}
                      color="success"
                      sx={{ height: 8, borderRadius: 4 }}
                    />
                  </ListItem>
                ))}
              </List>
            ) : (
              <Typography sx={{ color: 'text.secondary' }}>暂无数据</Typography>
            )}
          </Paper>
        </Grid>
      </Grid>
      
      {/* 其他信息 */}
      <Grid container spacing={3}>
        {/* 多模型验证统计 */}
        {multiModelStats && (
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  多模型验证统计
                </Typography>
                <Typography>总结果数: {multiModelStats.total_results}</Typography>
                <Typography>总文章数: {multiModelStats.total_articles}</Typography>
                <Typography>平均一致性: {(multiModelStats.avg_consistency * 100).toFixed(1)}%</Typography>
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2">模型分布:</Typography>
                  {multiModelStats && typeof multiModelStats.model_counts === 'object' && Object.entries(multiModelStats.model_counts).map(([model, count]) => (
                    <Typography key={model}>{model}: {count}</Typography>
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}
        
        {/* 最近增量分析日志 */}
        {incrementalLog && (
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  最近增量分析
                </Typography>
                <Typography>执行时间: {new Date(incrementalLog.executed_at).toLocaleString()}</Typography>
                <Typography>新增文章: {incrementalLog.new_articles_count}</Typography>
                <Typography>新增概念: {incrementalLog.new_concepts_count}</Typography>
                {incrementalLog.last_analysis_time && (
                  <Typography>
                    上次分析: {new Date(incrementalLog.last_analysis_time).toLocaleString()}
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default Dashboard;
