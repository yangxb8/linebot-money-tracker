"use client";

import { useCallback, useRef, useState } from "react";

const LONG_PRESS_MS = 450;
const MOVE_THRESHOLD_PX = 10;

type Position = { x: number; y: number };

type Options = {
  enabled: boolean;
  onTap: () => void;
  onDragStart: () => void;
  onDragMove: (position: Position) => void;
  onDragEnd: (position: Position) => void;
};

export function useLongPressDrag({
  enabled,
  onTap,
  onDragStart,
  onDragMove,
  onDragEnd,
}: Options) {
  const [isDragging, setIsDragging] = useState(false);
  const timerRef = useRef<number | null>(null);
  const startRef = useRef<Position | null>(null);
  const draggingRef = useRef(false);
  const activeRef = useRef(false);
  const callbacksRef = useRef({ onTap, onDragStart, onDragMove, onDragEnd });
  callbacksRef.current = { onTap, onDragStart, onDragMove, onDragEnd };

  const cleanupDocumentListeners = useRef<(() => void) | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const endInteraction = useCallback(() => {
    clearTimer();
    activeRef.current = false;
    cleanupDocumentListeners.current?.();
    cleanupDocumentListeners.current = null;
    startRef.current = null;
  }, [clearTimer]);

  const attachDocumentListeners = useCallback(() => {
    function onMove(event: PointerEvent) {
      const start = startRef.current;
      if (!start) return;

      if (!draggingRef.current) {
        if (Math.hypot(event.clientX - start.x, event.clientY - start.y) > MOVE_THRESHOLD_PX) {
          clearTimer();
        }
        return;
      }

      callbacksRef.current.onDragMove({ x: event.clientX, y: event.clientY });
    }

    function onUp(event: PointerEvent) {
      if (draggingRef.current) {
        draggingRef.current = false;
        setIsDragging(false);
        callbacksRef.current.onDragEnd({ x: event.clientX, y: event.clientY });
        endInteraction();
        return;
      }

      const start = startRef.current;
      const wasTap =
        start &&
        Math.hypot(event.clientX - start.x, event.clientY - start.y) < MOVE_THRESHOLD_PX;
      endInteraction();
      if (wasTap) {
        callbacksRef.current.onTap();
      }
    }

    function onCancel() {
      if (draggingRef.current) {
        draggingRef.current = false;
        setIsDragging(false);
      }
      endInteraction();
    }

    document.addEventListener("pointermove", onMove, { passive: true });
    document.addEventListener("pointerup", onUp);
    document.addEventListener("pointercancel", onCancel);
    cleanupDocumentListeners.current = () => {
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", onUp);
      document.removeEventListener("pointercancel", onCancel);
    };
  }, [clearTimer, endInteraction]);

  const onPointerDown = useCallback(
    (event: React.PointerEvent) => {
      if (!enabled || event.button !== 0 || activeRef.current) return;
      activeRef.current = true;
      draggingRef.current = false;
      startRef.current = { x: event.clientX, y: event.clientY };
      attachDocumentListeners();
      clearTimer();
      timerRef.current = window.setTimeout(() => {
        draggingRef.current = true;
        setIsDragging(true);
        callbacksRef.current.onDragStart();
        if (navigator.vibrate) {
          navigator.vibrate(10);
        }
      }, LONG_PRESS_MS);
    },
    [attachDocumentListeners, clearTimer, enabled],
  );

  return {
    isDragging,
    dragHandlers: { onPointerDown },
  };
}

export function findDropZone(
  position: Position,
): { type: "promote" } | { type: "l1"; id: string } | null {
  const element = document.elementFromPoint(position.x, position.y);
  if (!element) return null;
  const zone = element.closest("[data-drop-zone]") as HTMLElement | null;
  if (!zone) return null;
  const value = zone.dataset.dropZone;
  if (!value) return null;
  if (value === "promote") return { type: "promote" };
  if (value.startsWith("l1:")) {
    return { type: "l1", id: value.slice(3) };
  }
  return null;
}
