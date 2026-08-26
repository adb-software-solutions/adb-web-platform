import { cn } from "@/lib/utils/cn";
import { HTMLAttributes } from "react";

const variantStyles = {
    neutral: "border-slate-700 bg-slate-800/70 text-slate-300",
    info: "border-cyan-900/70 bg-cyan-950/50 text-cyan-200",
    success: "border-emerald-900/70 bg-emerald-950/50 text-emerald-200",
    warning: "border-amber-900/70 bg-amber-950/50 text-amber-200",
    danger: "border-red-900/70 bg-red-950/50 text-red-200",
};

type BadgeVariant = keyof typeof variantStyles;

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
    variant?: BadgeVariant;
}

export function Badge({
    className,
    variant = "neutral",
    ...props
}: BadgeProps) {
    return (
        <span
            className={cn(
                "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium",
                variantStyles[variant],
                className,
            )}
            {...props}
        />
    );
}
