import * as React from "react";

import { cn } from "@/lib/utils";

function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        "resize-none border-input placeholder:text-muted-foreground bg-input-background text-foreground flex field-sizing-content min-h-16 w-full rounded-[var(--theme-control-radius)] border border-[var(--theme-control-border-width)] px-3 py-2 text-sm shadow-[var(--theme-control-shadow)] transition-[color,border-color,box-shadow] outline-none",
        "focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] focus-visible:shadow-[var(--theme-control-hover-shadow)]",
        "aria-invalid:ring-destructive/20 aria-invalid:border-destructive disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}

export { Textarea };
