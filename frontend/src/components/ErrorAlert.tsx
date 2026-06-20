import React from 'react';
import { Alert, AlertTitle, IconButton } from '@mui/material';
import { Close } from '@mui/icons-material';

interface ErrorAlertProps {
  error: string | null;
  onClose?: () => void;
  severity?: 'error' | 'warning' | 'info' | 'success';
  title?: string;
}

const ErrorAlert: React.FC<ErrorAlertProps> = ({ 
  error, 
  onClose, 
  severity = 'error',
  title 
}) => {
  if (!error) return null;

  return (
    <Alert
      severity={severity}
      action={
        onClose ? (
          <IconButton
            aria-label="close"
            color="inherit"
            size="small"
            onClick={onClose}
          >
            <Close fontSize="inherit" />
          </IconButton>
        ) : undefined
      }
      sx={{ mb: 2 }}
    >
      {title && <AlertTitle>{title}</AlertTitle>}
      {error}
    </Alert>
  );
};

export default ErrorAlert;
