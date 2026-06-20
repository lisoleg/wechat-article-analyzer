import React from 'react';
import { Chip, Tooltip } from '@mui/material';
import { Psychology, Timeline, TrendingUp, School } from '@mui/icons-material';

interface PillarBadgeProps {
  pillar: string;
  color?: string;
  size?: 'small' | 'medium';
  onClick?: () => void;
}

const pillarConfig: Record<string, { icon: React.ReactNode; color: string }> = {
  '刘原理': { icon: <Psychology fontSize="small" />, color: '#1a73e8' },
  '三视界法': { icon: <Timeline fontSize="small" />, color: '#34a853' },
  '太乙预言机': { icon: <TrendingUp fontSize="small" />, color: '#ea4335' },
  '全息拓扑动力学': { icon: <School fontSize="small" />, color: '#fbbc04' },
};

const PillarBadge: React.FC<PillarBadgeProps> = ({ 
  pillar, 
  color,
  size = 'small',
  onClick 
}) => {
  const config = pillarConfig[pillar] || { icon: undefined, color: '#9aa0a6' };
  const badgeColor = color || config.color;
  const icon = config.icon as React.ReactElement | undefined;

  return (
    <Tooltip title={pillar}>
      <Chip
        label={pillar}
        icon={icon}
        size={size}
        onClick={onClick}
        sx={{
          bgcolor: `${badgeColor}20`,
          color: badgeColor,
          border: `1px solid ${badgeColor}`,
          fontSize: size === 'small' ? '0.7rem' : '0.8rem',
          height: size === 'small' ? '20px' : '24px',
          '& .MuiChip-icon': {
            color: badgeColor,
          },
        }}
      />
    </Tooltip>
  );
};

export default PillarBadge;
