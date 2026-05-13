import { useCallback, useEffect, useRef, useState } from "react";

export type WSStatus = "connecting" | "open" | "closed" | "error";

export interface UseWebSocketOptions<TMessage> {
  /** Callback fired for each parsed message. */
  onMessage?: (message: TMessage) => void;
  /** Initial reconnect delay in ms. Default 1 000. */
  initialDelayMs?: number;
  /** Maximum reconnect delay in ms. Default 30 000. */
  maxDelayMs?: number;
  /** Provide a custom WebSocket factory for testing. */
  socketFactory?: (url: string) => WebSocket;
}

interface State<TMessage> {
  status: WSStatus;
  lastMessage: TMessage | null;
}

/**
 * Connect to a WebSocket URL with auto-reconnect on close/error.
 * Backoff doubles after each failed connect, starting at `initialDelayMs`
 * and capped at `maxDelayMs`. Resets to initial on a successful open.
 */
export function useWebSocket<TMessage = unknown>(
  url: string,
  options: UseWebSocketOptions<TMessage> = {},
): { status: WSStatus; lastMessage: TMessage | null } {
  const { onMessage, initialDelayMs = 1_000, maxDelayMs = 30_000, socketFactory } = options;

  const [state, setState] = useState<State<TMessage>>({
    status: "connecting",
    lastMessage: null,
  });

  // Stable refs so reconnect logic doesn't churn on every render.
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;
  const factoryRef = useRef(socketFactory);
  factoryRef.current = socketFactory;
  const urlRef = useRef(url);
  urlRef.current = url;

  const socketRef = useRef<WebSocket | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const delayRef = useRef(initialDelayMs);
  const closedByUserRef = useRef(false);

  const cleanup = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    if (socketRef.current) {
      // Detach handlers so a late close doesn't try to reconnect.
      socketRef.current.onopen = null;
      socketRef.current.onclose = null;
      socketRef.current.onerror = null;
      socketRef.current.onmessage = null;
      if (
        socketRef.current.readyState === WebSocket.OPEN ||
        socketRef.current.readyState === WebSocket.CONNECTING
      ) {
        socketRef.current.close();
      }
      socketRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    setState((prev) => ({ ...prev, status: "connecting" }));
    const factory = factoryRef.current;
    const socket: WebSocket = factory ? factory(urlRef.current) : new WebSocket(urlRef.current);
    socketRef.current = socket;

    socket.onopen = () => {
      delayRef.current = initialDelayMs;
      setState((prev) => ({ ...prev, status: "open" }));
    };

    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as TMessage;
        setState((prev) => ({ ...prev, lastMessage: parsed }));
        onMessageRef.current?.(parsed);
      } catch {
        // Ignore non-JSON frames; backend only sends JSON.
      }
    };

    socket.onerror = () => {
      setState((prev) => ({ ...prev, status: "error" }));
    };

    socket.onclose = () => {
      socketRef.current = null;
      if (closedByUserRef.current) {
        setState((prev) => ({ ...prev, status: "closed" }));
        return;
      }
      setState((prev) => ({ ...prev, status: "closed" }));
      const delay = delayRef.current;
      delayRef.current = Math.min(delay * 2, maxDelayMs);
      timerRef.current = setTimeout(connect, delay);
    };
  }, [initialDelayMs, maxDelayMs]);

  useEffect(() => {
    closedByUserRef.current = false;
    delayRef.current = initialDelayMs;
    connect();
    return () => {
      closedByUserRef.current = true;
      cleanup();
    };
    // We intentionally do not depend on `connect` identity beyond the
    // initial mount; url changes are handled via urlRef.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);

  return state;
}
