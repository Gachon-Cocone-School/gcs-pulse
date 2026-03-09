import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";


const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[var(--theme-control-radius)] text-sm font-[var(--theme-button-font-weight)] tracking-[var(--theme-button-letter-spacing)] shadow-[var(--theme-control-shadow)] transition-[color,background-color,border-color,box-shadow] disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:border-[var(--sys-focus-visible)] focus-visible:ring-[color:var(--sys-focus-visible)]/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 aria-invalid:border-destructive",
  {
    variants: {
      variant: {
        default:
          "border border-[var(--sys-cta-primary-border)] border-[var(--theme-control-border-width)] bg-[var(--sys-cta-primary-bg)] text-[var(--sys-cta-primary-fg)] hover:bg-[var(--sys-cta-primary-hover)] active:bg-[var(--sys-cta-primary-active)] hover:shadow-[var(--theme-control-hover-shadow)]",
        destructive:
          "border border-destructive/20 border-[var(--theme-control-border-width)] bg-destructive text-destructive-foreground hover:bg-destructive/90 hover:shadow-[var(--theme-control-hover-shadow)] focus-visible:ring-destructive/20",
        outline:
          "border border-border border-[var(--theme-control-border-width)] bg-background text-foreground hover:bg-accent hover:text-accent-foreground hover:shadow-[var(--theme-control-hover-shadow)]",
        secondary:
          "border border-border border-[var(--theme-control-border-width)] bg-secondary text-secondary-foreground hover:bg-secondary/80 hover:shadow-[var(--theme-control-hover-shadow)]",
        ghost:
          "border border-transparent border-[var(--theme-control-border-width)] hover:border-border/60 hover:bg-accent hover:text-accent-foreground data-[state=active]:border-[var(--sys-current-border)] data-[state=active]:bg-[var(--sys-current-bg)] data-[state=active]:text-[var(--sys-current-fg)] hover:shadow-[var(--theme-control-hover-shadow)]",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2 has-[>svg]:px-3",
        sm: "h-8 gap-1.5 px-3 has-[>svg]:px-2.5",
        lg: "h-10 px-6 has-[>svg]:px-4",
        icon: "size-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

const ChevronDown = (p: React.SVGProps<SVGSVGElement>) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={2}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden
    {...p}
  >
    <path d="M6 9l6 6 6-6" />
  </svg>
);

const ChevronUp = (p: React.SVGProps<SVGSVGElement>) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={2}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden
    {...p}
  >
    <path d="M18 15l-6-6-6 6" />
  </svg>
);

function Button({
  className,
  variant,
  size,
  asChild = false,
  togglable = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
    togglable?: boolean;
  }) {
  const Comp = asChild ? Slot : "button";
  const [toggled, setToggled] = React.useState(false);

  // Extract onClick and children so we can wrap click behavior when togglable
  const { onClick, children, ...rest } = props as any;

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (togglable) setToggled((s: boolean) => !s);
    if (typeof onClick === "function") onClick(e);
  };

  return (
    <Comp
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      onClick={handleClick}
      aria-pressed={togglable ? toggled : undefined}
      {...rest}
    >
      {togglable ? (
        toggled ? (
          <ChevronUp className="size-4" />
        ) : (
          <ChevronDown className="size-4" />
        )
      ) : (
        children
      )}
    </Comp>
  );
}

export { Button };
