import { strict as assert } from "node:assert";
import { test } from "node:test";
import {
  isPolitePeer,
  isScreenVideoTrack,
  shouldIgnoreOffer,
  uniqueParticipants,
} from "./webrtcMesh.js";

test("perfect negotiation: only the impolite peer ignores a colliding offer", () => {
  assert.equal(isPolitePeer("a", "b"), true);
  assert.equal(isPolitePeer("b", "a"), false);
  assert.equal(
    shouldIgnoreOffer({ polite: false, makingOffer: true, signalingState: "have-local-offer" }),
    true
  );
  assert.equal(
    shouldIgnoreOffer({ polite: true, makingOffer: true, signalingState: "have-local-offer" }),
    false
  );
  assert.equal(shouldIgnoreOffer({ polite: false, makingOffer: false, signalingState: "stable" }), false);
});

test("screen tracks stay separate from camera tracks", () => {
  assert.equal(isScreenVideoTrack({ kind: "audio" }), false);
  assert.equal(isScreenVideoTrack({ kind: "video", contentHint: "detail" }), true);
  assert.equal(isScreenVideoTrack({ kind: "video", contentHint: "motion" }), false);
  assert.equal(
    isScreenVideoTrack(
      { kind: "video", getSettings: () => ({ displaySurface: "monitor" }) },
      { hasLiveCameraTrack: false }
    ),
    true
  );
  assert.equal(
    isScreenVideoTrack({ kind: "video" }, { hasLiveCameraTrack: true, cameraStreamId: "cam", eventStreamId: "screen" }),
    true
  );
});

test("participant tiles never duplicate the same identity", () => {
  const people = uniqueParticipants([
    { identity: "u1", name: "أ" },
    { identity: "u1", name: "أ" },
    { identity: "u1-screen", name: "أ — شاشة" },
    { identity: "u2", name: "ب" },
    { identity: "", name: "فارغ" },
  ]);
  assert.deepEqual(
    people.map((item) => item.identity),
    ["u1", "u1-screen", "u2"]
  );
});
