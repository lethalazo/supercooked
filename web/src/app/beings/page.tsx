'use client';

import { useState, useEffect } from 'react';
import Typography from '@mui/material/Typography';
import Grid from '@mui/material/Grid2';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import PeopleIcon from '@mui/icons-material/People';
import BeingCard from '@/components/BeingCard';
import { fetchBeings, Being } from '@/lib/api';

export default function BeingsListPage() {
  const [beings, setBeings] = useState<Being[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchBeings()
      .then((data) => {
        setBeings(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load beings');
        setLoading(false);
      });
  }, []);

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h2" sx={{ mb: 0.5 }}>
          Beings
        </Typography>
        <Typography variant="body1" color="text.secondary">
          All digital beings in your network.
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : beings.length === 0 ? (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            py: 10,
          }}
        >
          <PeopleIcon sx={{ fontSize: 80, color: 'text.disabled', mb: 2 }} />
          <Typography variant="h5" color="text.secondary" sx={{ mb: 1 }}>
            No beings found
          </Typography>
          <Typography variant="body1" color="text.disabled">
            Create a being using the CLI or API to get started.
          </Typography>
        </Box>
      ) : (
        <Grid container spacing={3}>
          {beings.map((being) => (
            <Grid size={{ xs: 12, sm: 6, md: 4 }} key={being.being.slug}>
              <BeingCard being={being} />
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
}
