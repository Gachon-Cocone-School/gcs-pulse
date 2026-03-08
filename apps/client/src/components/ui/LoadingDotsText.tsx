import * as React from "react";

import { cn } from "@/lib/utils";

interface LoadingDotsTextProps {
  text: string;
  className?: string;
  textClassName?: string;
  ariaLabel?: string;
  children?: React.ReactNode;
}

export function LoadingDotsText({
  text,
  className,
  textClassName,
  ariaLabel = "loading dots",
  children,
}: LoadingDotsTextProps) {
  return (
    <div className={cn("flex items-center gap-1", className)}>
      <span className="flex items-center gap-1">
        <span className={cn("animate-pulse", textClassName)}>{text}</span>
        <span className="inline-flex" aria-label={ariaLabel}>
          <span className="animate-pulse">.</span>
          <span className="animate-pulse [animation-delay:150ms]">.</span>
          <span className="animate-pulse [animation-delay:300ms]">.</span>
        </span>
      </span>
      {children}
    </div>
  );
}
