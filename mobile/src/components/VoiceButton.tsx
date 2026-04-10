import React, { useEffect, useRef } from "react";
import { Animated, Pressable, StyleSheet, Text } from "react-native";

interface Props {
  isListening: boolean;
  onPressIn: () => void;
  onPressOut: () => void;
}

export function VoiceButton({ isListening, onPressIn, onPressOut }: Props) {
  const scale = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    Animated.spring(scale, {
      toValue: isListening ? 1.2 : 1,
      useNativeDriver: true,
    }).start();
  }, [isListening]);

  return (
    <Pressable onPressIn={onPressIn} onPressOut={onPressOut}>
      <Animated.View style={[styles.button, { transform: [{ scale }] }, isListening && styles.active]}>
        <Text style={styles.icon}>{isListening ? "🎙" : "🎤"}</Text>
      </Animated.View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    width: 80, height: 80, borderRadius: 40,
    backgroundColor: "#1e1e1e",
    justifyContent: "center", alignItems: "center",
    borderWidth: 2, borderColor: "#444",
  },
  active: { borderColor: "#ef4444", backgroundColor: "#2d1515" },
  icon: { fontSize: 32 },
});
