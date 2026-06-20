import React from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';
import { ArrowUpward, ArrowDownward } from '@mui/icons-material';

interface StatCardProps {
  title: string;
  value: number | string;
  icon?: React.ReactNode;
  color?: string;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  onClick?: () => void;
  clickable?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({ 
  title, 
  value, 
  icon, 
  color = 'primary.main',
  trend,
  onClick,
  clickable = false,
}) => {
  return (
    <Card 
      sx={{ 
        height: '100%', 
        cursor: clickable ? 'pointer' : 'default',
        transition: clickable ? 'transform 0.2s, box-shadow 0.2s' : 'none',
        '&:hover': clickable ? {
          transform: 'translateY(-4px)',
          boxShadow: 4,
        } : {},
      }}
      onClick={clickable ? onClick : undefined}
      role={clickable ? 'button' : undefined}
      tabIndex={clickable ? 0 : undefined}
    >
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="subtitle2" sx={{ color: 'text.secondary' }}>
            {title}
            {clickable && (
              <Typography component="span" variant="caption" sx={{ ml: 1, color: 'primary.main' }}>
                点击查看 →
              </Typography>
            )}
          </Typography>
          {icon && (
            <Box sx={{ color: color }}>
              {icon}
            </Box>
          )}
        </Box>
        <Typography variant="h4" component="div" sx={{ fontWeight: 'bold' }}>
          {value}
        </Typography>
        {trend && (
          <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
            {trend.isPositive ? (
              <ArrowUpward fontSize="small" color="success" />
            ) : (
              <ArrowDownward fontSize="small" color="error" />
            )}
            <Typography 
              variant="body2" 
              sx={{ color: trend.isPositive ? 'success.main' : 'error.main', ml: 0.5 }}
            >
              {trend.value}%
            </Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary', ml: 1 }}>
              与上月相比
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default StatCard;
