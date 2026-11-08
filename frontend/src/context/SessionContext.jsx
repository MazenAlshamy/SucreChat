import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { fetchInboxSummary, fetchSession, logout as logoutRequest } from "../api/client";
import useRealtime from "../hooks/useRealtime";

const SessionContext = createContext(null);

const emptySummary = { notifications: 0, messages: 0, join_requests: 0 };

export function SessionProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);
  const [summary, setSummary] = useState(emptySummary);
  const [toast, setToast] = useState("");

  const refreshSession = useCallback(async () => {
    try {
      const data = await fetchSession();
      setUser(data.user);
      return data.user;
    } catch {
      setUser(null);
      setSummary(emptySummary);
      return null;
    } finally {
      setReady(true);
    }
  }, []);

  const refreshSummary = useCallback(async () => {
    try {
      const data = await fetchInboxSummary();
      setSummary({
        notifications: data.notifications || 0,
        messages: data.messages || 0,
        join_requests: data.join_requests || 0,
      });
      return data;
    } catch {
      setSummary(emptySummary);
      return emptySummary;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchSession()
      .then((data) => {
        if (!cancelled) {
          setUser(data.user);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setUser(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setReady(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!user) {
      setSummary(emptySummary);
      return undefined;
    }
    refreshSummary();
    return undefined;
  }, [user, refreshSummary]);

  useRealtime(
    "/api/ws/inbox",
    (event) => {
      if (event.type === "notification") {
        refreshSummary();
        const item = event.notification;
        if (item?.title) {
          setToast(`${item.title}${item.body ? `: ${item.body}` : ""}`);
          window.setTimeout(() => setToast(""), 5000);
        }
      }
    },
    Boolean(user)
  );

  const logout = useCallback(async () => {
    try {
      await logoutRequest();
    } catch {
      /* ignore */
    }
    setUser(null);
    setSummary(emptySummary);
  }, []);

  const value = useMemo(
    () => ({
      user,
      ready,
      summary,
      refreshSession,
      refreshSummary,
      logout,
      setSummary,
      toast,
    }),
    [user, ready, summary, refreshSession, refreshSummary, logout, toast]
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const value = useContext(SessionContext);
  if (!value) {
    throw new Error("useSession must be used within SessionProvider");
  }
  return value;
}