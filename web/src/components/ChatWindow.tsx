'use client';

import { useState, useEffect, useRef, KeyboardEvent } from 'react';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import IconButton from '@mui/material/IconButton';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import SendIcon from '@mui/icons-material/Send';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import { createChatConnection, sendChatMessage, ChatMessage } from '@/lib/ws';

interface DisplayMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

interface ChatWindowProps {
  slug: string;
  beingName?: string;
}

export default function ChatWindow({ slug, beingName }: ChatWindowProps) {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    setIsConnecting(true);

    const ws = createChatConnection(
      slug,
      (msg: ChatMessage) => {
        const displayMsg: DisplayMessage = {
          id: Date.now().toString() + Math.random().toString(36).slice(2),
          role: msg.type === 'system' ? 'system' : msg.role || 'assistant',
          content: msg.message,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, displayMsg]);
        setIsSending(false);
      },
      () => {
        setIsConnected(true);
        setIsConnecting(false);
      },
      () => {
        setIsConnected(false);
        setIsConnecting(false);
      },
      () => {
        setIsConnected(false);
        setIsConnecting(false);
      }
    );

    wsRef.current = ws;

    return () => {
      ws.close();
    };
  }, [slug]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || !wsRef.current || !isConnected) return;

    const userMsg: DisplayMessage = {
      id: Date.now().toString() + Math.random().toString(36).slice(2),
      role: 'user',
      content: trimmed,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsSending(true);
    sendChatMessage(wsRef.current, trimmed);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Paper
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 160px)',
        minHeight: 500,
        overflow: 'hidden',
      }}
    >
      {/* Connection Status */}
      <Box
        sx={{
          px: 2.5,
          py: 1.5,
          borderBottom: '1px solid',
          borderColor: 'divider',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <Typography variant="h6">
          Chat with {beingName || slug}
        </Typography>
        <Chip
          icon={
            isConnecting ? (
              <CircularProgress size={12} />
            ) : (
              <FiberManualRecordIcon
                sx={{ fontSize: 10, color: isConnected ? 'success.main' : 'error.main' }}
              />
            )
          }
          label={isConnecting ? 'Connecting...' : isConnected ? 'Connected' : 'Disconnected'}
          size="small"
          variant="outlined"
          sx={{
            borderColor: isConnecting
              ? 'warning.light'
              : isConnected
                ? 'success.light'
                : 'error.light',
          }}
        />
      </Box>

      {/* Messages */}
      <Box
        sx={{
          flexGrow: 1,
          overflow: 'auto',
          px: 2.5,
          py: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: 1.5,
          bgcolor: 'background.default',
        }}
      >
        {messages.length === 0 && !isConnecting && (
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
            }}
          >
            <Typography variant="body1" color="text.secondary">
              Send a message to start chatting with {beingName || slug}.
            </Typography>
          </Box>
        )}

        {messages.map((msg) => (
          <Box
            key={msg.id}
            sx={{
              display: 'flex',
              justifyContent:
                msg.role === 'user'
                  ? 'flex-end'
                  : msg.role === 'system'
                    ? 'center'
                    : 'flex-start',
            }}
          >
            {msg.role === 'system' ? (
              <Chip
                label={msg.content}
                size="small"
                sx={{
                  bgcolor: 'rgba(0, 0, 0, 0.06)',
                  color: 'text.secondary',
                  fontSize: '0.75rem',
                  height: 'auto',
                  py: 0.5,
                  '& .MuiChip-label': { whiteSpace: 'normal' },
                }}
              />
            ) : (
              <Box
                sx={{
                  maxWidth: '75%',
                  px: 2,
                  py: 1.5,
                  borderRadius: 2.5,
                  bgcolor:
                    msg.role === 'user' ? 'primary.main' : 'background.paper',
                  color: msg.role === 'user' ? 'white' : 'text.primary',
                  boxShadow:
                    msg.role === 'user'
                      ? '0 2px 8px rgba(26, 35, 126, 0.3)'
                      : '0 1px 4px rgba(0, 0, 0, 0.08)',
                  borderBottomRightRadius: msg.role === 'user' ? 4 : undefined,
                  borderBottomLeftRadius: msg.role === 'assistant' ? 4 : undefined,
                }}
              >
                <Typography
                  variant="body2"
                  sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}
                >
                  {msg.content}
                </Typography>
                <Typography
                  variant="caption"
                  sx={{
                    display: 'block',
                    mt: 0.5,
                    opacity: 0.7,
                    fontSize: '0.65rem',
                    textAlign: msg.role === 'user' ? 'right' : 'left',
                  }}
                >
                  {msg.timestamp.toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </Typography>
              </Box>
            )}
          </Box>
        ))}

        {isSending && (
          <Box sx={{ display: 'flex', justifyContent: 'flex-start' }}>
            <Box
              sx={{
                px: 2.5,
                py: 1.5,
                borderRadius: 2.5,
                bgcolor: 'background.paper',
                boxShadow: '0 1px 4px rgba(0, 0, 0, 0.08)',
                borderBottomLeftRadius: 4,
              }}
            >
              <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
                <CircularProgress size={8} sx={{ color: 'text.secondary' }} />
                <CircularProgress size={8} sx={{ color: 'text.secondary', animationDelay: '0.2s' }} />
                <CircularProgress size={8} sx={{ color: 'text.secondary', animationDelay: '0.4s' }} />
              </Box>
            </Box>
          </Box>
        )}

        <div ref={messagesEndRef} />
      </Box>

      {/* Input */}
      <Box
        sx={{
          p: 2,
          borderTop: '1px solid',
          borderColor: 'divider',
          display: 'flex',
          gap: 1,
          alignItems: 'flex-end',
          bgcolor: 'background.paper',
        }}
      >
        <TextField
          inputRef={inputRef}
          fullWidth
          multiline
          maxRows={4}
          placeholder={isConnected ? 'Type a message...' : 'Waiting for connection...'}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={!isConnected}
          size="small"
          sx={{
            '& .MuiOutlinedInput-root': {
              bgcolor: 'background.default',
            },
          }}
        />
        <IconButton
          onClick={handleSend}
          disabled={!isConnected || !input.trim() || isSending}
          color="primary"
          sx={{
            bgcolor: 'primary.main',
            color: 'white',
            width: 40,
            height: 40,
            '&:hover': {
              bgcolor: 'primary.dark',
            },
            '&.Mui-disabled': {
              bgcolor: 'action.disabledBackground',
              color: 'action.disabled',
            },
          }}
        >
          <SendIcon sx={{ fontSize: 18 }} />
        </IconButton>
      </Box>
    </Paper>
  );
}
