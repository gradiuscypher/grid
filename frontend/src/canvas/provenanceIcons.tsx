import { Bot, Terminal, User, Workflow } from 'lucide-react'
import type { CreatedVia } from '../api/generated'

export const PROVENANCE_ICON: Record<CreatedVia, typeof User> = {
  user: User,
  transform: Workflow,
  llm: Bot,
  api: Terminal,
}

export const PROVENANCE_LABEL: Record<CreatedVia, string> = {
  user: 'Created by a user',
  transform: 'Created by a transform',
  llm: 'Created by an LLM',
  api: 'Created via the API',
}
