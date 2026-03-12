'use client';

import { useState } from 'react';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Divider from '@mui/material/Divider';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import AddIcon from '@mui/icons-material/Add';
import SendIcon from '@mui/icons-material/Send';
import { addIdea } from '@/lib/api';

const TEMPLATES = [
  { value: 'hot_take', label: 'Hot Take', description: 'Bold, provocative opinion' },
  { value: 'list_countdown', label: 'List / Countdown', description: 'Top N list or countdown format' },
  { value: 'talking_head', label: 'Talking Head', description: 'Direct-to-camera style video' },
  { value: 'photo_post', label: 'Photo Post', description: 'Image with caption' },
  { value: 'thread', label: 'Thread', description: 'Multi-post threaded content' },
  { value: 'story', label: 'Story', description: 'Short-form ephemeral content' },
  { value: 'reaction', label: 'Reaction', description: 'Response to trending content' },
  { value: 'tutorial', label: 'Tutorial', description: 'How-to or educational content' },
  { value: 'behind_the_scenes', label: 'Behind the Scenes', description: 'Personal/authentic peek' },
  { value: 'challenge', label: 'Challenge', description: 'Participatory challenge content' },
];

const CONTENT_TYPES = [
  'image', 'video', 'post', 'selfie', 'tweet', 'thread', 'story', 'audio', 'music', 'thumbnail',
];

interface AddIdeaFormProps {
  slug: string;
  beingName?: string;
  onIdeaAdded?: () => void;
}

export default function AddIdeaForm({ slug, beingName, onIdeaAdded }: AddIdeaFormProps) {
  const [title, setTitle] = useState('');
  const [concept, setConcept] = useState('');
  const [template, setTemplate] = useState('');
  const [contentTypes, setContentTypes] = useState<string[]>([]);
  const [tagsInput, setTagsInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const toggleContentType = (ct: string) => {
    setContentTypes((prev) =>
      prev.includes(ct) ? prev.filter((t) => t !== ct) : [...prev, ct]
    );
  };

  const handleSubmit = async () => {
    if (!title.trim()) {
      setError('Title is required.');
      return;
    }
    if (!concept.trim()) {
      setError('Concept is required.');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const tags = tagsInput
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);

      await addIdea(slug, {
        title: title.trim(),
        concept: concept.trim(),
        template: template || undefined,
        content_types: contentTypes.length > 0 ? contentTypes : undefined,
        tags: tags.length > 0 ? tags : undefined,
      });

      setSuccess('Idea added to backlog!');
      setTitle('');
      setConcept('');
      setTemplate('');
      setContentTypes([]);
      setTagsInput('');
      onIdeaAdded?.();
    } catch (err: any) {
      setError(err.message || 'Failed to add idea.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Paper sx={{ p: 4 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <AddIcon color="primary" />
        <Typography variant="h5">
          Add Idea
        </Typography>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Add a content idea to the backlog for {beingName || slug}. Draft, generate, and publish from the Ideas tab.
      </Typography>

      <Divider sx={{ mb: 3 }} />

      {success && (
        <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        <TextField
          fullWidth
          label="Title"
          placeholder="Give your idea a title..."
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />

        <TextField
          fullWidth
          multiline
          rows={4}
          label="Concept"
          placeholder="Describe the concept, idea, or angle..."
          value={concept}
          onChange={(e) => setConcept(e.target.value)}
          required
        />

        <FormControl fullWidth>
          <InputLabel>Template</InputLabel>
          <Select
            value={template}
            onChange={(e) => setTemplate(e.target.value)}
            label="Template"
          >
            <MenuItem value="">
              <Typography variant="body2" color="text.secondary">None</Typography>
            </MenuItem>
            {TEMPLATES.map((t) => (
              <MenuItem key={t.value} value={t.value}>
                <Box>
                  <Typography variant="body2" fontWeight={600}>
                    {t.label}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {t.description}
                  </Typography>
                </Box>
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Content Types
          </Typography>
          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
            {CONTENT_TYPES.map((ct) => (
              <Chip
                key={ct}
                label={ct}
                size="small"
                variant={contentTypes.includes(ct) ? 'filled' : 'outlined'}
                color={contentTypes.includes(ct) ? 'primary' : 'default'}
                onClick={() => toggleContentType(ct)}
                sx={{ textTransform: 'capitalize', cursor: 'pointer' }}
              />
            ))}
          </Stack>
        </Box>

        <TextField
          fullWidth
          label="Tags"
          placeholder="comma-separated tags, e.g. trending, tech, humor"
          value={tagsInput}
          onChange={(e) => setTagsInput(e.target.value)}
        />

        <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
          <Button
            variant="outlined"
            onClick={() => {
              setTitle('');
              setConcept('');
              setTemplate('');
              setContentTypes([]);
              setTagsInput('');
              setError(null);
              setSuccess(null);
            }}
            disabled={loading}
          >
            Clear
          </Button>
          <Button
            variant="contained"
            size="large"
            endIcon={loading ? <CircularProgress size={18} color="inherit" /> : <SendIcon />}
            onClick={handleSubmit}
            disabled={loading || !title.trim() || !concept.trim()}
          >
            {loading ? 'Adding...' : 'Add Idea'}
          </Button>
        </Box>
      </Box>
    </Paper>
  );
}
