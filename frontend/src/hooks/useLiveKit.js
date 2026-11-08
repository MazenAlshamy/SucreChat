import { useCallback, useEffect, useRef, useState } from "react";
import { Room, RoomEvent, Track } from "livekit-client";
import { getLiveKitToken } from "../api/client";

function permissionMessage(err) {
  const name = err?.name || "";
  const text = err?.message || "";
  if (name === "NotAllowedError" || /permission|denied|notallowed/i.test(text)) {
    return "رفض المتصفح إذن الكاميرا أو الميكروفون. اسمح بالوصول من إعدادات الموقع ثم أعد المحاولة.";
  }
  if (name === "NotFoundError") {
    return "لم يُعثر على كاميرا أو ميكروفون في هذا الجهاز.";
  }
  if (name === "NotReadableError") {
    return "الكاميرا أو الميكروفون مستخدمان من تطبيق آخر.";
  }
  return text || "تعذر تشغيل الوسائط";
}

function snapshot(room, speakingIds) {
  const people = [room.localParticipant, ...Array.from(room.remoteParticipants.values())];
  return people
    .filter((participant) => participant && participant.identity)
    .flatMap((participant) => {
      const camera = participant.getTrackPublication(Track.Source.Camera);
      const microphone = participant.getTrackPublication(Track.Source.Microphone);
      const screen = participant.getTrackPublication(Track.Source.ScreenShare);
      const cameraOn = participant.isCameraEnabled && Boolean(camera?.track) && !camera.isMuted;
      const micOn = participant.isMicrophoneEnabled && Boolean(microphone?.track) && !microphone?.isMuted;
      const screenOn = Boolean(screen?.track) && !screen.isMuted;
      const tiles = [
        {
          identity: participant.identity,
          name: participant.name || participant.identity,
          isLocal: participant === room.localParticipant,
          cameraOn,
          micOn,
          screenOn: false,
          speaking: speakingIds.has(participant.identity),
          videoTrack: camera?.track || null,
          audioTrack: microphone?.track || null,
        },
      ];
      if (screenOn) {
        tiles.push({
          identity: `${participant.identity}-screen`,
          name: `${participant.name || participant.identity} — شاشة`,
          isLocal: participant === room.localParticipant,
          cameraOn: false,
          micOn: false,
          screenOn: true,
          speaking: false,
          videoTrack: screen?.track || null,
          audioTrack: null,
        });
      }
      return tiles;
    });
}

async function listDevices() {
  if (!navigator.mediaDevices?.enumerateDevices) {
    return { cameras: [], mics: [], speakers: [] };
  }
  const devices = await navigator.mediaDevices.enumerateDevices();
  return {
    cameras: devices.filter((item) => item.kind === "videoinput"),
    mics: devices.filter((item) => item.kind === "audioinput"),
    speakers: devices.filter((item) => item.kind === "audiooutput"),
  };
}

async function stopLocalTracks(room) {
  if (!room) {
    return;
  }
  const publications = Array.from(room.localParticipant.trackPublications.values());
  for (const publication of publications) {
    const track = publication.track;
    if (!track) {
      continue;
    }
    try {
      await room.localParticipant.unpublishTrack(track, true);
    } catch {
      track.stop();
    }
  }
}

export default function useLiveKit(roomId, enabled) {
  const roomRef = useRef(null);
  const leavingRef = useRef(false);
  const speakingRef = useRef(new Set());
  const connectRef = useRef(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const [participants, setParticipants] = useState([]);
  const [micOn, setMicOn] = useState(false);
  const [camOn, setCamOn] = useState(false);
  const [screenOn, setScreenOn] = useState(false);
  const [devices, setDevices] = useState({ cameras: [], mics: [], speakers: [] });
  const [selected, setSelected] = useState({ cameraId: "", micId: "", speakerId: "" });

  const refresh = useCallback((room) => {
    if (!room) {
      setParticipants([]);
      setMicOn(false);
      setCamOn(false);
      return;
    }
    setParticipants(snapshot(room, speakingRef.current));
    setMicOn(room.localParticipant.isMicrophoneEnabled);
    setCamOn(room.localParticipant.isCameraEnabled);
    setScreenOn(room.localParticipant.isScreenShareEnabled);
  }, []);

  const refreshDevices = useCallback(async () => {
    try {
      setDevices(await listDevices());
    } catch {
      return;
    }
  }, []);

  useEffect(() => {
    if (!enabled || !roomId) {
      setStatus("idle");
      setError("");
      setParticipants([]);
      return undefined;
    }

    let cancelled = false;
    let reconnectTimer;
    let retry = 1500;
    leavingRef.current = false;
    const room = new Room({
      adaptiveStream: true,
      dynacast: true,
      disconnectOnPageLeave: true,
      stopLocalTrackOnUnpublish: true,
    });
    roomRef.current = room;

    const onChange = () => refresh(room);
    room.on(RoomEvent.ParticipantConnected, onChange);
    room.on(RoomEvent.ParticipantDisconnected, onChange);
    room.on(RoomEvent.TrackSubscribed, onChange);
    room.on(RoomEvent.TrackUnsubscribed, onChange);
    room.on(RoomEvent.LocalTrackPublished, onChange);
    room.on(RoomEvent.LocalTrackUnpublished, onChange);
    room.on(RoomEvent.TrackMuted, onChange);
    room.on(RoomEvent.TrackUnmuted, onChange);
    room.on(RoomEvent.ConnectionQualityChanged, onChange);
    room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
      speakingRef.current = new Set(speakers.map((item) => item.identity));
      refresh(room);
    });
    room.on(RoomEvent.MediaDevicesError, (err) => {
      setError(permissionMessage(err));
    });
    room.on(RoomEvent.Reconnecting, () => {
      if (!leavingRef.current) {
        setStatus("connecting");
      }
    });
    room.on(RoomEvent.Reconnected, () => {
      setStatus("connected");
      setError("");
      refresh(room);
    });
    room.on(RoomEvent.Disconnected, () => {
      setParticipants([]);
      setMicOn(false);
      setCamOn(false);
      if (leavingRef.current || cancelled) {
        setStatus("disconnected");
        return;
      }
      setStatus("connecting");
      reconnectTimer = window.setTimeout(() => connectRef.current?.(), retry);
      retry = Math.min(retry * 2, 12000);
    });

    async function enableMedia() {
      try {
        await room.localParticipant.setMicrophoneEnabled(true);
      } catch (err) {
        setError(permissionMessage(err));
      }
      try {
        await room.localParticipant.setCameraEnabled(true);
      } catch (err) {
        setError(permissionMessage(err));
      }
    }

    async function connect() {
      if (cancelled || leavingRef.current) {
        return;
      }
      setStatus("connecting");
      try {
        const creds = await getLiveKitToken(roomId);
        if (cancelled || leavingRef.current) {
          return;
        }
        await room.connect(creds.url, creds.token, { autoSubscribe: true });
        if (cancelled || leavingRef.current) {
          await stopLocalTracks(room);
          await room.disconnect();
          return;
        }
        await enableMedia();
        retry = 1500;
        setStatus("connected");
        setError("");
        refresh(room);
        await refreshDevices();
      } catch (err) {
        if (!cancelled && !leavingRef.current) {
          const message = permissionMessage(err);
          setError(message);
          setStatus("error");
          const fatal = /صلاحية|غير مُعد|مغلقة|ليست لديك عضوية|يلزم بدء جلسة|LIVEKIT_URL/.test(message);
          if (fatal) {
            return;
          }
          reconnectTimer = window.setTimeout(() => connectRef.current?.(), retry);
          retry = Math.min(retry * 2, 12000);
        }
      }
    }

    connectRef.current = connect;

    function onOnline() {
      if (!cancelled && !leavingRef.current && room.state !== "connected") {
        window.clearTimeout(reconnectTimer);
        retry = 1500;
        connect();
      }
    }

    connect();
    window.addEventListener("online", onOnline);
    navigator.mediaDevices?.addEventListener?.("devicechange", refreshDevices);
    return () => {
      cancelled = true;
      leavingRef.current = true;
      window.clearTimeout(reconnectTimer);
      window.removeEventListener("online", onOnline);
      navigator.mediaDevices?.removeEventListener?.("devicechange", refreshDevices);
      room.removeAllListeners();
      stopLocalTracks(room).finally(() => {
        room.disconnect();
      });
      roomRef.current = null;
    };
  }, [roomId, enabled, refresh, refreshDevices]);

  async function toggleMic() {
    const room = roomRef.current;
    if (!room || room.state !== "connected") {
      return;
    }
    try {
      const next = !room.localParticipant.isMicrophoneEnabled;
      await room.localParticipant.setMicrophoneEnabled(next);
      setMicOn(room.localParticipant.isMicrophoneEnabled);
      refresh(room);
    } catch (err) {
      setError(permissionMessage(err));
    }
  }

  async function toggleCam() {
    const room = roomRef.current;
    if (!room || room.state !== "connected") {
      return;
    }
    try {
      const next = !room.localParticipant.isCameraEnabled;
      await room.localParticipant.setCameraEnabled(next);
      setCamOn(room.localParticipant.isCameraEnabled);
      refresh(room);
    } catch (err) {
      setError(permissionMessage(err));
    }
  }

  async function switchDevice(kind, deviceId) {
    const room = roomRef.current;
    if (!room || room.state !== "connected" || !deviceId) {
      return;
    }
    try {
      await room.switchActiveDevice(kind, deviceId);
      setSelected((current) => ({
        ...current,
        cameraId: kind === "videoinput" ? deviceId : current.cameraId,
        micId: kind === "audioinput" ? deviceId : current.micId,
        speakerId: kind === "audiooutput" ? deviceId : current.speakerId,
      }));
      refresh(room);
    } catch (err) {
      setError(permissionMessage(err));
    }
  }

  async function toggleScreen() {
    const room = roomRef.current;
    if (!room || room.state !== "connected") {
      return;
    }
    try {
      const next = !room.localParticipant.isScreenShareEnabled;
      await room.localParticipant.setScreenShareEnabled(next);
      setScreenOn(room.localParticipant.isScreenShareEnabled);
      refresh(room);
    } catch (err) {
      if (err?.name === "NotAllowedError") {
        return;
      }
      setError(permissionMessage(err));
    }
  }

  async function reconnect() {
    const room = roomRef.current;
    if (leavingRef.current || !room) {
      return;
    }
    setError("");
    setStatus("connecting");
    try {
      await stopLocalTracks(room);
      if (room.state === "connected" || room.state === "reconnecting") {
        await room.disconnect();
      }
      await connectRef.current?.();
    } catch {
      setError("تعذر إعادة الاتصال");
    }
  }

  async function leave() {
    leavingRef.current = true;
    const room = roomRef.current;
    if (room) {
      room.removeAllListeners();
      await stopLocalTracks(room);
      await room.disconnect();
    }
    roomRef.current = null;
    setStatus("disconnected");
    setParticipants([]);
    setMicOn(false);
    setCamOn(false);
    setScreenOn(false);
  }

  return {
    status,
    error,
    participants,
    micOn,
    camOn,
    screenOn,
    devices,
    selected,
    toggleMic,
    toggleCam,
    toggleScreen,
    switchDevice,
    reconnect,
    leave,
  };
}
