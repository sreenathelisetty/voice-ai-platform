import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export type ConnectionStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "ready"
  | "error"
  | "failed";

export interface TranscriptEntry {
  id: string;
  role: "user" | "assistant";
  text: string;
  timestamp: number;
}

interface SessionState {
  sessionId: string | null;
  status: ConnectionStatus;
  isConnected: boolean;
  transcript: TranscriptEntry[];
}

const initialState: SessionState = {
  sessionId: null,
  status: "idle",
  isConnected: false,
  transcript: [],
};

export const sessionSlice = createSlice({
  name: "session",
  initialState,
  reducers: {
    setSessionId(state, action: PayloadAction<string>) {
      state.sessionId = action.payload;
    },
    setStatus(state, action: PayloadAction<ConnectionStatus>) {
      state.status = action.payload;
    },
    setConnected(state, action: PayloadAction<boolean>) {
      state.isConnected = action.payload;
    },
    addTranscript(state, action: PayloadAction<Omit<TranscriptEntry, "id">>) {
      state.transcript.push({
        ...action.payload,
        id: `${Date.now()}-${Math.random()}`,
      });
    },
    clearTranscript(state) {
      state.transcript = [];
    },
  },
});

export const { setSessionId, setStatus, setConnected, addTranscript, clearTranscript } =
  sessionSlice.actions;

export default sessionSlice.reducer;
