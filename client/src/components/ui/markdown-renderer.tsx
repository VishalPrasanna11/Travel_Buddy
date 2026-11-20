import { AnswerMarkdown } from "@/components/chat/answer-markdown"

/**
 * Kept for the /chatmaps message list. Delegates to the shared, safe answer
 * renderer so the app ships one markdown pipeline and one lazy, fine-grained
 * Shiki build (the old version imported every Shiki grammar).
 */
export function MarkdownRenderer({ children }: { children: string }) {
  return <AnswerMarkdown>{children}</AnswerMarkdown>
}

export default MarkdownRenderer
