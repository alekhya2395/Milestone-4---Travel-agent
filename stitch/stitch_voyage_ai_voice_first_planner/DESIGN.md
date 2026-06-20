---
name: Voyage AI Design System
colors:
  surface: '#10131a'
  surface-dim: '#10131a'
  surface-bright: '#363941'
  surface-container-lowest: '#0b0e15'
  surface-container-low: '#191c22'
  surface-container: '#1d2027'
  surface-container-high: '#272a31'
  surface-container-highest: '#32353c'
  on-surface: '#e0e2ec'
  on-surface-variant: '#bacac5'
  inverse-surface: '#e0e2ec'
  inverse-on-surface: '#2d3038'
  outline: '#859490'
  outline-variant: '#3c4a46'
  surface-tint: '#3cddc7'
  primary: '#57f1db'
  on-primary: '#003731'
  primary-container: '#2dd4bf'
  on-primary-container: '#00574d'
  inverse-primary: '#006b5f'
  secondary: '#ffb95f'
  on-secondary: '#472a00'
  secondary-container: '#ee9800'
  on-secondary-container: '#5b3800'
  tertiary: '#e0d3ff'
  on-tertiary: '#381385'
  tertiary-container: '#c6b3ff'
  on-tertiary-container: '#5538a2'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#62fae3'
  primary-fixed-dim: '#3cddc7'
  on-primary-fixed: '#00201c'
  on-primary-fixed-variant: '#005047'
  secondary-fixed: '#ffddb8'
  secondary-fixed-dim: '#ffb95f'
  on-secondary-fixed: '#2a1700'
  on-secondary-fixed-variant: '#653e00'
  tertiary-fixed: '#e8ddff'
  tertiary-fixed-dim: '#cebdff'
  on-tertiary-fixed: '#21005e'
  on-tertiary-fixed-variant: '#4f319c'
  background: '#10131a'
  on-background: '#e0e2ec'
  surface-variant: '#32353c'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base_unit: 8px
  container_max_width: 1280px
  gutter: 24px
  margin_mobile: 16px
  margin_desktop: 48px
---

## Brand & Style
The brand personality is high-end, intelligent, and serenely futuristic. It targets the "modern explorer"—users who value precision and seamlessness in their travel planning. The UI evokes a sense of calm reliability through deep, nocturnal backgrounds, punctuated by vibrant accents that suggest the presence of a sophisticated AI agent.

The design style is **Modern/Tech-Forward** with a heavy influence of **Glassmorphism**. It utilizes subtle glows, blurred backdrops, and precise 1px borders to create a layered, "dashboard of the future" feel. The interface feels light despite its dark palette, prioritizing "active" states with soft bioluminescent effects.

## Colors
The palette is rooted in a deep charcoal base to minimize eye strain during late-night planning sessions. 

- **Primary (Electric Teal):** Used for essential actions and the "Active" state of the AI assistant.
- **Secondary (Warm Amber):** Specifically reserved for financial/budgeting indicators to provide high-contrast visibility against the dark base.
- **Voice Accent (Soft Violet):** Defines the "Listening" and "Thinking" states of the AI orb.
- **Surfaces:** Use a tiered gray system. The base background is `#0B0D10`, while cards use `#1A1D24` with a consistent 1px `#2A2F38` border to maintain definition without relying on heavy shadows.

## Typography
The system relies exclusively on **Inter** to ensure maximum legibility and a systematic, clean aesthetic. 

- **Display & Headlines:** Use tighter letter spacing and heavier weights to anchor the page.
- **Body Text:** Uses standard weights for high readability against dark backgrounds.
- **Labels:** Small labels use uppercase styling with increased letter spacing to distinguish metadata (like flight numbers or dates) from narrative content.
- **AI Transcription:** Transcription bubbles should use `body-lg` to prioritize the conversational interface.

## Layout & Spacing
The system utilizes an **8px grid** for all spatial relationships. 

- **Grid:** A 12-column fluid grid on desktop, transitioning to a 4-column grid on mobile.
- **Margins:** 48px horizontal margins on desktop to allow the content to "breathe" in the center of the screen.
- **Safe Areas:** AI Voice controls (the Mic Orb) are always positioned in a floating safe area at the bottom center of the viewport, detached from the main content grid.

## Elevation & Depth
Depth is created through **Tonal Layering** and **Subtle Glows** rather than traditional shadows.

1.  **Level 0 (Background):** `#0B0D10` - The infinite canvas.
2.  **Level 1 (Cards):** `#1A1D24` with a 1px border.
3.  **Level 2 (Modals/Active Cards):** `#22262E`. These elements receive a "Primary Glow"—a very low-opacity (10%) teal drop shadow with a large 32px blur to simulate a bioluminescent underside.
4.  **Glassmorphism:** Use a `backdrop-filter: blur(12px)` on navigation bars and floating AI transcription bubbles to maintain context of the underlying map or itinerary.

## Shapes
The design system uses a consistent **16px (1rem) radius** for all primary containers, cards, and input fields. This softness balances the "tech" feel of the teal and violet accents, making the app feel approachable.

- **Buttons:** Fully rounded (pill) for secondary actions; 12px radius for primary CTAs.
- **AI Orb:** Perfect circle.
- **Badges:** 4px radius for a sharper, more technical "tag" look.

## Components

### AI Voice UI
- **Mic Button:** A circular button with a 2px Electric Teal stroke. When active, it pulses with a Soft Violet outer glow.
- **Waveforms:** 3px wide bars with rounded caps, varying in height based on input frequency, colored with a gradient from Teal to Violet.
- **The Orb:** A multi-layered radial gradient (`primary` to `tertiary` to `transparent`) that expands and contracts during processing.

### Buttons & Controls
- **Primary CTA:** Background `primary_color_hex`, text `#0B0D10` (High contrast).
- **Secondary CTA:** Ghost style with 1px `border_subtle` and white text.
- **Chips/Badges:** Small, condensed text within a slightly lighter surface (`#2A2F38`). Groq and Gemini badges should use their respective brand colors at 20% opacity for the background with full-color text.

### Cards & Lists
- **Itinerary Cards:** Use `#1A1D24` surfaces. Hovering over a card increases the border brightness to `primary_color_hex` at 50% opacity.
- **Budget Items:** Use the Secondary (Amber) color for the currency amount to ensure financial data is the most prominent element in the list.

### Input Fields
- Dark backgrounds (`#0B0D10`) with 1px border. Focus state changes border to Teal and adds a subtle internal glow.