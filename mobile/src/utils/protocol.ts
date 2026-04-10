/**
 * Binary frame header: [version(1), type(1), session_hash(4), payload_len(2)]
 * Total: 8 bytes
 */

import { FRAME } from "./constants";

export function encodeFrame(type: number, sessionHash: number, payload: Uint8Array): ArrayBuffer {
  const buf = new ArrayBuffer(FRAME.HEADER_BYTES + payload.byteLength);
  const view = new DataView(buf);
  view.setUint8(0, FRAME.VERSION);
  view.setUint8(1, type);
  view.setUint32(2, sessionHash, false); // big-endian
  view.setUint16(6, payload.byteLength, false);
  new Uint8Array(buf, FRAME.HEADER_BYTES).set(payload);
  return buf;
}

export function decodeFrame(buf: ArrayBuffer): {
  version: number;
  type: number;
  sessionHash: number;
  payload: Uint8Array;
} {
  const view = new DataView(buf);
  return {
    version: view.getUint8(0),
    type: view.getUint8(1),
    sessionHash: view.getUint32(2, false),
    payload: new Uint8Array(buf, FRAME.HEADER_BYTES),
  };
}

/** Simple djb2-style hash of a session ID string → uint32 */
export function hashSessionId(sessionId: string): number {
  let hash = 5381;
  for (let i = 0; i < sessionId.length; i++) {
    hash = ((hash << 5) + hash + sessionId.charCodeAt(i)) >>> 0;
  }
  return hash;
}
