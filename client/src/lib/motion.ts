/**
 * Motion tokens, mirrored from global.css. Use these instead of ad-hoc
 * durations/easings so motion stays consistent. Full presets land in Phase 4.
 */
export const duration = {
  fast: 0.15,
  base: 0.2,
  slow: 0.28,
} as const;

export const ease = {
  /** ease-out-quart: routine UI changes */
  out: [0.25, 1, 0.5, 1],
  /** ease-out-expo: larger layout moves */
  outExpo: [0.16, 1, 0.3, 1],
  inOut: [0.65, 0, 0.35, 1],
  in: [0.5, 0, 0.75, 0],
} as const satisfies Record<string, [number, number, number, number]>;

export const transition = {
  fast: { duration: duration.fast, ease: ease.out },
  base: { duration: duration.base, ease: ease.out },
  slow: { duration: duration.slow, ease: ease.outExpo },
} as const;
