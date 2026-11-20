import { lazy, Suspense, memo, type ReactNode } from "react"
import Markdown, { type Components } from "react-markdown"
import remarkGfm from "remark-gfm"
import { ExternalLink } from "lucide-react"

import { cn } from "@/lib/utils"

const CodeBlock = lazy(() => import("./code-block"))

/**
 * Renders an assistant answer. Safe by default: react-markdown does not
 * render raw HTML, so model or Places text can't inject markup. The agents
 * sometimes emit literal <br/> tags; those become line breaks first.
 */
function normalize(md: string) {
  return md
    .replace(/<br\s*\/?>\s*/gi, "  \n")
    .replace(/\n{3,}/g, "\n\n")
    .trim()
}

function textOf(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node)
  if (Array.isArray(node)) return node.map(textOf).join("")
  if (node && typeof node === "object" && "props" in node) return textOf((node as { props: { children?: ReactNode } }).props.children)
  return ""
}

const components: Components = {
  // The page owns h1/h2; answer headings start at h3.
  h1: ({ children }) => <h3 className="mt-8 mb-3 text-title font-semibold first:mt-0">{children}</h3>,
  h2: ({ children }) => <h3 className="mt-8 mb-3 text-title font-semibold first:mt-0">{children}</h3>,
  h3: ({ children }) => <h3 className="mt-7 mb-2 border-b pb-2 text-heading font-semibold first:mt-0">{children}</h3>,
  h4: ({ children }) => <h4 className="mt-5 mb-1.5 text-base font-semibold">{children}</h4>,
  h5: ({ children }) => <h4 className="mt-4 mb-1 text-base font-semibold">{children}</h4>,
  h6: ({ children }) => <h4 className="mt-4 mb-1 text-sm font-semibold">{children}</h4>,
  p: ({ children }) => <p className="my-3 first:mt-0 last:mb-0">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold text-ink">{children}</strong>,
  em: ({ children }) => <em>{children}</em>,
  ul: ({ children }) => <ul className="my-3 list-disc space-y-1.5 pl-5 marker:text-gray-strong">{children}</ul>,
  ol: ({ children }) => <ol className="my-3 list-decimal space-y-3 pl-6 marker:font-semibold marker:text-muted-foreground">{children}</ol>,
  li: ({ children }) => <li className="pl-1 [&>p]:my-1 [&>ul]:my-1.5">{children}</li>,
  a: ({ children, href }) => {
    const external = href ? /^https?:\/\//.test(href) : false
    return (
      <a
        href={href}
        {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
        className="font-medium text-raspberry underline decoration-raspberry/40 underline-offset-2 hover:decoration-raspberry break-words"
      >
        {children}
        {external && (
          <>
            <ExternalLink className="ml-0.5 inline size-3.5 align-[-2px]" aria-hidden="true" />
            <span className="sr-only"> (opens in a new tab)</span>
          </>
        )}
      </a>
    )
  },
  blockquote: ({ children }) => <blockquote className="my-4 rounded-lg bg-muted px-4 py-3 text-ink">{children}</blockquote>,
  hr: () => <hr className="my-6 border-border" />,
  img: ({ src, alt }) =>
    typeof src === "string" ? (
      <img
        src={src}
        alt={alt ?? ""}
        loading="lazy"
        decoding="async"
        className="my-3 aspect-[4/3] w-full max-w-md rounded-lg bg-muted object-cover"
        onError={(e) => { e.currentTarget.style.display = "none" }}
      />
    ) : null,
  table: ({ children }) => (
    <div className="scroll-thin my-4 max-w-full overflow-x-auto rounded-lg border" tabIndex={0} role="region" aria-label="Table">
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-muted text-left">{children}</thead>,
  th: ({ children }) => <th className="whitespace-nowrap px-3 py-2 font-semibold">{children}</th>,
  td: ({ children }) => <td className="border-t px-3 py-2 align-top tabular">{children}</td>,
  pre: ({ children }) => <>{children}</>,
  code: ({ className, children }) => {
    const match = /language-([\w+-]+)/.exec(className ?? "")
    const code = textOf(children).replace(/\n$/, "")
    const isBlock = Boolean(match) || code.includes("\n")
    if (!isBlock) {
      return <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[0.9em]">{children}</code>
    }
    return (
      <Suspense fallback={<pre className="my-4 overflow-x-auto rounded-lg border bg-muted p-4 font-mono text-sm">{code}</pre>}>
        <CodeBlock code={code} language={match?.[1]} />
      </Suspense>
    )
  },
}

export const AnswerMarkdown = memo(function AnswerMarkdown({ children, className }: { children: string; className?: string }) {
  return (
    <div className={cn("max-w-prose break-words text-base text-ink", className)}>
      <Markdown remarkPlugins={[remarkGfm]} components={components}>
        {normalize(children)}
      </Markdown>
    </div>
  )
})
