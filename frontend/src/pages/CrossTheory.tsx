import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  FormGroup,
  FormControlLabel,
  Checkbox,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
} from '@mui/material';
import { useAppStore } from '../store/useAppStore';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';

const CrossTheory: React.FC = () => {
  const {
    crossTheory,
    theorySystems,
    loading,
    error,
    fetchCrossTheory,
    fetchTheorySystems,
    clearError,
  } = useAppStore();

  const [selectedSystems, setSelectedSystems] = useState<string[]>([]);

  useEffect(() => {
    fetchTheorySystems();
    fetchCrossTheory();
  }, [fetchTheorySystems, fetchCrossTheory]);

  useEffect(() => {
    if (theorySystems.length > 0 && selectedSystems.length === 0) {
      setSelectedSystems(theorySystems.slice(0, 2).map(s => s.id));
    }
  }, [theorySystems, selectedSystems]);

  const handleSystemToggle = (systemId: string) => {
    setSelectedSystems(prev => {
      if (prev.includes(systemId)) {
        return prev.filter(id => id !== systemId);
      } else {
        return [...prev, systemId];
      }
    });
  };

  // 获取选中的系统数据
  const selectedSystemsData = React.useMemo(() => {
    if (!crossTheory) return [];
    return crossTheory.systems.filter(s => 
      selectedSystems.some(id => 
        theorySystems.find(ts => ts.id === id)?.system_name === s.name
      )
    );
  }, [crossTheory, selectedSystems, theorySystems]);

  // 准备对比矩阵数据
  const pivotData = React.useMemo(() => {
    if (selectedSystemsData.length === 0) return [];
    
    const allPillars = new Set<string>();
    selectedSystemsData.forEach(system => {
      system.pillars.forEach(pillar => allPillars.add(pillar));
      Object.keys(system.pillar_distribution).forEach(pillar => allPillars.add(pillar));
    });
    
    return Array.from(allPillars).map(pillar => {
      const row: any = { pillar };
      selectedSystemsData.forEach(system => {
        row[system.name] = system.pillar_distribution[pillar] || 0;
      });
      return row;
    });
  }, [selectedSystemsData]);

  if (loading && !crossTheory) {
    return <LoadingSpinner message="加载跨理论数据..." />;
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        跨理论体系对比
      </Typography>
      
      <ErrorAlert error={error} onClose={clearError} />
      
      {/* 理论体系选择器 */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          选择理论体系 (至少选择2个):
        </Typography>
        <FormGroup row>
          {theorySystems.map(system => (
            <FormControlLabel
              key={system.id}
              control={
                <Checkbox
                  checked={selectedSystems.includes(system.id)}
                  onChange={() => handleSystemToggle(system.id)}
                  disabled={!selectedSystems.includes(system.id) && selectedSystems.length >= 3}
                />
              }
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Chip
                    label={system.system_name}
                    size="small"
                    sx={{
                      bgcolor: `${system.color_code}20`,
                      color: system.color_code,
                      border: `1px solid ${system.color_code}`,
                    }}
                  />
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                    ({system.pillars.join(', ')})
                  </Typography>
                </Box>
              }
            />
          ))}
        </FormGroup>
      </Paper>
      
      {selectedSystemsData.length >= 2 && (
        <>
          {/* 对比矩阵 */}
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              理论支柱分布对比
            </Typography>
            {pivotData.length > 0 ? (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>理论支柱</TableCell>
                      {selectedSystemsData.map(system => (
                        <TableCell key={system.name} align="center">
                          <Chip
                            label={system.name}
                            size="small"
                            sx={{
                              bgcolor: `${system.color_code}20`,
                              color: system.color_code,
                              border: `1px solid ${system.color_code}`,
                            }}
                          />
                        </TableCell>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {pivotData.map(row => (
                      <TableRow key={row.pillar}>
                        <TableCell component="th" scope="row">
                          {row.pillar}
                        </TableCell>
                        {selectedSystemsData.map(system => (
                          <TableCell key={system.name} align="center">
                            <Box
                              sx={{
                                bgcolor: row[system.name] > 0 ? `${system.color_code}40` : 'transparent',
                                color: row[system.name] > 0 ? system.color_code : 'text.disabled',
                                fontWeight: row[system.name] > 0 ? 'bold' : 'normal',
                                py: 1,
                                borderRadius: 1,
                              }}
                            >
                              {row[system.name] || '-'}
                            </Box>
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Typography sx={{ color: 'text.secondary' }}>暂无数据</Typography>
            )}
          </Paper>
          
          {/* Venn图区域 - 简化为文本展示 */}
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              概念重叠分析
            </Typography>
            {crossTheory && (
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" gutterBottom>
                    共有概念 ({crossTheory.shared_concepts.length}):
                  </Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, maxHeight: '200px', overflow: 'auto' }}>
                    {crossTheory.shared_concepts.map(concept => (
                      <Chip key={concept} label={concept} size="small" />
                    ))}
                  </Box>
                </Grid>
                
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" gutterBottom>
                    独有概念:
                  </Typography>
                  {selectedSystemsData.map(system => (
                    <Box key={system.name} sx={{ mb: 2 }}>
                      <Chip
                        label={system.name}
                        size="small"
                        sx={{
                          bgcolor: `${system.color_code}20`,
                          color: system.color_code,
                          border: `1px solid ${system.color_code}`,
                          mb: 1,
                        }}
                      />
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {system.unique_concepts.slice(0, 20).map(concept => (
                          <Chip key={concept} label={concept} size="small" variant="outlined" />
                        ))}
                        {system.unique_concepts.length > 20 && (
                          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                            +{system.unique_concepts.length - 20} 更多
                          </Typography>
                        )}
                      </Box>
                    </Box>
                  ))}
                </Grid>
              </Grid>
            )}
          </Paper>
        </>
      )}
    </Box>
  );
};

export default CrossTheory;
