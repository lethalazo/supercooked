'use client';

import { useState, useEffect, MouseEvent } from 'react';
import { useRouter } from 'next/navigation';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import IconButton from '@mui/material/IconButton';
import Divider from '@mui/material/Divider';
import DashboardIcon from '@mui/icons-material/Dashboard';
import PeopleIcon from '@mui/icons-material/People';
import DynamicFeedIcon from '@mui/icons-material/DynamicFeed';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import { fetchBeings, Being } from '@/lib/api';

export default function Navbar() {
  const router = useRouter();
  const [beings, setBeings] = useState<Being[]>([]);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  useEffect(() => {
    fetchBeings()
      .then(setBeings)
      .catch(() => setBeings([]));
  }, []);

  const handleMenuOpen = (event: MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleBeingSelect = (slug: string) => {
    handleMenuClose();
    router.push(`/beings/${slug}`);
  };

  return (
    <AppBar position="sticky" elevation={0}>
      <Toolbar sx={{ gap: 1 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            cursor: 'pointer',
            mr: 3,
          }}
          onClick={() => router.push('/')}
        >
          <SmartToyIcon sx={{ color: 'primary.main', fontSize: 28 }} />
          <Typography
            variant="h6"
            sx={{
              fontWeight: 800,
              background: 'linear-gradient(135deg, #1a237e 0%, #00897b 100%)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              letterSpacing: '-0.02em',
            }}
          >
            Super Cooked
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', gap: 0.5, flexGrow: 1 }}>
          <Button
            startIcon={<DashboardIcon />}
            onClick={() => router.push('/')}
            sx={{ color: 'text.primary' }}
          >
            Dashboard
          </Button>
          <Button
            startIcon={<PeopleIcon />}
            onClick={() => router.push('/beings')}
            sx={{ color: 'text.primary' }}
          >
            Beings
          </Button>
          <Button
            startIcon={<DynamicFeedIcon />}
            onClick={() => router.push('/feed')}
            sx={{ color: 'text.primary' }}
          >
            Feed
          </Button>
        </Box>

        <Button
          variant="outlined"
          size="small"
          endIcon={<KeyboardArrowDownIcon />}
          onClick={handleMenuOpen}
          sx={{
            borderColor: 'divider',
            color: 'text.primary',
            '&:hover': {
              borderColor: 'primary.main',
              backgroundColor: 'rgba(26, 35, 126, 0.04)',
            },
          }}
        >
          {beings.length > 0 ? 'Switch Being' : 'No Beings'}
        </Button>
        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl)}
          onClose={handleMenuClose}
          PaperProps={{
            sx: {
              mt: 1,
              minWidth: 200,
              borderRadius: 2,
              boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
            },
          }}
        >
          {beings.length === 0 && (
            <MenuItem disabled>
              <Typography variant="body2" color="text.secondary">
                No beings found
              </Typography>
            </MenuItem>
          )}
          {beings.map((being) => (
            <MenuItem
              key={being.being.slug}
              onClick={() => handleBeingSelect(being.being.slug)}
              sx={{ py: 1.5, px: 2 }}
            >
              <Box>
                <Typography variant="body2" fontWeight={600}>
                  {being.being.name}
                </Typography>
                {being.being.tagline && (
                  <Typography variant="caption" color="text.secondary">
                    {being.being.tagline}
                  </Typography>
                )}
              </Box>
            </MenuItem>
          ))}
        </Menu>
      </Toolbar>
    </AppBar>
  );
}
