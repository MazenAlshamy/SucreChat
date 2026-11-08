import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { getMeeting, getRoom, listMessages, markMessagesRead, sendMessage } from "../api/client";
import { canSendChat, mergeChatMessages } from "../utils/chat";
import useLiveKit from "../hooks/useLiveKit";
import useRealtime from "../hooks/useRealtime";
import useWebRtc from "../hooks/useWebRtc";

const RoomSessionContext = createContext(null);

function idleMedia() {
  return {
    status: "idle",
    error: "",
    participants: [],
    micOn: false,
    camOn: false,
    screenOn: false,
    devices: { cameras: [], mics: [], speakers: [] },
    selected: { cameraId: "", micId: "", speakerId: "" },
    toggleMic: async () => {},
    toggleCam: async () => {},
    toggleScreen: async () => {},
    switchDevice: async () => {},
    reconnect: async () => {},
    leave: async () => {},
    handleSignal: async () => {},
  };
}

function roomPathId(pathname) {
  const match = pathname.match(/^\/rooms\/([^/]+)/);
  return match ? match[1] : "";
}

function applyRoomEvent(current, event) {
  if (!current) {
    if (event.type === "connected" && event.room) {
      return {
        room: event.room,
        members: event.members || [],
        join_requests: [],
        invitations: [],
        role: event.role,
        user_id: event.user_id,
        media_enabled: event.media_enabled ?? false,
        media_provider: event.media_provider || "none",
        media_reason: event.media_reason ?? null,
        meeting_started_at: event.meeting_started_at || null,
        meeting_ended_at: event.meeting_ended_at || null,
        elapsed_seconds: event.elapsed_seconds || 0,
        meeting_running: Boolean(event.meeting_running),
        unread_messages: 0,
      };
    }
    return current;
  }
  const next = { ...current };
  if (event.room) {
    next.room = { ...current.room, ...event.room, is_owner: current.room?.is_owner ?? event.room.is_owner };
  }
  if (event.members) {
    next.members = event.members;
  }
  if (event.media_provider) {
    next.media_provider = event.media_provider;
  }
  if (event.media_enabled != null) {
    next.media_enabled = event.media_enabled;
  }
  if (event.media_reason !== undefined) {
    next.media_reason = event.media_reason;
  }
  if (event.meeting_started_at !== undefined) {
    next.meeting_started_at = event.meeting_started_at;
  }
  if (event.elapsed_seconds != null) {
    next.elapsed_seconds = event.elapsed_seconds;
  }
  if (event.meeting_running != null) {
    next.meeting_running = event.meeting_running;
  }
  if (event.role) {
    next.role = event.role;
  }
  if (event.user_id) {
    next.user_id = event.user_id;
  }
  if (event.type === "join_request" && event.request) {
    const others = (current.join_requests || []).filter((item) => item.id !== event.request.id);
    next.join_requests = [event.request, ...others];
  }
  if (event.type === "request_updated" && event.request) {
    next.join_requests = (current.join_requests || []).map((item) =>
      item.id === event.request.id ? event.request : item
    );
  }
  if (event.type === "presence" && event.online_users) {
    const online = new Set(event.online_users.map((item) => item.user_id));
    next.members = (event.members || current.members || []).map((member) => ({
      ...member,
      online: online.has(member.user_id),
    }));
  }
  return next;
}

export function RoomSessionProvider({ children }) {
  const content = children ?? <Outlet />;
  const location = useLocation();
  const pathRoomId = roomPathId(location.pathname);
  const [heldRoomId, setHeldRoomId] = useState("");
  const [left, setLeft] = useState(false);
  const [mediaHeld, setMediaHeld] = useState(false);
  const roomId = pathRoomId || (mediaHeld && !left ? heldRoomId : "");
  const inMeeting = Boolean(pathRoomId && location.pathname.endsWith("/meeting"));
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");
  const [messages, setMessages] = useState([]);
  const [chatError, setChatError] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [unreadChat, setUnreadChat] = useState(0);
  const chatOpenRef = useRef(false);
  const userIdRef = useRef("");
  const [signalEvent, setSignalEvent] = useState(null);
  const sendRef = useRef(() => false);
  const signalHandlerRef = useRef(null);
  const elapsedBaseRef = useRef({ seconds: 0, at: Date.now(), running: false });
  const [elapsedTick, setElapsedTick] = useState(0);
  const heldRoomIdRef = useRef("");

  useEffect(() => {
    if (!pathRoomId) {
      return;
    }
    if (heldRoomIdRef.current && pathRoomId !== heldRoomIdRef.current) {
      setLeft(false);
      setMediaHeld(false);
      setError("");
      setChatError("");
      setMessages([]);
      setUnreadChat(0);
      setSignalEvent(null);
      setDetail(null);
    }
    heldRoomIdRef.current = pathRoomId;
    setHeldRoomId(pathRoomId);
  }, [pathRoomId]);

  useEffect(() => {
    if (!roomId) {
      setDetail(null);
      setMessages([]);
      setError("");
      setChatError("");
      setUnreadChat(0);
      setSignalEvent(null);
    }
  }, [roomId]);

  useEffect(() => {
    if (!roomId) {
      return undefined;
    }
    let cancelled = false;
    Promise.all([
      inMeeting ? getMeeting(roomId).catch(() => null) : Promise.resolve(null),
      getRoom(roomId).catch(() => null),
    ])
      .then(([meeting, room]) => {
        if (cancelled) {
          return;
        }
        if (!meeting && !room) {
          setError("تعذر تحميل الغرفة");
          return;
        }
        setDetail((current) => ({
          ...(current || {}),
          ...(meeting || {}),
          room: room?.room || meeting?.room,
          members: room?.members || meeting?.members || [],
          invitations: room?.invitations || [],
          join_requests: room?.join_requests || [],
        }));
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [roomId, inMeeting]);

  useEffect(() => {
    if (inMeeting) {
      setLeft(false);
      setMediaHeld(true);
    }
  }, [inMeeting]);

  useEffect(() => {
    if (!roomId) {
      return undefined;
    }
    let cancelled = false;
    setChatLoading(true);
    listMessages(roomId)
      .then((data) => {
        if (!cancelled) {
          setMessages(mergeChatMessages([], data.messages || []));
          setUnreadChat(data.unread_count || 0);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setChatError("تعذر تحميل المحادثة");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setChatLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [roomId]);

  const connection = useRealtime(
    roomId ? `/api/ws/rooms/${roomId}` : "",
    (event) => {
      if (event.type === "signal") {
        if (signalHandlerRef.current) {
          signalHandlerRef.current(event);
        } else {
          setSignalEvent(event);
        }
      }
      if ((event.type === "chat_message" || event.type === "chat_ack") && event.message) {
        setMessages((current) => mergeChatMessages(current, event.message));
        if (event.message.user_id && event.message.user_id !== userIdRef.current && !chatOpenRef.current) {
          setUnreadChat((value) => value + 1);
        }
      }
      if (event.type === "error" && event.message) {
        setChatError(event.message);
      }
      setDetail((current) => applyRoomEvent(current, event));
    },
    Boolean(roomId) && !left
  );
  sendRef.current = connection.send;

  useEffect(() => {
    elapsedBaseRef.current = {
      seconds: detail?.elapsed_seconds || 0,
      at: Date.now(),
      running: Boolean(detail?.meeting_running && detail?.room?.status === "active"),
    };
  }, [detail?.elapsed_seconds, detail?.meeting_running, detail?.meeting_started_at, detail?.room?.status]);

  useEffect(() => {
    if (!elapsedBaseRef.current.running) {
      return undefined;
    }
    const timer = window.setInterval(() => setElapsedTick((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, [detail?.meeting_running, detail?.room?.status]);

  const elapsedSeconds = elapsedBaseRef.current.running
    ? elapsedBaseRef.current.seconds + Math.floor((Date.now() - elapsedBaseRef.current.at) / 1000)
    : detail?.elapsed_seconds || 0;
  void elapsedTick;

  const provider = detail?.media_provider || (detail?.media_enabled ? "livekit" : "none");
  const socketReady = connection.status === "connected";
  const keepMedia = (inMeeting || mediaHeld) && !left && detail?.room?.status === "active";
  const mediaEnabled = Boolean(detail?.media_enabled) && keepMedia;
  const useLiveKitMedia = provider === "livekit" && mediaEnabled;
  const usePeerMedia = provider === "webrtc" && mediaEnabled;

  useEffect(() => {
    if (socketReady && keepMedia && !left) {
      sendRef.current({ type: "signal", action: "join-media" });
    }
  }, [socketReady, keepMedia, left, roomId]);

  useEffect(() => {
    if (!roomId || connection.status !== "connected") {
      return undefined;
    }
    let cancelled = false;
    listMessages(roomId)
      .then((data) => {
        if (!cancelled) {
          setMessages((current) => mergeChatMessages(current, data.messages || []));
          if (!chatOpenRef.current) {
            setUnreadChat(data.unread_count || 0);
          }
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [roomId, connection.status]);
  const localUser = detail
    ? {
        id: detail.user_id,
        name: detail.members?.find((item) => item.user_id === detail.user_id)?.display_name || "أنت",
      }
    : null;
  userIdRef.current = detail?.user_id || "";

  const livekit = useLiveKit(roomId, useLiveKitMedia);
  const webrtc = useWebRtc(
    roomId,
    localUser,
    (payload) => sendRef.current(payload),
    signalEvent,
    usePeerMedia
  );
  const media = useLiveKitMedia ? livekit : usePeerMedia ? webrtc : idleMedia();
  signalHandlerRef.current = webrtc.handleSignal;

  const reload = useCallback(async () => {
    if (!roomId) {
      return;
    }
    const [meeting, room] = await Promise.all([
      inMeeting || mediaHeld ? getMeeting(roomId).catch(() => null) : Promise.resolve(null),
      getRoom(roomId).catch(() => null),
    ]);
    setDetail((current) => ({
      ...(current || {}),
      ...(meeting || {}),
      room: room?.room || meeting?.room,
      members: room?.members || meeting?.members || current?.members || [],
      invitations: room?.invitations || current?.invitations || [],
      join_requests: room?.join_requests || current?.join_requests || [],
    }));
  }, [roomId, inMeeting, mediaHeld]);

  const postChat = useCallback(
    async (body) => {
      if (!roomId) {
        throw new Error("لا توجد غرفة");
      }
      const check = canSendChat(body);
      if (!check.ok) {
        const message = check.reason === "too_long" ? "الرسالة أطول من الحد المسموح" : "لا يمكن إرسال رسالة فارغة";
        setChatError(message);
        throw new Error(message);
      }
      setChatError("");
      try {
        const message = await sendMessage(roomId, check.body);
        setMessages((current) => mergeChatMessages(current, message));
        return message;
      } catch (err) {
        setChatError(err.message);
        throw err;
      }
    },
    [roomId]
  );

  const markChatRead = useCallback(async () => {
    if (!roomId) {
      return;
    }
    setUnreadChat(0);
    chatOpenRef.current = true;
    try {
      await markMessagesRead(roomId);
    } catch {
      return;
    }
  }, [roomId]);

  const setChatOpen = useCallback((open) => {
    chatOpenRef.current = Boolean(open);
    if (open) {
      setUnreadChat(0);
    }
  }, []);

  const leaveMedia = useCallback(async () => {
    setLeft(true);
    setMediaHeld(false);
    await media.leave();
  }, [media]);

  const value = useMemo(
    () => ({
      roomId,
      inMeeting,
      detail,
      error,
      setError,
      connection,
      media,
      provider,
      messages,
      chatError,
      chatLoading,
      elapsedSeconds,
      reload,
      postChat,
      markChatRead,
      setChatOpen,
      unreadChat,
      leaveMedia,
      left,
      mediaHeld,
      pathRoomId,
    }),
    [
      roomId,
      inMeeting,
      detail,
      error,
      connection,
      media,
      provider,
      messages,
      chatError,
      chatLoading,
      elapsedSeconds,
      reload,
      postChat,
      markChatRead,
      setChatOpen,
      unreadChat,
      leaveMedia,
      left,
      mediaHeld,
      pathRoomId,
    ]
  );

  return <RoomSessionContext.Provider value={value}>{content}</RoomSessionContext.Provider>;
}

export function useRoomSession() {
  return useContext(RoomSessionContext);
}
