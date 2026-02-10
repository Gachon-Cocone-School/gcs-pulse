# Daily Snippet UX Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor the Daily Snippet editor to a single-view experience where AI analysis automatically updates the content and presents feedback below the editor, replacing the tabbed interface.

**Architecture:**
- **Single View:** Editor and Analysis Report are on the same page.
- **Auto-Replace:** AI structured content immediately replaces the editor content.
- **Undo Mechanism:** Toast notification (Sonner) allows reverting to original content.
- **Component Extraction:** Analysis UI logic moved to a dedicated component.

**Tech Stack:** React, Tailwind CSS, React Hook Form, Sonner (Toast), Lucide Icons.

---

### Task 1: Create SnippetAnalysisReport Component

Extract the visualization of AI feedback (scores, cards, etc.) from `SnippetForm.tsx` into a reusable component.

**Files:**
- Create: `apps/client/src/components/views/SnippetAnalysisReport.tsx`
- Reference: `apps/client/src/components/views/SnippetForm.tsx` (source of UI code)

**Step 1: Create the component file**
Copy the UI logic from `SnippetForm.tsx` (the content of `activeTab === "ai"`) into a new component.
It should accept `feedback` and `structuredContent` as props.

```tsx
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Sparkles, Brain, TrendingUp, Target, CheckCircle2, MessageCircle, Quote, Flag, Lightbulb } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";

// Define Feedback interface here or import if shared
export interface Feedback {
  total_score: number;
  scores: Record<string, { score: number; max_score: number }>;
  key_learning: string;
  learning_sources: string[];
  next_action: string;
  mentor_comment: string;
  next_reflection_mission?: string;
  anchoring_message?: string;
}

interface SnippetAnalysisReportProps {
    feedback: Feedback | null;
    structuredContent?: string | null;
}

// ... Implementation details from SnippetForm.tsx ...
```

**Step 2: Export Component**
Ensure it's exported correctly for use in `SnippetForm`.

---

### Task 2: Refactor SnippetForm State & UI Structure

Remove the tabbed interface and implement the single-view layout with the new "Star" button and Preview toggle.

**Files:**
- Modify: `apps/client/src/components/views/SnippetForm.tsx`

**Step 1: Remove Tab State**
Remove `activeTab`, `tabClasses` and the tab switching UI.
Add new state variables:
```tsx
const [showPreview, setShowPreview] = useState(false);
const [originalContent, setOriginalContent] = useState<string | null>(null);
const [isAnalyzed, setIsAnalyzed] = useState(false); // Controls visibility of report
```

**Step 2: Add Undo Logic with Sonner**
Import `toast` from `sonner`.
Update `handleOrganizeClick`:
1. Save current content.
2. Set `originalContent` to `currentContent`.
3. Call `onOrganize()`.
4. Update form content with new `structuredContent`.
5. `setIsAnalyzed(true)`.
6. Trigger Toast:
```tsx
toast("✨ AI가 내용을 다듬었습니다.", {
  action: {
    label: "원래대로 되돌리기",
    onClick: () => {
       setValue("content", originalContent);
       // Optional: setIsAnalyzed(false) if we want to hide the report too,
       // but keeping the report visible might be better.
    },
  },
});
```

**Step 3: Update Editor UI**
- Add "Preview" toggle button near the editor (e.g., top right of the editor area).
- Add "Star" button (floating or toolbar) that triggers `handleOrganizeClick`.
- Render `SnippetAnalysisReport` below the editor, conditionally visible:
```tsx
{isAnalyzed && feedback && (
    <div className="mt-8 animate-in slide-in-from-top-4 fade-in duration-500">
        <SnippetAnalysisReport feedback={feedback} structuredContent={structuredContent} />
    </div>
)}
```

**Step 4: Handle Read-Only Mode**
If `readOnly` is true, show the content (as markdown) and the report (if available) without the editor controls.

---

### Task 3: Cleanup & Integration

Ensure everything works together and clean up unused imports.

**Files:**
- Modify: `apps/client/src/components/views/SnippetForm.tsx`

**Step 1: Verify Imports**
Remove unused imports (e.g., icons only used in the extracted report component).

**Step 2: Test the flow**
- Write content -> Click Star -> Auto-update -> Toast appears -> Undo works.
- Check "Preview" toggle toggles between Textarea and Markdown view.
