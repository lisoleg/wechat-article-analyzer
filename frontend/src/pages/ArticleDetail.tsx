import React, { useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Chip,
  Button,
} from '@mui/material';
import { useAppStore } from '../store/useAppStore';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';
import PillarBadge from '../components/PillarBadge';

// 用 window.location.hash 替代 navigate
const go = (path: string) => { window.location.hash = path; };

interface ArticleDetailProps {
  id: string;
}

const ArticleDetail: React.FC<ArticleDetailProps> = ({ id }) => {
  const {
    articles,
    loading,
    error,
    fetchArticle,
    clearError,
  } = useAppStore();

  useEffect(() => {
    if (id) {
      fetchArticle(id);
    }
  }, [id, fetchArticle]);

  const article = articles?.find(a => String(a.id) === String(id));

  if (loading && !article) {
    return <LoadingSpinner message="加载文章详情..." />;
  }

  if (!article && !loading) {
    return (
      <Box>
        <ErrorAlert error={error || '文章未找到'} onClose={clearError} />
        <Button onClick={() => go('/articles')} sx={{ mt: 2 }}>
          返回文章列表
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>文章详情</Typography>
      <ErrorAlert error={error} onClose={clearError} />

      {article && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h5" gutterBottom>{article.title}</Typography>

          <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
            <Chip label={new Date(article.publish_time).toLocaleString()} size="small" variant="outlined" />
            <Chip label={article.url ? '有链接' : '无链接'} size="small" color={article.url ? 'primary' : 'default'} />
            <Button size="small" onClick={() => window.open(article.url, '_blank')} disabled={!article.url}>
              查看原文
            </Button>
          </Box>

          {article.concepts && article.concepts.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>概念标签</Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {article.concepts.map((concept, index) => (
                  <Chip key={index} label={concept}
                    onClick={() => go(`/graph?concept=${encodeURIComponent(concept)}`)}
                    sx={{ bgcolor: 'primary.light', color: 'primary.contrastText', '&:hover': { bgcolor: 'primary.main' } }}
                  />
                ))}
              </Box>
            </Box>
          )}

          {article.keywords && article.keywords.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>关键词</Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {article.keywords.map((keyword, index) => (
                  <Chip key={index} label={keyword} variant="outlined" size="small" />
                ))}
              </Box>
            </Box>
          )}

          {article.theory_pillars && article.theory_pillars.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>理论支柱</Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {article.theory_pillars.map((pillar, index) => (
                  <PillarBadge key={index} pillar={pillar} size="medium" />
                ))}
              </Box>
            </Box>
          )}

          {article.convergence_analysis && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>收敛性分析</Typography>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="body2">
                  {typeof article.convergence_analysis === 'string'
                    ? article.convergence_analysis
                    : JSON.stringify(article.convergence_analysis, null, 2)}
                </Typography>
              </Paper>
            </Box>
          )}

          {article.content_summary && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>内容摘要</Typography>
              <Typography variant="body1" paragraph>{article.content_summary}</Typography>
            </Box>
          )}

          {/* 文章全文 */}
          {article.content_text && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>文章全文</Typography>
              <Paper
                variant="outlined"
                sx={{
                  p: 2,
                  overflow: 'auto',
                  bgcolor: 'grey.50',
                  fontSize: '0.9rem',
                  lineHeight: 1.8,
                }}
              >
                <Box
                  sx={{ '& p': { mt: 0, mb: '1em' }, '& br': { lineHeight: 1.5 } }}
                  dangerouslySetInnerHTML={{
                    __html: article.content_text
                      .split(/\n\s*\n/)
                      .map(p => `<p>${p.replace(/\n/g, '<br/>')}</p>`)
                      .join(''),
                  }}
                />
              </Paper>
            </Box>
          )}

          <Box sx={{ display: 'flex', gap: 2, mt: 3 }}>
            <Button variant="outlined" onClick={() => go('/articles')}>返回列表</Button>
            <Button variant="contained" onClick={() => go(`/concept-graph?articleId=${id}`)}>查看概念图谱</Button>
          </Box>
        </Paper>
      )}
    </Box>
  );
};

export default ArticleDetail;
