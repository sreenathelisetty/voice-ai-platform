import React from "react";
import { SafeAreaView, ScrollView, StyleSheet, Text, View } from "react-native";
import { useSelector } from "react-redux";
import { VoiceButton } from "../components/VoiceButton";
import { TranscriptView } from "../components/TranscriptView";
import { StatusBanner } from "../components/StatusBanner";
import { useVoiceSession } from "../hooks/useVoiceSession";
import type { RootState } from "../store/store";

export function HomeScreen() {
  const { isListening, setIsListening, sendAudioChunk } = useVoiceSession();
  const status = useSelector((s: RootState) => s.session.status);

  return (
    <SafeAreaView style={styles.container}>
      <StatusBanner status={status} />
      <View style={styles.main}>
        <TranscriptView />
      </View>
      <View style={styles.footer}>
        <VoiceButton
          isListening={isListening}
          onPressIn={() => setIsListening(true)}
          onPressOut={() => setIsListening(false)}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f0f0f" },
  main: { flex: 1, paddingHorizontal: 16 },
  footer: { alignItems: "center", paddingBottom: 48, paddingTop: 16 },
});
