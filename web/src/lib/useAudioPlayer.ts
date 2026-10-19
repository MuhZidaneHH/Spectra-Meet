"use client";

import { useCallback, useRef, useState, type SyntheticEvent } from "react";

export const PLAYBACK_RATES = [1, 1.5, 2];

/** Mengendalikan satu elemen <audio>. Pasang `audioProps` ke elemennya. */
export function useAudioPlayer(src: string, fallbackDuration: number) {
  const ref = useRef<HTMLAudioElement>(null);
  const [current, setCurrent] = useState(0);
  const [mediaDuration, setMediaDuration] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [rate, setRate] = useState(1);
  const [failed, setFailed] = useState(false);

  // Rekaman webm dari mikrofon sering tak punya durasi di header; pakai durasi cadangan.
  const duration = mediaDuration > 0 ? mediaDuration : fallbackDuration;

  const seek = useCallback(
    (seconds: number) => {
      const audio = ref.current;
      if (!audio) return;
      audio.currentTime = Math.max(0, duration > 0 ? Math.min(seconds, duration) : seconds);
      setCurrent(audio.currentTime);
    },
    [duration],
  );

  const play = useCallback(() => {
    ref.current?.play().catch((e: unknown) => {
      // Diblokir kebijakan autoplay atau dibatalkan pemuatan baru: bukan kerusakan audio.
      const name = e instanceof DOMException ? e.name : "";
      if (name !== "NotAllowedError" && name !== "AbortError") setFailed(true);
    });
  }, []);

  const toggle = useCallback(() => {
    const audio = ref.current;
    if (!audio) return;
    if (audio.paused) play();
    else audio.pause();
  }, [play]);

  const cycleRate = useCallback(() => {
    setRate((r) => {
      const next = PLAYBACK_RATES[(PLAYBACK_RATES.indexOf(r) + 1) % PLAYBACK_RATES.length];
      if (ref.current) ref.current.playbackRate = next;
      return next;
    });
  }, []);

  const onMetadata = (e: SyntheticEvent<HTMLAudioElement>) => {
    const audio = e.currentTarget;
    if (audio.duration === Infinity) {
      // Rekaman webm dari MediaRecorder tak punya durasi di header. Loncat ke ujung
      // memaksa browser menghitungnya (durationchange menyusul), lalu kembali ke awal.
      const back = () => {
        audio.removeEventListener("timeupdate", back);
        audio.currentTime = 0;
      };
      audio.addEventListener("timeupdate", back);
      audio.currentTime = 1e101;
      return;
    }
    if (Number.isFinite(audio.duration)) setMediaDuration(audio.duration);
  };

  const audioProps = {
    ref,
    src,
    preload: "metadata" as const,
    onTimeUpdate: (e: SyntheticEvent<HTMLAudioElement>) => setCurrent(e.currentTarget.currentTime),
    onLoadedMetadata: onMetadata,
    onDurationChange: onMetadata,
    onPlay: () => setPlaying(true),
    onPause: () => setPlaying(false),
    onEnded: () => setPlaying(false),
    onError: () => setFailed(true),
  };

  return { audioProps, current, duration, playing, rate, failed, seek, play, toggle, cycleRate };
}

export type AudioPlayerState = ReturnType<typeof useAudioPlayer>;
