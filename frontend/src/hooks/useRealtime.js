import { useEffect, useRef, useState } from "react";

export default function useRealtime(path, onMessage, enabled = true) {
  const [status, setStatus] = useState("disconnected");
  const handlerRef = useRef(onMessage);
  const socketRef = useRef(null);
  handlerRef.current = onMessage;

  useEffect(() => {
    if (!enabled || !path) {
      setStatus("disconnected");
      return undefined;
    }

    let socket;
    let closed = false;
    let retry = 800;
    let retryTimer;
    let pingTimer;
    let currentSocket;

    function clearTimers() {
      window.clearTimeout(retryTimer);
      window.clearInterval(pingTimer);
    }

    function connect() {
      if (closed) {
        return;
      }
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(`${protocol}://${window.location.host}${path}`);
      currentSocket = socket;
      socketRef.current = socket;
      setStatus("connecting");
      socket.onopen = () => {
        setStatus("connected");
        retry = 800;
        window.clearInterval(pingTimer);
        pingTimer = window.setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "ping" }));
          }
        }, 25000);
      };
      socket.onmessage = (event) => {
        try {
          handlerRef.current(JSON.parse(event.data));
        } catch {
          return;
        }
      };
      socket.onclose = (closeEvent) => {
        window.clearInterval(pingTimer);
        setStatus("disconnected");
        if (closeEvent.code === 1008) {
          return;
        }
        if (!closed) {
          retryTimer = window.setTimeout(connect, retry);
          retry = Math.min(retry * 2, 8000);
        }
      };
      socket.onerror = () => {
        socket.close();
      };
    }

    function onOnline() {
      if (!closed && (!currentSocket || currentSocket.readyState !== WebSocket.OPEN)) {
        window.clearTimeout(retryTimer);
        connect();
      }
    }

    function onVisibility() {
      if (document.visibilityState === "visible") {
        onOnline();
      }
    }

    connect();
    window.addEventListener("online", onOnline);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      closed = true;
      clearTimers();
      window.removeEventListener("online", onOnline);
      document.removeEventListener("visibilitychange", onVisibility);
      if (socket && socket.readyState === WebSocket.OPEN) {
        try {
          socket.send(JSON.stringify({ type: "leave" }));
        } catch {
          return;
        }
      }
      socket?.close();
      socketRef.current = null;
    };
  }, [path, enabled]);

  function send(payload) {
    const socket = socketRef.current;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(payload));
      return true;
    }
    return false;
  }

  return { status, send };
}
