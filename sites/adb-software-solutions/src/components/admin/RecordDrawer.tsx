"use client";

import { Button, ButtonLink } from "@/components/ui";
import { ReactNode, useEffect } from "react";

export function RecordDrawer({
    children,
    onClose,
    fullPageHref,
}: {
    children: ReactNode;
    onClose: () => void;
    fullPageHref?: string;
}) {
    useEffect(() => {
        const previousOverflow = document.body.style.overflow;
        document.body.style.overflow = "hidden";

        function handleKeyDown(event: KeyboardEvent) {
            if (event.key === "Escape") onClose();
        }

        window.addEventListener("keydown", handleKeyDown);
        return () => {
            document.body.style.overflow = previousOverflow;
            window.removeEventListener("keydown", handleKeyDown);
        };
    }, [onClose]);

    return (
        <div className="fixed inset-0 z-50 flex justify-end">
            <button
                type="button"
                aria-label="Close details"
                onClick={onClose}
                className="absolute inset-0 bg-black/65 backdrop-blur-[1px]"
            />
            <aside className="relative h-full w-full overflow-y-auto border-l border-slate-800 bg-slate-950 shadow-2xl shadow-black/50 sm:max-w-4xl 2xl:max-w-6xl">
                <div className="sticky top-0 z-20 flex items-center justify-end gap-2 border-b border-slate-800 bg-slate-950/95 px-5 py-3 backdrop-blur">
                    {fullPageHref ? (
                        <ButtonLink href={fullPageHref} variant="ghost" size="sm">
                            Open full page
                        </ButtonLink>
                    ) : null}
                    <Button type="button" variant="ghost" size="sm" onClick={onClose}>
                        Close
                    </Button>
                </div>
                <div className="p-5 sm:p-7">{children}</div>
            </aside>
        </div>
    );
}
