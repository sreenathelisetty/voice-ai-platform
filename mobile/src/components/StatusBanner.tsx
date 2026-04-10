import React from "react";
import { StyleSheet, Text, View } from "react-native";
import type { ConnectionStatus } from "../store/sessionSlice";

const STATUS_CONFIG: Record<ConnectionStatus, { label: string; color: string }> = {
  idle: { label: "Not connected", color: "#6b7280" },
  connecting: { label: "Connecting…", color: "#f59e0b" },
  connected: { label: "Connected", color: "#10b981" },
  ready: { label: "Ready", color: "#10b981" },
  error: { label: "Connection error", color: "#ef4444" },
  failed: { label: "Failed — restart app", color: "#ef4444" },
};

export function StatusBanner({ status }: { status: ConnectionStatus }) {
  const { label, color } = STATUS_CONFIG[status];
  return (
    <View style={[styles.banner, { backgroundColor: color + "22" }]}>
      <View style={[styles.dot, { backgroundColor: color }]} />
      <Text style={[styles.text, { color }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: { flexDirection: "row", alignItems: "center", paddingHorizontal: 16, paddingVertical: 6 },
  dot: { width: 8, height: 8, borderRadius: 4, marginRight: 8 },
  text: { fontSize: 13, fontWeight: "600" },
});
