"use client";

import { useEffect, useRef } from "react";
import { isDragScrollLocked, scrollDragLocked } from "@/components/categories/dragScrollLock";

/** Pointer must be within this band of the viewport edge before scrolling starts. */
const EDGE_ZONE_PX = 56;
const MAX_SCROLL_PX = 14;

export function useDragAutoScroll(
  active: boolean,
  getPosition: () => { x: number; y: number } | null,
  onScroll: () => void,
) {
  const getPositionRef = useRef(getPosition);
  const onScrollRef = useRef(onScroll);
  getPositionRef.current = getPosition;
  onScrollRef.current = onScroll;

  useEffect(() => {
    if (!active) return;

    let rafId = 0;

    function step() {
      const pos = getPositionRef.current();
      if (pos && isDragScrollLocked()) {
        const { innerHeight } = window;
        let delta = 0;

        if (pos.y < EDGE_ZONE_PX) {
          const intensity = 1 - Math.max(0, pos.y) / EDGE_ZONE_PX;
          delta = -MAX_SCROLL_PX * intensity;
        } else if (pos.y > innerHeight - EDGE_ZONE_PX) {
          const distanceFromBottom = innerHeight - pos.y;
          const intensity = 1 - Math.max(0, distanceFromBottom) / EDGE_ZONE_PX;
          delta = MAX_SCROLL_PX * intensity;
        }

        if (delta !== 0) {
          scrollDragLocked(delta);
          onScrollRef.current();
        }
      }

      rafId = requestAnimationFrame(step);
    }

    rafId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(rafId);
  }, [active]);
}
