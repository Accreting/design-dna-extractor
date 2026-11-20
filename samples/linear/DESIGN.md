# Design DNA Specification: Linear – The system for product development
> Source URL: https://linear.app | Base Theme: Dark Mode | Target: Claude Code / Cursor

## 1. Core Color Palette and Contrast Validation
| Semantic Role | Hex Value | RGB Value | Contrast vs BG | WCAG AA Status |
| :--- | :--- | :--- | :---: | :---: |
| Background (bg-background) | `#08090a` | `(8, 9, 10)` | - | Baseline |
| Surface (bg-surface) | `#0f1011` | `(15, 16, 17)` | - | Elevated Container |
| Foreground / Text (text-primary) | `#f7f8f8` | `(247, 248, 248)` | **18.73:1** | AA Normal PASS |
| Accent / Brand (bg-accent) | `#5e6ad2` | `(94, 106, 210)` | **4.24:1** | AA Large/UI Only |
| Muted Text (text-muted) | `#62666d` | `(98, 102, 109)` | - | Secondary Subtext |
| Border (border-border) | `#27272a` | - | - | Dividers & Borders |

## 2. Typography Hierarchy and Fallbacks
- Display / Heading Font: `Inter Variable` (Google Font fallback: `Inter`)
- Body / UI Font: `Inter Variable` (Google Font fallback: `Inter`)
- Monospace Font: `Berkeley Mono` (Google Font fallback: `JetBrains Mono`)

## 3. Surface and Spacing DNA
- Border Radii: Small `4px`, Medium/Card `8px`, Large `12px`
- Card Elevation: Border `none`, Shadow `none`

## 4. Cursor / Claude Code System Prompt Preset
```markdown
You are designing modern web components matching linear.app.
- Theme: Dark Mode (Background: #08090a, Surface: #0f1011)
- Typography:
  * Headings: Inter Variable (size 64px, line-height 64px, weight 510)
  * Body & UI: Inter Variable (size 15px, line-height 24px)
  * Code & Mono: Berkeley Mono (fallback: monospace)
- Brand Accent: #5e6ad2 (Buttons, active tabs, interactive highlights)
- Layout & Elevation:
  * Card radius: 8px, Border: none, Shadow: none
  * Button radius: 4px, Border: none
```
