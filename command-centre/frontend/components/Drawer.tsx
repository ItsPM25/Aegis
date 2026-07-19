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
      
      <div 
        className="gsap-panel pointer-events-auto absolute left-[52px] top-28 bottom-6 z-30 w-[22rem] origin-left flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Press Esc to exit */}
        <div className="absolute -top-7 left-0 flex items-center">
          <span className="text-xs text-zinc-500 whitespace-nowrap">
            Press <kbd className="font-sans border border-white/10 bg-white/5 px-1.5 py-0.5 rounded text-zinc-400 mx-1">Esc</kbd> to exit
          </span>
        </div>
        
        {/* drawer panel */}
        <aside className="glass-drawer flex-1 overflow-y-auto scroll-thin w-full rounded-sm">
          {children}
        </aside>
      </div>
    </div>
  );
}
