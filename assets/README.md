# KasirKita — Asset System

This directory contains first-party visual assets for KasirKita Desktop. Assets should remain lightweight, local, and usable without a network connection or paid service.

## Directory map

- `brand/` — approved logo, app icon, and brand exports.
- `icons/` — interface icon sources and runtime-ready exports.
- `splash/` — startup screen artwork and loading visuals.
- `themes/` — visual design tokens such as colors, spacing, and typography.

## Brand asset status

The official KasirKita logo is still being prepared separately. Do not invent or permanently substitute a logo before the approved files arrive. When supplied, preserve the original master and add appropriately sized exports for the application window, splash screen, and Windows icon.

## Compatibility and cost rules

- No remote fonts, CDNs, hosted images, paid icon packs, or runtime downloads.
- Prefer small, locally bundled assets.
- Use SVG as a scalable source when useful, but do not assume Tkinter can render SVG directly. Any asset used by Tkinter at runtime must have a supported local format such as PNG or GIF.
- Keep icons visually consistent: simple silhouettes, consistent stroke weight, and readable at small sizes.
- Avoid large background images and effects that make the app slow on older laptops.
- Keep brand colors centralized in `themes/theme.json`; avoid defining conflicting palettes across screens.

## Planned visual direction

- Deep navy for navigation and important structure.
- Clean neutral surfaces for work areas.
- Restrained cyan accent for primary actions and focus states.
- Clear typography, readable contrast, consistent spacing, and calm feedback states.
- Prioritize usability and clarity over decorative animation.

## Status

This is the initial asset foundation. It does not mean the logo, splash screen, or full UI redesign is finished or integrated yet.
