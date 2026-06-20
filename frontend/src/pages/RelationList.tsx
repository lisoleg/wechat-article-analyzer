import React, { useState, useEffect, useCallback } from 'react';
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
  InputAdornment,
  IconButton,
  Chip,
} from '@mui/material';
import { Search as SearchIcon, ArrowBack } from '@mui/icons-material';
import { useAppStore } from '../store/useAppStore';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';

interface RelationItem {
  concept_a: string;
  concept_b: string;
  relation_type: string;
  weight: number;
  pillar?: string;
}

const RelationList: React.FC = () => {
  const { error, clearError } = useAppStore();
  const [relations, setRelations] = useState<RelationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [inputValue, setInputValue] = useState('');

  const fetchRelations = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        limit: String(pageSize),
        offset: String(page * pageSize),
      });
      if (search.trim()) {
        params.append('search', search.trim());
      }
      const res = await fetch(`/api/relations?${params.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setRelations(data.items || data || []);
      setTotal(data.total || (data || []).length);
    } catch (e: any) {
      console.error('[RelationList] 获取关系列表失败:', e);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search]);

  useEffect(() => {
    fetchRelations();
  }, [fetchRelations]);

  const handleSearch = () => {
    setPage(0);
    setSearch(inputValue);
  };

  const handlePageChange = (_: any, newPage: number) => {
    setPage(newPage);
  };

  const handlePageSizeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setPageSize(parseInt(event.target.value, 10));
    setPage(0);
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 2 }}>
        <IconButton onClick={() => { window.location.hash = '#/dashboard'; }}>
          <ArrowBack />
        </IconButton>
        <Typography variant="h4">关系列表</Typography>
      </Box>

      <ErrorAlert error={error} onClose={clearError} />

      {/* 搜索栏 */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <TextField
          fullWidth
          placeholder="搜索概念 A 或概念 B..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSearch(); }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
            endAdornment: (
              <IconButton onClick={handleSearch} disabled={loading}>
                搜索
              </IconButton>
            ),
          }}
        />
      </Paper>

      {/* 关系表格 */}
      <Paper>
        {loading ? (
          <LoadingSpinner message="加载关系列表..." />
        ) : (
          <>
            <TableContainer sx={{ maxHeight: 'calc(100vh - 300px)', overflow: 'auto' }}>
              <Table stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell>概念 A</TableCell>
                    <TableCell>概念 B</TableCell>
                    <TableCell>关系类型</TableCell>
                    <TableCell align="right">权重</TableCell>
                    <TableCell>理论支柱</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {relations.length > 0 ? (
                    relations.map((rel, idx) => (
                      <TableRow key={`${rel.concept_a}-${rel.concept_b}-${idx}`} hover>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontWeight: 500, cursor: 'pointer', color: 'primary.main' }}
                            onClick={() => { window.location.hash = `#/concepts?search=${encodeURIComponent(rel.concept_a)}`; }}>
                            {rel.concept_a}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontWeight: 500, cursor: 'pointer', color: 'primary.main' }}
                            onClick={() => { window.location.hash = `#/concepts?search=${encodeURIComponent(rel.concept_b)}`; }}>
                            {rel.concept_b}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip label={rel.relation_type || '相关'} size="small" color="primary" variant="outlined" />
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2">{rel.weight?.toFixed(2) || '-'}</Typography>
                        </TableCell>
                        <TableCell>
                          {rel.pillar && <Chip label={rel.pillar} size="small" />}
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={5} align="center">
                        <Typography sx={{ color: 'text.secondary', py: 4 }}>
                          {search ? '没有找到匹配的关系' : '暂无关系数据'}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
            <TablePagination
              component="div"
              count={total}
              page={page}
              onPageChange={handlePageChange}
              rowsPerPage={pageSize}
              onRowsPerPageChange={handlePageSizeChange}
              rowsPerPageOptions={[10, 20, 50, 100]}
            />
          </>
        )}
      </Paper>
    </Box>
  );
};

export default RelationList;
