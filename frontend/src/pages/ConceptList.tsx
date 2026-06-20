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
  InputAdornment,
  Chip,
  LinearProgress,
} from '@mui/material';
import { Search as SearchIcon, Psychology as ConceptIcon } from '@mui/icons-material';
import { api } from '../api/client';

interface ConceptItem {
  concept: string;
  frequency: number;
}

const ConceptList: React.FC = () => {
  const [concepts, setConcepts] = useState<ConceptItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(20);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchConcepts = async (p: number, size: number, q?: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getConcepts(p + 1, size, q);
      setConcepts(response.data.items || []);
      setTotal(response.data.total || 0);
    } catch (err: any) {
      // fallback: use top concepts API if paginated endpoint not available
      try {
        const n = size;
        const res = await api.getTopConcepts(Math.max(n * (p + 1), 200));
        const allItems: ConceptItem[] = (res.data || []).map((item: any) => ({
          concept: item.concept,
          frequency: item.frequency,
        }));
        // filter by search
        let filtered = allItems;
        if (q && q.trim()) {
          filtered = allItems.filter((c: ConceptItem) =>
            c.concept.toLowerCase().includes(q.trim().toLowerCase())
          );
        }
        setTotal(filtered.length);
        setConcepts(filtered.slice(p * size, p * size + size));
      } catch (fallbackErr: any) {
        setError(fallbackErr.message || '加载失败');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConcepts(page, rowsPerPage, search);
  }, [page, rowsPerPage]);

  // debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setPage(0); // reset to first page on search
      fetchConcepts(0, rowsPerPage, search);
    }, 400);
    return () => clearTimeout(timer);
  }, [search]);

  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <ConceptIcon color="primary" />
        概念列表
        <Typography variant="body2" component="span" sx={{ color: 'text.secondary', fontWeight: 'normal' }}>
          （按权重排列，共 {total > 0 ? total : '...'} 个）
        </Typography>
      </Typography>

      {/* 搜索框 */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <TextField
          fullWidth
          placeholder="搜索概念..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon color="action" />
              </InputAdornment>
            ),
          }}
          size="small"
        />
      </Paper>

      {loading && <LinearProgress sx={{ mb: 2 }} />}
      {error && (
        <Typography color="error" sx={{ mb: 2 }}>
          {error}
        </Typography>
      )}

      {/* 概念表格 */}
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell width="60">#</TableCell>
              <TableCell>概念名称</TableCell>
              <TableCell width="120" align="right">权重（频次）</TableCell>
              <TableCell width="100" align="right">占比</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {concepts.map((item, idx) => (
              <TableRow key={item.concept} hover>
                <TableCell>
                  <Chip label={page * rowsPerPage + idx + 1} size="small" color="primary" />
                </TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>
                    {item.concept}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2" sx={{ fontFamily: 'monospace', fontWeight: 'bold' }}>
                    {item.frequency.toLocaleString()}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Box sx={{ width: '80px' }}>
                    <LinearProgress
                      variant="determinate"
                      value={total > 0 ? (item.frequency / (concepts[0]?.frequency || 1)) * 100 : 0}
                      color="success"
                      sx={{ height: 6, borderRadius: 3 }}
                    />
                  </Box>
                </TableCell>
              </TableRow>
            ))}
            {!loading && concepts.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} align="center" sx={{ py: 4 }}>
                  <Typography color="text.secondary">暂无数据</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        <TablePagination
          component="div"
          count={total}
          page={page}
          onPageChange={handleChangePage}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          rowsPerPageOptions={[20, 50, 100]}
          labelRowsPerPage="每页"
          labelDisplayedRows={({ from, to, count }) => `${from}-${to} / ${count !== -1 ? count : `超过 ${to}`}`}
        />
      </TableContainer>
    </Box>
  );
};

export default ConceptList;
