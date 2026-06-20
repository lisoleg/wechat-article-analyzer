import React from 'react';
import { Chip, Tooltip } from '@mui/material';
import { Psychology, TrendingUp, Timeline, School } from '@mui/icons-material';
import type { TheorySystem } from '../api/client';

interface ConceptNodeProps {
  concept: string;
  frequency: number;
  pillars: string[];
  theorySystems: TheorySystem[];
  onClick?: (concept: string) => void;
  size?: 'small' | 'medium' | 'large';
}

const pillarIcons: Record<string, React.ReactNode> = {
  '刘原理': <Psychology fontSize="small" />,
  '三视界法': <Timeline fontSize="small" />,
  '太乙预言机': <TrendingUp fontSize="small" />,
  '全息拓扑动力学': <School fontSize="small" />,
};

const getPillarColor = (pillar: string, theorySystems: TheorySystem[]): string => {
  for (const system of theorySystems) {
    if (system.pillars.includes(pillar)) {
      return system.color_code;
    }
  }
  return '#1a73e8'; // 默认颜色
};

const ConceptNode: React.FC<ConceptNodeProps> = ({
  concept,
  frequency,
  pillars,
  theorySystems,
  onClick,
  size = 'medium',
}) => {
  const mainPillar = pillars[0] || '';
  const pillarColor = getPillarColor(mainPillar, theorySystems);
  const icon = pillarIcons[mainPillar] as React.ReactElement | undefined;

  return (
    <Tooltip title={`${concept}: 频次 ${frequency}`}>
      <Chip
        label={concept}
        onClick={() => onClick?.(concept)}
        sx={{
          bgcolor: `${pillarColor}20`,
          color: pillarColor,
          border: `1px solid ${pillarColor}`,
          fontWeight: 'bold',
          '&:hover': {
            bgcolor: `${pillarColor}40`,
          },
          ...(size === 'small' && { fontSize: '0.75rem', height: '24px' }),
          ...(size === 'large' && { fontSize: '1rem', height: '36px' }),
        }}
        icon={icon}
      />
    </Tooltip>
  );
};

export default ConceptNode;
