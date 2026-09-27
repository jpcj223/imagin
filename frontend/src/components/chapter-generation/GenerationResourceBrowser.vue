<template>
      <!-- ===== 左侧：记忆系统 + 资源浏览器 ===== -->
      <aside class="left-panel">
        <!-- 四级记忆系统 -->
        <div class="memory-section">
          <MemoryLayer
            :levels="memoryLevels"
            :active-level="'working'"
            @level-click="handleMemoryLevelClick"
          />
        </div>

        <div class="panel-search">
          <n-input v-model:value="keyword" clearable :placeholder="searchPlaceholder">
            <template #prefix>🔍</template>
          </n-input>
        </div>

        <!-- 上下文简报 -->
        <div class="context-brief-card">
          <div class="brief-row">
            <span class="brief-label">当前大纲</span>
            <span class="brief-value" :title="selectedOutline?.title">
              {{ selectedOutline?.title || '未选择' }}
            </span>
          </div>
          <div class="brief-row">
            <span class="brief-label">当前章节</span>
            <span class="brief-value" :title="selectedChapter?.title || `第${form.chapter_no}章`">
              {{ selectedChapter?.title || `第${form.chapter_no}章` }}
            </span>
          </div>
          <div class="brief-row">
            <span class="brief-label">上下文</span>
            <span class="brief-value">
              <span class="brief-count">{{ totalSelectedCount }}</span> 项手选资料
            </span>
          </div>
          <div class="brief-tip">未手选的相关资料会按本章大纲自动推荐</div>
        </div>

        <!-- 资源 Tab 浏览器 -->
        <div class="resource-tabs">
          <div class="resource-tab-bar">
            <div
              v-for="tab in resourceTabs"
              :key="tab.key"
              class="resource-tab-item"
              :class="{ active: leftActiveTab === tab.key, 'has-match': keyword.trim() && tab.matchCount > 0, 'no-match': keyword.trim() && tab.matchCount === 0 }"
              @click="leftActiveTab = tab.key"
              :title="`${tab.label}：${tab.badgeText || `已选 ${tab.selectedCount} / 共 ${tab.count}`}${keyword.trim() ? ` · 当前匹配 ${tab.matchCount}` : ''}`"
            >
              <span class="tab-icon">{{ tab.icon }}</span>
              <span class="tab-name">{{ tab.label }}</span>
              <span class="tab-badge" :class="{ 'match-badge': keyword.trim() && tab.matchCount > 0 }">
                {{ tab.badgeText || `${tab.selectedCount}/${tab.count}` }}
              </span>
            </div>
          </div>

          <n-scrollbar class="resource-tab-content">
            <!-- 大纲 Tab -->
            <div v-if="leftActiveTab === 'outline'" class="tab-list outline-list">
              <div v-if="filteredOutlines.length === 0" class="list-empty">
                <template v-if="keyword.trim()">🔍 未找到匹配「{{ keyword }}」的大纲</template>
                <template v-else>暂无大纲</template>
              </div>
              <template v-if="filteredOverview">
                <div class="outline-group-label">全书规划</div>
                <section class="outline-entry" :class="{ expanded: expandedOutlineKey === `overview-${filteredOverview.id}` }">
                  <button class="outline-entry-header" type="button" @click="toggleOutline(`overview-${filteredOverview.id}`)">
                    <span class="outline-kind overview-kind">总览</span>
                    <span class="outline-entry-title">{{ filteredOverview.title || '大纲总览' }}</span>
                    <span class="outline-chevron" aria-hidden="true">⌄</span>
                  </button>
                  <p class="outline-entry-summary">{{ filteredOverview.description || '尚未填写全书主线' }}</p>
                  <div v-if="expandedOutlineKey === `overview-${filteredOverview.id}`" class="outline-entry-detail">
                    <div v-if="overviewExtra.target_words || overviewExtra.target_volumes || overviewExtra.target_chapters || overviewExtra.pace">
                      <strong>全书规模与节奏</strong>
                      <p>{{ overviewScaleSummary }}</p>
                    </div>
                    <div v-if="overviewExtra.core_conflict"><strong>核心冲突</strong><p>{{ overviewExtra.core_conflict }}</p></div>
                    <div v-if="overviewExtra.ending"><strong>结局方向</strong><p>{{ overviewExtra.ending }}</p></div>
                    <div class="outline-auto-note">✓ 生成章节时自动纳入</div>
                  </div>
                </section>
              </template>

              <div v-if="filteredVolumes.length" class="outline-group-label volume-group-label">
                分卷大纲 <span>{{ filteredVolumes.length }} 卷</span>
              </div>
              <section
                v-for="item in filteredVolumes"
                :key="item.id"
                class="outline-entry volume-outline-entry"
                :class="{ expanded: expandedOutlineKey === `volume-${item.id}` }"
              >
                <button class="outline-entry-header" type="button" @click="toggleOutline(`volume-${item.id}`)">
                  <span class="outline-kind volume-kind">卷{{ item.volume_no ?? '—' }}</span>
                  <span class="outline-entry-title">{{ item.title || '未命名卷' }}</span>
                  <span class="outline-entry-count">{{ chaptersInVolume(item.id).length }} 章</span>
                  <span class="outline-chevron" aria-hidden="true">⌄</span>
                </button>
                <p class="outline-entry-summary">{{ item.description || '尚未填写卷纲' }}</p>
                <div v-if="expandedOutlineKey === `volume-${item.id}`" class="outline-entry-detail">
                  <div v-if="volumeExtra(item).target_chapters"><strong>预计章节数</strong><p>{{ volumeExtra(item).target_chapters }} 章</p></div>
                  <div v-if="volumeExtra(item).core_events"><strong>核心事件</strong><p>{{ volumeExtra(item).core_events }}</p></div>
                  <div v-if="volumeCharacterNames(item).length"><strong>本卷指定人物</strong><p>{{ volumeCharacterNames(item).join('、') }}</p></div>
                  <div v-if="volumeExtra(item).locations"><strong>主要场景</strong><p>{{ volumeExtra(item).locations }}</p></div>
                  <div v-if="volumeExtra(item).climax"><strong>卷末高潮</strong><p>{{ volumeExtra(item).climax }}</p></div>
                  <div v-if="volumeExtra(item).chapter_suggestions"><strong>章节建议</strong><p>{{ volumeExtra(item).chapter_suggestions }}</p></div>
                  <div class="outline-auto-note">✓ 生成章节时自动纳入</div>
                </div>
              </section>
            </div>

            <!-- 章节 Tab -->
            <div v-if="leftActiveTab === 'chapter'" class="tab-list">
              <div v-if="filteredChapters.length === 0" class="list-empty">
                <template v-if="keyword.trim()">🔍 未找到匹配「{{ keyword }}」的章节</template>
                <template v-else>暂无章节草稿</template>
              </div>
              <div
                v-for="item in filteredChapters"
                :key="item.id"
                class="resource-item"
                :class="{ active: chapterId === item.id }"
                :ref="chapterId === item.id ? setActiveChapterElement : undefined"
                @click="selectChapter(item)"
              >
                <div class="item-main">
                  <div class="item-title-row">
                    <span class="item-title" v-html="safeHighlight(item.title)"></span>
                    <n-tag size="tiny" :type="statusTagType(item.status)">
                      {{ statusLabel(item.status) }}
                    </n-tag>
                  </div>
                  <div class="item-meta">
                    第 {{ item.chapter_no }} 章 · {{ formatChars(item.content) }} 字
                  </div>
                </div>
              </div>
            </div>

            <!-- 人物 Tab -->
            <div v-if="leftActiveTab === 'character'" class="tab-list card-list">
              <div v-if="characters.length === 0 && !keyword.trim()" class="list-empty">
                暂无角色
              </div>
              <div v-else-if="filteredCharacters.length === 0 && keyword.trim()" class="list-empty">
                🔍 未找到匹配「{{ keyword }}」的角色
              </div>
              <div
                v-for="c in filteredCharacters"
                :key="c.id"
                class="character-card"
                :class="{ selected: selectedCharacterIds.includes(c.id) }"
                @click="toggleCharacter(c.id)"
              >
                <div class="char-header">
                  <div class="char-avatar" :style="{ background: avatarColor(c.name) }">
                    {{ c.name?.charAt(0) || '?' }}
                  </div>
                  <div class="char-info">
                    <div class="char-name" v-html="safeHighlight(c.name)"></div>
                    <div class="char-type">
                      <n-tag size="tiny" :type="charRoleTagType(c.role_type)">
                        {{ charRoleLabel(c.role_type) }}
                      </n-tag>
                    </div>
                  </div>
                  <div class="char-check" :class="{ checked: selectedCharacterIds.includes(c.id) }">
                    <span v-if="selectedCharacterIds.includes(c.id)">✓</span>
                  </div>
                </div>
                <div v-if="c.identity" class="char-desc" v-html="safeHighlight(c.identity)"></div>
                <div class="char-tags">
                  <span v-if="c.personality" class="char-tag">{{ c.personality }}</span>
                  <span v-if="c.mbti_primary" class="char-tag mbti">{{ c.mbti_primary }}</span>
                </div>
              </div>
            </div>

            <!-- 组织 Tab -->
            <div v-if="leftActiveTab === 'organization'" class="tab-list">
              <div v-if="organizations.length === 0 && !keyword.trim()" class="list-empty">
                暂无组织
              </div>
              <div v-else-if="filteredOrganizations.length === 0 && keyword.trim()" class="list-empty">
                🔍 未找到匹配「{{ keyword }}」的组织
              </div>
              <div
                v-for="org in filteredOrganizations"
                :key="org.id"
                class="resource-item"
                :class="{ active: selectedOrganizationIds.includes(org.id) }"
                @click="toggleOrganization(org.id)"
              >
                <div class="item-main">
                  <div class="item-title-row">
                    <span class="item-title" v-html="safeHighlight(org.name)"></span>
                    <div
                      class="item-check"
                      :class="{ checked: selectedOrganizationIds.includes(org.id) }"
                    >
                      <span v-if="selectedOrganizationIds.includes(org.id)">✓</span>
                    </div>
                  </div>
                  <div class="item-meta">
                    <span class="chapter-no-badge">{{ org.org_type || '未知类型' }}</span>
                    <span v-html="safeHighlight(org.slogan || org.description || '')"></span>
                  </div>
                  <div v-if="org.power_level" class="item-power">
                    <span class="power-label">实力</span>
                    <div class="power-bar">
                      <div class="power-fill" :style="{ width: powerPercent(org.power_level) + '%' }"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 世界观 Tab -->
            <div v-if="leftActiveTab === 'world'" class="tab-list">
              <div v-if="worlds.length === 0 && !keyword.trim()" class="list-empty">
                暂无世界观设定
              </div>
              <div v-else-if="filteredWorlds.length === 0 && keyword.trim()" class="list-empty">
                🔍 未找到匹配「{{ keyword }}」的世界观
              </div>
              <div
                v-for="w in filteredWorlds"
                :key="w.id"
                class="resource-item world-item"
                :class="{ active: selectedWorldIds.includes(w.id) }"
                @click="toggleWorld(w.id)"
              >
                <div class="world-category" :data-category="w.category">
                  {{ worldCategoryLabel(w.category) }}
                </div>
                <div class="item-main">
                  <div class="item-title-row">
                    <span class="item-title" v-html="safeHighlight(w.title)"></span>
                    <div
                      class="item-check"
                      :class="{ checked: selectedWorldIds.includes(w.id) }"
                    >
                      <span v-if="selectedWorldIds.includes(w.id)">✓</span>
                    </div>
                  </div>
                  <div v-if="w.rules" class="item-meta" v-html="safeHighlight(w.rules)"></div>
                  <div v-else-if="w.geography" class="item-meta" v-html="safeHighlight(w.geography)"></div>
                </div>
                <div v-if="w.importance === 'high' || w.importance === '核心'" class="importance-dot high" title="核心设定">★</div>
              </div>
            </div>

            <!-- 伏笔 Tab -->
            <div v-if="leftActiveTab === 'foreshadowing'" class="tab-list">
              <div v-if="foreshadowings.length === 0 && !keyword.trim()" class="list-empty">
                暂无伏笔
              </div>
              <div v-else-if="filteredForeshadowings.length === 0 && keyword.trim()" class="list-empty">
                🔍 未找到匹配「{{ keyword }}」的伏笔
              </div>
              <div
                v-for="f in filteredForeshadowings"
                :key="f.id"
                class="resource-item"
                :class="{ active: selectedForeshadowingIds.includes(f.id) }"
                @click="toggleForeshadowing(f.id)"
              >
                <div class="item-main">
                  <div class="item-title-row">
                    <span class="item-title" v-html="safeHighlight(f.keyword)"></span>
                    <div class="item-row-right">
                      <span
                        v-if="f.payoff_chapter === form.chapter_no"
                        class="payoff-badge"
                      >
                        本章回收
                      </span>
                      <div
                        class="item-check"
                        :class="{ checked: selectedForeshadowingIds.includes(f.id) }"
                      >
                        <span v-if="selectedForeshadowingIds.includes(f.id)">✓</span>
                      </div>
                    </div>
                  </div>
                  <div class="item-meta">
                    <n-tag size="tiny" :type="foreshadowTagType(f.status)">
                      {{ foreshadowStatusLabel(f.status) }}
                    </n-tag>
                    <span v-if="f.description" style="margin-left: 6px;" v-html="safeHighlight(f.description)"></span>
                  </div>
                </div>
              </div>
            </div>
          </n-scrollbar>
        </div>
      </aside>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, toRefs, watch, type ComponentPublicInstance } from 'vue'
import MemoryLayer from '@/components/MemoryLayer.vue'
import type { MemoryLevel } from '@/components/MemoryLayer.vue'
import type {
  ChapterItem,
  CharacterItem,
  ForeshadowingItem,
  OrganizationItem,
  OutlineItem,
  WorldSetting,
} from '@/types/domain'

type TabKey = 'outline' | 'chapter' | 'character' | 'organization' | 'world' | 'foreshadowing'
type ResourceTab = { key: TabKey; label: string; icon: string; count: number; selectedCount: number; matchCount: number; badgeText?: string }

type ResourceProps = {
  memoryLevels: MemoryLevel[]
  outlines: OutlineItem[]
  chapters: ChapterItem[]
  characters: CharacterItem[]
  organizations: OrganizationItem[]
  worlds: WorldSetting[]
  foreshadowings: ForeshadowingItem[]
  selectedOutline: OutlineItem | null
  selectedChapter: ChapterItem | null
  outlineId: number | null
  chapterId: number | null
  chapterNo: number
  selectedCharacterIds: number[]
  selectedOrganizationIds: number[]
  selectedWorldIds: number[]
  selectedForeshadowingIds: number[]
}

const props = defineProps<ResourceProps>()
const emit = defineEmits<{
  (event: 'select-outline', item: OutlineItem): void
  (event: 'select-chapter', item: ChapterItem): void
  (event: 'toggle-character', id: number): void
  (event: 'toggle-organization', id: number): void
  (event: 'toggle-world', id: number): void
  (event: 'toggle-foreshadowing', id: number): void
  (event: 'memory-level-click', level: string): void
}>()

// 步骤 1：将只用于左侧资料浏览的输入转换为可追踪响应式引用。
const {
  memoryLevels, outlines, chapters, characters, organizations, worlds, foreshadowings,
  selectedOutline, selectedChapter, outlineId, chapterId, chapterNo,
  selectedCharacterIds, selectedOrganizationIds, selectedWorldIds, selectedForeshadowingIds,
} = toRefs(props)
const keyword = ref('')
const leftActiveTab = ref<TabKey>('outline')
const expandedOutlineKey = ref<string | null>(null)
const activeChapterElement = ref<HTMLElement | null>(null)

// 步骤 2：按当前搜索词筛选资源，并为各个页签生成数量摘要。
const overviewOutline = computed(() => outlines.value.find((item) => item.node_type === 'overview' || item.title === '大纲总览') ?? null)
const volumeOutlines = computed(() => outlines.value
  .filter((item) => item.node_type === 'volume')
  .sort((left, right) => (left.volume_no ?? Number.MAX_SAFE_INTEGER) - (right.volume_no ?? Number.MAX_SAFE_INTEGER) || left.id - right.id))
const filteredOutlines = computed(() => {
  const text = keyword.value.trim().toLocaleLowerCase('zh-CN')
  const available = [overviewOutline.value, ...volumeOutlines.value].filter((item): item is OutlineItem => Boolean(item))
  if (!text) return available
  return available.filter((item) => [item.title, item.description].join(' ').toLocaleLowerCase('zh-CN').includes(text))
})
const filteredOverview = computed(() => filteredOutlines.value.find((item) => item.node_type === 'overview' || item.title === '大纲总览') ?? null)
const filteredVolumes = computed(() => filteredOutlines.value.filter((item) => item.node_type === 'volume'))
const filteredChapters = computed(() => {
  const text = keyword.value.trim().toLocaleLowerCase('zh-CN')
  const ordered = [...chapters.value].sort((left, right) => left.chapter_no - right.chapter_no || left.id - right.id)
  if (!text) return ordered
  return ordered.filter((item) => [item.title, item.content].join(' ').toLocaleLowerCase('zh-CN').includes(text))
})
const filteredCharacters = computed(() => {
  const text = keyword.value.trim().toLocaleLowerCase('zh-CN')
  if (!text) return characters.value
  return characters.value.filter((item) => [item.name, item.identity, item.personality].join(' ').toLocaleLowerCase('zh-CN').includes(text))
})
const filteredOrganizations = computed(() => {
  const text = keyword.value.trim().toLocaleLowerCase('zh-CN')
  if (!text) return organizations.value
  return organizations.value.filter((item) => [item.name, item.slogan, item.description].join(' ').toLocaleLowerCase('zh-CN').includes(text))
})
const filteredWorlds = computed(() => {
  const text = keyword.value.trim().toLocaleLowerCase('zh-CN')
  if (!text) return worlds.value
  return worlds.value.filter((item) => [item.title, item.rules, item.category].join(' ').toLocaleLowerCase('zh-CN').includes(text))
})
const filteredForeshadowings = computed(() => {
  const text = keyword.value.trim().toLocaleLowerCase('zh-CN')
  if (!text) return foreshadowings.value
  return foreshadowings.value.filter((item) => [item.keyword, item.description].join(' ').toLocaleLowerCase('zh-CN').includes(text))
})
const resourceTabs = computed<ResourceTab[]>(() => [
  { key: 'outline', label: '大纲', icon: '📋', count: filteredOutlines.value.length, selectedCount: 0, matchCount: filteredOutlines.value.length, badgeText: '自动' },
  { key: 'chapter', label: '章节', icon: '📝', count: chapters.value.length, selectedCount: chapterId.value ? 1 : 0, matchCount: filteredChapters.value.length },
  { key: 'character', label: '人物', icon: '👤', count: characters.value.length, selectedCount: selectedCharacterIds.value.length, matchCount: filteredCharacters.value.length },
  { key: 'organization', label: '组织', icon: '🏛️', count: organizations.value.length, selectedCount: selectedOrganizationIds.value.length, matchCount: filteredOrganizations.value.length },
  { key: 'world', label: '世界观', icon: '🌍', count: worlds.value.length, selectedCount: selectedWorldIds.value.length, matchCount: filteredWorlds.value.length },
  { key: 'foreshadowing', label: '伏笔', icon: '🎭', count: foreshadowings.value.length, selectedCount: selectedForeshadowingIds.value.length, matchCount: filteredForeshadowings.value.length },
])
const searchPlaceholder = computed(() => ({
  outline: '搜索大纲...', chapter: '搜索章节...', character: '搜索角色...',
  organization: '搜索组织...', world: '搜索世界观...', foreshadowing: '搜索伏笔...',
}[leftActiveTab.value] || '搜索...'))
const totalSelectedCount = computed(() => selectedCharacterIds.value.length + selectedOrganizationIds.value.length + selectedWorldIds.value.length + selectedForeshadowingIds.value.length)
const form = computed(() => ({ outline_id: outlineId.value, chapter_no: chapterNo.value }))

// 步骤 3：保持列表显示辅助逻辑与生成工作台状态相互隔离。
function selectChapter(item: ChapterItem) { emit('select-chapter', item) }
function toggleOutline(key: string) {
  expandedOutlineKey.value = expandedOutlineKey.value === key ? null : key
}
function chaptersInVolume(volumeId: number) {
  return outlines.value.filter((item) => item.node_type === 'chapter' && item.volume_id === volumeId)
}
function parseExtra(item: OutlineItem): Record<string, unknown> {
  try {
    const value = JSON.parse(item.extra || '{}')
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {}
  } catch {
    return {}
  }
}
const overviewExtra = computed(() => overviewOutline.value ? parseExtra(overviewOutline.value) : {})
const paceLabels: Record<string, string> = { '1': '慢热', '2': '偏慢', '3': '适中', '4': '偏快', '5': '高燃' }
const overviewScaleSummary = computed(() => [
  overviewExtra.value.target_words ? `约 ${overviewExtra.value.target_words} 字` : '',
  overviewExtra.value.target_volumes ? `${overviewExtra.value.target_volumes} 卷` : '',
  overviewExtra.value.target_chapters ? `${overviewExtra.value.target_chapters} 章` : '',
  overviewExtra.value.pace ? `整体节奏 ${paceLabels[String(overviewExtra.value.pace)] || overviewExtra.value.pace}` : '',
].filter(Boolean).join(' · '))
function volumeExtra(item: OutlineItem) {
  return parseExtra(item) as Record<string, string>
}
function volumeCharacterNames(item: OutlineItem): string[] {
  const values = parseExtra(item).characters
  const ids = (Array.isArray(values) ? values : String(values || '').split(/[,，;；\s]+/))
    .map((value) => Number(value))
    .filter((value) => Number.isInteger(value) && value > 0)
  return ids.map((id) => characters.value.find((character) => character.id === id)?.name || `人物 ${id}`)
}
function setActiveChapterElement(element: Element | ComponentPublicInstance | null) {
  activeChapterElement.value = element instanceof HTMLElement ? element : null
}
watch([chapterId, leftActiveTab], async ([, tab]) => {
  if (tab !== 'chapter') return
  await nextTick()
  activeChapterElement.value?.scrollIntoView({ block: 'nearest' })
})
function toggleCharacter(id: number) { emit('toggle-character', id) }
function toggleOrganization(id: number) { emit('toggle-organization', id) }
function toggleWorld(id: number) { emit('toggle-world', id) }
function toggleForeshadowing(id: number) { emit('toggle-foreshadowing', id) }
function handleMemoryLevelClick(level: string) { emit('memory-level-click', level) }

function charRoleTagType(role?: string): 'success' | 'warning' | 'error' | 'info' {
  if (role === 'protagonist') return 'success'
  if (role === 'antagonist') return 'error'
  return 'info'
}
function charRoleLabel(role?: string): string {
  return ({ protagonist: '主角', supporting: '配角', antagonist: '反派' } as Record<string, string>)[role || ''] || '未分类'
}
function avatarColor(name?: string): string {
  if (!name) return '#6366f1'
  let hash = 0
  for (let index = 0; index < name.length; index++) hash = name.charCodeAt(index) + ((hash << 5) - hash)
  const colors = [
    'linear-gradient(135deg, #6366f1, #8b5cf6)', 'linear-gradient(135deg, #ec4899, #f472b6)',
    'linear-gradient(135deg, #f59e0b, #fbbf24)', 'linear-gradient(135deg, #10b981, #34d399)',
    'linear-gradient(135deg, #3b82f6, #60a5fa)', 'linear-gradient(135deg, #ef4444, #f87171)',
    'linear-gradient(135deg, #8b5cf6, #a78bfa)', 'linear-gradient(135deg, #14b8a6, #2dd4bf)',
  ]
  return colors[Math.abs(hash) % colors.length]
}
function powerPercent(level: string | number | null | undefined): number {
  if (level == null) return 0
  const value = typeof level === 'number' ? level : Number.parseInt(String(level), 10)
  if (Number.isNaN(value)) return 30
  return Math.min(100, Math.max(5, value * 20))
}
function worldCategoryLabel(category?: string): string {
  const labels: Record<string, string> = { era: '时代背景', location: '地理环境', power: '力量体系', rule: '世界规则', taboo: '禁忌设定', term: '专有名词' }
  return labels[category || ''] || '其他'
}
function foreshadowStatusLabel(status?: string): string {
  const labels: Record<string, string> = { pending: '待埋设', planted: '已埋设', developing: '发展中', payoff_pending: '待回收', resolved: '已回收', abandoned: '已废弃' }
  return labels[status || ''] || status || '未知'
}
function safeHighlight(value: string | null | undefined): string {
  if (!value) return ''
  // 步骤 1：先转义原始文本，再包裹匹配片段，避免资料内容被当作 HTML 执行。
  const escaped = value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
  const search = keyword.value.trim()
  if (!search) return escaped
  const escapedSearch = search.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return escaped.replace(new RegExp(`(${escapedSearch})`, 'gi'), '<mark class="search-highlight">$1</mark>')
}
function statusLabel(status: string): string {
  const labels: Record<string, string> = { draft: '草稿', confirmed: '已确认', published: '已发布' }
  return labels[status] || status || '未知'
}
function statusTagType(status: string): 'default' | 'success' | 'info' | 'warning' | 'error' {
  const types: Record<string, 'default' | 'success' | 'info' | 'warning' | 'error'> = { draft: 'default', confirmed: 'success', published: 'info' }
  return types[status] || 'default'
}
function foreshadowTagType(status?: string): 'default' | 'success' | 'info' | 'warning' | 'error' {
  const types: Record<string, 'default' | 'success' | 'info' | 'warning' | 'error'> = {
    pending: 'warning', planted: 'info', developing: 'info', payoff_pending: 'warning', resolved: 'success', abandoned: 'default',
  }
  return types[status || ''] || 'default'
}
function formatChars(content: string): string {
  const length = content?.replace(/\s/g, '').length || 0
  return length >= 10000 ? `${(length / 10000).toFixed(1)}万` : String(length)
}
</script>
<style scoped>
/* ===== 左侧面板 ===== */
.left-panel {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  backdrop-filter: blur(10px);
}

.left-panel::-webkit-scrollbar {
  width: 4px;
}

.left-panel::-webkit-scrollbar-track {
  background: transparent;
}

.left-panel::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
}

.left-panel::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}

.memory-section {
  padding: 12px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.panel-search {
  padding: 12px;
  border-bottom: 1px solid var(--border);
}

.panel-search :deep(.n-input) {
  background: rgba(255, 255, 255, 0.04) !important;
  border-color: var(--border) !important;
}

.context-brief-card {
  margin: 0 12px 10px;
  padding: 10px 12px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
}

.brief-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.brief-label {
  color: var(--text-muted);
  flex-shrink: 0;
  width: 60px;
}

.brief-value {
  flex: 1;
  color: var(--text-primary);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.brief-count {
  font-weight: 700;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.brief-tip { margin-top: -4px; padding-left: 68px; color: var(--text-muted); font-size: 10px; line-height: 1.45; }

/* ===== 资源 Tab 浏览器 ===== */
.resource-tabs {
  flex: 1 0 220px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border-top: 1px solid var(--border);
}

.resource-tab-bar {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  padding: 4px 6px;
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.resource-tab-item {
  position: relative;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-start;
  gap: 5px;
  padding: 7px 5px;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
  border-bottom: 2px solid transparent;
}

.resource-tab-item:hover {
  background: rgba(255, 255, 255, 0.04);
}

.resource-tab-item.active {
  border-bottom-color: #8b5cf6;
}

.tab-icon {
  font-size: 14px;
  line-height: 1;
  flex-shrink: 0;
}

.tab-name { color: var(--text-secondary); font-size: 10px; white-space: nowrap; }
.resource-tab-item.active .tab-name { color: #c7d2fe; }

.tab-badge {
  min-width: 24px;
  padding: 2px 5px;
  background: rgba(255, 255, 255, 0.06);
  color: #9aa9bf;
  font-size: 9px;
  font-weight: 600;
  border-radius: 10px;
  text-align: center;
  line-height: 1;
  margin-left: auto;
}

.resource-tab-content {
  flex: 1;
  min-height: 0;
  padding: 8px;
}

.tab-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.outline-list {
  gap: 8px;
}

.outline-group-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 2px 0;
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.outline-group-label span {
  color: var(--text-secondary);
  font-weight: 400;
}

.volume-group-label {
  margin-top: 4px;
}

.outline-entry {
  min-width: 0;
  padding: 9px 10px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.025);
  transition: border-color 0.15s ease, background 0.15s ease;
}

.outline-entry:hover,
.outline-entry.expanded {
  border-color: rgba(129, 140, 248, 0.32);
  background: rgba(99, 102, 241, 0.07);
}

.outline-entry-header {
  display: flex;
  align-items: center;
  gap: 7px;
  width: 100%;
  padding: 0;
  border: 0;
  color: inherit;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.outline-entry-title {
  min-width: 0;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.outline-kind {
  flex: 0 0 auto;
  padding: 2px 6px;
  border-radius: 5px;
  font-size: 10px;
  font-weight: 600;
}

.overview-kind {
  color: #c4b5fd;
  background: rgba(139, 92, 246, 0.17);
}

.volume-kind {
  color: #93c5fd;
  background: rgba(59, 130, 246, 0.16);
}

.outline-entry-count {
  flex: 0 0 auto;
  margin-left: auto;
  color: var(--text-muted);
  font-size: 10px;
}

.outline-chevron {
  flex: 0 0 auto;
  color: var(--text-muted);
  transition: transform 0.15s ease;
}

.outline-entry.expanded .outline-chevron {
  transform: rotate(180deg);
}

.outline-entry-summary {
  display: -webkit-box;
  overflow: hidden;
  margin: 6px 0 0;
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 1.5;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.outline-entry-detail {
  display: grid;
  gap: 8px;
  margin-top: 9px;
  padding-top: 8px;
  border-top: 1px solid rgba(148, 163, 184, 0.12);
}

.outline-entry-detail strong {
  color: #cbd5e1;
  font-size: 10px;
}

.outline-entry-detail p {
  margin: 3px 0 0;
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 1.5;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.outline-auto-note {
  color: #34d399;
  font-size: 10px;
}

.list-empty {
  text-align: center;
  color: var(--text-muted);
  font-size: 12px;
  padding: 30px 10px;
}

/* 通用资源项 */
.resource-item {
  position: relative;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.02);
}

.resource-item:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.08);
}

.resource-item.active {
  background: rgba(99, 102, 241, 0.12);
  border-color: rgba(99, 102, 241, 0.35);
}

.item-main {
  min-width: 0;
}

.item-title {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.item-row-right {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.item-meta {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
  gap: 6px;
}

.chapter-no-badge {
  color: #a5b4fc;
  font-weight: 600;
  font-size: 10px;
  padding: 1px 5px;
  background: rgba(99, 102, 241, 0.15);
  border-radius: 3px;
  flex-shrink: 0;
}

/* 选中勾选框 */
.item-check {
  width: 16px;
  height: 16px;
  border: 1.5px solid rgba(255, 255, 255, 0.15);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  color: transparent;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.item-check.checked {
  background: var(--accent-gradient);
  border-color: transparent;
  color: #fff;
  box-shadow: 0 0 8px rgba(139, 92, 246, 0.4);
}

/* ===== 人物卡片 ===== */
.card-list {
  gap: 8px;
}

.character-card {
  padding: 12px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.2s ease;
}

.character-card:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.1);
  transform: translateY(-1px);
}

.character-card.selected {
  background: rgba(99, 102, 241, 0.1);
  border-color: rgba(139, 92, 246, 0.4);
  box-shadow: 0 0 12px rgba(139, 92, 246, 0.15);
}

.char-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.char-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 600;
  font-size: 14px;
  flex-shrink: 0;
}

.char-info {
  flex: 1;
  min-width: 0;
}

.char-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 3px;
}

.char-type {
  font-size: 10px;
}

.char-check {
  width: 18px;
  height: 18px;
  border: 1.5px solid rgba(255, 255, 255, 0.15);
  border-radius: 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: transparent;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.char-check.checked {
  background: var(--accent-gradient);
  border-color: transparent;
  color: #fff;
  box-shadow: 0 0 8px rgba(139, 92, 246, 0.4);
}

.char-desc {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 8px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.char-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
}

.char-tag {
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  font-size: 10px;
  color: var(--text-secondary);
}

.char-tag.mbti {
  background: rgba(99, 102, 241, 0.15);
  border-color: rgba(99, 102, 241, 0.3);
  color: #a5b4fc;
  font-weight: 500;
}

/* 组织实力条 */
.item-power {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.power-label {
  font-size: 10px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.power-bar {
  flex: 1;
  height: 4px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 2px;
  overflow: hidden;
}

.power-fill {
  height: 100%;
  background: var(--accent-gradient);
  border-radius: 2px;
  transition: width 0.3s ease;
}

/* 世界观分类标签 */
.world-item {
  padding-top: 8px;
}

.world-category {
  display: inline-block;
  padding: 1px 6px;
  font-size: 10px;
  border-radius: 3px;
  margin-bottom: 6px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-secondary);
}

.world-category[data-category="era"] {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
}
.world-category[data-category="location"] {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
}
.world-category[data-category="power"] {
  background: rgba(236, 72, 153, 0.15);
  color: #f472b6;
}
.world-category[data-category="rule"] {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}
.world-category[data-category="taboo"] {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}
.world-category[data-category="term"] {
  background: rgba(139, 92, 246, 0.15);
  color: #a78bfa;
}

.importance-dot {
  position: absolute;
  top: 8px;
  right: 10px;
  font-size: 12px;
  color: #fbbf24;
}

/* 伏笔本章回收徽章 */
.payoff-badge {
  padding: 2px 6px;
  background: linear-gradient(135deg, #f59e0b, #ef4444);
  color: #fff;
  font-size: 10px;
  font-weight: 600;
  border-radius: 4px;
  animation: payoffPulse 2s ease-in-out infinite;
}

@keyframes payoffPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.4); }
  50% { box-shadow: 0 0 8px 2px rgba(245, 158, 11, 0.3); }
}

/* ===== 搜索高亮 ===== */
:deep(.search-highlight) {
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.3), rgba(245, 158, 11, 0.4));
  color: #fef3c7;
  padding: 1px 3px;
  border-radius: 3px;
  font-weight: 600;
}

/* Tab 搜索状态 */
.resource-tab-item.has-match {
  opacity: 1;
}

.resource-tab-item.no-match {
  opacity: 0.4;
}

.resource-tab-item .tab-badge.match-badge {
  background: linear-gradient(135deg, #10b981, #059669);
  animation: matchPop 0.3s ease;
}

@keyframes matchPop {
  0% { transform: scale(1); }
  50% { transform: scale(1.2); }
  100% { transform: scale(1); }
}


</style>
