"use client";

import type { ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type MarkdownChildrenProps = { children?: ReactNode };
type MarkdownLinkProps = MarkdownChildrenProps & { href?: string };

export function MarkdownContent({ content }: { content: string }) {
    if (!content.trim()) {
        return <p className="text-sm text-slate-500">No content has been written yet.</p>;
    }

    return (
        <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
                h1: ({ children }: MarkdownChildrenProps) => (
                    <h1 className="mb-5 mt-8 text-3xl font-semibold text-slate-100 first:mt-0">
                        {children}
                    </h1>
                ),
                h2: ({ children }: MarkdownChildrenProps) => (
                    <h2 className="mb-4 mt-8 border-b border-slate-800 pb-2 text-2xl font-semibold text-slate-100">
                        {children}
                    </h2>
                ),
                h3: ({ children }: MarkdownChildrenProps) => (
                    <h3 className="mb-3 mt-6 text-xl font-semibold text-slate-100">{children}</h3>
                ),
                p: ({ children }: MarkdownChildrenProps) => (
                    <p className="my-4 leading-7 text-slate-300">{children}</p>
                ),
                a: ({ children, href }: MarkdownLinkProps) => (
                    <a
                        href={href}
                        className="text-adb-cyan-300 underline decoration-adb-cyan-700 underline-offset-4 hover:text-adb-cyan-200"
                    >
                        {children}
                    </a>
                ),
                ul: ({ children }: MarkdownChildrenProps) => (
                    <ul className="my-4 list-disc space-y-2 pl-6 text-slate-300">{children}</ul>
                ),
                ol: ({ children }: MarkdownChildrenProps) => (
                    <ol className="my-4 list-decimal space-y-2 pl-6 text-slate-300">{children}</ol>
                ),
                blockquote: ({ children }: MarkdownChildrenProps) => (
                    <blockquote className="my-5 border-l-4 border-adb-cyan-700 pl-4 text-slate-400">
                        {children}
                    </blockquote>
                ),
                code: ({ children }: MarkdownChildrenProps) => (
                    <code className="rounded bg-slate-950 px-1.5 py-0.5 text-sm text-adb-cyan-200">
                        {children}
                    </code>
                ),
                pre: ({ children }: MarkdownChildrenProps) => (
                    <pre className="my-5 overflow-x-auto rounded-xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-200 [&_code]:bg-transparent [&_code]:p-0">
                        {children}
                    </pre>
                ),
                table: ({ children }: MarkdownChildrenProps) => (
                    <div className="my-5 overflow-x-auto">
                        <table className="w-full border-collapse text-left text-sm text-slate-300">
                            {children}
                        </table>
                    </div>
                ),
                th: ({ children }: MarkdownChildrenProps) => (
                    <th className="border border-slate-700 bg-slate-900 px-3 py-2 font-semibold text-slate-100">
                        {children}
                    </th>
                ),
                td: ({ children }: MarkdownChildrenProps) => (
                    <td className="border border-slate-800 px-3 py-2">{children}</td>
                ),
                hr: () => <hr className="my-8 border-slate-800" />,
            }}
        >
            {content}
        </ReactMarkdown>
    );
}
