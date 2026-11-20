# Design DNA Specification: Stripe | Financial Infrastructure to Grow Your Revenue
> Source URL: https://stripe.com | Base Theme: Light Mode | Target: Claude Code / Cursor

## 1. Core Color Palette and Contrast Validation
| Semantic Role | Hex Value | RGB Value | Contrast vs BG | WCAG AA Status |
| :--- | :--- | :--- | :---: | :---: |
| Background (bg-background) | `#ffffff` | `(255, 255, 255)` | - | Baseline |
| Surface (bg-surface) | `#e5edf5` | `(229, 237, 245)` | - | Elevated Container |
| Foreground / Text (text-primary) | `#061b31` | `(6, 27, 49)` | **17.37:1** | AA Normal PASS |
| Accent / Brand (bg-accent) | `#533afd` | `(83, 58, 253)` | **6.19:1** | AA Normal PASS |
| Muted Text (text-muted) | `#64748d` | `(100, 116, 141)` | - | Secondary Subtext |
| Border (border-border) | `#e2e8f0` | - | - | Dividers & Borders |

## 2. Typography Hierarchy and Fallbacks
- Display / Heading Font: `sohne-var` (Google Font fallback: `Inter`)
- Body / UI Font: `sohne-var` (Google Font fallback: `Inter`)
- Monospace Font: `SourceCodePro` (Google Font fallback: `JetBrains Mono`)

## 3. Surface and Spacing DNA
- Border Radii: Small `4px`, Medium/Card `6px`, Large `6px`
- Card Elevation: Border `none`, Shadow `none`

## 4. Cursor / Claude Code System Prompt Preset
```markdown
You are designing modern web components matching stripe.com.
- Theme: Light Mode (Background: #ffffff, Surface: #e5edf5)
- Typography:
  * Headings: sohne-var (size 48px, line-height 55.2px, weight 300)
  * Body & UI: sohne-var (size 14px, line-height 19.6px)
  * Code & Mono: SourceCodePro (fallback: monospace)
- Brand Accent: #533afd (Buttons, active tabs, interactive highlights)
- Layout & Elevation:
  * Card radius: 6px, Border: none, Shadow: none
  * Button radius: 4px, Border: none
```
