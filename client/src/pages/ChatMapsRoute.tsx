import { MotionConfig } from "framer-motion";
import ChatMapsPage from "./ChatMapsPage";

/**
 * /chatmaps is the only screen that still uses Framer Motion (the legacy chat
 * kit). MotionConfig lives here, not in main.tsx, so Framer stays out of the
 * entry bundle; reducedMotion="user" honours prefers-reduced-motion.
 */
export default function ChatMapsRoute() {
  return (
    <MotionConfig reducedMotion="user">
      <ChatMapsPage />
    </MotionConfig>
  );
}
