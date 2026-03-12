'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Typography from '@mui/material/Typography';
import Grid from '@mui/material/Grid2';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Avatar from '@mui/material/Avatar';
import Stack from '@mui/material/Stack';
import Divider from '@mui/material/Divider';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import LightbulbIcon from '@mui/icons-material/Lightbulb';
import ArticleIcon from '@mui/icons-material/Article';
import HistoryIcon from '@mui/icons-material/History';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import {
  fetchBeings,
  fetchIdeas,
  fetchActivity,
  Being,
  ContentIdea,
  ActionEntry,
} from '@/lib/api';

function getInitials(name: string): string {
  return name.split(' ').map((w) => w[0]).join('').toUpperCase().slice(0, 2);
}

function getAvatarColor(name: string): string {
  const colors = ['#1a237e', '#283593', '#0d47a1', '#01579b', '#006064', '#004d40', '#4a148c', '#880e4f'];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return colors[Math.abs(hash) % colors.length];
}

function formatTimestamp(ts: string): string {
  try {
    return new Date(ts).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch { return ts; }
}

const statusColors: Record<string, 'default' | 'info' | 'warning' | 'success'> = {
  backlog: 'default', in_progress: 'warning', drafted: 'info', published: 'success',
};

interface BeingDashboard {
  being: Being;
  ideas: ContentIdea[];
  actions: ActionEntry[];
}

export default function DashboardPage() {
  const router = useRouter();
  const [dashboards, setDashboards] = useState<BeingDashboard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const beings = await fetchBeings();
        const results = await Promise.all(
          beings.map(async (being) => {
            const slug = being.being.slug;
            const [ideas, activity] = await Promise.all([
              fetchIdeas(slug).catch(() => ({ slug, ideas: [] })),
              fetchActivity(slug, 7).catch(() => ({ slug, days: 7, actions: [] })),
            ]);
            return { being, ideas: ideas.ideas || [], actions: activity.actions || [] };
          })
        );
        setDashboards(results);
      } catch (err: any) {
        setError(err.message || 'Failed to load');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', py: 12 }}>
        <CircularProgress size={48} />
        <Typography variant="body1" color="text.secondary" sx={{ mt: 2 }}>Loading dashboard...</Typography>
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>;
  }

  if (dashboards.length === 0) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 12 }}>
        <SmartToyIcon sx={{ fontSize: 80, color: 'text.disabled', mb: 2 }} />
        <Typography variant="h5" color="text.secondary" sx={{ mb: 1 }}>No beings yet</Typography>
        <Typography variant="body1" color="text.disabled">Create your first digital being to get started.</Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h2" sx={{ mb: 0.5 }}>Super Cooked</Typography>
        <Typography variant="body1" color="text.secondary">
          Digital beings on the human internet. {dashboards.length} being{dashboards.length !== 1 ? 's' : ''} active.
        </Typography>
      </Box>

      {dashboards.map(({ being, ideas, actions }) => {
        const { being: info, persona, platforms } = being;
        const enabledPlatforms = Object.entries(platforms)
          .filter(([_, c]) => c.enabled)
          .map(([k, c]) => ({ key: k, handle: c.handle }));
        const backlogCount = ideas.filter((i) => i.status === 'backlog').length;
        const draftedCount = ideas.filter((i) => i.status === 'drafted').length;
        const generatedCount = ideas.filter((i) => i.status === 'generated').length;
        const publishedCount = ideas.filter((i) => i.status === 'published').length;

        return (
          <Box key={info.slug} sx={{ mb: 4 }}>
            {/* Being Header Card */}
            <Paper
              sx={{ p: 3, mb: 2, cursor: 'pointer', '&:hover': { boxShadow: '0 4px 20px rgba(0,0,0,0.08)' } }}
              onClick={() => router.push(`/beings/${info.slug}`)}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Avatar sx={{ width: 56, height: 56, bgcolor: getAvatarColor(info.name), fontSize: '1.25rem', fontWeight: 700 }}>
                    {getInitials(info.name)}
                  </Avatar>
                  <Box>
                    <Typography variant="h4" sx={{ fontWeight: 700 }}>{info.name}</Typography>
                    <Typography variant="body2" color="text.secondary">{info.tagline}</Typography>
                    <Stack direction="row" spacing={0.5} sx={{ mt: 0.5 }}>
                      <Chip label={persona.archetype} size="small" color="primary" variant="outlined" sx={{ fontSize: '0.7rem' }} />
                      {enabledPlatforms.map((p) => (
                        <Chip key={p.key} label={p.handle} size="small" sx={{ bgcolor: 'rgba(0,137,123,0.08)', color: 'secondary.dark', fontSize: '0.7rem' }} />
                      ))}
                    </Stack>
                  </Box>
                </Box>
                <Button endIcon={<ArrowForwardIcon />} sx={{ fontWeight: 600 }}>Manage</Button>
              </Box>

              {/* Stats */}
              <Grid container spacing={2} sx={{ mt: 2 }}>
                <Grid size={{ xs: 'grow' }}>
                  <Box sx={{ textAlign: 'center', p: 1, borderRadius: 1.5, bgcolor: 'rgba(230,81,0,0.04)' }}>
                    <Typography variant="h5" fontWeight={700} color="#e65100">{backlogCount}</Typography>
                    <Typography variant="caption" color="text.secondary">Backlog</Typography>
                  </Box>
                </Grid>
                <Grid size={{ xs: 'grow' }}>
                  <Box sx={{ textAlign: 'center', p: 1, borderRadius: 1.5, bgcolor: 'rgba(1,87,155,0.04)' }}>
                    <Typography variant="h5" fontWeight={700} color="#01579b">{draftedCount}</Typography>
                    <Typography variant="caption" color="text.secondary">Drafted</Typography>
                  </Box>
                </Grid>
                <Grid size={{ xs: 'grow' }}>
                  <Box sx={{ textAlign: 'center', p: 1, borderRadius: 1.5, bgcolor: 'rgba(156,39,176,0.04)' }}>
                    <Typography variant="h5" fontWeight={700} color="#9c27b0">{generatedCount}</Typography>
                    <Typography variant="caption" color="text.secondary">Generated</Typography>
                  </Box>
                </Grid>
                <Grid size={{ xs: 'grow' }}>
                  <Box sx={{ textAlign: 'center', p: 1, borderRadius: 1.5, bgcolor: 'rgba(46,125,50,0.04)' }}>
                    <Typography variant="h5" fontWeight={700} color="success.main">{publishedCount}</Typography>
                    <Typography variant="caption" color="text.secondary">Published</Typography>
                  </Box>
                </Grid>
                <Grid size={{ xs: 'grow' }}>
                  <Box sx={{ textAlign: 'center', p: 1, borderRadius: 1.5, bgcolor: 'rgba(26,35,126,0.04)' }}>
                    <Typography variant="h5" fontWeight={700} color="primary.main">{ideas.length}</Typography>
                    <Typography variant="caption" color="text.secondary">Total</Typography>
                  </Box>
                </Grid>
              </Grid>
            </Paper>

            <Grid container spacing={2}>
              {/* Recent Ideas */}
              <Grid size={{ xs: 12, md: 4 }}>
                <Paper sx={{ p: 2.5, height: '100%' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                    <LightbulbIcon sx={{ color: 'primary.main', fontSize: 20 }} />
                    <Typography variant="subtitle1" fontWeight={600}>Ideas</Typography>
                    <Chip label={ideas.length} size="small" sx={{ ml: 'auto' }} />
                  </Box>
                  <Divider sx={{ mb: 1.5 }} />
                  {ideas.length === 0 ? (
                    <Typography variant="body2" color="text.disabled" sx={{ py: 2, textAlign: 'center' }}>
                      No ideas yet
                    </Typography>
                  ) : (
                    <Stack spacing={1}>
                      {ideas.slice(0, 6).map((idea) => (
                        <Box key={idea.id} sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 0.5 }}>
                          <Chip
                            label={idea.status}
                            size="small"
                            color={statusColors[idea.status] || 'default'}
                            variant={idea.status === 'backlog' ? 'outlined' : 'filled'}
                            sx={{ fontSize: '0.65rem', minWidth: 60, textTransform: 'capitalize' }}
                          />
                          <Typography variant="body2" sx={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {idea.title}
                          </Typography>
                        </Box>
                      ))}
                      {ideas.length > 6 && (
                        <Typography variant="caption" color="text.disabled" sx={{ textAlign: 'center' }}>
                          +{ideas.length - 6} more
                        </Typography>
                      )}
                    </Stack>
                  )}
                </Paper>
              </Grid>

              {/* Recent Drafts */}
              <Grid size={{ xs: 12, md: 4 }}>
                <Paper sx={{ p: 2.5, height: '100%' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                    <ArticleIcon sx={{ color: '#01579b', fontSize: 20 }} />
                    <Typography variant="subtitle1" fontWeight={600}>Drafted</Typography>
                    <Chip label={draftedCount} size="small" sx={{ ml: 'auto' }} />
                  </Box>
                  <Divider sx={{ mb: 1.5 }} />
                  {draftedCount === 0 ? (
                    <Typography variant="body2" color="text.disabled" sx={{ py: 2, textAlign: 'center' }}>
                      No drafted ideas yet
                    </Typography>
                  ) : (
                    <Stack spacing={1}>
                      {ideas.filter((i) => i.status === 'drafted').slice(0, 5).map((idea) => (
                        <Box key={idea.id} sx={{ py: 0.5 }}>
                          <Typography variant="body2" fontWeight={500} sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {idea.title}
                          </Typography>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {idea.template && (
                              <Chip label={idea.template.replace(/_/g, ' ')} size="small" variant="outlined" sx={{ fontSize: '0.65rem', textTransform: 'capitalize' }} />
                            )}
                          </Box>
                        </Box>
                      ))}
                    </Stack>
                  )}
                </Paper>
              </Grid>

              {/* Recent Activity */}
              <Grid size={{ xs: 12, md: 4 }}>
                <Paper sx={{ p: 2.5, height: '100%' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                    <HistoryIcon sx={{ color: '#00897b', fontSize: 20 }} />
                    <Typography variant="subtitle1" fontWeight={600}>Activity</Typography>
                    <Chip label={actions.length} size="small" sx={{ ml: 'auto' }} />
                  </Box>
                  <Divider sx={{ mb: 1.5 }} />
                  {actions.length === 0 ? (
                    <Typography variant="body2" color="text.disabled" sx={{ py: 2, textAlign: 'center' }}>
                      No activity yet
                    </Typography>
                  ) : (
                    <Stack spacing={1}>
                      {actions.slice(0, 5).map((action, i) => (
                        <Box key={i} sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, py: 0.5 }}>
                          <CheckCircleOutlineIcon sx={{ fontSize: 16, color: action.error ? 'error.main' : 'success.main', mt: 0.25 }} />
                          <Box sx={{ flex: 1, minWidth: 0 }}>
                            <Typography variant="body2" fontWeight={500}>{action.action}</Typography>
                            <Typography variant="caption" color="text.disabled">{formatTimestamp(action.timestamp)}</Typography>
                          </Box>
                        </Box>
                      ))}
                    </Stack>
                  )}
                </Paper>
              </Grid>
            </Grid>
          </Box>
        );
      })}
    </Box>
  );
}
