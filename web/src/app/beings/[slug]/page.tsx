'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Paper from '@mui/material/Paper';
import Chip from '@mui/material/Chip';
import Avatar from '@mui/material/Avatar';
import Grid from '@mui/material/Grid2';
import Stack from '@mui/material/Stack';
import Divider from '@mui/material/Divider';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import LinearProgress from '@mui/material/LinearProgress';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import LightbulbIcon from '@mui/icons-material/Lightbulb';
import ArticleIcon from '@mui/icons-material/Article';
import HistoryIcon from '@mui/icons-material/History';
import ChatIcon from '@mui/icons-material/Chat';
import PersonIcon from '@mui/icons-material/Person';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import RecordVoiceOverIcon from '@mui/icons-material/RecordVoiceOver';
import BlockIcon from '@mui/icons-material/Block';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import VisibilityIcon from '@mui/icons-material/Visibility';
import CategoryIcon from '@mui/icons-material/Category';
import MoodIcon from '@mui/icons-material/Mood';
import AddIcon from '@mui/icons-material/Add';
import YouTubeIcon from '@mui/icons-material/YouTube';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import PublishIcon from '@mui/icons-material/Publish';
import BuildIcon from '@mui/icons-material/Build';
import EditNoteIcon from '@mui/icons-material/EditNote';
import AudioFileIcon from '@mui/icons-material/AudioFile';
import RefreshIcon from '@mui/icons-material/Refresh';
import FaceIcon from '@mui/icons-material/Face';
import {
  fetchBeing,
  fetchIdeas,
  fetchContent,
  fetchActivity,
  fetchContentDetail,
  generateIdeas,
  draftIdea,
  generateIdea,
  publishIdea,
  regenerateIdea,
  generateFace,
  getFaceUrl,
  getFileUrl,
  Being,
  ContentIdea,
  ContentResponse,
  ActionEntry,
} from '@/lib/api';
import AddIdeaForm from '@/components/AddIdeaForm';
import ActivityLog from '@/components/ActivityLog';
import ChatWindow from '@/components/ChatWindow';
import TextFileViewer from '@/components/TextFileViewer';

const platformLabels: Record<string, string> = {
  youtube_shorts: 'YouTube Shorts',
  x: 'X (Twitter)',
  instagram: 'Instagram',
  tiktok: 'TikTok',
  twitch: 'Twitch',
};

const statusColors: Record<string, 'default' | 'primary' | 'secondary' | 'success' | 'warning' | 'info' | 'error'> = {
  backlog: 'default',
  in_progress: 'warning',
  drafted: 'info',
  generated: 'secondary',
  published: 'success',
  archived: 'default',
};

const templateColors: Record<string, 'primary' | 'secondary' | 'success' | 'warning' | 'info' | 'error' | 'default'> = {
  hot_take: 'error',
  list_countdown: 'warning',
  talking_head: 'info',
  photo_post: 'success',
  thread: 'primary',
  story: 'secondary',
};

function formatTimestamp(ts: string): string {
  try {
    const date = new Date(ts);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return ts;
  }
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel({ children, value, index }: TabPanelProps) {
  if (value !== index) return null;
  return <Box sx={{ pt: 3 }}>{children}</Box>;
}

export default function BeingManagementPage() {
  const params = useParams();
  const router = useRouter();
  const slug = params.slug as string;

  const [tab, setTab] = useState(0);
  const [being, setBeing] = useState<Being | null>(null);
  const [ideas, setIdeas] = useState<ContentIdea[]>([]);
  const [content, setContent] = useState<ContentResponse | null>(null);
  const [actions, setActions] = useState<ActionEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Ideation state
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);

  // Pipeline action state
  const [actionId, setActionId] = useState<string | null>(null);
  const [actionType, setActionType] = useState<string | null>(null);
  const [produceError, setProduceError] = useState<string | null>(null);
  const [produceSuccess, setProduceSuccess] = useState<string | null>(null);

  // Script preview dialog
  const [previewIdea, setPreviewIdea] = useState<string | null>(null);
  const [previewScript, setPreviewScript] = useState<any>(null);

  // Face generation state
  const [faceUrl, setFaceUrl] = useState<string | null>(null);
  const [generatingFace, setGeneratingFace] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [beingData, ideasData, contentData, activityData] = await Promise.all([
        fetchBeing(slug),
        fetchIdeas(slug).catch(() => ({ slug, ideas: [] })),
        fetchContent(slug).catch(() => ({ slug, drafts: [], published: [] })),
        fetchActivity(slug, 30).catch(() => ({ slug, days: 30, actions: [] })),
      ]);
      setBeing(beingData);
      setIdeas(ideasData.ideas || []);
      setContent(contentData);
      setActions(activityData.actions || []);
      // Try loading face image (may 404 if not generated yet)
      setFaceUrl(getFaceUrl(slug) + `?t=${Date.now()}`);
    } catch (err: any) {
      setError(err.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setGenerateError(null);
    try {
      await generateIdeas(slug, 5);
      // Reload ideas
      const ideasData = await fetchIdeas(slug);
      setIdeas(ideasData.ideas || []);
    } catch (err: any) {
      setGenerateError(err.message || 'Failed to generate ideas');
    } finally {
      setIsGenerating(false);
    }
  };

  const reloadData = async () => {
    const [ideasData, contentData, activityData] = await Promise.all([
      fetchIdeas(slug).catch(() => ({ slug, ideas: [] })),
      fetchContent(slug).catch(() => ({ slug, drafts: [], published: [] })),
      fetchActivity(slug, 30).catch(() => ({ slug, days: 30, actions: [] })),
    ]);
    setIdeas(ideasData.ideas || []);
    setContent(contentData);
    setActions(activityData.actions || []);
  };

  const handleDraft = async (ideaId: string) => {
    setActionId(ideaId);
    setActionType('draft');
    setProduceError(null);
    setProduceSuccess(null);
    try {
      const result = await draftIdea(slug, ideaId);
      setProduceSuccess(`Drafted: ${result.title}`);
      await reloadData();
    } catch (err: any) {
      setProduceError(err.message || 'Failed to draft content');
    } finally {
      setActionId(null);
      setActionType(null);
    }
  };

  const handleGenerateMedia = async (ideaId: string) => {
    setActionId(ideaId);
    setActionType('generate');
    setProduceError(null);
    setProduceSuccess(null);
    try {
      const result = await generateIdea(slug, ideaId);
      setProduceSuccess(`Generated ${result.files?.length || 0} files for: ${result.title}`);
      await reloadData();
    } catch (err: any) {
      setProduceError(err.message || 'Failed to generate media');
    } finally {
      setActionId(null);
      setActionType(null);
    }
  };

  const handlePublish = async (ideaId: string) => {
    setActionId(ideaId);
    setActionType('publish');
    setProduceError(null);
    setProduceSuccess(null);
    try {
      const result = await publishIdea(slug, ideaId);
      setProduceSuccess(`Published: ${ideaId}`);
      await reloadData();
    } catch (err: any) {
      setProduceError(err.message || 'Failed to publish content');
    } finally {
      setActionId(null);
      setActionType(null);
    }
  };

  const handleRegenerate = async (ideaId: string) => {
    setActionId(ideaId);
    setActionType('regenerate');
    setProduceError(null);
    setProduceSuccess(null);
    try {
      const result = await regenerateIdea(slug, ideaId);
      setProduceSuccess(`Re-generated ${result.files?.length || 0} files for: ${result.title}`);
      await reloadData();
    } catch (err: any) {
      setProduceError(err.message || 'Failed to re-generate media');
    } finally {
      setActionId(null);
      setActionType(null);
    }
  };

  const handleGenerateFace = async () => {
    setGeneratingFace(true);
    setProduceError(null);
    try {
      await generateFace(slug);
      setFaceUrl(getFaceUrl(slug) + `?t=${Date.now()}`);
      setProduceSuccess('Face/profile picture generated!');
    } catch (err: any) {
      setProduceError(err.message || 'Failed to generate face');
    } finally {
      setGeneratingFace(false);
    }
  };

  const handlePreviewScript = async (ideaId: string) => {
    try {
      const data = await fetchContentDetail(slug, ideaId);
      setPreviewIdea(ideaId);
      setPreviewScript(data);
    } catch {
      // Fallback: search local content data
      const draft = content?.drafts?.find((d: any) => d.idea_id === ideaId || d.id === ideaId);
      const pub = content?.published?.find((d: any) => d.idea_id === ideaId || d.id === ideaId);
      const found = draft || pub;
      if (found) {
        setPreviewIdea(ideaId);
        setPreviewScript(found);
      }
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !being) {
    return (
      <Box>
        <Button startIcon={<ArrowBackIcon />} onClick={() => router.push('/')} sx={{ mb: 2 }}>
          Back
        </Button>
        <Alert severity="error">{error || 'Being not found'}</Alert>
      </Box>
    );
  }

  const { being: info, persona, platforms, content_strategy } = being;
  const enabledPlatforms = Object.entries(platforms)
    .filter(([_, config]) => config.enabled)
    .map(([key, config]) => ({ key, label: platformLabels[key] || key, ...config }));

  const ideaCount = ideas.length;
  const backlogCount = ideas.filter((i) => i.status === 'backlog').length;
  const draftedCount = ideas.filter((i) => i.status === 'drafted').length;
  const generatedCount = ideas.filter((i) => i.status === 'generated').length;
  const publishedCount = ideas.filter((i) => i.status === 'published').length;

  return (
    <Box>
      {/* Header */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2.5 }}>
            <Box sx={{ position: 'relative' }}>
              <Avatar
                src={faceUrl || undefined}
                sx={{
                  width: 72,
                  height: 72,
                  bgcolor: 'primary.main',
                  fontSize: '1.75rem',
                  fontWeight: 700,
                }}
                imgProps={{ onError: () => setFaceUrl(null) }}
              >
                {info.name.split(' ').map((w: string) => w[0]).join('').toUpperCase().slice(0, 2)}
              </Avatar>
              <Tooltip title={faceUrl ? 'Regenerate face' : 'Generate face'}>
                <IconButton
                  size="small"
                  onClick={handleGenerateFace}
                  disabled={generatingFace}
                  sx={{
                    position: 'absolute',
                    bottom: -4,
                    right: -4,
                    bgcolor: 'background.paper',
                    border: '2px solid',
                    borderColor: 'divider',
                    width: 28,
                    height: 28,
                    '&:hover': { bgcolor: 'action.hover' },
                  }}
                >
                  {generatingFace ? <CircularProgress size={14} /> : <FaceIcon sx={{ fontSize: 16 }} />}
                </IconButton>
              </Tooltip>
            </Box>
            <Box>
              <Typography variant="h3" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
                {info.name}
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ mt: 0.25 }}>
                {info.tagline}
              </Typography>
              <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                <Chip label={persona.archetype} size="small" color="primary" variant="outlined" />
                {enabledPlatforms.map((p) => (
                  <Chip
                    key={p.key}
                    label={p.handle || p.label}
                    size="small"
                    sx={{ bgcolor: 'rgba(0, 137, 123, 0.08)', color: 'secondary.dark', fontSize: '0.75rem' }}
                  />
                ))}
              </Stack>
            </Box>
          </Box>
          <Button startIcon={<ArrowBackIcon />} onClick={() => router.push('/')} sx={{ color: 'text.secondary' }}>
            Dashboard
          </Button>
        </Box>

        {/* Quick Stats Bar */}
        <Grid container spacing={2} sx={{ mt: 2.5 }}>
          <Grid size={{ xs: 6, sm: 'grow' }}>
            <Box sx={{ textAlign: 'center', p: 1.5, borderRadius: 2, bgcolor: 'rgba(230, 81, 0, 0.04)' }}>
              <Typography variant="h4" sx={{ fontWeight: 700, color: '#e65100' }}>{backlogCount}</Typography>
              <Typography variant="caption" color="text.secondary">Backlog</Typography>
            </Box>
          </Grid>
          <Grid size={{ xs: 6, sm: 'grow' }}>
            <Box sx={{ textAlign: 'center', p: 1.5, borderRadius: 2, bgcolor: 'rgba(1, 87, 155, 0.04)' }}>
              <Typography variant="h4" sx={{ fontWeight: 700, color: '#01579b' }}>{draftedCount}</Typography>
              <Typography variant="caption" color="text.secondary">Drafted</Typography>
            </Box>
          </Grid>
          <Grid size={{ xs: 6, sm: 'grow' }}>
            <Box sx={{ textAlign: 'center', p: 1.5, borderRadius: 2, bgcolor: 'rgba(156, 39, 176, 0.04)' }}>
              <Typography variant="h4" sx={{ fontWeight: 700, color: '#9c27b0' }}>{generatedCount}</Typography>
              <Typography variant="caption" color="text.secondary">Generated</Typography>
            </Box>
          </Grid>
          <Grid size={{ xs: 6, sm: 'grow' }}>
            <Box sx={{ textAlign: 'center', p: 1.5, borderRadius: 2, bgcolor: 'rgba(46, 125, 50, 0.04)' }}>
              <Typography variant="h4" sx={{ fontWeight: 700, color: 'success.main' }}>{publishedCount}</Typography>
              <Typography variant="caption" color="text.secondary">Published</Typography>
            </Box>
          </Grid>
          <Grid size={{ xs: 6, sm: 'grow' }}>
            <Box sx={{ textAlign: 'center', p: 1.5, borderRadius: 2, bgcolor: 'rgba(26, 35, 126, 0.04)' }}>
              <Typography variant="h4" sx={{ fontWeight: 700, color: 'primary.main' }}>{ideaCount}</Typography>
              <Typography variant="caption" color="text.secondary">Total</Typography>
            </Box>
          </Grid>
        </Grid>
      </Paper>

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={tab}
          onChange={(_, v) => setTab(v)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{
            px: 2,
            '& .MuiTab-root': { minHeight: 56, fontWeight: 600, textTransform: 'none', fontSize: '0.95rem' },
          }}
        >
          <Tab icon={<LightbulbIcon />} iconPosition="start" label="Ideas" />
          <Tab icon={<ArticleIcon />} iconPosition="start" label="Content" />
          <Tab icon={<HistoryIcon />} iconPosition="start" label="Activity" />
          <Tab icon={<PersonIcon />} iconPosition="start" label="Identity" />
          <Tab icon={<AddIcon />} iconPosition="start" label="Add Idea" />
          <Tab icon={<ChatIcon />} iconPosition="start" label="Chat" />
        </Tabs>
      </Paper>

      {/* ═══ IDEAS TAB ═══ */}
      <TabPanel value={tab} index={0}>
        {produceSuccess && (
          <Alert severity="success" sx={{ mb: 2 }} onClose={() => setProduceSuccess(null)}>
            {produceSuccess}
          </Alert>
        )}
        {produceError && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setProduceError(null)}>
            {produceError}
          </Alert>
        )}

        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h5" sx={{ fontWeight: 600 }}>
            Content Ideas ({ideaCount})
          </Typography>
          <Button
            variant="contained"
            startIcon={isGenerating ? <CircularProgress size={18} color="inherit" /> : <AutoAwesomeIcon />}
            onClick={handleGenerate}
            disabled={isGenerating}
          >
            {isGenerating ? 'Generating with Opus...' : 'Generate Ideas'}
          </Button>
        </Box>

        {generateError && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setGenerateError(null)}>
            {generateError}
          </Alert>
        )}

        {isGenerating && <LinearProgress sx={{ mb: 2, borderRadius: 1 }} />}

        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow sx={{ '& th': { fontWeight: 700, bgcolor: 'rgba(0,0,0,0.02)' } }}>
                <TableCell>ID</TableCell>
                <TableCell>Title</TableCell>
                <TableCell>Concept</TableCell>
                <TableCell>Template</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Tags</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {ideas.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} sx={{ textAlign: 'center', py: 6, color: 'text.secondary' }}>
                    No ideas yet. Click "Generate Ideas" to brainstorm with AI.
                  </TableCell>
                </TableRow>
              ) : (
                ideas.map((idea) => (
                  <TableRow
                    key={idea.id}
                    sx={{ '&:hover': { bgcolor: 'rgba(0,0,0,0.02)' }, opacity: actionId === idea.id ? 0.5 : 1 }}
                  >
                    <TableCell>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>
                        {idea.id}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight={600}>{idea.title}</Typography>
                      {idea.content_types?.length > 0 && (
                        <Stack direction="row" spacing={0.5} sx={{ mt: 0.5, flexWrap: 'wrap', gap: 0.25 }}>
                          {idea.content_types.map((ct) => (
                            <Chip key={ct} label={ct} size="small" variant="outlined"
                              sx={{ fontSize: '0.65rem', height: 20 }} />
                          ))}
                        </Stack>
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{
                          maxWidth: 250,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {idea.concept}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {idea.template ? (
                        <Chip
                          label={idea.template.replace(/_/g, ' ')}
                          size="small"
                          color={templateColors[idea.template] || 'default'}
                          sx={{ textTransform: 'capitalize' }}
                        />
                      ) : (
                        <Typography variant="caption" color="text.disabled">-</Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={idea.status}
                        size="small"
                        color={statusColors[idea.status] || 'default'}
                        variant={idea.status === 'backlog' ? 'outlined' : 'filled'}
                        sx={{ textTransform: 'capitalize' }}
                      />
                    </TableCell>
                    <TableCell>
                      <Stack direction="row" spacing={0.5} sx={{ flexWrap: 'wrap', gap: 0.5 }}>
                        {idea.tags?.map((tag) => (
                          <Chip key={tag} label={tag} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
                        ))}
                      </Stack>
                    </TableCell>
                    <TableCell align="right">
                      <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                        {idea.status === 'backlog' && (
                          <Tooltip title="Draft - generate script">
                            <IconButton
                              size="small"
                              color="primary"
                              onClick={() => handleDraft(idea.id)}
                              disabled={actionId !== null}
                            >
                              {actionId === idea.id && actionType === 'draft' ? <CircularProgress size={18} /> : <EditNoteIcon />}
                            </IconButton>
                          </Tooltip>
                        )}
                        {idea.status === 'drafted' && (
                          <>
                            <Tooltip title="View script">
                              <IconButton
                                size="small"
                                color="info"
                                onClick={() => handlePreviewScript(idea.id)}
                              >
                                <VisibilityIcon />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="Generate - create media files">
                              <IconButton
                                size="small"
                                color="secondary"
                                onClick={() => handleGenerateMedia(idea.id)}
                                disabled={actionId !== null}
                              >
                                {actionId === idea.id && actionType === 'generate' ? <CircularProgress size={18} /> : <BuildIcon />}
                              </IconButton>
                            </Tooltip>
                          </>
                        )}
                        {idea.status === 'generated' && (
                          <>
                            <Tooltip title="View generated files">
                              <IconButton
                                size="small"
                                color="info"
                                onClick={() => handlePreviewScript(idea.id)}
                              >
                                <VisibilityIcon />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="Re-generate media">
                              <IconButton
                                size="small"
                                color="warning"
                                onClick={() => handleRegenerate(idea.id)}
                                disabled={actionId !== null}
                              >
                                {actionId === idea.id && actionType === 'regenerate' ? <CircularProgress size={18} /> : <RefreshIcon />}
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="Publish to platforms">
                              <IconButton
                                size="small"
                                color="success"
                                onClick={() => handlePublish(idea.id)}
                                disabled={actionId !== null}
                              >
                                {actionId === idea.id && actionType === 'publish' ? <CircularProgress size={18} /> : <PublishIcon />}
                              </IconButton>
                            </Tooltip>
                          </>
                        )}
                        {idea.status === 'published' && (
                          <Tooltip title="View published content">
                            <IconButton
                              size="small"
                              color="success"
                              onClick={() => handlePreviewScript(idea.id)}
                            >
                              <CheckCircleIcon />
                            </IconButton>
                          </Tooltip>
                        )}
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </TabPanel>

      {/* ═══ CONTENT TAB ═══ */}
      <TabPanel value={tab} index={1}>
        <Grid container spacing={3}>
          {/* Drafts */}
          <Grid size={12}>
            <Typography variant="h5" sx={{ fontWeight: 600, mb: 2 }}>
              Drafts ({content?.drafts?.length || 0})
            </Typography>
            {!content?.drafts?.length ? (
              <Paper sx={{ p: 4, textAlign: 'center' }}>
                <ArticleIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
                <Typography color="text.secondary">No drafts yet. Produce content from an idea.</Typography>
              </Paper>
            ) : (
              <Stack spacing={2}>
                {content?.drafts?.map((draft: any) => (
                  <Card key={draft.id || draft.idea_id}>
                    <CardContent sx={{ p: 3 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <Box sx={{ flex: 1 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            {draft.template && (
                              <Chip
                                label={draft.template.replace(/_/g, ' ')}
                                size="small"
                                color={templateColors[draft.template] || 'default'}
                                sx={{ textTransform: 'capitalize' }}
                              />
                            )}
                            <Chip
                              label={draft.status || 'drafted'}
                              size="small"
                              variant="outlined"
                              color={statusColors[draft.status] || 'info'}
                            />
                          </Box>
                          <Typography variant="h6" sx={{ fontWeight: 600 }}>
                            {draft.title || 'Untitled'}
                          </Typography>
                          {draft.hook && (
                            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, fontStyle: 'italic' }}>
                              Hook: "{draft.hook}"
                            </Typography>
                          )}
                          {draft.concept && (
                            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                              {draft.concept}
                            </Typography>
                          )}
                          <Stack direction="row" spacing={2} sx={{ mt: 1.5 }}>
                            {draft.duration_estimate > 0 && (
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                <AccessTimeIcon sx={{ fontSize: 14, color: 'text.disabled' }} />
                                <Typography variant="caption" color="text.disabled">
                                  {draft.duration_estimate}s
                                </Typography>
                              </Box>
                            )}
                            {draft.created_at && (
                              <Typography variant="caption" color="text.disabled">
                                {formatTimestamp(draft.created_at)}
                              </Typography>
                            )}
                          </Stack>
                          {/* Generated files - inline media */}
                          {draft.media_files && draft.media_files.length > 0 && (
                            <Box sx={{ mt: 2, p: 1.5, bgcolor: 'rgba(0,0,0,0.02)', borderRadius: 1 }}>
                              <Typography variant="overline" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                                Generated Files
                              </Typography>
                              <Stack spacing={1.5}>
                                {draft.media_files.map((file: any) => {
                                  const url = getFileUrl(slug, draft.id || draft.idea_id, file.name);
                                  if (['png', 'jpg', 'jpeg'].includes(file.type)) {
                                    return (
                                      <Box key={file.name}>
                                        <img
                                          src={url}
                                          alt={file.name}
                                          style={{ maxWidth: '100%', maxHeight: 300, borderRadius: 8 }}
                                        />
                                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                                          {file.name}
                                        </Typography>
                                      </Box>
                                    );
                                  }
                                  if (file.type === 'mp4') {
                                    return (
                                      <Box key={file.name}>
                                        <video controls style={{ maxWidth: '100%', maxHeight: 300, borderRadius: 8 }}>
                                          <source src={url} type="video/mp4" />
                                        </video>
                                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                                          {file.name}
                                        </Typography>
                                      </Box>
                                    );
                                  }
                                  if (['mp3', 'wav'].includes(file.type)) {
                                    return (
                                      <Box key={file.name} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                        <AudioFileIcon color="info" />
                                        <audio controls style={{ flex: 1 }}>
                                          <source src={url} type={file.type === 'mp3' ? 'audio/mpeg' : 'audio/wav'} />
                                        </audio>
                                        <Typography variant="caption" color="text.secondary">{file.name}</Typography>
                                      </Box>
                                    );
                                  }
                                  if (file.type === 'txt') {
                                    return (
                                      <Box key={file.name}>
                                        <TextFileViewer
                                          url={url}
                                          filename={file.name}
                                        />
                                      </Box>
                                    );
                                  }
                                  return (
                                    <Chip
                                      key={file.name}
                                      label={file.name}
                                      size="small"
                                      icon={<ArticleIcon />}
                                      variant="outlined"
                                      sx={{ fontSize: '0.75rem' }}
                                    />
                                  );
                                })}
                              </Stack>
                            </Box>
                          )}
                        </Box>
                        {draft.tags && draft.tags.length > 0 && (
                          <Stack direction="row" spacing={0.5} sx={{ flexWrap: 'wrap', gap: 0.5, ml: 2 }}>
                            {draft.tags.map((tag: string) => (
                              <Chip key={tag} label={tag} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
                            ))}
                          </Stack>
                        )}
                      </Box>
                    </CardContent>
                  </Card>
                ))}
              </Stack>
            )}
          </Grid>

          {/* Published */}
          <Grid size={12}>
            <Typography variant="h5" sx={{ fontWeight: 600, mb: 2, mt: 2 }}>
              Published ({publishedCount})
            </Typography>
            {publishedCount === 0 ? (
              <Paper sx={{ p: 4, textAlign: 'center' }}>
                <YouTubeIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
                <Typography color="text.secondary">No published content yet.</Typography>
              </Paper>
            ) : (
              <Stack spacing={2}>
                {content?.published?.map((item: any) => (
                  <Card key={item.id}>
                    <CardContent>
                      <Typography variant="h6" fontWeight={600}>{item.title}</Typography>
                    </CardContent>
                  </Card>
                ))}
              </Stack>
            )}
          </Grid>
        </Grid>
      </TabPanel>

      {/* ═══ ACTIVITY TAB ═══ */}
      <TabPanel value={tab} index={2}>
        <Typography variant="h5" sx={{ fontWeight: 600, mb: 2 }}>
          Activity Log ({actions.length} actions)
        </Typography>
        <ActivityLog actions={actions} />
      </TabPanel>

      {/* ═══ IDENTITY TAB ═══ */}
      <TabPanel value={tab} index={3}>
        <Grid container spacing={3}>
          <Grid size={{ xs: 12, md: 6 }}>
            <Paper sx={{ p: 3, height: '100%' }}>
              <Typography variant="h5" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                <PersonIcon color="primary" /> Persona
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Stack spacing={2}>
                {persona.archetype && (
                  <Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                      <CategoryIcon sx={{ fontSize: 18, color: 'text.secondary' }} />
                      <Typography variant="overline" color="text.secondary">Archetype</Typography>
                    </Box>
                    <Chip label={persona.archetype} color="primary" variant="outlined" />
                  </Box>
                )}
                {persona.tone && (
                  <Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                      <MoodIcon sx={{ fontSize: 18, color: 'text.secondary' }} />
                      <Typography variant="overline" color="text.secondary">Tone</Typography>
                    </Box>
                    <Typography variant="body1">{persona.tone}</Typography>
                  </Box>
                )}
                {persona.perspective && (
                  <Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                      <VisibilityIcon sx={{ fontSize: 18, color: 'text.secondary' }} />
                      <Typography variant="overline" color="text.secondary">Perspective</Typography>
                    </Box>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-line' }}>{persona.perspective}</Typography>
                  </Box>
                )}
              </Stack>
            </Paper>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }}>
            <Paper sx={{ p: 3, height: '100%' }}>
              <Typography variant="h5" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                <RecordVoiceOverIcon color="primary" /> Voice & Boundaries
              </Typography>
              <Divider sx={{ mb: 2 }} />
              {persona.voice_traits.length > 0 && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="overline" color="text.secondary" sx={{ mb: 1, display: 'block' }}>Voice Traits</Typography>
                  <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
                    {persona.voice_traits.map((trait, i) => (
                      <Chip key={i} label={trait} size="small" icon={<RecordVoiceOverIcon />}
                        sx={{ bgcolor: 'rgba(26, 35, 126, 0.06)', color: 'primary.dark' }} />
                    ))}
                  </Stack>
                </Box>
              )}
              {persona.boundaries.length > 0 && (
                <Box>
                  <Typography variant="overline" color="text.secondary" sx={{ mb: 1, display: 'block' }}>Boundaries</Typography>
                  {persona.boundaries.map((b, i) => (
                    <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 0.25 }}>
                      <BlockIcon sx={{ fontSize: 16, color: 'error.main' }} />
                      <Typography variant="body2">{b}</Typography>
                    </Box>
                  ))}
                </Box>
              )}
            </Paper>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h5" sx={{ mb: 2 }}>Platforms</Typography>
              <Divider sx={{ mb: 2 }} />
              <Grid container spacing={2}>
                {Object.entries(platforms).map(([key, config]) => (
                  <Grid size={{ xs: 12, sm: 6 }} key={key}>
                    <Box
                      sx={{
                        p: 2, borderRadius: 2, border: '1px solid',
                        borderColor: config.enabled ? 'success.light' : 'divider',
                        bgcolor: config.enabled ? 'rgba(46, 125, 50, 0.04)' : 'rgba(0, 0, 0, 0.02)',
                      }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <Typography variant="body1" fontWeight={600}>{platformLabels[key] || key}</Typography>
                        {config.enabled ? <CheckCircleIcon sx={{ color: 'success.main', fontSize: 20 }} />
                          : <CancelIcon sx={{ color: 'text.disabled', fontSize: 20 }} />}
                      </Box>
                      <Typography variant="body2" color={config.handle ? 'text.secondary' : 'text.disabled'} sx={{ mt: 0.5 }}>
                        {config.handle ? `@${config.handle}` : 'Not configured'}
                      </Typography>
                    </Box>
                  </Grid>
                ))}
              </Grid>
            </Paper>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h5" sx={{ mb: 2 }}>Content Strategy</Typography>
              <Divider sx={{ mb: 2 }} />
              <Stack spacing={1.5}>
                {content_strategy?.posting_frequency?.shorts && (
                  <Box>
                    <Typography variant="overline" color="text.secondary">Shorts</Typography>
                    <Typography variant="body2">{content_strategy.posting_frequency.shorts}</Typography>
                  </Box>
                )}
                {content_strategy?.posting_frequency?.images && (
                  <Box>
                    <Typography variant="overline" color="text.secondary">Images</Typography>
                    <Typography variant="body2">{content_strategy.posting_frequency.images}</Typography>
                  </Box>
                )}
                {content_strategy?.posting_frequency?.tweets && (
                  <Box>
                    <Typography variant="overline" color="text.secondary">Tweets</Typography>
                    <Typography variant="body2">{content_strategy.posting_frequency.tweets}</Typography>
                  </Box>
                )}
                {content_strategy?.series?.length > 0 && (
                  <Box>
                    <Typography variant="overline" color="text.secondary" sx={{ display: 'block', mb: 1 }}>Series</Typography>
                    {content_strategy.series.map((s, i) => (
                      <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 0.5 }}>
                        <Chip label={s.format.replace(/_/g, ' ')} size="small" variant="outlined" sx={{ textTransform: 'capitalize' }} />
                        <Typography variant="body2" fontWeight={500}>{s.name}</Typography>
                        <Typography variant="caption" color="text.disabled">({s.frequency})</Typography>
                      </Box>
                    ))}
                  </Box>
                )}
              </Stack>
            </Paper>
          </Grid>
        </Grid>
      </TabPanel>

      {/* ═══ ADD IDEA TAB ═══ */}
      <TabPanel value={tab} index={4}>
        <AddIdeaForm slug={slug} beingName={info.name} onIdeaAdded={reloadData} />
      </TabPanel>

      {/* ═══ CHAT TAB ═══ */}
      <TabPanel value={tab} index={5}>
        <ChatWindow slug={slug} beingName={info.name} />
      </TabPanel>

      {/* Script Preview Dialog */}
      <Dialog open={!!previewIdea} onClose={() => setPreviewIdea(null)} maxWidth="md" fullWidth>
        <DialogTitle>
          {previewScript?.status === 'generated' ? 'Generated' :
           previewScript?.status === 'published' ? 'Published' : 'Draft'}
          : {previewScript?.title || previewIdea}
        </DialogTitle>
        <DialogContent dividers>
          {previewScript?.hook && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="overline" color="text.secondary">Hook</Typography>
              <Typography variant="body1" sx={{ fontStyle: 'italic' }}>"{previewScript.hook}"</Typography>
            </Box>
          )}
          {previewScript?.concept && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="overline" color="text.secondary">Concept</Typography>
              <Typography variant="body2">{previewScript.concept}</Typography>
            </Box>
          )}
          {previewScript?.duration_estimate > 0 && (
            <Chip label={`${previewScript.duration_estimate}s estimated`} size="small" sx={{ mb: 2 }} />
          )}
          {/* Generated files - inline media */}
          {previewScript?.files && previewScript.files.length > 0 && previewIdea && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="overline" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                Generated Files ({previewScript.files.length})
              </Typography>
              <Stack spacing={2}>
                {/* Carousel slides - horizontal scrollable gallery */}
                {(() => {
                  const carouselFiles = previewScript.files.filter((f: any) => f.type === 'carousel');
                  if (carouselFiles.length > 0) {
                    return (
                      <Box key="carousel" sx={{ mb: 2 }}>
                        <Typography variant="caption" color="text.secondary" fontWeight={600} sx={{ display: 'block', mb: 1 }}>
                          Carousel ({carouselFiles.length} slides)
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 1.5, overflowX: 'auto', pb: 1 }}>
                          {carouselFiles.map((file: any, idx: number) => {
                            const cUrl = getFileUrl(slug, previewIdea!, file.file);
                            return (
                              <Box key={idx} sx={{ flexShrink: 0 }}>
                                <img src={cUrl} alt={file.file} style={{ height: 250, borderRadius: 8 }} />
                                <Typography variant="caption" color="text.disabled" sx={{ display: 'block', mt: 0.5 }}>
                                  {file.file}
                                </Typography>
                              </Box>
                            );
                          })}
                        </Box>
                      </Box>
                    );
                  }
                  return null;
                })()}
                {previewScript.files.filter((f: any) => f.type !== 'carousel').map((file: any, idx: number) => {
                  const url = getFileUrl(slug, previewIdea!, file.file);
                  if (file.type === 'story') {
                    return (
                      <Box key={idx} sx={{ position: 'relative', display: 'inline-block' }}>
                        <img src={url} alt={file.file} style={{ maxWidth: '100%', maxHeight: 500, borderRadius: 8 }} />
                        {previewScript.hook && (
                          <Box sx={{
                            position: 'absolute', bottom: 0, left: 0, right: 0,
                            background: 'linear-gradient(transparent, rgba(0,0,0,0.8))',
                            borderRadius: '0 0 8px 8px', p: 2, pt: 6,
                          }}>
                            <Typography variant="body1" sx={{ color: 'white', fontWeight: 600, textAlign: 'center' }}>
                              {previewScript.hook}
                            </Typography>
                          </Box>
                        )}
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                          {file.file} ({file.type})
                        </Typography>
                      </Box>
                    );
                  }
                  if (['image', 'post', 'selfie', 'thumbnail'].includes(file.type)) {
                    return (
                      <Box key={idx}>
                        <img src={url} alt={file.file} style={{ maxWidth: '100%', borderRadius: 8 }} />
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                          {file.file} ({file.type})
                        </Typography>
                      </Box>
                    );
                  }
                  if (file.type === 'video') {
                    return (
                      <Box key={idx}>
                        <video controls style={{ maxWidth: '100%', borderRadius: 8 }}>
                          <source src={url} type="video/mp4" />
                        </video>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                          {file.file} ({file.type})
                        </Typography>
                      </Box>
                    );
                  }
                  if (['audio', 'music'].includes(file.type)) {
                    return (
                      <Box key={idx} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <AudioFileIcon color="info" />
                        <audio controls style={{ flex: 1 }}>
                          <source src={url} type={file.file.endsWith('.wav') ? 'audio/wav' : 'audio/mpeg'} />
                        </audio>
                        <Typography variant="caption" color="text.secondary">{file.file}</Typography>
                      </Box>
                    );
                  }
                  if (['tweet', 'thread'].includes(file.type) || file.file.endsWith('.txt')) {
                    return (
                      <Box key={idx}>
                        <TextFileViewer url={url} filename={file.file} />
                      </Box>
                    );
                  }
                  return (
                    <Box key={idx} sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 1, bgcolor: 'rgba(0,0,0,0.03)', borderRadius: 1 }}>
                      <ArticleIcon color="action" />
                      <Typography variant="body2" fontWeight={600}>{file.file}</Typography>
                    </Box>
                  );
                })}
              </Stack>
            </Box>
          )}
          {/* Errors */}
          {previewScript?.errors && previewScript.errors.length > 0 && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="overline" color="error" sx={{ display: 'block', mb: 1 }}>
                Errors ({previewScript.errors.length})
              </Typography>
              {previewScript.errors.map((err: any, idx: number) => (
                <Alert key={idx} severity="error" sx={{ mb: 1 }}>
                  <strong>{err.content_type}:</strong> {err.error}
                </Alert>
              ))}
            </Box>
          )}
          {/* Media files from disk - inline rendering */}
          {previewScript?.media_files && previewScript.media_files.length > 0 && previewIdea && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="overline" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                Files on Disk
              </Typography>
              <Stack spacing={1.5}>
                {previewScript.media_files.map((file: any) => {
                  const url = getFileUrl(slug, previewIdea!, file.name);
                  if (['png', 'jpg', 'jpeg'].includes(file.type)) {
                    return (
                      <Box key={file.name}>
                        <img src={url} alt={file.name} style={{ maxWidth: '100%', borderRadius: 8 }} />
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                          {file.name} ({Math.round(file.size / 1024)}KB)
                        </Typography>
                      </Box>
                    );
                  }
                  if (file.type === 'mp4') {
                    return (
                      <Box key={file.name}>
                        <video controls style={{ maxWidth: '100%', borderRadius: 8 }}>
                          <source src={url} type="video/mp4" />
                        </video>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                          {file.name} ({Math.round(file.size / 1024)}KB)
                        </Typography>
                      </Box>
                    );
                  }
                  if (['mp3', 'wav'].includes(file.type)) {
                    return (
                      <Box key={file.name} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <AudioFileIcon color="info" />
                        <audio controls style={{ flex: 1 }}>
                          <source src={url} type={file.type === 'mp3' ? 'audio/mpeg' : 'audio/wav'} />
                        </audio>
                        <Typography variant="caption" color="text.secondary">
                          {file.name} ({Math.round(file.size / 1024)}KB)
                        </Typography>
                      </Box>
                    );
                  }
                  if (file.type === 'txt') {
                    return (
                      <Box key={file.name}>
                        <TextFileViewer url={url} filename={file.name} />
                      </Box>
                    );
                  }
                  return (
                    <Chip
                      key={file.name}
                      label={`${file.name} (${Math.round(file.size / 1024)}KB)`}
                      size="small"
                      variant="outlined"
                    />
                  );
                })}
              </Stack>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewIdea(null)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
