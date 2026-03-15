'use client';

import { useState, useEffect } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';

interface TextFileViewerProps {
  url: string;
  filename: string;
  variant?: 'tweet' | 'thread' | 'default';
}

function detectVariant(filename: string): 'tweet' | 'thread' | 'default' {
  const lower = filename.toLowerCase();
  if (lower.includes('tweet')) return 'tweet';
  if (lower.includes('thread')) return 'thread';
  return 'default';
}

export default function TextFileViewer({ url, filename, variant }: TextFileViewerProps) {
  const [text, setText] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const resolvedVariant = variant || detectVariant(filename);

  useEffect(() => {
    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch');
        return res.text();
      })
      .then((content) => {
        setText(content);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, [url]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 1 }}>
        <CircularProgress size={16} />
        <Typography variant="caption" color="text.secondary">Loading {filename}...</Typography>
      </Box>
    );
  }

  if (error || text === null) {
    return (
      <Typography variant="caption" color="text.disabled">
        Could not load {filename}
      </Typography>
    );
  }

  if (resolvedVariant === 'tweet') {
    return (
      <Box
        sx={{
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 3,
          p: 2,
          bgcolor: 'background.paper',
          maxWidth: 500,
        }}
      >
        <Typography
          variant="body1"
          sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.5 }}
        >
          {text}
        </Typography>
        <Typography variant="caption" color="text.disabled" sx={{ mt: 1, display: 'block' }}>
          {filename}
        </Typography>
      </Box>
    );
  }

  if (resolvedVariant === 'thread') {
    const posts = text.split(/\n{2,}/).filter(Boolean);
    return (
      <Box sx={{ maxWidth: 500 }}>
        {posts.map((post, i) => (
          <Box
            key={i}
            sx={{
              borderLeft: '3px solid',
              borderColor: 'primary.main',
              pl: 2,
              py: 1.5,
              mb: 0,
              position: 'relative',
              '&:not(:last-child)': {
                pb: 2,
              },
            }}
          >
            <Typography variant="caption" color="primary.main" fontWeight={600} sx={{ mb: 0.5, display: 'block' }}>
              {i + 1}/{posts.length}
            </Typography>
            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
              {post}
            </Typography>
          </Box>
        ))}
        <Typography variant="caption" color="text.disabled" sx={{ mt: 1, display: 'block' }}>
          {filename}
        </Typography>
      </Box>
    );
  }

  // Default: plain text box
  return (
    <Box
      sx={{
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 1,
        p: 2,
        bgcolor: 'rgba(0,0,0,0.02)',
      }}
    >
      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.5, fontFamily: 'inherit' }}>
        {text}
      </Typography>
      <Typography variant="caption" color="text.disabled" sx={{ mt: 1, display: 'block' }}>
        {filename}
      </Typography>
    </Box>
  );
}
