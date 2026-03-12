'use client';

import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Divider from '@mui/material/Divider';
import Avatar from '@mui/material/Avatar';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import ArticleIcon from '@mui/icons-material/Article';
import { ContentItem } from '@/lib/api';

function formatTimestamp(ts?: string): string {
  if (!ts) return '';
  try {
    const date = new Date(ts);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return ts;
  }
}

function getTypeBadgeColor(type?: string): 'primary' | 'secondary' | 'success' | 'warning' | 'info' | 'error' | 'default' {
  const map: Record<string, 'primary' | 'secondary' | 'success' | 'warning' | 'info' | 'error'> = {
    hot_take: 'error',
    list_countdown: 'warning',
    talking_head: 'info',
    photo_post: 'success',
    thread: 'primary',
    story: 'secondary',
  };
  return type ? map[type] || 'default' : 'default';
}

interface ContentFeedProps {
  items: ContentItem[];
  showBeing?: boolean;
}

export default function ContentFeed({ items, showBeing = false }: ContentFeedProps) {
  if (items.length === 0) {
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
        <ArticleIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
        <Typography variant="h6" color="text.secondary">
          No content yet
        </Typography>
        <Typography variant="body2" color="text.disabled">
          Content will appear here once created.
        </Typography>
      </Box>
    );
  }

  return (
    <Stack spacing={2}>
      {items.map((item, index) => {
        const contentType = item.template || item.type || 'content';
        const timestamp = item.published_at || item.created;

        return (
          <Card key={item.id || item.content_id || index}>
            <CardContent sx={{ p: 3, '&:last-child': { pb: 3 } }}>
              <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 1.5 }}>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                    <Chip
                      label={contentType.replace(/_/g, ' ')}
                      size="small"
                      color={getTypeBadgeColor(contentType)}
                      sx={{ textTransform: 'capitalize' }}
                    />
                    {item.status && (
                      <Chip
                        label={item.status}
                        size="small"
                        variant="outlined"
                        sx={{ textTransform: 'capitalize' }}
                      />
                    )}
                    {item.platform && (
                      <Chip
                        label={item.platform}
                        size="small"
                        variant="outlined"
                        color="secondary"
                        sx={{ textTransform: 'capitalize' }}
                      />
                    )}
                  </Box>
                  <Typography variant="h6" sx={{ fontWeight: 600, mt: 1 }}>
                    {item.title || 'Untitled'}
                  </Typography>
                </Box>
              </Box>

              {showBeing && item.being?.name && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                  <Avatar sx={{ width: 20, height: 20, fontSize: '0.6rem', bgcolor: 'primary.main' }}>
                    {item.being.name[0]}
                  </Avatar>
                  <Typography variant="caption" color="text.secondary" fontWeight={500}>
                    {item.being.name}
                  </Typography>
                </Box>
              )}

              {(item.caption || item.concept) && (
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                    mt: 1,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    display: '-webkit-box',
                    WebkitLineClamp: 3,
                    WebkitBoxOrient: 'vertical',
                  }}
                >
                  {item.caption || item.concept}
                </Typography>
              )}

              {timestamp && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 2 }}>
                  <AccessTimeIcon sx={{ fontSize: 14, color: 'text.disabled' }} />
                  <Typography variant="caption" color="text.disabled">
                    {formatTimestamp(timestamp)}
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        );
      })}
    </Stack>
  );
}
