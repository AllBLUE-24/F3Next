---
description: Apply the modern, minimalist, highly dense enterprise aesthetic for F3Next (Impeccable UI)
---
# Teach Impeccable (UI/UX Skill)

When building or modifying frontend components for F3Next, you **must** apply the "Impeccable" enterprise aesthetic. This design philosophy emphasizes high data density, absolute clarity, and a premium modern workspace feel (akin to cursor, Linear, or high-end IDEs).

## 1. High Data Density
- **Micro-paddings:** Minimize excessive whitespace inside data tables, forms, and lists. Use tight paddings (e.g. `px-2 py-1` or `px-3 py-2`).
- **Collaterals/Side Panels:** Use split panes and side-collaterals instead of page routing. Complex arrays, JSONs, or multi-step logic should be viewable side-by-side with the chat/action feed.

## 2. Minimalist Enterprise Aesthetic
- **Color Palettes:** Rely on grayscale, sophisticated dark themes, and subtle muted UI borders (`border-border/40`, `bg-muted/30`).
- **Depth and Focus:** Use subtle drop shadows (`shadow-sm`, `ring`) or slight opacity glassmorphism to separate floating elements or modals from the background without loud colors.

## 3. Typography
- **Hierarchy:** Rely on font weight (`font-medium`, `font-semibold`) and muted colors (`text-muted-foreground`) to establish hierarchy, rather than drastically changing font sizes.
- **Sizes:** Keep base fonts small to fit more into the viewport (`text-sm`, `text-[13px]`).

## 4. Single Dynamic Window UX
- **No Page Refresh:** Build single unified dynamic windows. All user workflows (uploading, validating, mappings) should happen sequentially via state changes and dynamic agent streams within the same screen layout.
