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
  Grid,
  Card,
  CardContent,
  Chip,
} from '@mui/material';
import { useAppStore } from '../store/useAppStore';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';

const Settings: React.FC = () => {
  const {
    theorySystems,
    status,
    loading,
    error,
    fetchTheorySystems,
    fetchStatus,
    clearError,
  } = useAppStore();

  const [openDialog, setOpenDialog] = useState<boolean>(false);
  const [newSystem, setNewSystem] = useState({
    system_name: '',
    description: '',
    pillars: '',
    color_code: '#1a73e8',
  });

  useEffect(() => {
    fetchTheorySystems();
    fetchStatus();
  }, [fetchTheorySystems, fetchStatus]);

  const handleAddSystem = () => {
    // 这里应该调用API添加理论系统，暂时只是模拟
    console.log('Adding theory system:', newSystem);
    setOpenDialog(false);
    setNewSystem({
      system_name: '',
      description: '',
      pillars: '',
      color_code: '#1a73e8',
    });
  };

  const handleDeleteSystem = (id: string) => {
    // 这里应该调用API删除理论系统，暂时只是模拟
    console.log('Deleting theory system:', id);
  };

  const checkApiStatus = async () => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE || 'http://localhost:8000'}/api/status`);
      if (response.ok) {
        alert('API 服务器连接正常');
      } else {
        alert('API 服务器响应异常');
      }
    } catch (error) {
      alert('无法连接到 API 服务器');
    }
  };

  if (loading && !theorySystems.length && !status) {
    return <LoadingSpinner message="加载设置..." />;
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        设置
      </Typography>
      
      <ErrorAlert error={error} onClose={clearError} />
      
      {/* 理论体系管理 */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">
            理论体系管理
          </Typography>
          <Button
            variant="contained"
            onClick={() => setOpenDialog(true)}
          >
            添加理论体系
          </Button>
        </Box>
        
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>系统名称</TableCell>
                <TableCell>描述</TableCell>
                <TableCell>理论支柱</TableCell>
                <TableCell>颜色</TableCell>
                <TableCell>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {theorySystems && theorySystems.length > 0 ? (
                theorySystems.map((system) => (
                  <TableRow key={system.id}>
                    <TableCell>{system.system_name}</TableCell>
                    <TableCell>{system.description}</TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {system.pillars.map((pillar, index) => (
                          <Chip
                            key={index}
                            label={pillar}
                            size="small"
                            sx={{
                              bgcolor: `${system.color_code}20`,
                              color: system.color_code,
                              border: `1px solid ${system.color_code}`,
                            }}
                          />
                        ))}
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Box
                        sx={{
                          width: 24,
                          height: 24,
                          bgcolor: system.color_code,
                          borderRadius: '4px',
                          border: '1px solid #ccc',
                        }}
                      />
                    </TableCell>
                    <TableCell>
                      <Button
                        size="small"
                        color="error"
                        onClick={() => handleDeleteSystem(system.id)}
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
                      暂无理论体系数据
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
      
      {/* 数据库信息 */}
      {status && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            数据库信息
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="subtitle2" sx={{ color: 'text.secondary' }}>
                    数据库大小
                  </Typography>
                  <Typography variant="h4">
                    {status.db_size_mb?.toFixed(2) || 0} MB
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="subtitle2" sx={{ color: 'text.secondary' }}>
                    文章统计
                  </Typography>
                  <Typography variant="body1">
                    总数: {status.total_articles || 0} | 
                    已采集: {status.crawled || 0} | 
                    已分析: {status.analyzed || 0}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Paper>
      )}
      
      {/* API 服务器状态 */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          API 服务器状态
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Chip
            label={status ? '运行中' : '未连接'}
            color={status ? 'success' : 'error'}
          />
          <Typography>
            API 地址: {import.meta.env.VITE_API_BASE || 'http://localhost:8000'}
          </Typography>
          <Button
            variant="outlined"
            onClick={checkApiStatus}
          >
            检查连接
          </Button>
        </Box>
      </Paper>
      
      {/* 添加理论体系对话框 */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)}>
        <DialogTitle>添加理论体系</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2, minWidth: '400px' }}>
            <TextField
              fullWidth
              label="系统名称"
              value={newSystem.system_name}
              onChange={(e) => setNewSystem({ ...newSystem, system_name: e.target.value })}
            />
            <TextField
              fullWidth
              label="描述"
              value={newSystem.description}
              onChange={(e) => setNewSystem({ ...newSystem, description: e.target.value })}
              multiline
              rows={3}
            />
            <TextField
              fullWidth
              label="理论支柱 (逗号分隔)"
              value={newSystem.pillars}
              onChange={(e) => setNewSystem({ ...newSystem, pillars: e.target.value })}
              helperText="例如: 刘原理,三视界法,太乙预言机"
            />
            <TextField
              fullWidth
              label="颜色代码"
              value={newSystem.color_code}
              onChange={(e) => setNewSystem({ ...newSystem, color_code: e.target.value })}
              helperText="十六进制颜色代码，例如: #1a73e8"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>取消</Button>
          <Button
            onClick={handleAddSystem}
            disabled={!newSystem.system_name || !newSystem.pillars}
          >
            添加
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Settings;
