"use client";

import { useCallback, useRef, useState } from "react";
import {
  lockDragScroll,
  scrollDragLocked,
  unlockDragScroll,
} from "@/components/categories/dragScrollLock";

const LONG_PRESS_MS = 450;
const MOVE_THRESHOLD_PX = 10;
const EDGE_ZONE_PX = 72;
const MAX_SCROLL_PX = 16;

type Position = { x: number; y: number };

type Options = {
  enabled: boolean;
  onTap: () => void;
  onDragStart: (position: Position) => void;
  onDragMove: (position: Position) => void;
  onDragEnd: (position: Position) => void;
};

function edgeScrollDelta(y: number): number {
  const { innerHeight } = window;

  if (y < EDGE_ZONE_PX) {
    const intensity = 1 - Math.max(0, y) / EDGE_ZONE_PX;
    return -MAX_SCROLL_PX * intensity;
  }

  if (y > innerHeight - EDGE_ZONE_PX) {
    const distanceFromBottom = innerHeight - y;
    const intensity = 1 - Math.max(0, distanceFromBottom) / EDGE_ZONE_PX;
    return MAX_SCROLL_PX * intensity;
  }

  return 0;
}

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
  const lastPositionRef = useRef<Position | null>(null);
  const draggingRef = useRef(false);
  const activeRef = useRef(false);
  const pointerIdRef = useRef<number | null>(null);
  const targetRef = useRef<HTMLElement | null>(null);
  const scrollLockedRef = useRef(false);
  const autoScrollRafRef = useRef(0);
  const callbacksRef = useRef({ onTap, onDragStart, onDragMove, onDragEnd });
  callbacksRef.current = { onTap, onDragStart, onDragMove, onDragEnd };

  const cleanupDocumentListeners = useRef<(() => void) | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const stopAutoScroll = useCallback(() => {
    if (autoScrollRafRef.current) {
      cancelAnimationFrame(autoScrollRafRef.current);
      autoScrollRafRef.current = 0;
    }
  }, []);

  const tickAutoScroll = useCallback(() => {
    if (!draggingRef.current) {
      autoScrollRafRef.current = 0;
      return;
    }

    const pos = lastPositionRef.current;
    if (pos && scrollLockedRef.current) {
      const delta = edgeScrollDelta(pos.y);
      if (delta !== 0) {
        scrollDragLocked(delta);
        callbacksRef.current.onDragMove(pos);
      }
    }

    autoScrollRafRef.current = requestAnimationFrame(tickAutoScroll);
  }, []);

  const startAutoScroll = useCallback(() => {
    stopAutoScroll();
    autoScrollRafRef.current = requestAnimationFrame(tickAutoScroll);
  }, [stopAutoScroll, tickAutoScroll]);

  const releasePointerCapture = useCallback(() => {
    const target = targetRef.current;
    const pointerId = pointerIdRef.current;
    if (target && pointerId !== null && target.hasPointerCapture(pointerId)) {
      target.releasePointerCapture(pointerId);
    }
  }, []);

  const finishDrag = useCallback(
    (position: Position) => {
      if (!draggingRef.current) return;
      draggingRef.current = false;
      setIsDragging(false);
      releasePointerCapture();
      callbacksRef.current.onDragEnd(position);
    },
    [releasePointerCapture],
  );

  const endInteraction = useCallback(() => {
    clearTimer();
    stopAutoScroll();
    activeRef.current = false;
    cleanupDocumentListeners.current?.();
    cleanupDocumentListeners.current = null;
    releasePointerCapture();
    if (scrollLockedRef.current) {
      unlockDragScroll();
      scrollLockedRef.current = false;
    }
    startRef.current = null;
    lastPositionRef.current = null;
    pointerIdRef.current = null;
    targetRef.current = null;
  }, [clearTimer, releasePointerCapture, stopAutoScroll]);

  const attachDocumentListeners = useCallback(() => {
    function currentPosition(event?: PointerEvent): Position | null {
      if (event) {
        return { x: event.clientX, y: event.clientY };
      }
      return lastPositionRef.current ?? startRef.current;
    }

    function onMove(event: PointerEvent) {
      const start = startRef.current;
      if (!start) return;

      if (!draggingRef.current) {
        if (Math.hypot(event.clientX - start.x, event.clientY - start.y) > MOVE_THRESHOLD_PX) {
          clearTimer();
        }
        return;
      }

      event.preventDefault();
      const position = { x: event.clientX, y: event.clientY };
      lastPositionRef.current = position;
      callbacksRef.current.onDragMove(position);
    }

    function onUp(event: PointerEvent) {
      if (draggingRef.current) {
        const position = currentPosition(event);
        if (position) finishDrag(position);
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

    function onCancel(event: PointerEvent) {
      if (draggingRef.current) {
        const position = currentPosition(event);
        if (position) finishDrag(position);
      }
      endInteraction();
    }

    function onLostCapture(event: PointerEvent) {
      if (!draggingRef.current) return;
      const position = currentPosition(event);
      if (position) finishDrag(position);
      endInteraction();
    }

    function onTouchMove(event: TouchEvent) {
      if (draggingRef.current) {
        event.preventDefault();
      }
    }

    function onWheel(event: WheelEvent) {
      if (draggingRef.current) {
        event.preventDefault();
      }
    }

    document.addEventListener("pointermove", onMove, { passive: false });
    document.addEventListener("pointerup", onUp);
    document.addEventListener("pointercancel", onCancel);
    document.addEventListener("lostpointercapture", onLostCapture);
    document.addEventListener("touchmove", onTouchMove, { passive: false });
    document.addEventListener("wheel", onWheel, { passive: false });

    cleanupDocumentListeners.current = () => {
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", onUp);
      document.removeEventListener("pointercancel", onCancel);
      document.removeEventListener("lostpointercapture", onLostCapture);
      document.removeEventListener("touchmove", onTouchMove);
      document.removeEventListener("wheel", onWheel);
    };
  }, [clearTimer, endInteraction, finishDrag]);

  const onPointerDown = useCallback(
    (event: React.PointerEvent<HTMLElement>) => {
      if (!enabled || event.button !== 0 || activeRef.current) return;

      activeRef.current = true;
      draggingRef.current = false;
      pointerIdRef.current = event.pointerId;
      targetRef.current = event.currentTarget;
      startRef.current = { x: event.clientX, y: event.clientY };
      lastPositionRef.current = startRef.current;
      attachDocumentListeners();
      clearTimer();

      timerRef.current = window.setTimeout(() => {
        draggingRef.current = true;
        setIsDragging(true);

        lockDragScroll();
        scrollLockedRef.current = true;
        startAutoScroll();

        const target = targetRef.current;
        const pointerId = pointerIdRef.current;
        if (target && pointerId !== null) {
          try {
            target.setPointerCapture(pointerId);
          } catch {
            // Ignore capture failures on unsupported platforms.
          }
        }

        const start = startRef.current;
        if (start) {
          lastPositionRef.current = start;
          callbacksRef.current.onDragStart(start);
          callbacksRef.current.onDragMove(start);
        }

        if (navigator.vibrate) {
          navigator.vibrate(10);
        }
      }, LONG_PRESS_MS);
    },
    [attachDocumentListeners, clearTimer, enabled, startAutoScroll],
  );

  return {
    isDragging,
    dragHandlers: { onPointerDown },
  };
}

export function findDropZone(
  position: Position,
): { type: "promote" } | { type: "l1"; id: string } | null {
  const elements = document.elementsFromPoint(position.x, position.y);
  for (const element of elements) {
    const zone = element.closest("[data-drop-zone]") as HTMLElement | null;
    if (!zone) continue;
    const value = zone.dataset.dropZone;
    if (!value) continue;
    if (value === "promote") return { type: "promote" };
    if (value.startsWith("l1:")) {
      return { type: "l1", id: value.slice(3) };
    }
  }
  return null;
}
