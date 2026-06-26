---
version: alpha
name: GBIF Light Atlas
description: A high-contrast scientific interface on a light surface, with a nature-forward accent and restrained, utility-first presentation, matching gbif.org.
colors:
  primary: "#61A350"
  secondary: "#0079B5"
  tertiary: "#94A3B8"
  ink: "#121212"
  surface: "#FFFFFF"
  muted: "#475569"
  panel: "#ECEEF6"
  hairline: "#E2E8F0"
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
    fontFamily: "Helvetica Neue"
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
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.surface}"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: "11px 20px"
    height: "38px"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    border: "1px solid {colors.hairline}"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: "11px 20px"
    height: "38px"
  button-link:
    backgroundColor: "transparent"
    textColor: "{colors.primary}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.none}"
    padding: "0px"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    border: "1px solid {colors.hairline}"
    rounded: "{rounded.lg}"
    padding: "16px"
  panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "40px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    border: "1px solid {colors.hairline}"
    rounded: "{rounded.md}"
    padding: "10px 16px"
  chip:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.muted}"
    rounded: "{rounded.full}"
    padding: "6px 12px"
---

# GBIF Light Atlas

## Overview
GBIF presents as a globally credible, science-forward information platform with a strong conservation and research identity. The tone is professional, calm, and authoritative, while the green accent adds an accessible, human, and nature-connected quality. The interface uses a light surface that matches gbif.org: white backgrounds, dark text, and thin neutral borders. Layouts feel spacious and data-led, prioritizing clarity, trust, and quick scanning over decorative complexity.

## Colors
- **Primary (#61A350):** A nature-green accent used for links and calls to action. It signals ecology, sustainability, and discovery without overpowering the interface.
- **Secondary (#0079B5):** A clean institutional blue used for primary actions and navigational emphasis. It pairs with the green accent to reinforce credibility and public-service utility.
- **Tertiary (#94A3B8):** A muted slate used for placeholder text and subtle UI support.
- **Ink (#121212):** The near-black primary text color, used for headings and body copy on the light surface.
- **Surface (#FFFFFF):** The page background and the fill for cards, inputs, and most controls.
- **Muted (#475569):** A slate gray for secondary text, labels, and supporting copy. It reduces visual noise while staying readable.
- **Panel (#ECEEF6):** A pale blue-gray used for the hero block, summary surfaces, and chips, giving gentle separation from the white surface without a border.
- **Hairline (#E2E8F0):** A light border used for cards, inputs, dividers, and outlined controls. It provides structure without strong contrast.
- **Info (#0B84C6):** A supporting blue for informational emphasis and interface feedback where needed.
- **Error (#D64545):** Reserved for invalid states, flagged counts, and destructive feedback, intentionally vivid so it remains distinct from the core brand palette.

## Typography
The system is built around Helvetica Neue for all UI and editorial copy, producing a clean, modern, highly legible tone. Headlines use strong weights and compact line heights, with the largest display setting at 48px and smaller headers stepping down in a disciplined hierarchy.

Body text stays at 16px with a 28px line height, which supports readability in dense data contexts and long-form content. Labels and calls to action are bold and efficient, with a clear utility-first voice. Letter spacing is essentially neutral; the interface does not rely on uppercase or wide tracking for emphasis, preferring weight, size, and contrast.

## Layout
The layout follows a broad, fluid hero-first structure with ample horizontal breathing room and left-aligned content blocks within a centered maximum width. The top navigation stretches across the page; on small screens the links collapse into a menu button. Below the hero, metrics and how-to cards are arranged in evenly spaced columns, suggesting a predictable grid and a balanced, data-dashboard rhythm.

Spacing is conservative and modular, using a small rhythm of 6px, 16px, 24px, 40px, and 64px. Controls and content clusters use tight vertical stacking inside larger section paddings, which keeps the page feeling spacious without becoming sparse. Cards and inset elements generally prefer internal padding around 16px, while major sections open up to 40px or 64px separations.

## Elevation & Depth
The system is intentionally flat and low-elevation. Depth is communicated through thin hairline borders and the soft contrast between the white surface and the pale panel fill, rather than through dramatic shadows. When shadows appear, they are subtle and functional, as on floating overlays such as the map controls and the welcome card; the broader interface avoids heavy material depth.

Borders and tonal panels do most of the hierarchy work. White cards, pale panels, and thin outlines create separation without visual clutter, which fits the scientific and documentary tone.

## Shapes
The shape language is restrained and mostly rectangular. Corners are slightly softened with 3px to 8px radii, enough to reduce harshness while preserving an analytical, structured feel. Primary controls read as simple, practical forms rather than playful pills or highly rounded cards.

Use `rounded.md` for core inputs and prominent controls, `rounded.lg` for cards and panels, and `rounded.full` for chips or compact status tokens.

## Components
Buttons are practical and text-forward. `button-primary` is a solid blue action with white text, 11px 20px padding, and a 38px target height; it should feel authoritative and clickable, not decorative. `button-secondary` is an outlined variant with a white fill, dark text, and a hairline border. `button-link` is a lightweight green text action for tertiary navigation.

Cards use a white fill, a 1px hairline border, an 8px radius, and 16px padding. Keep card content compact and readable, with enough internal spacing for metrics, summaries, or feature modules, but avoid excessive shadowing. Cards should look like information containers, not floating panels. The hero and summary blocks use the `panel` surface (pale blue-gray, no border) to set themselves apart from plain cards.

Inputs use a white surface with a hairline border and dark text. The search field is the model: white background, comfortable horizontal padding, and minimal chrome. Focus states emphasize clarity and accessibility, shifting the border to the secondary blue rather than adding ornament.

Chips and small category tags are understated and functional, typically using full rounding, the pale panel fill, and concise labels. They support navigation and filtering without competing with the hero or metric content. Iconography remains thin, simple, and monochrome to match the disciplined feel.

## Do's and Don'ts
- Do keep the interface high-contrast and readable: dark text on white, with the pale panel for gentle grouping.
- Do use the green primary accent sparingly for key links, and the blue secondary for primary actions.
- Do preserve generous whitespace around major content groups and metrics.
- Do prefer thin hairline borders and subtle shadows over heavy elevation effects.
- Don't introduce bright gradients, neon colors, or highly saturated decorative surfaces.
- Don't over-round controls or cards; the system should stay crisp and architectural.
- Don't use playful illustration styles or informal type treatments that weaken the scientific tone.
- Don't crowd the hero area; headline, navigation, and search must remain immediately scannable.
