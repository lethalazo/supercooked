'use client';

import { useRouter } from 'next/navigation';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CardActions from '@mui/material/CardActions';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Avatar from '@mui/material/Avatar';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import { Being } from '@/lib/api';

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

function getAvatarColor(name: string): string {
  const colors = [
    '#1a237e', '#283593', '#0d47a1', '#01579b',
    '#006064', '#004d40', '#1b5e20', '#33691e',
    '#4a148c', '#880e4f', '#b71c1c', '#e65100',
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

interface BeingCardProps {
  being: Being;
}

export default function BeingCard({ being }: BeingCardProps) {
  const router = useRouter();
  const { being: info, persona, platforms } = being;

  const enabledPlatforms = Object.entries(platforms)
    .filter(([_, config]) => config.enabled)
    .map(([name, config]) => ({ name: name.replace('_', ' '), handle: config.handle }));

  return (
    <Card
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        cursor: 'pointer',
        '&:hover': {
          transform: 'translateY(-2px)',
        },
      }}
      onClick={() => router.push(`/beings/${info.slug}`)}
    >
      <CardContent sx={{ flexGrow: 1, p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, mb: 2 }}>
          <Avatar
            sx={{
              width: 56,
              height: 56,
              bgcolor: getAvatarColor(info.name),
              fontSize: '1.25rem',
              fontWeight: 700,
            }}
          >
            {getInitials(info.name)}
          </Avatar>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.25 }}>
              {info.name}
            </Typography>
            {info.tagline && (
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {info.tagline}
              </Typography>
            )}
          </Box>
        </Box>

        {persona.archetype && (
          <Chip
            label={persona.archetype}
            size="small"
            variant="outlined"
            sx={{ mb: 1.5, color: 'primary.main', borderColor: 'primary.light' }}
          />
        )}

        {enabledPlatforms.length > 0 && (
          <Stack direction="row" spacing={0.5} sx={{ flexWrap: 'wrap', gap: 0.5 }}>
            {enabledPlatforms.map((p) => (
              <Chip
                key={p.name}
                label={p.handle || p.name}
                size="small"
                sx={{
                  bgcolor: 'rgba(0, 137, 123, 0.08)',
                  color: 'secondary.dark',
                  fontSize: '0.75rem',
                }}
              />
            ))}
          </Stack>
        )}
      </CardContent>

      <CardActions sx={{ px: 3, pb: 2.5, pt: 0 }}>
        <Button
          size="small"
          endIcon={<ArrowForwardIcon sx={{ fontSize: 16 }} />}
          sx={{ fontWeight: 600 }}
        >
          View Profile
        </Button>
      </CardActions>
    </Card>
  );
}
