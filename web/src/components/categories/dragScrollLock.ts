let lockCount = 0;
let lockedScrollY = 0;
let lockedMaxScroll = 0;

type SavedStyles = {
  htmlOverflow: string;
  htmlTouchAction: string;
  bodyPosition: string;
  bodyTop: string;
  bodyLeft: string;
  bodyRight: string;
  bodyWidth: string;
  bodyOverflow: string;
  bodyTouchAction: string;
};

let savedStyles: SavedStyles | null = null;

export function isDragScrollLocked() {
  return lockCount > 0;
}

export function lockDragScroll() {
  lockCount += 1;
  if (lockCount > 1) return;

  const html = document.documentElement;
  const body = document.body;

  lockedScrollY = window.scrollY;
  lockedMaxScroll = Math.max(
    0,
    document.documentElement.scrollHeight - window.innerHeight,
  );

  savedStyles = {
    htmlOverflow: html.style.overflow,
    htmlTouchAction: html.style.touchAction,
    bodyPosition: body.style.position,
    bodyTop: body.style.top,
    bodyLeft: body.style.left,
    bodyRight: body.style.right,
    bodyWidth: body.style.width,
    bodyOverflow: body.style.overflow,
    bodyTouchAction: body.style.touchAction,
  };

  html.style.overflow = "hidden";
  html.style.touchAction = "none";
  body.style.position = "fixed";
  body.style.top = `-${lockedScrollY}px`;
  body.style.left = "0";
  body.style.right = "0";
  body.style.width = "100%";
  body.style.overflow = "hidden";
  body.style.touchAction = "none";
}

export function scrollDragLocked(deltaY: number) {
  if (lockCount === 0) {
    window.scrollBy(0, deltaY);
    return;
  }

  lockedScrollY = Math.max(0, Math.min(lockedMaxScroll, lockedScrollY + deltaY));
  document.body.style.top = `-${lockedScrollY}px`;
}

export function unlockDragScroll() {
  if (lockCount === 0) return;
  lockCount -= 1;
  if (lockCount > 0) return;

  const html = document.documentElement;
  const body = document.body;
  const styles = savedStyles;
  const scrollY = lockedScrollY;

  if (styles) {
    html.style.overflow = styles.htmlOverflow;
    html.style.touchAction = styles.htmlTouchAction;
    body.style.position = styles.bodyPosition;
    body.style.top = styles.bodyTop;
    body.style.left = styles.bodyLeft;
    body.style.right = styles.bodyRight;
    body.style.width = styles.bodyWidth;
    body.style.overflow = styles.bodyOverflow;
    body.style.touchAction = styles.bodyTouchAction;
  }

  savedStyles = null;
  lockedMaxScroll = 0;
  window.scrollTo(0, scrollY);
}
