import { useCallback, useEffect, useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent, RefObject } from 'react';

export function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
}

/** True once the element has scrolled into view (stays true). */
export function useInView<T extends Element>(rootMargin = '0px 0px -10% 0px'): [RefObject<T>, boolean] {
  const ref = useRef<T>(null);
  const [shown, setShown] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || shown) return undefined;
    if (typeof IntersectionObserver === 'undefined' || prefersReducedMotion()) {
      setShown(true);
      return undefined;
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setShown(true);
          io.disconnect();
        }
      },
      { rootMargin },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [rootMargin, shown]);
  return [ref, shown];
}

/** Animates 0 → target over `ms` once `run` is true. Returns the current value. */
export function useTween(target: number, run: boolean, ms = 900): number {
  const [value, setValue] = useState(run && prefersReducedMotion() ? target : 0);
  useEffect(() => {
    if (!run) return undefined;
    if (prefersReducedMotion()) {
      setValue(target);
      return undefined;
    }
    let frame = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / ms);
      const eased = 1 - Math.pow(1 - t, 3);
      setValue(target * eased);
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, run, ms]);
  return value;
}

/** Pointer spotlight: sets --sx / --sy on the element so `.spotlight` can follow the pointer. */
export function useSpotlight<T extends HTMLElement>() {
  return useCallback((e: ReactPointerEvent<T>) => {
    const el = e.currentTarget;
    const r = el.getBoundingClientRect();
    el.style.setProperty('--sx', `${e.clientX - r.left}px`);
    el.style.setProperty('--sy', `${e.clientY - r.top}px`);
  }, []);
}

/** Splits a display string such as "₹8.2 lakh", "+17.4%" or "₹1,30,000" into prefix, number and suffix. */
export function splitDisplay(display: string): { prefix: string; value: number; decimals: number; grouped: boolean; sign: string; suffix: string } | null {
  const m = /([+\-−]?)(\d[\d,]*)(\.(\d+))?/.exec(display);
  if (!m || m.index === undefined) return null;
  const whole = m[2] ?? '';
  const decimals = m[4]?.length ?? 0;
  const value = Number(`${whole.replace(/,/g, '')}${decimals ? `.${m[4]}` : ''}`);
  if (!Number.isFinite(value)) return null;
  return {
    prefix: display.slice(0, m.index),
    value,
    decimals,
    grouped: whole.includes(','),
    sign: m[1] ?? '',
    suffix: display.slice(m.index + m[0].length),
  };
}

export function formatTweened(parts: NonNullable<ReturnType<typeof splitDisplay>>, current: number): string {
  const n = current.toLocaleString('en-IN', {
    minimumFractionDigits: parts.decimals,
    maximumFractionDigits: parts.decimals,
    useGrouping: parts.grouped,
  });
  return `${parts.prefix}${parts.sign}${n}${parts.suffix}`;
}
