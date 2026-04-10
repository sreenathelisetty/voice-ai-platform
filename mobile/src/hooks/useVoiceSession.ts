/**
 * Top-level hook managing the full voice session lifecycle:
 * WebSocket connection, audio capture → stream, receive audio → playback.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useDispatch } from "react-redux";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { WS } from "../utils/constants";
import { setStatus, addTranscript, setConnected } from "../store/sessionSlice";

const SESSION_ID_KEY = "@voice_session_id";
const BACKEND_WS_URL = process.env.EXPO_PUBLIC_BACKEND_WS_URL ?? "ws://localhost:8000";
const API_TOKEN = process.env.EXPO_PUBLIC_API_TOKEN ?? "dev-token";

export function useVoiceSession() {
  const dispatch = useDispatch();
  const wsRef = useRef<WebSocket | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const reconnectAttempts = useRef(0);
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [isListening, setIsListening] = useState(false);

  // ── Session ID persistence ──────────────────────────────────────────────────

  const getOrCreateSessionId = useCallback(async (): Promise<string> => {
    const stored = await AsyncStorage.getItem(SESSION_ID_KEY);
    if (stored) return stored;
    const newId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    await AsyncStorage.setItem(SESSION_ID_KEY, newId);
    return newId;
  }, []);

  // ── WebSocket connection ────────────────────────────────────────────────────

  const connect = useCallback(async () => {
    const sessionId = await getOrCreateSessionId();
    sessionIdRef.current = sessionId;

    const url = `${BACKEND_WS_URL}/ws/${sessionId}?token=${API_TOKEN}`;
    const ws = new WebSocket(url);
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;
    dispatch(setStatus("connecting"));

    ws.onopen = () => {
      reconnectAttempts.current = 0;
      dispatch(setConnected(true));
      dispatch(setStatus("connected"));
      // Heartbeat
      heartbeatRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send("ping");
      }, WS.HEARTBEAT_INTERVAL_MS);
    };

    ws.onmessage = (event) => {
      if (typeof event.data === "string") {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "session_ready") {
            dispatch(setStatus("ready"));
          }
        } catch {}
        return;
      }
      // Binary audio frame — enqueue for playback
      const frame = event.data as ArrayBuffer;
      // TODO: pipe to useAudioPlayback hook via event emitter or ref
    };

    ws.onerror = (e) => dispatch(setStatus("error"));
    ws.onclose = () => {
      dispatch(setConnected(false));
      if (heartbeatRef.current) clearInterval(heartbeatRef.current);
      scheduleReconnect();
    };
  }, [dispatch, getOrCreateSessionId]);

  const scheduleReconnect = useCallback(() => {
    if (reconnectAttempts.current >= WS.RECONNECT_MAX_ATTEMPTS) {
      dispatch(setStatus("failed"));
      return;
    }
    const delay = Math.min(
      WS.RECONNECT_BASE_DELAY_MS * 2 ** reconnectAttempts.current,
      WS.RECONNECT_MAX_DELAY_MS
    );
    reconnectAttempts.current += 1;
    setTimeout(connect, delay);
  }, [connect, dispatch]);

  // ── Audio sending ──────────────────────────────────────────────────────────

  const sendAudioChunk = useCallback((chunk: ArrayBuffer) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(chunk);
    }
  }, []);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (heartbeatRef.current) clearInterval(heartbeatRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { isListening, setIsListening, sendAudioChunk, disconnect };
}
