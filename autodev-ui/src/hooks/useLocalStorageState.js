import { useEffect, useRef, useState } from "react";

const memoryFallback = new Map();

function readStorage(key, fallback) {
  try {
    const raw = window.localStorage.getItem(key);
    return raw !== null ? JSON.parse(raw) : fallback;
  } catch {
    // localStorage can throw in private-browsing modes / when disabled,
    // and JSON.parse can throw on corrupted data — never let persistence
    // bugs take down the app, just fall back to in-memory-only state.
    return memoryFallback.has(key) ? memoryFallback.get(key) : fallback;
  }
}

function writeStorage(key, value) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    memoryFallback.set(key, value);
  }
}

/**
 * Drop-in replacement for useState that persists to localStorage under `key`.
 * Value is hydrated synchronously on first render (no flash of empty state)
 * and written back on every change.
 */
export function useLocalStorageState(key, initialValue) {
  const [state, setState] = useState(() => readStorage(key, initialValue));
  const keyRef = useRef(key);

  useEffect(() => {
    keyRef.current = key;
  }, [key]);

  useEffect(() => {
    writeStorage(keyRef.current, state);
  }, [state]);

  return [state, setState];
}
