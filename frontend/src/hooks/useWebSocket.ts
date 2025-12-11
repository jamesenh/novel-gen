import { useEffect, useRef, useState } from "react";

type MessageHandler = (data: any) => void;
type WebSocketOptions = {
  onOpen?: () => void;
  onClose?: () => void;
};

export function useWebSocket(url: string, onMessage: MessageHandler, options?: WebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const handlerRef = useRef<MessageHandler>(onMessage);

  // 保持最新的回调引用，避免 useEffect 依赖变化导致反复重连
  useEffect(() => {
    handlerRef.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    let retry = 0;
    let stopped = false;

    const connect = () => {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        retry = 0;
        options?.onOpen?.();
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          handlerRef.current(payload);
        } catch {
          // ignore parse error
        }
      };

      ws.onclose = () => {
        setConnected(false);
        options?.onClose?.();
        if (stopped) return;
        retry += 1;
        const delay = Math.min(5000, 500 * retry);
        setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      stopped = true;
      wsRef.current?.close();
    };
  }, [url]);

  return { connected };
}

