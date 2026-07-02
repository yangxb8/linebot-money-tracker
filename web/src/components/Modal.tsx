"use client";

import {
  useEffect,
  type FormHTMLAttributes,
  type HTMLAttributes,
  type ReactNode,
} from "react";
import { lockModalScroll, unlockModalScroll } from "@/lib/modalScrollLock";

type ModalProps = {
  open?: boolean;
  onClose: () => void;
  children: ReactNode;
  panelClassName?: string;
  /** Use split layout: fixed header + scrollable body (recommended for tall modals). */
  split?: boolean;
  as?: "div" | "form";
  formProps?: FormHTMLAttributes<HTMLFormElement>;
};

const backdropClassName =
  "modal-backdrop fixed inset-0 z-50 flex items-end justify-center overflow-hidden bg-black/40 sm:items-center";

const panelBaseClassName =
  "modal-panel w-full max-w-lg rounded-t-2xl bg-white shadow-xl sm:rounded-2xl";

function panelClassNameFor(split: boolean, extra?: string) {
  return [
    panelBaseClassName,
    split ? "modal-panel-split flex flex-col overflow-hidden" : "modal-panel-scroll overflow-y-auto overscroll-contain",
    extra,
  ]
    .filter(Boolean)
    .join(" ");
}

export function Modal({
  open = true,
  onClose,
  children,
  panelClassName = "",
  split = false,
  as = "div",
  formProps,
}: ModalProps) {
  useEffect(() => {
    if (!open) return;
    lockModalScroll();
    return () => {
      unlockModalScroll();
    };
  }, [open]);

  if (!open) return null;

  const panelClass = panelClassNameFor(split, panelClassName);

  return (
    <div className={backdropClassName} onClick={onClose}>
      {as === "form" ? (
        <form
          {...formProps}
          className={panelClass}
          onClick={(event) => event.stopPropagation()}
        >
          {children}
        </form>
      ) : (
        <div
          className={panelClass}
          onClick={(event) => event.stopPropagation()}
        >
          {children}
        </div>
      )}
    </div>
  );
}

export function ModalHeader({
  children,
  className = "",
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`modal-header flex-shrink-0 border-b border-gray-100 p-4 ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function ModalBody({
  children,
  className = "",
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`modal-body p-4 ${className}`} {...props}>
      {children}
    </div>
  );
}
