"use client";

/**
 * Central GSAP setup. `useGSAP` is a GSAP plugin and MUST be registered before
 * use — without `gsap.registerPlugin(useGSAP)` the hook's context/cleanup races
 * under React 19 StrictMode (dev double-invokes effects), which reverts each
 * `gsap.from()` tween mid-flight and leaves elements stranded at their start
 * state (opacity: 0) — i.e. the "invisible UI" bug.
 *
 * Import `useGSAP` and `gsap` from THIS module (not directly from the packages)
 * so registration is guaranteed to have run first.
 */
import gsap from "gsap";
import { useGSAP } from "@gsap/react";

gsap.registerPlugin(useGSAP);

/** Respect the OS "reduce motion" setting — skip slide/stagger animations and
 *  just show elements in their final state. */
export function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true
  );
}

export { gsap, useGSAP };
