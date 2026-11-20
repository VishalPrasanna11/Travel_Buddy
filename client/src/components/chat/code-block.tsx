import { useEffect, useState } from "react"
import type { HighlighterCore, ThemedToken } from "shiki/core"

import { CopyButton } from "@/components/ui/copy-button"

/**
 * Code block for AI answers. Lazy-loaded (React.lazy) so Shiki never ships in
 * the main bundle; only a handful of grammars are loaded on first use, with
 * the JavaScript regex engine (no WASM). Scrolls horizontally inside itself.
 */

const LANG_ALIASES: Record<string, string> = {
  js: "javascript", jsx: "javascript", ts: "typescript", tsx: "typescript",
  sh: "bash", shell: "bash", zsh: "bash", shellscript: "bash", py: "python", yml: "yaml",
}

// Palette-based theme: ink text, Raspberry keywords, derived inks for the rest.
const TRAVELBUDDY_THEME = {
  name: "travelbuddy",
  type: "light" as const,
  colors: { "editor.background": "#F7F7F7", "editor.foreground": "#374151" },
  tokenColors: [
    { scope: ["comment", "punctuation.definition.comment"], settings: { foreground: "#5B6472", fontStyle: "italic" } },
    { scope: ["keyword", "storage", "storage.type", "keyword.operator.new"], settings: { foreground: "#993456" } },
    { scope: ["string", "string.quoted", "markup.inline.raw"], settings: { foreground: "#397242" } },
    { scope: ["constant.numeric", "constant.language", "support.constant"], settings: { foreground: "#8C5416" } },
    { scope: ["entity.name.function", "support.function", "meta.function-call"], settings: { foreground: "#43646C" } },
    { scope: ["entity.name.type", "support.type", "entity.name.class"], settings: { foreground: "#43646C" } },
    { scope: ["support.type.property-name", "meta.object-literal.key", "entity.name.tag"], settings: { foreground: "#882449" } },
  ],
}

let highlighterPromise: Promise<HighlighterCore> | null = null

function getHighlighter() {
  highlighterPromise ??= (async () => {
    const [{ createHighlighterCore }, { createJavaScriptRegexEngine }, ...langs] = await Promise.all([
      import("shiki/core"),
      import("shiki/engine/javascript"),
      import("@shikijs/langs/json"),
      import("@shikijs/langs/bash"),
      import("@shikijs/langs/python"),
      import("@shikijs/langs/javascript"),
      import("@shikijs/langs/typescript"),
      import("@shikijs/langs/yaml"),
    ])
    return createHighlighterCore({
      themes: [TRAVELBUDDY_THEME],
      langs: langs.map((m) => m.default),
      engine: createJavaScriptRegexEngine(),
    })
  })()
  return highlighterPromise
}

export default function CodeBlock({ code, language }: { code: string; language?: string }) {
  const lang = language ? LANG_ALIASES[language] ?? language : undefined
  const [tokens, setTokens] = useState<ThemedToken[][] | null>(null)

  useEffect(() => {
    let cancelled = false
    if (!lang) return
    getHighlighter()
      .then((hl) => {
        if (cancelled || !hl.getLoadedLanguages().includes(lang)) return
        setTokens(hl.codeToTokensBase(code, { lang, theme: "travelbuddy" }))
      })
      .catch(() => { /* plain text fallback */ })
    return () => { cancelled = true }
  }, [code, lang])

  return (
    <div className="group/code relative my-4 max-w-full">
      {language && (
        <span className="absolute left-3 top-2 font-mono text-meta text-muted-foreground">{language}</span>
      )}
      <pre
        tabIndex={0}
        aria-label={language ? `${language} code` : "Code"}
        className="scroll-thin overflow-x-auto rounded-lg border bg-muted p-4 pt-8 font-mono text-sm leading-relaxed text-ink"
      >
        <code>
          {tokens
            ? tokens.map((line, i) => (
                <span key={i} className="block">
                  {line.length === 0 ? " " : line.map((t, j) => (
                    <span key={j} style={{ color: t.color, fontStyle: t.fontStyle === 1 ? "italic" : undefined }}>{t.content}</span>
                  ))}
                </span>
              ))
            : code}
        </code>
      </pre>
      <div className="absolute right-2 top-1.5 opacity-100 sm:opacity-0 sm:transition-opacity sm:group-hover/code:opacity-100 sm:group-focus-within/code:opacity-100">
        <CopyButton content={code} copyMessage="Code copied" />
      </div>
    </div>
  )
}
