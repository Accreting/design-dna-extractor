"""
projects/p1/extract_design_dna.py - P1: Visual DNA & Clean SVG Asset Extractor
CLI tool to pull semantic palettes, typography, Tailwind v4 @theme, and deduped SVGs.
"""
import argparse, asyncio, json, os, re, sys
from pathlib import Path
from urllib.parse import urlparse
import httpx

for p in [Path(__file__).resolve().parent, Path(__file__).resolve().parent.parent.parent]:
    if (p / "shared_infra").is_dir() and str(p) not in sys.path:
        sys.path.insert(0, str(p)); break

from shared_infra.browser import DEFAULT_USER_AGENT, get_browser_context
from shared_infra.packager import create_zip_archive, save_markdown_report

FONT_FALLBACKS = {
    "berkeley mono": "JetBrains Mono", "sohne-var": "Inter", "sohne": "Inter",
    "inter variable": "Inter", "geistsans": "Geist", "geist mono": "Geist Mono"
}


def is_trans(c: str) -> bool:
    if not c or c in ("transparent", "rgba(0, 0, 0, 0)", "rgba(255, 255, 255, 0)"): return True
    m = re.search(r"rgba\(\s*\d+,\s*\d+,\s*\d+,\s*([\d\.]+)\)", c)
    return float(m.group(1)) == 0 if m else False


def parse_rgb(c: str) -> tuple[int, int, int]:
    m = re.search(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", c or "")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (0, 0, 0)


def rgb_to_hex(r: int, g: int, b: int) -> str: return f"#{r:02x}{g:02x}{b:02x}"


def get_luminance(r: int, g: int, b: int) -> float:
    def ch(v): v = v / 255.0; return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> float:
    l1, l2 = get_luminance(*c1), get_luminance(*c2)
    return round((max(l1, l2) + 0.05) / (min(l1, l2) + 0.05), 2)


def color_sat(r: int, g: int, b: int) -> float:
    mx, mn = max(r, g, b), min(r, g, b)
    return (mx - mn) / mx if mx > 0 else 0.0


def eval_contrast(ratio: float) -> str:
    return "AA Normal PASS" if ratio >= 4.5 else ("AA Large/UI Only" if ratio >= 3.0 else "FAIL")


async def scrape_visual_dna(url: str) -> dict:
    js_extract = """() => {
        const isTrans = c => !c || c === 'transparent' || c === 'rgba(0, 0, 0, 0)' || c.endsWith(', 0)');
        const all = Array.from(document.querySelectorAll('*'));
        let effectiveBg = '';
        const bodyBg = window.getComputedStyle(document.body).backgroundColor;
        const htmlBg = window.getComputedStyle(document.documentElement).backgroundColor;
        if (!isTrans(bodyBg)) effectiveBg = bodyBg;
        else if (!isTrans(htmlBg)) effectiveBg = htmlBg;
        else {
            const boxes = all.filter(el => { const r = el.getBoundingClientRect(); return r.width > 300 && r.height > 200 && !isTrans(window.getComputedStyle(el).backgroundColor); })
                .sort((a, b) => (b.getBoundingClientRect().width * b.getBoundingClientRect().height) - (a.getBoundingClientRect().width * a.getBoundingClientRect().height));
            if (boxes.length > 0) effectiveBg = window.getComputedStyle(boxes[0]).backgroundColor;
        }
        if (!effectiveBg) effectiveBg = 'rgb(255, 255, 255)';

        const ctaColors = [], surfaceBgs = {}, textColors = {}, fonts = new Set(), rawRadii = new Set();
        document.querySelectorAll('button, a, [role=\"button\"]').forEach(el => {
            const s = window.getComputedStyle(el);
            if (!isTrans(s.backgroundColor)) ctaColors.push(s.backgroundColor);
            if (!isTrans(s.color)) ctaColors.push(s.color);
        });
        document.querySelectorAll('section, div, main, article').forEach(el => {
            const s = window.getComputedStyle(el), r = el.getBoundingClientRect();
            if (!isTrans(s.backgroundColor) && r.width > 200 && r.height > 100) surfaceBgs[s.backgroundColor] = (surfaceBgs[s.backgroundColor] || 0) + 1;
        });
        document.querySelectorAll('p, span, h1, h2, h3, h4, li').forEach(el => {
            const s = window.getComputedStyle(el);
            if (!isTrans(s.color)) textColors[s.color] = (textColors[s.color] || 0) + 1;
            if (s.fontFamily) { const f = s.fontFamily.split(',')[0].replace(/['\"]/g, '').trim(); if (f && !['inherit', 'initial', '-apple-system', 'system-ui'].includes(f)) fonts.add(f); }
        });
        all.slice(0, 350).forEach(el => { const s = window.getComputedStyle(el); if (s.borderRadius && s.borderRadius !== '0px') rawRadii.add(s.borderRadius); });

        const h1 = document.querySelector('h1'), p = document.querySelector('p') || document.querySelector('main span');
        const btn = document.querySelector('button, a[class*=\"btn\"], a[class*=\"button\"]');
        const card = document.querySelector('div[class*=\"card\"], section > div');

        const svgs = [], seenSvg = new Set();
        document.querySelectorAll('svg').forEach(s => {
            const r = s.getBoundingClientRect();
            if (r.width < 12 || r.height < 12 || (r.width / r.height) > 5.0 || (r.width / r.height) < 0.2 || s.querySelector('text')) return;
            let h = s.outerHTML;
            if (!h.includes('<path') && !h.includes('<polygon') && !h.includes('<circle') && !h.includes('<rect')) return;
            if (!h.includes('xmlns=')) h = h.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"');
            if (h.includes('fill="none"') && !h.includes('stroke=') && !h.includes('fill="#') && !h.includes('fill="rgb')) {
                h = h.replace('fill="none"', 'fill="currentColor"');
            }
            const key = h.replace(/\\s+/g, '').slice(0, 100);
            if (!seenSvg.has(key)) { seenSvg.add(key); svgs.push(h); }
        });

        const imgs = [], seenImg = new Set();
        document.querySelectorAll('img, picture source').forEach(el => {
            let src = el.src || el.getAttribute('srcset') || el.getAttribute('data-src');
            if (src && src.startsWith('http') && !src.match(/(pixel|tracker|analytics|badge)/i)) {
                src = src.split(' ')[0].split('?')[0];
                if (!seenImg.has(src)) { seenImg.add(src); imgs.push(src); }
            }
        });

        return {
            title: document.title || 'Untitled', effectiveBg, ctaColors: ctaColors.slice(0, 30),
            surfaceBgs, textColors, fonts: Array.from(fonts).slice(0, 6), rawRadii: Array.from(rawRadii),
            svgs: svgs.slice(0, 30), images: imgs.slice(0, 15),
            specs: {
                h1: h1 ? { font: window.getComputedStyle(h1).fontFamily.split(',')[0].replace(/['\"]/g, '').trim(), size: window.getComputedStyle(h1).fontSize, weight: window.getComputedStyle(h1).fontWeight, lh: window.getComputedStyle(h1).lineHeight } : null,
                body: p ? { font: window.getComputedStyle(p).fontFamily.split(',')[0].replace(/['\"]/g, '').trim(), size: window.getComputedStyle(p).fontSize, lh: window.getComputedStyle(p).lineHeight } : null,
                button: btn ? { radius: window.getComputedStyle(btn).borderRadius, shadow: window.getComputedStyle(btn).boxShadow, border: window.getComputedStyle(btn).border } : null,
                card: card ? { radius: window.getComputedStyle(card).borderRadius, shadow: window.getComputedStyle(card).boxShadow, border: window.getComputedStyle(card).border } : null
            }
        };
    }"""
    async with get_browser_context() as page:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(2.0)
        return await page.evaluate(js_extract)


def classify_palette(data: dict) -> dict:
    bg_rgb = parse_rgb(data.get("effectiveBg") or "rgb(255, 255, 255)")
    is_dark = get_luminance(*bg_rgb) < 0.2

    if is_dark:
        surfaces = [c for c, _ in sorted(data.get("surfaceBgs", {}).items(), key=lambda x: x[1], reverse=True) if c != data.get("effectiveBg") and color_sat(*parse_rgb(c)) < 0.2 and get_luminance(*parse_rgb(c)) < 0.35]
        surface_rgb = parse_rgb(surfaces[0]) if surfaces else (bg_rgb[0] + 12, bg_rgb[1] + 12, bg_rgb[2] + 14)
    else:
        surfaces = [c for c, _ in sorted(data.get("surfaceBgs", {}).items(), key=lambda x: x[1], reverse=True) if c != data.get("effectiveBg") and color_sat(*parse_rgb(c)) < 0.2 and get_luminance(*parse_rgb(c)) > 0.4]
        surface_rgb = parse_rgb(surfaces[0]) if surfaces else (255, 255, 255)

    accent_rgb = None
    for c in data.get("ctaColors", []):
        rgb = parse_rgb(c)
        if color_sat(*rgb) >= 0.35 and 0.08 <= get_luminance(*rgb) <= 0.85: accent_rgb = rgb; break
    if not accent_rgb: accent_rgb = (94, 106, 210) if is_dark else (0, 114, 245)

    texts = [parse_rgb(c) for c, _ in sorted(data.get("textColors", {}).items(), key=lambda x: x[1], reverse=True) if color_sat(*parse_rgb(c)) < 0.25 and contrast(parse_rgb(c), bg_rgb) >= 4.5]
    text_rgb = texts[0] if texts else ((247, 248, 248) if is_dark else (6, 27, 49))

    muteds = [parse_rgb(c) for c, _ in sorted(data.get("textColors", {}).items(), key=lambda x: x[1], reverse=True) if 2.5 <= contrast(parse_rgb(c), bg_rgb) < 4.5 and color_sat(*parse_rgb(c)) < 0.3]
    muted_rgb = muteds[0] if muteds else ((148, 163, 184) if is_dark else (100, 116, 141))

    cr_t, cr_a = contrast(text_rgb, bg_rgb), contrast(accent_rgb, bg_rgb)
    return {
        "is_dark": is_dark, "background": {"hex": rgb_to_hex(*bg_rgb), "rgb": bg_rgb},
        "surface": {"hex": rgb_to_hex(*surface_rgb), "rgb": surface_rgb},
        "foreground": {"hex": rgb_to_hex(*text_rgb), "rgb": text_rgb, "contrast": cr_t, "status": eval_contrast(cr_t)},
        "accent": {"hex": rgb_to_hex(*accent_rgb), "rgb": accent_rgb, "contrast": cr_a, "status": eval_contrast(cr_a)},
        "muted": {"hex": rgb_to_hex(*muted_rgb), "rgb": muted_rgb}, "border": {"hex": "#27272a" if is_dark else "#e2e8f0"}
    }


def classify_typo_and_radii(data: dict) -> tuple[dict, dict]:
    fonts = data.get("fonts", [])
    monos = [f for f in fonts if any(k in f.lower() for k in ["mono", "code", "consolas", "jetbrains", "berkeley", "fira"])]
    sans = [f for f in fonts if f not in monos]
    h1_f = data.get("specs", {}).get("h1", {}).get("font") if data.get("specs", {}).get("h1") else None
    disp = h1_f if (h1_f and h1_f not in monos) else (sans[0] if sans else "Inter")
    body = sans[1] if len(sans) > 1 else (sans[0] if sans else disp)
    mono = monos[0] if monos else None
    typo = {
        "display": disp, "display_fallback": FONT_FALLBACKS.get(disp.lower(), disp),
        "body": body, "body_fallback": FONT_FALLBACKS.get(body.lower(), body),
        "mono": mono, "mono_fallback": FONT_FALLBACKS.get(mono.lower(), "JetBrains Mono") if mono else None
    }
    px_vals, has_pill = [], False
    for r in data.get("rawRadii", []):
        m = re.search(r"([\d\.]+)px", r)
        if m:
            v = float(m.group(1))
            if v >= 100 or "9999" in r: has_pill = True
            elif 0 < v < 100: px_vals.append(v)
    px_s = sorted(set(px_vals))
    sm = f"{int(px_s[0])}px" if px_s else "4px"
    md = f"{int(px_s[1])}px" if len(px_s) > 1 else (f"{int(px_s[0])}px" if px_s else "8px")
    lg = f"{int(px_s[2])}px" if len(px_s) > 2 else (f"{int(px_s[-1])}px" if px_s else "12px")
    return typo, {"sm": sm, "md": md, "lg": lg, "pill": "9999px" if has_pill else None, "card": md, "button": sm}


def generate_artifacts(url: str, data: dict, palette: dict, typo: dict, radii: dict, out_dir: Path, obsidian: bool = False):
    domain, title, specs = urlparse(url).netloc.replace("www.", ""), data.get("title", "Site"), data.get("specs", {})
    h1_d = f"size {specs['h1']['size']}, line-height {specs['h1']['lh']}, weight {specs['h1']['weight']}" if specs.get("h1") else "scaled headings"
    body_d = f"size {specs['body']['size']}, line-height {specs['body']['lh']}" if specs.get("body") else "standard readable UI"
    c_specs, b_specs = specs.get("card") or {}, specs.get("button") or {}
    cb, bb = c_specs.get("border") or "none", b_specs.get("border") or "none"
    c_border = "none" if not cb or cb.startswith("0px") or "none" in cb else cb
    c_shadow = c_specs.get("shadow") or ("0 4px 12px rgba(0,0,0,0.15)" if palette["is_dark"] else "0 2px 8px rgba(0,0,0,0.06)")
    b_border = "none" if not bb or bb.startswith("0px") or "none" in bb else bb

    prompt_preset = f"""You are designing modern web components matching {domain}.
- Theme: {'Dark' if palette['is_dark'] else 'Light'} Mode (Background: {palette['background']['hex']}, Surface: {palette['surface']['hex']})
- Typography:
  * Headings: {typo['display']} ({h1_d})
  * Body & UI: {typo['body']} ({body_d})
  {f"* Code & Mono: {typo['mono']} (fallback: monospace)" if typo['mono'] else ""}
- Brand Accent: {palette['accent']['hex']} (Buttons, active tabs, interactive highlights)
- Layout & Elevation:
  * Card radius: {radii['card']}, Border: {c_border}, Shadow: {c_shadow}
  * Button radius: {radii['button']}, Border: {b_border}"""

    design_md = f"""# Design DNA Specification: {title}
> Source URL: {url} | Base Theme: {'Dark' if palette['is_dark'] else 'Light'} Mode | Target: Claude Code / Cursor

## 1. Core Color Palette and Contrast Validation
| Semantic Role | Hex Value | RGB Value | Contrast vs BG | WCAG AA Status |
| :--- | :--- | :--- | :---: | :---: |
| Background (bg-background) | `{palette['background']['hex']}` | `{palette['background']['rgb']}` | - | Baseline |
| Surface (bg-surface) | `{palette['surface']['hex']}` | `{palette['surface']['rgb']}` | - | Elevated Container |
| Foreground / Text (text-primary) | `{palette['foreground']['hex']}` | `{palette['foreground']['rgb']}` | **{palette['foreground']['contrast']}:1** | {palette['foreground']['status']} |
| Accent / Brand (bg-accent) | `{palette['accent']['hex']}` | `{palette['accent']['rgb']}` | **{palette['accent']['contrast']}:1** | {palette['accent']['status']} |
| Muted Text (text-muted) | `{palette['muted']['hex']}` | `{palette['muted']['rgb']}` | - | Secondary Subtext |
| Border (border-border) | `{palette['border']['hex']}` | - | - | Dividers & Borders |

## 2. Typography Hierarchy and Fallbacks
- Display / Heading Font: `{typo['display']}` (Google Font fallback: `{typo['display_fallback']}`)
- Body / UI Font: `{typo['body']}` (Google Font fallback: `{typo['body_fallback']}`)
{f"- Monospace Font: `{typo['mono']}` (Google Font fallback: `{typo['mono_fallback']}`)" if typo['mono'] else "- Monospace Font: system-ui monospace"}

## 3. Surface and Spacing DNA
- Border Radii: Small `{radii['sm']}`, Medium/Card `{radii['md']}`, Large `{radii['lg']}`{f", Pill `{radii['pill']}`" if radii['pill'] else ""}
- Card Elevation: Border `{c_border}`, Shadow `{c_shadow}`

## 4. Cursor / Claude Code System Prompt Preset
```markdown
{prompt_preset}
```
"""
    save_markdown_report(design_md, out_dir / "DESIGN.md")

    tw = (["@theme {"] + [f"  --color-{k}: {palette[k]['hex']};" for k in ["background", "surface", "foreground", "muted", "accent", "border"]]
          + ["", f'  --font-display: "{typo["display"]}", {typo["display_fallback"]}, sans-serif;', f'  --font-body: "{typo["body"]}", {typo["body_fallback"]}, sans-serif;']
          + ([f'  --font-mono: "{typo["mono"]}", {typo["mono_fallback"]}, monospace;'] if typo["mono"] else [])
          + [""] + [f"  --radius-{k}: {radii[k]};" for k in ["sm", "md", "lg"]]
          + ([f"  --radius-pill: {radii['pill']};"] if radii["pill"] else []) + ["}\n"])
    (out_dir / "tailwind-theme.css").write_text("\n".join(tw), encoding="utf-8")

    manifest = {"title": title, "url": url, "palette": palette, "typography": typo, "radii": radii, "specs": specs, "prompt_preset": prompt_preset}
    (out_dir / "dna_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    svg_dir = out_dir / "svgs"; svg_dir.mkdir(parents=True, exist_ok=True)
    for i, svg in enumerate(data.get("svgs", [])): (svg_dir / f"asset_{i+1:02d}.svg").write_text(svg, encoding="utf-8")

    if obsidian:
        obs_md = f"""---\ntitle: "Visual Inspiration: {title}"\nsource: "{url}"\ntheme: "{'dark' if palette['is_dark'] else 'light'}"\ntags: [design-inspiration, vibe-coding, visual-dna]\n---\n# Visual DNA: {title}\n- Background: <span style="background-color: {palette['background']['hex']}; padding: 2px 8px; border-radius: 4px; border: 1px solid #777;">{palette['background']['hex']}</span>\n- Surface: <span style="background-color: {palette['surface']['hex']}; padding: 2px 8px; border-radius: 4px; border: 1px solid #777;">{palette['surface']['hex']}</span>\n- Accent: <span style="background-color: {palette['accent']['hex']}; color: #fff; padding: 2px 8px; border-radius: 4px;">{palette['accent']['hex']}</span>\n- Text: <span style="background-color: {palette['foreground']['hex']}; color: {'#000' if palette['is_dark'] else '#fff'}; padding: 2px 8px; border-radius: 4px;">{palette['foreground']['hex']}</span>\n\nExtracted Assets: {len(data.get('svgs', []))} SVGs | Heading Font: {typo['display']}\n"""
        save_markdown_report(obs_md, out_dir / "Obsidian_Inspiration.md")


async def download_images(image_urls: list[str], img_dir: Path):
    img_dir.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for idx, u in enumerate(image_urls[:10]):
            try:
                resp = await client.get(u, headers={"User-Agent": DEFAULT_USER_AGENT})
                if resp.status_code == 200 and len(resp.content) > 500:
                    ext = "png" if "png" in resp.headers.get("content-type", "") else ("svg" if "svg" in u else "jpg")
                    (img_dir / f"asset_{idx+1:02d}.{ext}").write_bytes(resp.content)
            except Exception: pass


async def process_site(url: str, output_base: Path, obsidian: bool = False) -> str:
    slug = (urlparse(url).netloc.replace("www.", "").split(".")[0] or "sample")
    site_dir = output_base / slug; site_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nAnalyzing: {url} ...")
    data = await scrape_visual_dna(url)
    palette = classify_palette(data)
    typo, radii = classify_typo_and_radii(data)
    print(f"Extracted: BG={palette['background']['hex']}, Surface={palette['surface']['hex']}, FG={palette['foreground']['hex']}, Accent={palette['accent']['hex']}, CardRadius={radii['card']}")
    generate_artifacts(url, data, palette, typo, radii, site_dir, obsidian=obsidian)
    await download_images(data["images"], site_dir / "images")
    zip_file = output_base / f"{slug}_design_dna.zip"
    create_zip_archive(source=site_dir, output_zip_path=zip_file)
    print(f"Done: {zip_file} ({os.path.getsize(zip_file):,} bytes)")
    return str(zip_file)


def main():
    parser = argparse.ArgumentParser(description="Visual DNA Extractor")
    parser.add_argument("url", help="Target URL")
    parser.add_argument("--format", choices=["default", "obsidian"], default="default")
    parser.add_argument("--output", default="outbox/p1/samples" if Path("outbox/p1").exists() else "design_dna_samples")
    args = parser.parse_args()
    asyncio.run(process_site(args.url, Path(args.output), obsidian=(args.format == "obsidian")))


if __name__ == "__main__":
    main()
