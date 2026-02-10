# Design System & Stitch Prompting Guide

## 1. Design Tokens (Current Implementation)

### Colors
**Primary Palette (Rose)**
- `primary`: Rose-500 (`#e8508b`)
- `primary-foreground`: White / Slate-50

**Accent Palette (Violet)**
- `accent`: Violet-500 (`#8b5cf6`)
- `accent-foreground`: White (implied)

**Neutral Palette (Slate)**
- Background: Slate-50 (`#f8fafb`)
- Text Main: Slate-900 (`#0f172a`)
- Text Muted: Slate-600 (`#475569`)

**Special Effects**
- **Mesh Gradient**: Rose (`d5386f`) + Violet (`8b5cf6`) radial mixing.
- **Glassmorphism**: `bg-white/75` with `backdrop-blur-md` and `border-white/40`.

### Typography
- **Font**: Inter (`var(--font-sans)`)
- **Headings**:
  - H1: 3rem, Bold (700)
  - H2: 2.25rem, Bold (700)
  - H3: 1.875rem, SemiBold (600)
- **Body**: Base 1rem, Small 0.875rem.

### Shapes & Spacing
- **Container Radius**: `rounded-xl` (Cards, Dialogs)
- **Element Radius**: `rounded-md` (Buttons, Inputs)
- **Border Width**: 1px (default)
- **Input Height**: `h-9` (36px) standard

---

## 2. Stitch AI Prompt Template

Use the following "Context Block" when asking Stitch to generate new screens. This ensures the AI follows your established design system.

### 📋 Context Block (Copy & Paste this first)

```markdown
**Design System Context**
Target a modern, premium web application with the following specs:

**Visual Style:**
- **Theme**: "Soft Modern" with Glassmorphism.
- **Colors**: 
  - Primary: Rose Pink (#e8508b) for main actions.
  - Accent: Violet (#8b5cf6) for gradients and highlights.
  - Background: Very light slate (#f8fafb) with subtle mesh gradients.
- **Components**:
  - Cards: White background, 75% opacity (glass effect), rounded-xl, thin border, subtle shadow.
  - Buttons: Rounded-md, solid rose-500 for primary, ghost/outline for secondary.
  - Inputs: Rounded-md, h-9 (compact), slate-100 background on focus.
- **Typography**: Inter font, clean, high contrast headings (Slate-900).

**Technical Constraints:**
- Framework: Next.js + Tailwind CSS v4.
- Icons: Lucide React.
- Components: Radix UI primitives (where complex interactivity is needed).
```

---

## 3. Recommended Improvements

### A. Consistency Check
- **Radius Mismatch**: Cards use `rounded-xl` while buttons use `rounded-md`. This is acceptable as "nested curvature" (outer > inner), but verify if `rounded-lg` for buttons might feel more organic with `xl` cards.
- **Hardcoded Hex in Global CSS**: `globals.css` mixes `oklch` and standard Hex.
  - *Recommendation*: Standardize to `oklch` for better color mixing in gradients if supporting modern browsers, or stick to configured Hex for safety.

### B. Missing Components based on usage
- **Page Header**: Standardize a "Page Header" component that includes Breadcrumbs + H2 Title + Primary Action Button, as this pattern appears often.

---

## 4. Automated UI Generation (MCP Workflow)

Our agent system is integrated with Stitch via MCP. Instead of manually copying the context, the Agent should use the `mcp_stitch_generate_screen_from_text` tool directly.

**Target Project ID**: `10028458738181177293` (Project Name: GCS LMS)

**Agent Instructions**:
1.  **Retrieve Context**: Read the "Context Block" from Section 2 of this file or `stitch_prompt_context.md` in the artifacts.
2.  **Combine Prompt**:
    ```
    [Context Block]
    
    [User's Request]
    ```
3.  **Execute Tool**:
    Use the `mcp_stitch_generate_screen_from_text` tool with:
    - `project_id`: `10028458738181177293`
    - `prompt`: The combined prompt from step 2.
    - `model_id`: `GEMINI_3_PRO` (recommended for better design adherence)
4.  **Process Result**: The tool returns generated components or code. Present this to the user for review.

---

## 5. Workflow: Manual Generation (Fallback)

1.  **Define Goal**: "I need a User Settings page."
2.  **Paste Context**: Copy the Context Block above.
3.  **Add Specifics**:
    > "Create a User Settings page...."
4.  **Refine**: If the output looks too generic, add: "Apply the `.glass-card` class..."
