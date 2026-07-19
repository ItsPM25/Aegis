"use client";

import { useEffect, useRef } from "react";
import { playPanelExit, usePanelEntrance } from "@/lib/gsap";

export default function Drawer({
  children,
  onClose,
  scopeRef,
}: {
  children: React.ReactNode;
  onClose: () => void;
  /** Lets the parent tween this drawer out before unmounting it. The drawer
   *  sits below the top nav, so switching tabs is a real close path — and the
   *  parent owns that decision, not this shell. */
  scopeRef?: React.RefObject<HTMLDivElement | null>;
}) {
  const own = useRef<HTMLDivElement>(null);
  const scope = scopeRef ?? own;
  // Replaces the CSS `animate-slide-in`, which drove translateX(-100%) on this
  // blur(20px) surface right across the live map — a full re-blur every frame.
  // Anchored left so it still reads as opening from the rail.
  usePanelEntrance(scope, ".gsap-panel");
  // Closing has to defer the unmount, or React removes the drawer before the
  // tween can run and the exit is a hard cut.
  // Re-entrancy guard: a second Escape (or Esc + backdrop click) during the
  // exit tween would start a competing tween and fire onClose twice.
  const closing = useRef(false);
  const close = () => {
    if (closing.current) return;
    closing.current = true;
    playPanelExit(scope, onClose);
  };
  // Ref'd so the listener registers once — `onClose` is an inline arrow from
  // the parent, so a [onClose] dep re-subscribed on every parent render.
  const closeRef = useRef(close);
  closeRef.current = close;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") closeRef.current(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div ref={scope}>
      {/* click-away backdrop */}
      <div className="absolute inset-0 z-20" onClick={close} />
      {/* drawer panel */}
      <aside
        className="gsap-panel glass-drawer pointer-events-auto absolute left-[52px] top-14 bottom-0 z-30 w-[22rem] origin-left overflow-y-auto scroll-thin"
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </aside>
    </div>
  );
}
