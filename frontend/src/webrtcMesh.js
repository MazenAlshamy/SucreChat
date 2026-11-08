export function isPolitePeer(localId, remoteId) {
  return String(localId || "") < String(remoteId || "");
}

export function shouldIgnoreOffer({ polite, makingOffer, signalingState }) {
  const collision = Boolean(makingOffer) || signalingState !== "stable";
  return collision && !polite;
}

export function isScreenVideoTrack(track, meta = {}) {
  if (!track || track.kind !== "video") {
    return false;
  }
  const settings = typeof track.getSettings === "function" ? track.getSettings() : {};
  if (settings.displaySurface) {
    return true;
  }
  if (track.contentHint === "detail") {
    return true;
  }
  if (track.contentHint === "motion") {
    return false;
  }
  if (meta.cameraStreamId && meta.eventStreamId) {
    return meta.eventStreamId !== meta.cameraStreamId;
  }
  return Boolean(meta.hasLiveCameraTrack);
}

export function uniqueParticipants(people) {
  const seen = new Set();
  return (people || []).filter((item) => {
    const key = item?.identity;
    if (!key || seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}
