'use client';

import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1a237e',
      light: '#534bae',
      dark: '#000051',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#00897b',
      light: '#4ebaaa',
      dark: '#005b4f',
      contrastText: '#ffffff',
    },
    background: {
      default: '#f5f5f7',
      paper: '#ffffff',
    },
    text: {
      primary: '#1a1a2e',
      secondary: '#555770',
    },
    divider: 'rgba(0, 0, 0, 0.08)',
    error: {
      main: '#d32f2f',
    },
    warning: {
      main: '#f57c00',
    },
    success: {
      main: '#2e7d32',
    },
    info: {
      main: '#1565c0',
    },
  },
  typography: {
    fontFamily: [
      'Inter',
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
    h1: {
      fontSize: '2.25rem',
      fontWeight: 700,
      letterSpacing: '-0.02em',
      lineHeight: 1.2,
    },
    h2: {
      fontSize: '1.875rem',
      fontWeight: 700,
      letterSpacing: '-0.01em',
      lineHeight: 1.3,
    },
    h3: {
      fontSize: '1.5rem',
      fontWeight: 600,
      letterSpacing: '-0.01em',
      lineHeight: 1.4,
    },
    h4: {
      fontSize: '1.25rem',
      fontWeight: 600,
      lineHeight: 1.4,
    },
    h5: {
      fontSize: '1.1rem',
      fontWeight: 600,
      lineHeight: 1.5,
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 600,
      lineHeight: 1.5,
    },
    body1: {
      fontSize: '0.95rem',
      lineHeight: 1.6,
    },
    body2: {
      fontSize: '0.875rem',
      lineHeight: 1.6,
    },
    button: {
      textTransform: 'none',
      fontWeight: 600,
      letterSpacing: '0.01em',
    },
    caption: {
      fontSize: '0.75rem',
      color: '#555770',
    },
    overline: {
      fontSize: '0.7rem',
      fontWeight: 700,
      letterSpacing: '0.08em',
    },
  },
  shape: {
    borderRadius: 12,
  },
  shadows: [
    'none',
    '0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06)',
    '0 2px 4px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06)',
    '0 4px 6px rgba(0,0,0,0.04), 0 2px 4px rgba(0,0,0,0.06)',
    '0 6px 12px rgba(0,0,0,0.05), 0 3px 6px rgba(0,0,0,0.06)',
    '0 8px 16px rgba(0,0,0,0.06), 0 4px 8px rgba(0,0,0,0.06)',
    '0 10px 20px rgba(0,0,0,0.06), 0 5px 10px rgba(0,0,0,0.05)',
    '0 12px 24px rgba(0,0,0,0.07), 0 6px 12px rgba(0,0,0,0.05)',
    '0 14px 28px rgba(0,0,0,0.08), 0 7px 14px rgba(0,0,0,0.05)',
    '0 16px 32px rgba(0,0,0,0.08), 0 8px 16px rgba(0,0,0,0.05)',
    '0 18px 36px rgba(0,0,0,0.09), 0 9px 18px rgba(0,0,0,0.05)',
    '0 20px 40px rgba(0,0,0,0.09), 0 10px 20px rgba(0,0,0,0.05)',
    '0 22px 44px rgba(0,0,0,0.10), 0 11px 22px rgba(0,0,0,0.05)',
    '0 24px 48px rgba(0,0,0,0.10), 0 12px 24px rgba(0,0,0,0.05)',
    '0 26px 52px rgba(0,0,0,0.10), 0 13px 26px rgba(0,0,0,0.05)',
    '0 28px 56px rgba(0,0,0,0.11), 0 14px 28px rgba(0,0,0,0.05)',
    '0 30px 60px rgba(0,0,0,0.11), 0 15px 30px rgba(0,0,0,0.05)',
    '0 32px 64px rgba(0,0,0,0.12), 0 16px 32px rgba(0,0,0,0.06)',
    '0 34px 68px rgba(0,0,0,0.12), 0 17px 34px rgba(0,0,0,0.06)',
    '0 36px 72px rgba(0,0,0,0.13), 0 18px 36px rgba(0,0,0,0.06)',
    '0 38px 76px rgba(0,0,0,0.13), 0 19px 38px rgba(0,0,0,0.06)',
    '0 40px 80px rgba(0,0,0,0.14), 0 20px 40px rgba(0,0,0,0.06)',
    '0 42px 84px rgba(0,0,0,0.14), 0 21px 42px rgba(0,0,0,0.06)',
    '0 44px 88px rgba(0,0,0,0.15), 0 22px 44px rgba(0,0,0,0.06)',
    '0 46px 92px rgba(0,0,0,0.15), 0 23px 46px rgba(0,0,0,0.06)',
  ] as any,
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          padding: '8px 20px',
          fontSize: '0.875rem',
        },
        contained: {
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          '&:hover': {
            boxShadow: '0 4px 8px rgba(0,0,0,0.15)',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06)',
          border: '1px solid rgba(0,0,0,0.06)',
          transition: 'box-shadow 0.2s ease, transform 0.2s ease',
          '&:hover': {
            boxShadow: '0 8px 24px rgba(0,0,0,0.08)',
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          fontWeight: 500,
          fontSize: '0.8rem',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: '#ffffff',
          color: '#1a1a2e',
          boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 10,
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
  },
});

export default theme;
