---
version: alpha
name: GBIF Dark Atlas
description: A high-contrast scientific interface with a nature-forward accent and restrained, utility-first presentation.
colors:
  primary: "#61A350"
  secondary: "#0079B5"
  tertiary: "#94A3B8"
  neutral: "#121212"
  surface: "#FFFFFF"
  on-surface: "#FFFFFF"
  on-surface-muted: "#D1D5DB"
  border: "#374151"
  info: "#0B84C6"
  error: "#D64545"
typography:
  headline-display:
    fontFamily: "Helvetica Neue"
    fontSize: "48px"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "0px"
  headline-lg:
    fontFamily: "Helvetica Neue"
    fontSize: "36px"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "-0.75px"
  headline-md:
    fontFamily: "Times New Roman"
    fontSize: "28px"
    fontWeight: 600
    lineHeight: "34px"
    letterSpacing: "0px"
  headline-sm:
    fontFamily: "Helvetica Neue"
    fontSize: "21px"
    fontWeight: 500
    lineHeight: "28px"
    letterSpacing: "0px"
  body-lg:
    fontFamily: "Helvetica Neue"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: "28px"
    letterSpacing: "0px"
  body-md:
    fontFamily: "Helvetica Neue"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: "28px"
    letterSpacing: "0px"
  body-sm:
    fontFamily: "Helvetica Neue"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: "20px"
    letterSpacing: "0px"
  label-lg:
    fontFamily: "Helvetica Neue"
    fontSize: "16px"
    fontWeight: 700
    lineHeight: "24px"
    letterSpacing: "0px"
  label-md:
    fontFamily: "Helvetica Neue"
    fontSize: "14px"
    fontWeight: 700
    lineHeight: "20px"
    letterSpacing: "0px"
  label-sm:
    fontFamily: "Helvetica Neue"
    fontSize: "12px"
    fontWeight: 700
    lineHeight: "16px"
    letterSpacing: "0px"
  caption:
    fontFamily: "Helvetica Neue"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: "16px"
    letterSpacing: "0px"
rounded:
  none: 0px
  sm: 3px
  md: 4px
  lg: 8px
  xl: 12px
  full: 9999px
spacing:
  xs: 6px
  sm: 16px
  md: 24px
  lg: 40px
  xl: 64px
components:
  button-primary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.secondary}"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: "11px 20px"
    height: "38px"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.on-surface}"
    typography: "{typography.label-md}"
    rounded: "{rounded.sm}"
    padding: "11px 20px"
    height: "38px"
  button-link:
    backgroundColor: "transparent"
    textColor: "{colors.primary}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.none}"
    padding: "0px"
  card:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.lg}"
    padding: "16px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.neutral}"
    rounded: "{rounded.sm}"
    padding: "16px"
  chip:
    backgroundColor: "{colors.border}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.full}"
    padding: "6px 12px"
---

# GBIF Dark Atlas

## Overview
GBIF presents as a globally credible, science-forward information platform with a strong conservation and research identity. The tone is professional, calm, and authoritative, but the large wildlife imagery and green accent add an accessible, human, and nature-connected quality. Layouts feel spacious and data-led, prioritizing clarity, trust, and quick scanning over decorative complexity.

## Colors
- **Primary (#61A350):** A nature-green accent used for links and calls to action. It signals ecology, sustainability, and discovery without overpowering the interface.
- **Secondary (#0079B5):** A clean institutional blue that supports action states and navigational emphasis. It pairs with the green accent to reinforce credibility and public-service utility.
- **Tertiary (#94A3B8):** A muted slate used for outlines, subtle UI support, and secondary text treatments. It softens the interface while preserving legibility against dark backgrounds.
- **Neutral (#121212):** The deep near-black base for the system. It anchors the dark theme, allowing imagery, white text, and bright data points to stand out.
- **Surface (#FFFFFF):** The light surface color used for search fields and selected controls. It creates high contrast inside the otherwise dark visual system.
- **On-surface (#FFFFFF):** The main text color for dark sections, ensuring crisp readability over imagery and charcoal surfaces.
- **On-surface-muted (#D1D5DB):** A softer light gray for supporting labels and less prominent content. It reduces visual noise while keeping the UI readable.
- **Border (#374151):** A restrained charcoal border for cards and outlined elements. It provides structure without introducing strong contrast.
- **Info (#0B84C6):** A supporting blue for informational emphasis and interface feedback where needed.
- **Error (#D64545):** Reserved for invalid states and destructive feedback, intentionally vivid so it remains distinct from the core brand palette.

## Typography
The system is built around Helvetica Neue for most UI and editorial copy, producing a clean, modern, highly legible tone. Headlines use strong weights and compact line heights, with the largest display setting at 48px and smaller headers stepping down in a disciplined hierarchy. A serif accent appears in `headline-md` and `button-link`, giving select areas a more editorial, published feel.

Body text stays at 16px with a 28px line height, which supports readability in dense data contexts and long-form content. Labels and calls to action are bold and efficient, with a clear utility-first voice. Letter spacing is essentially neutral; the interface does not rely on uppercase or wide tracking for emphasis, preferring weight, size, and contrast.

## Layout
The layout follows a broad, fluid hero-first structure with ample horizontal breathing room and centered content blocks. The top navigation stretches across the page, while the hero overlays text on immersive imagery to create a strong focal point. Below the hero, metrics are arranged in evenly spaced columns, suggesting a predictable grid and a balanced, data-dashboard rhythm.

Spacing is conservative and modular, using a small rhythm of 6px, 16px, 24px, 40px, and 64px. Controls and content clusters use tight vertical stacking inside larger section paddings, which keeps the page feeling spacious without becoming sparse. Cards and inset elements generally prefer internal padding around 16px, while major sections open up to 40px or 64px separations.

## Elevation & Depth
The system is intentionally flat and low-elevation. Depth is communicated more through image layering, tonal overlays, and contrast between dark backgrounds and white surfaces than through dramatic shadows. When shadows appear, they are subtle and functional, as seen in the primary button treatment; the broader interface avoids heavy material depth.

Borders and translucency do much of the hierarchy work. Dark panels, white search fields, and thin outlines create separation without visual clutter, which fits the site’s scientific and documentary tone.

## Shapes
The shape language is restrained and mostly rectangular. Corners are slightly softened with 3px to 8px radii, enough to reduce harshness while preserving an analytical, structured feel. Primary controls read as simple, practical forms rather than playful pills or highly rounded cards.

Use `rounded.md` for core inputs and prominent controls, `rounded.sm` for secondary buttons, and `rounded.lg` for cards. Full rounding is reserved for chips or compact status tokens when needed.

## Components
Buttons are practical and text-forward. `button-primary` is a white, high-contrast action with blue text, 11px 20px padding, and a 38px target height; it should feel authoritative and clickable, not decorative. `button-secondary` is an outlined variant with transparent fill and white text for dark sections, while `button-link` is a lightweight underlined text action for tertiary navigation.

Cards should use the dark `card` treatment: charcoal background, 1px border, 8px radius, and 16px padding. Keep card content compact and readable, with enough internal spacing for metrics, summaries, or feature modules, but avoid excessive shadowing. Cards should look like information containers, not floating panels.

Inputs use a bright surface treatment to stand out against the dark UI. The search field is the model: white background, dark text, comfortable horizontal padding, and minimal chrome. Focus states should emphasize clarity and accessibility rather than ornament.

Chips and small category tags should be understated and functional, typically using full rounding, muted fills, and concise labels. They should support navigation and filtering without competing with the hero or metric content. Iconography should remain thin, simple, and monochrome to match the system’s disciplined feel.

## Do's and Don'ts
- Do keep the interface high-contrast and readable, especially over photographic backgrounds.
- Do use the green primary accent sparingly for key links and primary calls to action.
- Do preserve generous whitespace around major content groups and metrics.
- Do prefer simple borders and subtle shadows over heavy elevation effects.
- Don't introduce bright gradients, neon colors, or highly saturated decorative surfaces.
- Don't over-round controls or cards; the system should stay crisp and architectural.
- Don't use playful illustration styles or informal type treatments that weaken the scientific tone.
- Don't crowd the hero area; headline, navigation, and search must remain immediately scannable.
