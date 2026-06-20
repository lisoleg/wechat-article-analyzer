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
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import Chip from '@mui/material/Chip';
import { useAppStore } from '../store/useAppStore';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';

const Synonyms: React.FC = () => {
  const {
    synonyms,
    loading,
    error,
    fetchSynonyms,
    clearError,
  } = useAppStore();

  const [openDialog, setOpenDialog] = useState<boolean>(false);
  const [newMapping, setNewMapping] = useState({
    original_concept: '',
    standardized_concept: '',
    mapping_type: 'manual',
    confidence: 1.0,
  });

  useEffect(() => {
    fetchSynonyms();
  }, [fetchSynonyms]);

  const handleAddMapping = () => {
    // 这里应该调用API添加映射，暂时只是模拟
    console.log('Adding mapping:', newMapping);
    setOpenDialog(false);
    setNewMapping({
      original_concept: '',
      standardized_concept: '',
      mapping_type: 'manual',
      confidence: 1.0,
    });
  };

  const handleDeleteMapping = (id: string) => {
    // 这里应该调用API删除映射，暂时只是模拟
    console.log('Deleting mapping:', id);
  };

  if (loading && (!synonyms || synonyms.length === 0)) {
    return <LoadingSpinner message="加载同义词映射..." />;
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        同义词映射管理
      </Typography>
      
      <ErrorAlert error={error} onClose={clearError} />
      
      {/* 添加按钮 */}
      <Box sx={{ mb: 3 }}>
        <Button
          variant="contained"
          onClick={() => setOpenDialog(true)}
        >
          添加映射
        </Button>
      </Box>
      
      {/* 同义词映射表格 */}
      <Paper sx={{ p: 3 }}>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>原始概念</TableCell>
                <TableCell>标准化概念</TableCell>
                <TableCell>映射类型</TableCell>
                <TableCell>置信度</TableCell>
                <TableCell>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {synonyms && synonyms.length > 0 ? (
                synonyms.map((mapping) => (
                  <TableRow key={mapping.id}>
                    <TableCell>{mapping.original_concept}</TableCell>
                    <TableCell>{mapping.standardized_concept}</TableCell>
                    <TableCell>
                      <Chip
                        label={mapping.mapping_type}
                        size="small"
                        color={mapping.mapping_type === 'manual' ? 'primary' : 'default'}
                      />
                    </TableCell>
                    <TableCell>
                      {(mapping.confidence * 100).toFixed(0)}%
                    </TableCell>
                    <TableCell>
                      <Button
                        size="small"
                        color="error"
                        onClick={() => handleDeleteMapping(mapping.id)}
                      >
                        删除
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={5} align="center">
                    <Typography sx={{ color: 'text.secondary', py: 4 }}>
                      暂无同义词映射数据
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
      
      {/* 添加映射对话框 */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)}>
        <DialogTitle>添加同义词映射</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2, minWidth: '400px' }}>
            <TextField
              fullWidth
              label="原始概念"
              value={newMapping.original_concept}
              onChange={(e) => setNewMapping({ ...newMapping, original_concept: e.target.value })}
            />
            <TextField
              fullWidth
              label="标准化概念"
              value={newMapping.standardized_concept}
              onChange={(e) => setNewMapping({ ...newMapping, standardized_concept: e.target.value })}
            />
            <FormControl fullWidth>
              <InputLabel>映射类型</InputLabel>
              <Select
                value={newMapping.mapping_type}
                label="映射类型"
                onChange={(e) => setNewMapping({ ...newMapping, mapping_type: e.target.value })}
              >
                <MenuItem value="manual">手动</MenuItem>
                <MenuItem value="auto">自动</MenuItem>
                <MenuItem value="rule">规则</MenuItem>
              </Select>
            </FormControl>
            <TextField
              fullWidth
              label="置信度 (0-1)"
              type="number"
              inputProps={{ min: 0, max: 1, step: 0.1 }}
              value={newMapping.confidence}
              onChange={(e) => setNewMapping({ ...newMapping, confidence: parseFloat(e.target.value) })}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>取消</Button>
          <Button
            onClick={handleAddMapping}
            disabled={!newMapping.original_concept || !newMapping.standardized_concept}
          >
            添加
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Synonyms;
