# AGENTS.md (src/styles)

## OVERVIEW
This directory contains secondary or legacy global CSS files. The primary global styling configuration is managed within `src/app/globals.css`.

## WHERE TO LOOK
- `src/styles/globals.css`: A secondary global stylesheet. It contains a subset of design tokens (colors, typography, spacing) and base HTML styles.

## CONVENTIONS
- **Secondary Status**: Files in this directory should be treated as secondary. Do not use them as the primary source of styling for new components or pages.
- **Design Tokens**: Basic color variables (slate, rose, violet, coral) are defined here using CSS variables, but these are often redundant with the Tailwind v4 configuration in the App Router.

## ANTI-PATTERNS
- **Adding New Globals**: Do not add new global styles or Tailwind directives to this directory. All primary styling should be added to `src/app/globals.css`.
- **Primary Imports**: Avoid importing these stylesheets into the main application layout unless specifically required for legacy compatibility.

## NOTES
- **Legacy/Supplementary**: This file exists alongside `src/app/globals.css`. While it shares similar token names, `src/app/globals.css` is the source of truth for the Next.js App Router environment and contains the full Tailwind v4 setup.
- **Redundancy**: Much of the content in `src/styles/globals.css` is redundant with the primary configuration in `src/app/globals.css`. Use caution when modifying to avoid unexpected style overrides.
