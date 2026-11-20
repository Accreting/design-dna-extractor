# Design DNA Specification: Agentic Infrastructure - Vercel
> Source URL: https://vercel.com | Base Theme: Light Mode | Target: Claude Code / Cursor

## 1. Core Color Palette and Contrast Validation
| Semantic Role | Hex Value | RGB Value | Contrast vs BG | WCAG AA Status |
| :--- | :--- | :--- | :---: | :---: |
| Background (bg-background) | `#fafafa` | `(250, 250, 250)` | - | Baseline |
| Surface (bg-surface) | `#ffffff` | `(255, 255, 255)` | - | Elevated Container |
| Foreground / Text (text-primary) | `#171717` | `(23, 23, 23)` | **17.18:1** | AA Normal PASS |
| Accent / Brand (bg-accent) | `#0072f5` | `(0, 114, 245)` | **4.26:1** | AA Large/UI Only |
| Muted Text (text-muted) | `#8f8f8f` | `(143, 143, 143)` | - | Secondary Subtext |
| Border (border-border) | `#e2e8f0` | - | - | Dividers & Borders |

## 2. Typography Hierarchy and Fallbacks
- Display / Heading Font: `GeistSans` (Google Font fallback: `Geist`)
- Body / UI Font: `GeistSans` (Google Font fallback: `Geist`)
- Monospace Font: `Geist Mono` (Google Font fallback: `Geist Mono`)

## 3. Surface and Spacing DNA
- Border Radii: Small `6px`, Medium/Card `12px`, Large `12px`
- Card Elevation: Border `1px solid #e2e8f0`, Shadow `none`

## 4. Cursor / Claude Code System Prompt Preset
```markdown
You are designing modern web components matching vercel.com.
- Theme: Light Mode (Background: #fafafa, Surface: #ffffff)
- Typography:
  * Headings: GeistSans (size 64px, line-height 64px, weight 400)
  * Body & UI: GeistSans (size 16px, line-height 24px)
  * Code & Mono: Geist Mono (fallback: monospace)
- Brand Accent: #0072f5 (Buttons, active tabs, interactive highlights)
- Layout & Elevation:
  * Card radius: 12px, Border: 1px solid #e2e8f0, Shadow: none
  * Button radius: 6px, Border: 0px solid rgb(235, 235, 235)
```
