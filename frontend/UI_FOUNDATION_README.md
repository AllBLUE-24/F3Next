# F3Next UI Foundation — Tailark Premium Components

## Overview

This directory contains the foundational UI components and theme infrastructure for F3Next's ultra-minimalist, Agentic IDE Shell aesthetic. Inspired by Tailark, Cursor, and Raycast premium dark UIs.

## What's Been Created

### 1. **Core Utilities**

- **`lib/utils.ts`** — `cn()` helper for class merging (clsx + tailwind-merge)
- **`lib/motion-presets.ts`** — Standardized Framer Motion animations (spring, tween, fadeInUp, etc.)

### 2. **UI Primitives** (`components/ui/`)

- **`button.tsx`** — Shadcn-compatible button with CVA variants (default, ghost, outline, destructive)
- **`infinite-slider.tsx`** — Smooth infinite horizontal/vertical slider with hover speed control
- **`progressive-blur.tsx`** — Directional blur overlay for edge fades (top, right, bottom, left)

### 3. **Demo Block** (`components/blocks/`)

- **`hero-section-5.tsx`** — Full Tailark hero section with:
  - Scroll-aware glassmorphism header
  - Video background (pitch-black aesthetic)
  - Logo marquee with progressive blur edges
  - Mobile menu with animated icons

### 4. **Theme Architecture** (`app/globals.css`)

Expanded `@theme inline` directive with comprehensive token mapping:

```css
/* Ultra-dark canvas */
--color-pitch: #000000        /* absolute black */
--color-void: #09090b         /* near-black with warmth */
--color-shell: #0d0d11
--color-card: #17171d
--color-elevated: #1e1e25

/* Stark text hierarchy */
--color-primary: #fafafa       /* pure white */
--color-secondary: #a8a8b3     /* muted zinc */
--color-muted: #71717a

/* Borders & shadows */
--color-border-subtle: rgba(255, 255, 255, 0.055)
--shadow-lift, --shadow-accent, etc.
```

**Benefits:**
- Enables semantic Tailwind classes: `bg-void`, `text-secondary`, `border-subtle`, `shadow-lift`
- Eliminates verbose `bg-[var(--bg-void)]` syntax
- Centralizes all tokens for future light mode

## React 19 + Motion Compatibility

All components use `motion/react` (not `framer-motion`) for Next.js 16 + React 19 compiler compatibility.

## Usage Examples

### Button

```tsx
import { Button } from '@/components/ui/button'

<Button size="lg" variant="ghost">Click me</Button>
```

### Infinite Slider

```tsx
import { InfiniteSlider } from '@/components/ui/infinite-slider'

<InfiniteSlider speed={40} speedOnHover={20} gap={112}>
  <div>Item 1</div>
  <div>Item 2</div>
  {/* Items duplicate automatically */}
</InfiniteSlider>
```

### Motion Presets

```tsx
import { motion } from 'motion/react'
import { fadeInUp, spring } from '@/lib/motion-presets'

<motion.div {...fadeInUp} transition={spring.smooth}>
  Animates in from below with smooth spring
</motion.div>
```

### Progressive Blur

```tsx
import { ProgressiveBlur } from '@/components/ui/progressive-blur'

<div className="relative">
  <div className="overflow-x-auto">
    {/* scrollable content */}
  </div>
  <ProgressiveBlur 
    direction="right" 
    blurIntensity={1} 
    className="absolute right-0 top-0 h-full w-20"
  />
</div>
```

## Theme Token Usage (New Semantic Classes)

Before:
```tsx
className="bg-[var(--bg-void)] text-[var(--text-secondary)] border-[var(--border-subtle)]"
```

After:
```tsx
className="bg-void text-secondary border-subtle"
```

## Next Steps

1. **Delete orphaned components** — FloatingAIBubble, MigrationClient, Comparison, etc. (Plan Part 1.4)
2. **Build Session Tree** — Collapsible left sidebar replacing StepRail
3. **Build Agent Stream** — Center timeline with markdown messages
4. **Build Context Drawer** — Right panel with tabbed data views
5. **Migrate OS terminal** — Use same ultra-dark tokens (no more inline styles)

## Design References

- **Tailark** — Premium Tailwind blocks (hero sections, glassmorphism)
- **Cursor IDE** — Agent stream, file tree, right panel architecture
- **Raycast** — Ultra-dark canvas, subtle glassmorphism, command palette
- **Apple Music (dark)** — Pitch-black base, high contrast text

## File Structure

```
frontend/src/
├── lib/
│   ├── utils.ts              # cn() helper
│   └── motion-presets.ts     # Framer Motion library
├── components/
│   ├── ui/
│   │   ├── button.tsx
│   │   ├── infinite-slider.tsx
│   │   └── progressive-blur.tsx
│   └── blocks/
│       └── hero-section-5.tsx
└── app/
    └── globals.css           # Expanded @theme inline
```

## Dependencies Installed

```json
{
  "motion": "^latest",
  "@radix-ui/react-slot": "^latest",
  "class-variance-authority": "^latest",
  "react-use-measure": "^latest",
  "clsx": "^latest",
  "tailwind-merge": "^latest"
}
```

**Already had:** `framer-motion`, `lucide-react`

---

*Built for F3Next Agentic IDE Shell overhaul — June 2026*
