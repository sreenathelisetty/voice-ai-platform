/** Audio and WebSocket constants shared across the mobile app. */

export const AUDIO = {
  INPUT_SAMPLE_RATE: 16000,
  OUTPUT_SAMPLE_RATE: 24000,
  CHANNELS: 1,
  BIT_DEPTH: 16,
  CHUNK_DURATION_MS: 100,
  /** Bytes per 100ms PCM chunk at 16 kHz, 16-bit, mono */
  CHUNK_BYTES: (16000 * 100) / 1000 * 2, // 3200
} as const;

export const WS = {
  HEARTBEAT_INTERVAL_MS: 15_000,
  RECONNECT_BASE_DELAY_MS: 500,
  RECONNECT_MAX_DELAY_MS: 30_000,
  RECONNECT_MAX_ATTEMPTS: 10,
} as const;

export const FRAME = {
  HEADER_BYTES: 8,
  VERSION: 1,
  TYPE_AUDIO: 0x01,
  TYPE_CONTROL: 0x02,
} as const;
