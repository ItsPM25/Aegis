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
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import type { RefObject } from "react";

gsap.registerPlugin(useGSAP);

/** Respect the OS "reduce motion" setting — skip slide/stagger animations and
 *  just show elements in their final state. */
export function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true
  );
}

/**
 * The one entrance recipe for panels that open over the live map — drawers,
 * the modules/fraud-ring cards, the supply-trail panel.
 *
 * Deliberately scale + opacity only, from 0.96 rather than something dramatic.
 * Every one of these surfaces is `backdrop-filter: blur(20px)` sitting on the
 * map canvas, and the blur is re-sampled whenever the element's box moves over
 * changing content. The old drawer slid `translateX(-100%)` across the whole
 * viewport, which forced a full re-blur every frame — that is the jank that
 * made the alert animations feel bad. A near-1 scale barely moves the sampling
 * region, so the compositor can reuse it.
 *
 * fromTo (never `from`) with an explicit end state + clearProps: under React 19
 * StrictMode a reverted `from()` strands the element at opacity 0 — the
 * "invisible UI" bug. clearProps also drops the inline transform afterwards so
 * it cannot fight hover/layout styles.
 *
 * @param scope     the container ref useGSAP scopes selectors to
 * @param selector  which children to reveal; defaults to the panel itself
 * @param deps      re-run the entrance when these change (e.g. a tab switch)
 */
export function usePanelEntrance(
  scope: RefObject<HTMLElement | null>,
  selector = ".gsap-panel",
  deps: unknown[] = [],
) {
  useGSAP(
    () => {
      const els = gsap.utils.toArray<HTMLElement>(selector);
      if (!els.length) return;
      if (prefersReducedMotion()) {
        gsap.set(els, { opacity: 1, scale: 1, clearProps: "all" });
        return;
      }
      gsap.fromTo(
        els,
        { opacity: 0, scale: 0.96 },
        {
          opacity: 1,
          scale: 1,
          duration: 0.42,
          stagger: 0.07,
          ease: "power3.out",
          force3D: true,
          willChange: "transform,opacity",
          clearProps: "all",
        },
      );
    },
    { scope, dependencies: deps },
  );
}

/**
 * Play the exit tween, THEN close.
 *
 * A conditionally-rendered panel (`{open && <Panel/>}`) is torn out of the DOM
 * the instant its flag flips, so there is no element left to animate — which is
 * why closing was a hard cut while opening was animated. The close has to be
 * gated: tween first, flip the state in onComplete. Callers pass their real
 * close handler as `done`.
 *
 * Faster and sharper than the entrance (0.22s, power2.in): an exit should get
 * out of the way, not perform. `overwrite` kills any entrance still running so
 * a quick open→close cannot leave two tweens fighting over the same element.
 *
 * If there is nothing to animate, or the user asked for reduced motion, `done`
 * runs immediately — the panel must always close, animation or not.
 */
export function playPanelExit(
  scope: RefObject<HTMLElement | null>,
  done: () => void,
  selector = ".gsap-panel",
) {
  const root = scope.current;
  const els = root ? gsap.utils.toArray<HTMLElement>(selector, root) : [];
  if (!els.length || prefersReducedMotion()) {
    done();
    return;
  }
  gsap.to(els, {
    opacity: 0,
    scale: 0.96,
    duration: 0.22,
    stagger: 0.04,
    ease: "power2.in",
    force3D: true,
    overwrite: true,
    onComplete: done,
  });
}

export { gsap, useGSAP };
