export interface ChapterDialogueMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  usageLabel?: string
}

export interface ChapterDialogueCandidate {
  scope: 'chapter' | 'selection'
  expectedContent: string
  proposedContent: string
  originalSegment: string
  revisedSegment: string
}
