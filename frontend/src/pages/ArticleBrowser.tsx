import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TextField,
  Button,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
} from '@mui/material';
// 用 window.location.hash 替代 react-router-dom 的 navigate
const go = (path: string) => { window.location.hash = path; };
import { useAppStore } from '../store/useAppStore';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';

const ArticleBrowser: React.FC = () => {
  const {
    articles,
    totalArticles,
    currentPage,
    pageSize,
    loading,
    error,
    fetchArticles,
    clearError,
  } = useAppStore();

  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [timeFilter, setTimeFilter] = useState<string>('all');

  useEffect(() => {
    fetchArticles(1, pageSize);
  }, [fetchArticles, pageSize]);

  const handleSearch = () => {
    if (searchQuery.trim()) {
      // 这里应该调用搜索API，暂时使用客户端过滤
      fetchArticles(1, pageSize);
    }
  };

  const handleChangePage = (_event: unknown, newPage: number) => {
    fetchArticles(newPage + 1, pageSize);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    fetchArticles(1, parseInt(event.target.value, 10));
  };

  const filteredArticles = React.useMemo(() => {
    if (!articles) return [];
    
    return articles.filter(article => {
      // 状态过滤
      if (statusFilter === 'complete' && article.crawl_status !== 'complete') return false;
      if (statusFilter === 'analyzed' && !article.has_analysis) return false;
      
      // 搜索过滤
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        return article.title.toLowerCase().includes(query);
      }
      
      return true;
    });
  }, [articles, statusFilter, searchQuery]);

  if (loading && (!articles || articles.length === 0)) {
    return <LoadingSpinner message="加载文章列表..." />;
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        文章浏览
      </Typography>
      
      <ErrorAlert error={error} onClose={clearError} />
      
      {/* 搜索和筛选 */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Grid container spacing={2} sx={{ alignItems: 'center' }}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="搜索文章标题"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              size="small"
            />
          </Grid>
          <Grid item xs={12} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>状态筛选</InputLabel>
              <Select
                value={statusFilter}
                label="状态筛选"
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <MenuItem value="all">全部</MenuItem>
                <MenuItem value="complete">已采集</MenuItem>
                <MenuItem value="analyzed">已分析</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>时间范围</InputLabel>
              <Select
                value={timeFilter}
                label="时间范围"
                onChange={(e) => setTimeFilter(e.target.value)}
              >
                <MenuItem value="all">全部时间</MenuItem>
                <MenuItem value="today">今天</MenuItem>
                <MenuItem value="week">本周</MenuItem>
                <MenuItem value="month">本月</MenuItem>
                <MenuItem value="year">本年</MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </Paper>
      
      {/* 文章列表 */}
      <Paper sx={{ p: 3 }}>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>标题</TableCell>
                <TableCell>发布时间</TableCell>
                <TableCell>状态</TableCell>
                <TableCell>分析</TableCell>
                <TableCell>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredArticles.length > 0 ? (
                filteredArticles.map((article) => (
                  <TableRow
                    key={article.id}
                    hover
                    onClick={() => go(`/articles/${article.id}`)}
                    sx={{ cursor: 'pointer' }}
                  >
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                        {article.title}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {new Date(article.publish_time).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={article.crawl_status === 'complete' ? '已采集' : '待采集'}
                        color={article.crawl_status === 'complete' ? 'success' : 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={article.has_analysis ? '已分析' : '未分析'}
                        color={article.has_analysis ? 'primary' : 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Button
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          go(`/articles/${article.id}`);
                        }}
                      >
                        查看详情
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={5} align="center">
                    <Typography sx={{ color: 'text.secondary', py: 4 }}>
                      暂无文章数据
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
        
        <TablePagination
          rowsPerPageOptions={[10, 20, 50]}
          component="div"
          count={totalArticles}
          rowsPerPage={pageSize}
          page={currentPage - 1}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          labelRowsPerPage="每页行数:"
          labelDisplayedRows={({ from, to, count }) => `${from}-${to} 共 ${count}`}
        />
      </Paper>
    </Box>
  );
};

export default ArticleBrowser;
