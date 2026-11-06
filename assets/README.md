# KasirKita — Asset System

This directory contains first-party visual assets for KasirKita Desktop. Assets should remain lightweight, local, and usable without a network connection or paid service.

## Directory map

- `brand/` — approved TCS identity logo and KasirKita-specific brand assets.
- `icons/` — interface icon sources and runtime-ready exports.
- `splash/` — startup screen artwork and loading visuals.
- `themes/` — visual design tokens such as colors, spacing, and typography.

## TCS identity asset

The website and brand source logo is `brand/tcs-logo-resmi.svg`. It has been replaced using the owner-provided reference image. Keep the official artwork unchanged. Never create, redraw, add decorative lines to, or substitute the TCS logo.

KasirKita-specific visual assets remain separate and must not be confused with the TCS identity.

## Compatibility and cost rules

- No remote fonts, CDNs, hosted images, paid icon packs, or runtime downloads.
- Prefer small, locally bundled assets.
- Use SVG as a scalable source when useful, but do not assume Tkinter can render SVG directly. Any asset used by Tkinter at runtime must have a supported local format such as PNG or GIF.
- Keep icons visually consistent: simple silhouettes, consistent stroke weight, and readable at small sizes.
- Avoid large background images and effects that make the app slow on older laptops.

## Status

This is the initial asset foundation. It does not mean the logo, splash screen, or full UI redesign is finished or integrated yet.
