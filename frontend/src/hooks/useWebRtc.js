import { useCallback, useEffect, useRef, useState } from "react";
import {
  isPolitePeer,
  isScreenVideoTrack,
  shouldIgnoreOffer,
  uniqueParticipants,
} from "../webrtcMesh";

const ICE_SERVERS = [
  { urls: "stun:stun.l.google.com:19302" },
  { urls: "stun:stun1.l.google.com:19302" },
];

function logMedia(event, detail = {}) {
  try {
    console.info("[webrtc]", event, detail);
  } catch {
    return;
  }
}

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
  if (name === "AbortError" || name === "InterruptedError") {
    return "أُلغي طلب الكاميرا أو الميكروفون. أعد المحاولة من زر إعادة الاتصال.";
  }
  if (name === "SecurityError" || /https|secure/i.test(text)) {
    return "يلزم HTTPS أو localhost لتشغيل الكاميرا والميكروفون.";
  }
  return text || "تعذر تشغيل الوسائط";
}

function screenShareError(err) {
  const name = err?.name || "";
  if (name === "NotAllowedError") {
    return "";
  }
  if (name === "NotFoundError") {
    return "لم يُعثر على شاشة أو نافذة للمشاركة.";
  }
  if (name === "NotReadableError") {
    return "تعذر التقاط الشاشة لأنها مستخدمة من تطبيق آخر.";
  }
  if (name === "AbortError") {
    return "";
  }
  if (name === "SecurityError" || /https|secure/i.test(err?.message || "")) {
    return "يلزم HTTPS أو localhost لمشاركة الشاشة.";
  }
  if (!navigator.mediaDevices?.getDisplayMedia) {
    return "هذا المتصفح لا يدعم مشاركة الشاشة.";
  }
  return err?.message || "تعذر بدء مشاركة الشاشة.";
}

async function requestUserMedia(constraints) {
  if (!navigator.mediaDevices?.getUserMedia) {
    const err = new Error("يلزم HTTPS أو localhost لتشغيل الكاميرا والميكروفون.");
    err.name = "SecurityError";
    throw err;
  }
  try {
    return await navigator.mediaDevices.getUserMedia(constraints);
  } catch (err) {
    if (err?.name === "AbortError" || err?.name === "InterruptedError") {
      return navigator.mediaDevices.getUserMedia(constraints);
    }
    throw err;
  }
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

function stopStream(stream) {
  stream?.getTracks().forEach((track) => track.stop());
}

function markCameraTrack(track) {
  if (track && "contentHint" in track) {
    track.contentHint = "motion";
  }
}

function markScreenTrack(track) {
  if (track && "contentHint" in track) {
    track.contentHint = "detail";
  }
}

export default function useWebRtc(roomId, localUser, sendSignal, incoming, enabled) {
  const peersRef = useRef(new Map());
  const localStreamRef = useRef(null);
  const leavingRef = useRef(false);
  const pendingRef = useRef([]);
  const sendRef = useRef(sendSignal);
  const localUserRef = useRef(localUser);
  const handleSignalRef = useRef(null);
  const sessionRef = useRef(0);
  const signalChainRef = useRef(Promise.resolve());
  sendRef.current = sendSignal;
  localUserRef.current = localUser;

  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const [participants, setParticipants] = useState([]);
  const [micOn, setMicOn] = useState(false);
  const [camOn, setCamOn] = useState(false);
  const [screenOn, setScreenOn] = useState(false);
  const screenStreamRef = useRef(null);
  const [devices, setDevices] = useState({ cameras: [], mics: [], speakers: [] });
  const [selected, setSelected] = useState({ cameraId: "", micId: "", speakerId: "" });
  const selectedRef = useRef(selected);
  selectedRef.current = selected;
  const enabledRef = useRef(enabled);
  enabledRef.current = enabled;

  const publishSnapshot = useCallback(() => {
    const localUserId = localUserRef.current?.id;
    const localName = localUserRef.current?.name || "أنت";
    const localStream = localStreamRef.current;
    const people = [];
    if (localUserId) {
      const screenTrack = screenStreamRef.current?.getVideoTracks()[0] || null;
      const cameraTrack = localStream?.getVideoTracks()[0] || null;
      const audioTrack = localStream?.getAudioTracks()[0] || null;
      people.push({
        identity: localUserId,
        name: localName,
        isLocal: true,
        cameraOn: Boolean(cameraTrack && cameraTrack.enabled && cameraTrack.readyState === "live"),
        micOn: Boolean(audioTrack && audioTrack.enabled && audioTrack.readyState === "live"),
        screenOn: false,
        speaking: false,
        stream: localStream,
        videoTrack: cameraTrack,
        audioTrack,
      });
      if (screenTrack && screenTrack.readyState === "live") {
        people.push({
          identity: `${localUserId}-screen`,
          name: `${localName} — شاشة`,
          isLocal: true,
          cameraOn: false,
          micOn: false,
          screenOn: true,
          speaking: false,
          stream: screenStreamRef.current,
          videoTrack: screenTrack,
          audioTrack: null,
        });
      }
    }
    peersRef.current.forEach((peer, identity) => {
      const stream = peer.stream;
      const videoTrack = stream?.getVideoTracks()[0] || null;
      const audioTrack = stream?.getAudioTracks()[0] || null;
      const liveVideo = Boolean(videoTrack && videoTrack.readyState === "live");
      const liveAudio = Boolean(audioTrack && audioTrack.readyState === "live");
      people.push({
        identity,
        name: peer.name || identity,
        isLocal: false,
        cameraOn: liveVideo ? videoTrack.enabled !== false && peer.cameraOn !== false : Boolean(peer.cameraOn),
        micOn: liveAudio ? audioTrack.enabled !== false && peer.micOn !== false : Boolean(peer.micOn),
        screenOn: false,
        speaking: false,
        stream,
        videoTrack,
        audioTrack,
        connectionState: peer.pc?.connectionState || "",
        videoLost: Boolean(peer.hadVideo && !liveVideo),
      });
      const screenTrack = peer.screenStream?.getVideoTracks()[0] || null;
      if (screenTrack || peer.screenOn) {
        people.push({
          identity: `${identity}-screen`,
          name: `${peer.name || identity} — شاشة`,
          isLocal: false,
          cameraOn: false,
          micOn: false,
          screenOn: true,
          speaking: false,
          stream: peer.screenStream,
          videoTrack: screenTrack,
          audioTrack: null,
        });
      }
    });
    setParticipants(uniqueParticipants(people));
    const localAudio = localStream?.getAudioTracks()[0];
    const localVideo = localStream?.getVideoTracks()[0];
    setMicOn(Boolean(localAudio && localAudio.enabled));
    setCamOn(Boolean(localVideo && localVideo.enabled));
  }, []);

  const closePeer = useCallback((identity) => {
    const peer = peersRef.current.get(identity);
    if (!peer) {
      return;
    }
    try {
      peer.pc.close();
    } catch {
      /* ignore */
    }
    peersRef.current.delete(identity);
    logMedia("peer-closed", { identity });
  }, []);

  const closeAll = useCallback(() => {
    peersRef.current.forEach((peer) => {
      try {
        peer.pc.close();
      } catch {
        /* ignore */
      }
    });
    peersRef.current.clear();
    stopStream(localStreamRef.current);
    localStreamRef.current = null;
    stopStream(screenStreamRef.current);
    screenStreamRef.current = null;
  }, []);

  const flushIce = useCallback(async (peer) => {
    if (!peer?.pc?.remoteDescription) {
      return;
    }
    const queued = peer.pendingIce.splice(0);
    for (const candidate of queued) {
      try {
        await peer.pc.addIceCandidate(new RTCIceCandidate(candidate));
      } catch (err) {
        if (!peer.ignoreOffer) {
          logMedia("ice-error", { message: err?.message });
        }
      }
    }
  }, []);

  const ensurePeer = useCallback(
    (identity, name) => {
      const existing = peersRef.current.get(identity);
      if (existing) {
        if (name) {
          existing.name = name;
        }
        return existing;
      }
      const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
      const peer = {
        pc,
        stream: new MediaStream(),
        name: name || identity,
        cameraOn: false,
        micOn: false,
        screenOn: false,
        screenStream: null,
        hadVideo: false,
        makingOffer: false,
        ignoreOffer: false,
        polite: isPolitePeer(localUserRef.current?.id, identity),
        pendingIce: [],
      };
      pc.onicecandidate = (event) => {
        if (event.candidate && !leavingRef.current) {
          sendRef.current?.({
            type: "signal",
            action: "ice",
            to_user: identity,
            data: event.candidate.toJSON ? event.candidate.toJSON() : event.candidate,
          });
        }
      };
      pc.onnegotiationneeded = async () => {
        if (leavingRef.current || peer.makingOffer || pc.signalingState !== "stable") {
          return;
        }
        try {
          peer.makingOffer = true;
          const offer = await pc.createOffer();
          await pc.setLocalDescription(offer);
          if (leavingRef.current) {
            return;
          }
          logMedia("offer", { to: identity, polite: peer.polite });
          sendRef.current?.({
            type: "signal",
            action: "offer",
            to_user: identity,
            data: pc.localDescription,
          });
        } catch (err) {
          logMedia("offer-error", { to: identity, message: err?.message });
        } finally {
          peer.makingOffer = false;
        }
      };
      pc.ontrack = (event) => {
        const track = event.track;
        if (!track) {
          return;
        }
        const cameraTrack = peer.stream.getVideoTracks()[0];
        const screen = isScreenVideoTrack(track, {
          hasLiveCameraTrack: Boolean(cameraTrack),
          cameraStreamId: peer.stream.id,
          eventStreamId: event.streams?.[0]?.id,
        });
        if (screen) {
          peer.screenStream = peer.screenStream || new MediaStream();
          if (!peer.screenStream.getTracks().some((item) => item.id === track.id)) {
            peer.screenStream.addTrack(track);
          }
          peer.screenOn = true;
          track.onended = () => {
            peer.screenOn = false;
            try {
              peer.screenStream?.removeTrack(track);
            } catch {
              /* ignore */
            }
            publishSnapshot();
          };
          logMedia("recv-screen", { from: identity, trackId: track.id });
          publishSnapshot();
          return;
        }
        if (!peer.stream.getTracks().some((item) => item.id === track.id)) {
          peer.stream.addTrack(track);
        }
        if (track.kind === "video") {
          peer.hadVideo = true;
          peer.cameraOn = track.enabled !== false;
          logMedia("recv-video", { from: identity, trackId: track.id, muted: track.muted });
        }
        if (track.kind === "audio") {
          peer.micOn = track.enabled !== false;
          logMedia("recv-audio", { from: identity, trackId: track.id, muted: track.muted, enabled: track.enabled });
        }
        track.onunmute = () => {
          if (track.kind === "video") {
            peer.cameraOn = true;
            peer.hadVideo = true;
          }
          if (track.kind === "audio") {
            peer.micOn = true;
          }
          publishSnapshot();
        };
        track.onmute = () => publishSnapshot();
        track.onended = () => {
          try {
            peer.stream.removeTrack(track);
          } catch {
            /* ignore */
          }
          publishSnapshot();
        };
        publishSnapshot();
      };
      pc.onconnectionstatechange = () => {
        logMedia("pc-state", { identity, state: pc.connectionState, ice: pc.iceConnectionState });
        if (pc.connectionState === "failed") {
          try {
            pc.restartIce();
          } catch {
            /* ignore */
          }
          return;
        }
        if (pc.connectionState === "closed" || pc.connectionState === "disconnected") {
          if (pc.connectionState === "closed") {
            closePeer(identity);
            publishSnapshot();
          }
        }
      };
      pc.oniceconnectionstatechange = () => {
        logMedia("ice-state", { identity, state: pc.iceConnectionState });
        if (pc.iceConnectionState === "failed") {
          try {
            pc.restartIce();
          } catch {
            /* ignore */
          }
        }
      };
      const localStream = localStreamRef.current;
      if (localStream) {
        localStream.getTracks().forEach((track) => {
          pc.addTrack(track, localStream);
        });
      } else {
        pc.addTransceiver("audio", { direction: "recvonly" });
        pc.addTransceiver("video", { direction: "recvonly" });
      }
      const screenTrack = screenStreamRef.current?.getVideoTracks()[0];
      if (screenTrack) {
        pc.addTrack(screenTrack, screenStreamRef.current);
      }
      peersRef.current.set(identity, peer);
      logMedia("peer-created", { identity, polite: peer.polite });
      return peer;
    },
    [closePeer, publishSnapshot]
  );

  const attachLocalTracks = useCallback((stream) => {
    if (!stream) {
      return;
    }
    peersRef.current.forEach((peer) => {
      stream.getTracks().forEach((track) => {
        const sender = peer.pc.getSenders().find((item) => item.track?.kind === track.kind && item.track?.contentHint !== "detail");
        if (sender) {
          sender.replaceTrack(track);
          return;
        }
        const transceiver = peer.pc.getTransceivers().find((item) => {
          const kind = item.sender.track?.kind || item.receiver.track?.kind;
          return kind === track.kind && item.sender.track?.contentHint !== "detail";
        });
        if (transceiver) {
          transceiver.direction = "sendrecv";
          transceiver.sender.replaceTrack(track);
        } else {
          peer.pc.addTrack(track, stream);
        }
      });
    });
  }, []);

  const processSignal = useCallback(
    async (event) => {
      if (!event || event.type !== "signal" || leavingRef.current) {
        return;
      }
      if (event.action === "media-peers") {
        const peers = Array.isArray(event.peers) ? event.peers : [];
        logMedia("media-peers", { count: peers.length });
        for (const item of peers) {
          if (!item?.user_id || item.user_id === localUserRef.current?.id) {
            continue;
          }
          const existing = peersRef.current.get(item.user_id);
          if (existing && ["failed", "closed", "disconnected"].includes(existing.pc.connectionState)) {
            closePeer(item.user_id);
          }
          ensurePeer(item.user_id, item.display_name);
        }
        publishSnapshot();
        return;
      }
      const fromUser = event.from_user;
      if (!fromUser || fromUser === localUserRef.current?.id) {
        return;
      }
      if (event.action === "join-media") {
        const existing = peersRef.current.get(fromUser);
        if (existing && ["failed", "closed", "disconnected"].includes(existing.pc.connectionState)) {
          closePeer(fromUser);
        }
        ensurePeer(fromUser, event.display_name);
        publishSnapshot();
        return;
      }
      if (event.action === "leave-media") {
        closePeer(fromUser);
        publishSnapshot();
        return;
      }
      if (event.action === "screen-start" || event.action === "screen-stop") {
        const peer = peersRef.current.get(fromUser);
        if (peer) {
          peer.screenOn = event.action === "screen-start";
          if (event.action === "screen-stop") {
            peer.screenStream = null;
          }
          if (event.display_name) {
            peer.name = event.display_name;
          }
          publishSnapshot();
        }
        return;
      }
      if (event.action === "media-state") {
        const peer = peersRef.current.get(fromUser);
        if (peer) {
          peer.cameraOn = Boolean(event.state?.cameraOn);
          peer.micOn = Boolean(event.state?.micOn);
          if (event.state?.screenOn != null) {
            peer.screenOn = Boolean(event.state.screenOn);
          }
          if (event.display_name) {
            peer.name = event.display_name;
          }
          publishSnapshot();
        }
        return;
      }
      const peer = ensurePeer(fromUser, event.display_name);
      if (event.action === "offer" && event.data) {
        const ignore = shouldIgnoreOffer({
          polite: peer.polite,
          makingOffer: peer.makingOffer,
          signalingState: peer.pc.signalingState,
        });
        peer.ignoreOffer = ignore;
        if (ignore) {
          logMedia("offer-ignored", { from: fromUser, state: peer.pc.signalingState });
          return;
        }
        const collision = peer.makingOffer || peer.pc.signalingState !== "stable";
        if (collision && peer.polite) {
          try {
            await peer.pc.setLocalDescription({ type: "rollback" });
          } catch (err) {
            logMedia("rollback-error", { from: fromUser, message: err?.message });
          }
        }
        await peer.pc.setRemoteDescription(new RTCSessionDescription(event.data));
        await flushIce(peer);
        const answer = await peer.pc.createAnswer();
        await peer.pc.setLocalDescription(answer);
        logMedia("answer", { to: fromUser });
        sendRef.current?.({
          type: "signal",
          action: "answer",
          to_user: fromUser,
          data: peer.pc.localDescription,
        });
      } else if (event.action === "answer" && event.data) {
        if (peer.pc.signalingState === "have-local-offer") {
          await peer.pc.setRemoteDescription(new RTCSessionDescription(event.data));
          await flushIce(peer);
        } else {
          logMedia("answer-skipped", { from: fromUser, state: peer.pc.signalingState });
        }
      } else if (event.action === "ice" && event.data) {
        if (!peer.pc.remoteDescription) {
          peer.pendingIce.push(event.data);
        } else {
          try {
            await peer.pc.addIceCandidate(new RTCIceCandidate(event.data));
          } catch (err) {
            if (!peer.ignoreOffer) {
              logMedia("ice-error", { from: fromUser, message: err?.message });
            }
          }
        }
      }
      publishSnapshot();
    },
    [closePeer, ensurePeer, flushIce, publishSnapshot]
  );

  const handleSignal = useCallback(
    (event) => {
      if (!event || event.type !== "signal" || leavingRef.current || !enabledRef.current) {
        return Promise.resolve();
      }
      const queued = signalChainRef.current.then(() => processSignal(event)).catch((err) => {
        logMedia("signal-error", { action: event.action, message: err?.message });
        setError(permissionMessage(err));
      });
      signalChainRef.current = queued;
      return queued;
    },
    [processSignal]
  );

  handleSignalRef.current = handleSignal;

  useEffect(() => {
    if (incoming) {
      handleSignal(incoming);
    }
  }, [incoming, handleSignal]);

  async function announceMedia() {
    const stream = localStreamRef.current;
    sendRef.current?.({ type: "signal", action: "join-media" });
    sendRef.current?.({
      type: "signal",
      action: "media-state",
      state: {
        cameraOn: Boolean(stream?.getVideoTracks()[0]?.enabled),
        micOn: Boolean(stream?.getAudioTracks()[0]?.enabled),
        screenOn: Boolean(screenStreamRef.current),
      },
    });
  }

  useEffect(() => {
    if (!enabled || !roomId || !localUser?.id) {
      setStatus("idle");
      setError("");
      setParticipants([]);
      return undefined;
    }

    let cancelled = false;
    const session = sessionRef.current + 1;
    sessionRef.current = session;
    leavingRef.current = false;
    setStatus("connecting");
    logMedia("connect", { roomId, userId: localUser.id });

    async function connect() {
      let stream = null;
      let mediaError = "";
      const choice = selectedRef.current;
      try {
        const constraints = {
          audio: choice.micId ? { deviceId: { exact: choice.micId } } : true,
          video: choice.cameraId ? { deviceId: { exact: choice.cameraId } } : true,
        };
        try {
          stream = await requestUserMedia(constraints);
        } catch (err) {
          try {
            stream = await requestUserMedia({ audio: true, video: false });
            mediaError = permissionMessage(err);
          } catch (audioErr) {
            mediaError = permissionMessage(audioErr);
          }
        }
        if (cancelled || leavingRef.current || sessionRef.current !== session) {
          stopStream(stream);
          return;
        }
        if (stream) {
          stream.getVideoTracks().forEach(markCameraTrack);
          localStreamRef.current = stream;
          attachLocalTracks(stream);
          logMedia("local-tracks", {
            audio: Boolean(stream.getAudioTracks()[0]),
            video: Boolean(stream.getVideoTracks()[0]),
          });
        }
        const queued = pendingRef.current.splice(0);
        for (const item of queued) {
          await handleSignalRef.current?.(item);
        }
        await announceMedia();
        if (mediaError) {
          setError(mediaError);
        }
        setStatus("connected");
        publishSnapshot();
        setDevices(await listDevices());
      } catch (err) {
        if (!cancelled && !leavingRef.current && sessionRef.current === session) {
          setError(permissionMessage(err));
          await announceMedia();
          setStatus("connected");
          publishSnapshot();
        }
      }
    }

    connect();
    return () => {
      cancelled = true;
      queueMicrotask(() => {
        if (sessionRef.current !== session) {
          return;
        }
        leavingRef.current = true;
        sendRef.current?.({ type: "signal", action: "leave-media" });
        closeAll();
        setParticipants([]);
        setStatus("disconnected");
      });
    };
  }, [enabled, roomId, localUser?.id, attachLocalTracks, closeAll, publishSnapshot]);

  async function replaceLocalTrack(kind, deviceId) {
    const stream = localStreamRef.current;
    if (!stream || !navigator.mediaDevices?.getUserMedia) {
      return;
    }
    const constraints =
      kind === "video"
        ? { video: deviceId ? { deviceId: { exact: deviceId } } : true, audio: false }
        : { audio: deviceId ? { deviceId: { exact: deviceId } } : true, video: false };
    const next = await requestUserMedia(constraints);
    const track = kind === "video" ? next.getVideoTracks()[0] : next.getAudioTracks()[0];
    if (!track) {
      stopStream(next);
      return;
    }
    if (kind === "video") {
      markCameraTrack(track);
    }
    const previous = kind === "video" ? stream.getVideoTracks()[0] : stream.getAudioTracks()[0];
    if (previous) {
      stream.removeTrack(previous);
      previous.stop();
    }
    stream.addTrack(track);
    peersRef.current.forEach((peer) => {
      const sender = peer.pc.getSenders().find((item) => item.track?.kind === kind && item.track?.contentHint !== "detail");
      if (sender) {
        sender.replaceTrack(track);
      } else {
        peer.pc.addTrack(track, stream);
      }
    });
    stopStream(new MediaStream(next.getTracks().filter((item) => item.id !== track.id)));
    publishSnapshot();
    await announceMedia();
  }

  async function toggleMic() {
    const track = localStreamRef.current?.getAudioTracks()[0];
    if (!track) {
      return;
    }
    track.enabled = !track.enabled;
    setMicOn(track.enabled);
    logMedia("mic", { enabled: track.enabled });
    sendRef.current?.({
      type: "signal",
      action: "media-state",
      state: {
        cameraOn: Boolean(localStreamRef.current?.getVideoTracks()[0]?.enabled),
        micOn: track.enabled,
      },
    });
    publishSnapshot();
  }

  async function toggleCam() {
    const track = localStreamRef.current?.getVideoTracks()[0];
    if (!track) {
      return;
    }
    track.enabled = !track.enabled;
    setCamOn(track.enabled);
    logMedia("camera", { enabled: track.enabled });
    sendRef.current?.({
      type: "signal",
      action: "media-state",
      state: {
        cameraOn: track.enabled,
        micOn: Boolean(localStreamRef.current?.getAudioTracks()[0]?.enabled),
      },
    });
    publishSnapshot();
  }

  async function switchDevice(kind, deviceId) {
    if (!deviceId) {
      return;
    }
    setSelected((current) => ({
      ...current,
      cameraId: kind === "videoinput" ? deviceId : current.cameraId,
      micId: kind === "audioinput" ? deviceId : current.micId,
      speakerId: kind === "audiooutput" ? deviceId : current.speakerId,
    }));
    if (kind === "audiooutput") {
      return;
    }
    try {
      await replaceLocalTrack(kind === "videoinput" ? "video" : "audio", deviceId);
    } catch (err) {
      setError(permissionMessage(err));
    }
  }

  async function reconnect() {
    setError("");
    leavingRef.current = false;
    sendRef.current?.({ type: "signal", action: "leave-media" });
    peersRef.current.forEach((peer) => {
      try {
        peer.pc.close();
      } catch {
        /* ignore */
      }
    });
    peersRef.current.clear();
    setStatus("connecting");
    stopStream(localStreamRef.current);
    localStreamRef.current = null;
    const screen = screenStreamRef.current;
    let stream = null;
    let mediaError = "";
    const choice = selectedRef.current;
    try {
      stream = await requestUserMedia({
        audio: choice.micId ? { deviceId: { exact: choice.micId } } : true,
        video: choice.cameraId ? { deviceId: { exact: choice.cameraId } } : true,
      });
      stream.getVideoTracks().forEach(markCameraTrack);
    } catch (err) {
      try {
        stream = await requestUserMedia({ audio: true, video: false });
        mediaError = permissionMessage(err);
      } catch (audioErr) {
        mediaError = permissionMessage(audioErr);
      }
    }
    if (stream) {
      localStreamRef.current = stream;
    }
    if (screen) {
      screenStreamRef.current = screen;
    }
    await announceMedia();
    if (mediaError) {
      setError(mediaError);
    }
    setStatus("connected");
    publishSnapshot();
  }

  async function stopScreenShare(notify = true) {
    const screenStream = screenStreamRef.current;
    if (!screenStream) {
      setScreenOn(false);
      return;
    }
    const screenTrack = screenStream.getVideoTracks()[0];
    peersRef.current.forEach((peer) => {
      peer.pc.getSenders().forEach((sender) => {
        if (sender.track && sender.track.id === screenTrack?.id) {
          try {
            peer.pc.removeTrack(sender);
          } catch {
            sender.replaceTrack(null);
          }
        }
      });
    });
    stopStream(screenStream);
    screenStreamRef.current = null;
    setScreenOn(false);
    if (notify && !leavingRef.current) {
      sendRef.current?.({ type: "signal", action: "screen-stop" });
    }
    publishSnapshot();
  }

  async function toggleScreen() {
    if (screenStreamRef.current) {
      await stopScreenShare();
      return;
    }
    if (!window.isSecureContext && !["localhost", "127.0.0.1"].includes(window.location.hostname)) {
      setError("يلزم HTTPS أو localhost لمشاركة الشاشة.");
      return;
    }
    if (!navigator.mediaDevices?.getDisplayMedia) {
      setError("هذا المتصفح لا يدعم مشاركة الشاشة.");
      return;
    }
    try {
      const screenStream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: false,
      });
      const screenTrack = screenStream.getVideoTracks()[0];
      if (!screenTrack) {
        stopStream(screenStream);
        return;
      }
      markScreenTrack(screenTrack);
      screenStreamRef.current = screenStream;
      setScreenOn(true);
      peersRef.current.forEach((peer) => {
        peer.pc.addTrack(screenTrack, screenStream);
      });
      screenTrack.onended = () => {
        stopScreenShare();
      };
      sendRef.current?.({ type: "signal", action: "screen-start" });
      publishSnapshot();
    } catch (err) {
      const message = screenShareError(err);
      if (message) {
        setError(message);
      }
    }
  }

  async function leave() {
    leavingRef.current = true;
    sendRef.current?.({ type: "signal", action: "leave-media" });
    await stopScreenShare(false);
    closeAll();
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
    handleSignal,
  };
}
