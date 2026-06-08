/**
 * Framer Motion Animation Presets
 * Standardized micro-interactions for F3Next Agentic UI
 * 
 * Usage:
 * ```tsx
 * import { motion } from 'motion/react'
 * import { fadeInUp, spring } from '@/lib/motion-presets'
 * 
 * <motion.div {...fadeInUp} transition={spring.smooth}>
 *   Content
 * </motion.div>
 * ```
 */

// ── Spring Presets ───────────────────────────────────────────────────────────

export const spring = {
  /** Smooth, natural spring (300 stiffness, 30 damping) - for panels, modals */
  smooth: { type: "spring" as const, stiffness: 300, damping: 30 },
  
  /** Bouncy spring (400 stiffness, 15 damping) - for playful interactions */
  bounce: { type: "spring" as const, stiffness: 400, damping: 15 },
  
  /** Tight spring (500 stiffness, 40 damping) - for immediate feedback */
  tight: { type: "spring" as const, stiffness: 500, damping: 40 },
  
  /** Gentle spring (200 stiffness, 25 damping) - for large elements */
  gentle: { type: "spring" as const, stiffness: 200, damping: 25 },
};

// ── Tween Presets ────────────────────────────────────────────────────────────

export const tween = {
  /** Fast (150ms) with ease-out curve */
  fast: { duration: 0.15, ease: [0.16, 1, 0.3, 1] },
  
  /** Base (200ms) with ease-out curve */
  base: { duration: 0.2, ease: [0.16, 1, 0.3, 1] },
  
  /** Slow (300ms) with ease-out curve */
  slow: { duration: 0.3, ease: [0.16, 1, 0.3, 1] },
  
  /** Slower (500ms) with ease-out curve */
  slower: { duration: 0.5, ease: [0.16, 1, 0.3, 1] },
  
  /** Linear for continuous animations */
  linear: { duration: 0.2, ease: "linear" },
};

// ── Common Animation Variants ────────────────────────────────────────────────

/** Fade in from below (8px translateY) */
export const fadeInUp = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
};

/** Fade in from above (8px translateY) */
export const fadeInDown = {
  initial: { opacity: 0, y: -8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: 8 },
};

/** Simple fade */
export const fade = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
};

/** Slide in from right (100% translateX) */
export const slideInRight = {
  initial: { x: "100%" },
  animate: { x: 0 },
  exit: { x: "100%" },
};

/** Slide in from left (100% translateX) */
export const slideInLeft = {
  initial: { x: "-100%" },
  animate: { x: 0 },
  exit: { x: "-100%" },
};

/** Scale up from center */
export const scaleIn = {
  initial: { scale: 0.95, opacity: 0 },
  animate: { scale: 1, opacity: 1 },
  exit: { scale: 0.95, opacity: 0 },
};

/** Scale down to center */
export const scaleOut = {
  initial: { scale: 1, opacity: 1 },
  animate: { scale: 0.95, opacity: 0 },
  exit: { scale: 1, opacity: 1 },
};

// ── Stagger Presets ──────────────────────────────────────────────────────────

/** Stagger children with delay */
export const staggerChildren = (delayPerChild = 0.1) => ({
  animate: {
    transition: {
      staggerChildren: delayPerChild,
    },
  },
});

/** Stagger in reverse (bottom-up) */
export const staggerChildrenReverse = (delayPerChild = 0.1) => ({
  animate: {
    transition: {
      staggerChildren: delayPerChild,
      staggerDirection: -1,
    },
  },
});

// ── Interaction Presets ──────────────────────────────────────────────────────

/** Button press down animation */
export const buttonPress = {
  whileTap: { scale: 0.98, y: 1 },
  transition: tween.fast,
};

/** Lift up on hover */
export const hoverLift = {
  whileHover: { y: -2, transition: tween.fast },
  whileTap: { y: 1, scale: 0.98, transition: tween.fast },
};

/** Gentle scale on hover */
export const hoverScale = {
  whileHover: { scale: 1.02, transition: tween.fast },
  whileTap: { scale: 0.98, transition: tween.fast },
};

/** Pulse animation (like live dots) */
export const pulse = {
  animate: {
    scale: [1, 1.08, 1],
    opacity: [0.85, 1, 0.85],
  },
  transition: {
    duration: 2.4,
    repeat: Infinity,
    ease: "easeInOut",
  },
};

// ── Gate/Modal Presets ───────────────────────────────────────────────────────

/** Drawer slide-in animation */
export const drawerSlide = {
  ...slideInRight,
  transition: spring.smooth,
};

/** Modal backdrop fade */
export const backdropFade = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
  transition: tween.base,
};

/** Gate banner slide down from top */
export const bannerSlideDown = {
  initial: { y: -100, opacity: 0 },
  animate: { y: 0, opacity: 1 },
  exit: { y: -100, opacity: 0 },
  transition: spring.smooth,
};

// ── Message Stream Presets ───────────────────────────────────────────────────

/** Message item fade in (for chat streams) */
export const messageFadeIn = {
  initial: { opacity: 0, y: 12, scale: 0.98 },
  animate: { opacity: 1, y: 0, scale: 1 },
  transition: spring.gentle,
};

/** Typing indicator pulse */
export const typingIndicator = {
  animate: {
    opacity: [0.4, 1, 0.4],
  },
  transition: {
    duration: 1.5,
    repeat: Infinity,
    ease: "easeInOut",
  },
};
