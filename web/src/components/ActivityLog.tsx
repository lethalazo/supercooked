'use client';

import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import HistoryIcon from '@mui/icons-material/History';
import TimelineIcon from '@mui/icons-material/Timeline';
import { ActionEntry } from '@/lib/api';

function formatTimestamp(ts: string): string {
  try {
    const date = new Date(ts);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return ts;
  }
}

interface ActivityLogProps {
  actions: ActionEntry[];
}

export default function ActivityLog({ actions }: ActivityLogProps) {
  if (actions.length === 0) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          py: 8,
        }}
      >
        <HistoryIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
        <Typography variant="h6" color="text.secondary">
          No activity yet
        </Typography>
        <Typography variant="body2" color="text.disabled">
          Actions will appear here as the being operates.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ position: 'relative' }}>
      {/* Timeline line */}
      <Box
        sx={{
          position: 'absolute',
          left: 20,
          top: 0,
          bottom: 0,
          width: 2,
          bgcolor: 'divider',
          zIndex: 0,
        }}
      />

      <Stack spacing={0}>
        {actions.map((action, index) => {
          const hasError = !!action.error;

          return (
            <Box
              key={index}
              sx={{
                display: 'flex',
                gap: 2,
                position: 'relative',
                zIndex: 1,
                py: 1.5,
              }}
            >
              {/* Timeline dot */}
              <Box
                sx={{
                  width: 42,
                  display: 'flex',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <Box
                  sx={{
                    width: 12,
                    height: 12,
                    borderRadius: '50%',
                    bgcolor: hasError ? 'error.main' : 'success.main',
                    border: '2px solid',
                    borderColor: 'background.paper',
                    boxShadow: '0 0 0 3px ' + (hasError ? 'rgba(211, 47, 47, 0.15)' : 'rgba(46, 125, 50, 0.15)'),
                    mt: 0.75,
                  }}
                />
              </Box>

              {/* Entry content */}
              <Paper
                sx={{
                  flex: 1,
                  p: 2,
                  borderLeft: '3px solid',
                  borderColor: hasError ? 'error.light' : 'success.light',
                }}
              >
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    justifyContent: 'space-between',
                    gap: 1,
                    mb: 0.75,
                  }}
                >
                  <Typography variant="body2" fontWeight={600}>
                    {action.action}
                  </Typography>
                  <Typography variant="caption" color="text.disabled" sx={{ flexShrink: 0 }}>
                    {formatTimestamp(action.timestamp)}
                  </Typography>
                </Box>

                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                  {action.platform && (
                    <Chip
                      label={action.platform}
                      size="small"
                      variant="outlined"
                      color="secondary"
                      sx={{ textTransform: 'capitalize' }}
                    />
                  )}

                  {action.result && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <CheckCircleOutlineIcon sx={{ fontSize: 14, color: 'success.main' }} />
                      <Typography variant="caption" color="success.main">
                        {action.result}
                      </Typography>
                    </Box>
                  )}

                  {action.error && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <ErrorOutlineIcon sx={{ fontSize: 14, color: 'error.main' }} />
                      <Typography variant="caption" color="error.main">
                        {action.error}
                      </Typography>
                    </Box>
                  )}
                </Box>
              </Paper>
            </Box>
          );
        })}
      </Stack>
    </Box>
  );
}
