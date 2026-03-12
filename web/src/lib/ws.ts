const WS_BASE = 'ws://localhost:8888';

export interface ChatMessage {
  type: 'system' | 'message' | 'error';
  role?: 'user' | 'assistant';
  message: string;
}

export function createChatConnection(
  slug: string,
  onMessage: (msg: ChatMessage) => void,
  onOpen?: () => void,
  onClose?: () => void,
  onError?: (error: Event) => void
): WebSocket {
  const ws = new WebSocket(`${WS_BASE}/ws/chat/${slug}`);

  ws.onopen = () => {
    onOpen?.();
  };

  ws.onmessage = (event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data) as ChatMessage;
      onMessage(data);
    } catch {
      onMessage({
        type: 'error',
        message: 'Failed to parse server message',
      });
    }
  };

  ws.onclose = () => {
    onClose?.();
  };

  ws.onerror = (error: Event) => {
    onError?.(error);
  };

  return ws;
}

export function sendChatMessage(ws: WebSocket, message: string): void {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ message }));
  }
}
