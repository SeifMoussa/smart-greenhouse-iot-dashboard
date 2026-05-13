import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useWebSocket } from "../src/hooks/useWebSocket";

/** Minimal WebSocket stub usable as the second arg to the hook's factory. */
class MockWebSocket {
  static OPEN = 1;
  static CLOSED = 3;
  static CONNECTING = 0;

  readonly url: string;
  readyState: number = MockWebSocket.CONNECTING;
  onopen: ((ev: Event) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    instances.push(this);
  }

  close(): void {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent("close"));
  }

  // Helpers for tests.
  open(): void {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.(new Event("open"));
  }
  receive(payload: unknown): void {
    this.onmessage?.(new MessageEvent("message", { data: JSON.stringify(payload) }));
  }
  failClose(): void {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent("close"));
  }
}

let instances: MockWebSocket[] = [];

beforeEach(() => {
  instances = [];
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useWebSocket", () => {
  it("starts in connecting and moves to open when the socket opens", () => {
    const factory = (url: string) => new MockWebSocket(url) as unknown as WebSocket;
    const { result } = renderHook(() =>
      useWebSocket<{ kind: string }>("ws://test", { socketFactory: factory }),
    );

    expect(result.current.status).toBe("connecting");
    act(() => instances[0]!.open());
    expect(result.current.status).toBe("open");
  });

  it("delivers messages to onMessage", () => {
    const factory = (url: string) => new MockWebSocket(url) as unknown as WebSocket;
    const messages: Array<{ kind: string }> = [];
    renderHook(() =>
      useWebSocket<{ kind: string }>("ws://test", {
        socketFactory: factory,
        onMessage: (m) => messages.push(m),
      }),
    );
    act(() => {
      instances[0]!.open();
      instances[0]!.receive({ kind: "reading" });
    });
    expect(messages).toEqual([{ kind: "reading" }]);
  });

  it("reconnects with exponential backoff on close", async () => {
    const factory = (url: string) => new MockWebSocket(url) as unknown as WebSocket;
    const { result } = renderHook(() =>
      useWebSocket<unknown>("ws://test", {
        socketFactory: factory,
        initialDelayMs: 1_000,
        maxDelayMs: 10_000,
      }),
    );

    // First socket opens then closes.
    act(() => instances[0]!.open());
    expect(result.current.status).toBe("open");
    act(() => instances[0]!.failClose());
    expect(result.current.status).toBe("closed");

    // After the initial delay the hook creates a second socket.
    expect(instances.length).toBe(1);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });
    expect(instances.length).toBe(2);

    // Second socket also fails — backoff doubles to 2 000 ms.
    act(() => instances[1]!.failClose());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });
    expect(instances.length).toBe(2); // not yet
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });
    expect(instances.length).toBe(3);
  });

  it("resets backoff after a successful open", async () => {
    const factory = (url: string) => new MockWebSocket(url) as unknown as WebSocket;
    renderHook(() =>
      useWebSocket<unknown>("ws://test", {
        socketFactory: factory,
        initialDelayMs: 1_000,
        maxDelayMs: 10_000,
      }),
    );

    // 1st: open then close
    act(() => instances[0]!.open());
    act(() => instances[0]!.failClose());

    // wait 1s → 2nd socket created
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });
    expect(instances.length).toBe(2);

    // 2nd opens successfully then closes again
    act(() => instances[1]!.open());
    act(() => instances[1]!.failClose());

    // After success, the next delay returns to 1s (not 2s).
    await act(async () => {
      await vi.advanceTimersByTimeAsync(999);
    });
    expect(instances.length).toBe(2); // not yet
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(instances.length).toBe(3);
  });

  it("does not reconnect after unmount", async () => {
    const factory = (url: string) => new MockWebSocket(url) as unknown as WebSocket;
    const { unmount } = renderHook(() =>
      useWebSocket<unknown>("ws://test", {
        socketFactory: factory,
        initialDelayMs: 100,
      }),
    );
    act(() => instances[0]!.open());
    unmount();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });
    // Only the initial socket — no reconnect attempts after unmount.
    expect(instances.length).toBe(1);
  });

  it("ignores non-JSON frames without crashing", () => {
    const factory = (url: string) => new MockWebSocket(url) as unknown as WebSocket;
    const messages: unknown[] = [];
    renderHook(() =>
      useWebSocket<unknown>("ws://test", {
        socketFactory: factory,
        onMessage: (m) => messages.push(m),
      }),
    );
    act(() => instances[0]!.open());
    act(() => {
      instances[0]!.onmessage?.(new MessageEvent("message", { data: "garbage{not json" }));
    });
    // Parse failure is synchronous inside onmessage; no message should reach the callback.
    expect(messages).toEqual([]);
  });
});
