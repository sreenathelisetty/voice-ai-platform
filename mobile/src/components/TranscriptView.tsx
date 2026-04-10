import React, { useRef, useEffect } from "react";
import { FlatList, StyleSheet, Text, View } from "react-native";
import { useSelector } from "react-redux";
import type { RootState } from "../store/store";

export function TranscriptView() {
  const entries = useSelector((s: RootState) => s.session.transcript);
  const listRef = useRef<FlatList>(null);

  useEffect(() => {
    if (entries.length > 0) listRef.current?.scrollToEnd({ animated: true });
  }, [entries.length]);

  return (
    <FlatList
      ref={listRef}
      data={entries}
      keyExtractor={(item) => item.id}
      renderItem={({ item }) => (
        <View style={[styles.bubble, item.role === "user" ? styles.user : styles.assistant]}>
          <Text style={styles.text}>{item.text}</Text>
        </View>
      )}
      contentContainerStyle={styles.list}
    />
  );
}

const styles = StyleSheet.create({
  list: { paddingVertical: 12 },
  bubble: {
    maxWidth: "80%", marginVertical: 4, padding: 12, borderRadius: 16,
  },
  user: { alignSelf: "flex-end", backgroundColor: "#1d4ed8" },
  assistant: { alignSelf: "flex-start", backgroundColor: "#1e1e1e" },
  text: { color: "#fff", fontSize: 15, lineHeight: 22 },
});
