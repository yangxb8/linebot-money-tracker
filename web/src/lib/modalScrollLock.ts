let lockCount = 0;
let lockedScrollY = 0;

type SavedStyles = {
  htmlOverflow: string;
  bodyPosition: string;
  bodyTop: string;
  bodyLeft: string;
  bodyRight: string;
  bodyWidth: string;
  bodyOverflow: string;
};

let savedStyles: SavedStyles | null = null;

export function lockModalScroll() {
  lockCount += 1;
  if (lockCount > 1) return;

  const html = document.documentElement;
  const body = document.body;

  lockedScrollY = window.scrollY;

  savedStyles = {
    htmlOverflow: html.style.overflow,
    bodyPosition: body.style.position,
    bodyTop: body.style.top,
    bodyLeft: body.style.left,
    bodyRight: body.style.right,
    bodyWidth: body.style.width,
    bodyOverflow: body.style.overflow,
  };

  html.style.overflow = "hidden";
  body.style.position = "fixed";
  body.style.top = `-${lockedScrollY}px`;
  body.style.left = "0";
  body.style.right = "0";
  body.style.width = "100%";
  body.style.overflow = "hidden";
}

export function unlockModalScroll() {
  if (lockCount === 0) return;
  lockCount -= 1;
  if (lockCount > 0) return;

  const html = document.documentElement;
  const body = document.body;
  const styles = savedStyles;
  const scrollY = lockedScrollY;

  if (styles) {
    html.style.overflow = styles.htmlOverflow;
    body.style.position = styles.bodyPosition;
    body.style.top = styles.bodyTop;
    body.style.left = styles.bodyLeft;
    body.style.right = styles.bodyRight;
    body.style.width = styles.bodyWidth;
    body.style.overflow = styles.bodyOverflow;
  }

  savedStyles = null;
  window.scrollTo(0, scrollY);
}
