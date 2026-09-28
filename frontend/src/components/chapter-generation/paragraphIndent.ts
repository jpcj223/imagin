const PARAGRAPH_INDENT = '　　'

/** 为正文中的每个非空行补齐两个全角空格，保持空行与段落换行不变。 */
export function indentChapterParagraphs(content: string): string {
  return content.split('\n').map((line) => {
    const text = line.replace(/^[\t \u3000]+/, '')
    return text.replace(/\r$/, '') ? `${PARAGRAPH_INDENT}${text}` : line
  }).join('\n')
}

/** 流式输出逐段到达时复用同一格式化规则，避免段落缩进重复叠加。 */
export function appendIndentedChapterText(current: string, delta: string): string {
  return indentChapterParagraphs(current + delta)
}

export function indentChapterInput(content: string, selectionStart: number, selectionEnd: number) {
  const lines = content.split('\n')
  let inputOffset = 0
  let startAdjustment = 0
  let endAdjustment = 0

  for (const line of lines) {
    const leadingLength = line.match(/^[\t \u3000]*/)?.[0].length ?? 0
    const hasText = Boolean(line.slice(leadingLength).replace(/\r$/, ''))
    if (hasText) {
      const adjustment = PARAGRAPH_INDENT.length - leadingLength
      if (selectionStart >= inputOffset + leadingLength) startAdjustment += adjustment
      if (selectionEnd >= inputOffset + leadingLength) endAdjustment += adjustment
    }
    inputOffset += line.length + 1
  }

  return {
    value: indentChapterParagraphs(content),
    selectionStart: Math.max(0, selectionStart + startAdjustment),
    selectionEnd: Math.max(0, selectionEnd + endAdjustment),
  }
}
