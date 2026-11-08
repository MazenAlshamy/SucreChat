import { useEffect, useRef } from "react";

function initials(name) {
  const parts = (name || "").trim().split(/\s+/).filter(Boolean);
  if (!parts.length) {
    return "?";
  }
  return parts.slice(0, 2).map((part) => part[0]).join("");
}

function bindMedia(element, track, stream, videoOnly) {
  if (!element) {
    return undefined;
  }
  if (track?.attach) {
    track.attach(element);
    return () => {
      track.detach(element);
    };
  }
  const sourceTrack = track || (videoOnly ? stream?.getVideoTracks()[0] : stream?.getAudioTracks()[0]);
  if (sourceTrack) {
    const next = new MediaStream([sourceTrack]);
    if (element.srcObject !== next) {
      element.srcObject = next;
    }
  } else if (stream) {
    if (element.srcObject !== stream) {
      element.srcObject = stream;
    }
  } else {
    element.srcObject = null;
    return undefined;
  }
  element.muted = Boolean(videoOnly);
  if (!videoOnly) {
    element.volume = 1;
  }
  const play = element.play();
  if (play?.catch) {
    play.catch(() => {});
  }
  return undefined;
}

export default function ParticipantTile({ participant }) {
  const videoRef = useRef(null);
  const audioRef = useRef(null);
  const showVideo = Boolean(participant.videoTrack && (participant.cameraOn || participant.screenOn));
  const videoLost = Boolean(participant.videoLost);

  useEffect(() => {
    return bindMedia(videoRef.current, participant.videoTrack, participant.stream, true);
  }, [participant.videoTrack, participant.stream, participant.identity]);

  useEffect(() => {
    if (participant.isLocal || participant.screenOn) {
      return undefined;
    }
    return bindMedia(audioRef.current, participant.audioTrack, participant.stream, false);
  }, [participant.audioTrack, participant.isLocal, participant.screenOn, participant.stream, participant.identity]);

  return (
    <article
      className={`tile ${participant.isLocal ? "local" : ""} ${participant.screenOn ? "screen" : ""} ${participant.speaking ? "speaking" : ""}`}
    >
      <div className="tile-media">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className={showVideo ? "is-visible" : "is-hidden"}
        />
        {!showVideo ? (
          <div className="tile-placeholder">
            {videoLost ? "انقطع الفيديو" : initials(participant.name)}
          </div>
        ) : null}
        {participant.isLocal || participant.screenOn ? null : <audio ref={audioRef} autoPlay playsInline />}
        <div className="tile-badges">
          <span className={`media-badge ${participant.micOn ? "on" : "off"}`}>
            {participant.micOn ? "ميكروفون" : "صامت"}
          </span>
          <span className={`media-badge ${participant.cameraOn ? "on" : "off"}`}>
            {participant.cameraOn ? "كاميرا" : videoLost ? "انقطع الفيديو" : "بدون فيديو"}
          </span>
          {participant.screenOn ? <span className="media-badge on">شاشة</span> : null}
        </div>
      </div>
      <span className="tile-name">
        {participant.name}
        {participant.isLocal ? " (أنت)" : ""}
        {participant.speaking ? " · يتحدث" : ""}
      </span>
    </article>
  );
}
