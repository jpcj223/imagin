<template>
  <div class="context-selector">
    <!-- 头部 -->
    <div class="cs-header">
      <div class="cs-title">
        <span class="cs-title-icon">📚</span>
        <span>上下文资料</span>
      </div>
      <button class="cs-recommend-btn" @click="handleAutoRecommend">
        <span class="recommend-icon">✨</span>
        <span>智能推荐</span>
      </button>
    </div>

    <div class="cs-subtitle">
      选择 AI 生成章节时的参考资料
    </div>

    <div class="cs-panels">
      <!-- 1. 出场角色 -->
      <div class="cs-panel" :class="{ expanded: expanded.characters }">
        <div class="panel-header" @click="togglePanel('characters')">
          <div class="panel-header-left">
            <span class="panel-arrow" :class="{ expanded: expanded.characters }">▸</span>
            <span class="panel-icon">👤</span>
            <span class="panel-name">出场角色</span>
          </div>
          <div class="panel-count">
            已选 {{ selectedCharacterIds.length }}/{{ characters.length }}
          </div>
        </div>

        <transition name="panel-expand">
          <div v-if="expanded.characters" class="panel-body">
            <!-- 搜索框 -->
            <div v-if="characters.length > 6" class="panel-search">
              <span class="search-icon">🔍</span>
              <input
                v-model="searchKeywords.characters"
                type="text"
                class="search-input"
                placeholder="搜索角色..."
              />
            </div>

            <!-- 列表 -->
            <div class="panel-list">
              <label
                v-for="char in filteredCharacters"
                :key="char.id"
                class="list-item"
                :class="{ selected: selectedCharacterIds.includes(char.id) }"
              >
                <input
                  type="checkbox"
                  :value="char.id"
                  v-model="localSelectedCharacterIds"
                  class="item-checkbox"
                />
                <div class="item-content">
                  <div class="item-title">
                    <span class="item-name">{{ char.name }}</span>
                    <span class="item-badge role" :class="char.role_type">
                      {{ roleTypeLabel(char.role_type) }}
                    </span>
                  </div>
                  <div class="item-desc">{{ char.identity || char.faction || '—' }}</div>
                </div>
              </label>

              <div v-if="filteredCharacters.length === 0" class="empty-tip">
                暂无匹配的角色
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="panel-actions">
              <button class="action-btn" @click="selectAllCharacters">全选</button>
              <button class="action-btn" @click="clearCharacters">取消</button>
              <button class="action-btn primary" @click="resetCharacters">重置推荐</button>
            </div>
          </div>
        </transition>
      </div>

      <!-- 2. 关联组织 -->
      <div class="cs-panel" :class="{ expanded: expanded.organizations }">
        <div class="panel-header" @click="togglePanel('organizations')">
          <div class="panel-header-left">
            <span class="panel-arrow" :class="{ expanded: expanded.organizations }">▸</span>
            <span class="panel-icon">🏛️</span>
            <span class="panel-name">关联组织</span>
          </div>
          <div class="panel-count">
            已选 {{ selectedOrganizationIds.length }}/{{ organizations.length }}
          </div>
        </div>

        <transition name="panel-expand">
          <div v-if="expanded.organizations" class="panel-body">
            <div v-if="organizations.length > 6" class="panel-search">
              <span class="search-icon">🔍</span>
              <input
                v-model="searchKeywords.organizations"
                type="text"
                class="search-input"
                placeholder="搜索组织..."
              />
            </div>

            <div class="panel-list">
              <label
                v-for="org in filteredOrganizations"
                :key="org.id"
                class="list-item"
                :class="{ selected: selectedOrganizationIds.includes(org.id) }"
              >
                <input
                  type="checkbox"
                  :value="org.id"
                  v-model="localSelectedOrganizationIds"
                  class="item-checkbox"
                />
                <div class="item-content">
                  <div class="item-title">
                    <span class="item-name">{{ org.name }}</span>
                    <span class="item-badge org-type">{{ org.org_type }}</span>
                  </div>
                  <div class="item-desc">
                    实力 Lv.{{ org.power_level }} · {{ org.goal || org.slogan || '—' }}
                  </div>
                </div>
              </label>

              <div v-if="filteredOrganizations.length === 0" class="empty-tip">
                暂无匹配的组织
              </div>
            </div>

            <div class="panel-actions">
              <button class="action-btn" @click="selectAllOrganizations">全选</button>
              <button class="action-btn" @click="clearOrganizations">取消</button>
              <button class="action-btn primary" @click="resetOrganizations">重置推荐</button>
            </div>
          </div>
        </transition>
      </div>

      <!-- 3. 世界观设定 -->
      <div class="cs-panel" :class="{ expanded: expanded.worldSettings }">
        <div class="panel-header" @click="togglePanel('worldSettings')">
          <div class="panel-header-left">
            <span class="panel-arrow" :class="{ expanded: expanded.worldSettings }">▸</span>
            <span class="panel-icon">🌍</span>
            <span class="panel-name">世界观设定</span>
          </div>
          <div class="panel-count">
            已选 {{ selectedWorldIds.length }}/{{ worldSettings.length }}
          </div>
        </div>

        <transition name="panel-expand">
          <div v-if="expanded.worldSettings" class="panel-body">
            <div v-if="worldSettings.length > 6" class="panel-search">
              <span class="search-icon">🔍</span>
              <input
                v-model="searchKeywords.worldSettings"
                type="text"
                class="search-input"
                placeholder="搜索设定..."
              />
            </div>

            <div class="panel-list">
              <label
                v-for="ws in filteredWorldSettings"
                :key="ws.id"
                class="list-item"
                :class="{ selected: selectedWorldIds.includes(ws.id) }"
              >
                <input
                  type="checkbox"
                  :value="ws.id"
                  v-model="localSelectedWorldIds"
                  class="item-checkbox"
                />
                <div class="item-content">
                  <div class="item-title">
                    <span class="item-name">{{ ws.title }}</span>
                    <span class="item-badge category">{{ categoryLabel(ws.category) }}</span>
                  </div>
                  <div class="item-desc">{{ ws.rules || ws.era || ws.geography || '—' }}</div>
                </div>
                <div class="item-importance" :class="ws.importance" :title="'重要性：' + ws.importance">
                </div>
              </label>

              <div v-if="filteredWorldSettings.length === 0" class="empty-tip">
                暂无匹配的设定
              </div>
            </div>

            <div class="panel-actions">
              <button class="action-btn" @click="selectAllWorldSettings">全选</button>
              <button class="action-btn" @click="clearWorldSettings">取消</button>
              <button class="action-btn primary" @click="resetWorldSettings">重置推荐</button>
            </div>
          </div>
        </transition>
      </div>

      <!-- 4. 伏笔线索 -->
      <div class="cs-panel" :class="{ expanded: expanded.foreshadowings }">
        <div class="panel-header" @click="togglePanel('foreshadowings')">
          <div class="panel-header-left">
            <span class="panel-arrow" :class="{ expanded: expanded.foreshadowings }">▸</span>
            <span class="panel-icon">🎭</span>
            <span class="panel-name">伏笔线索</span>
          </div>
          <div class="panel-count">
            已选 {{ selectedForeshadowingIds.length }}/{{ foreshadowings.length }}
          </div>
        </div>

        <transition name="panel-expand">
          <div v-if="expanded.foreshadowings" class="panel-body">
            <div v-if="foreshadowings.length > 6" class="panel-search">
              <span class="search-icon">🔍</span>
              <input
                v-model="searchKeywords.foreshadowings"
                type="text"
                class="search-input"
                placeholder="搜索伏笔..."
              />
            </div>

            <div class="panel-list">
              <label
                v-for="fs in filteredForeshadowings"
                :key="fs.id"
                class="list-item"
                :class="{ selected: selectedForeshadowingIds.includes(fs.id) }"
              >
                <input
                  type="checkbox"
                  :value="fs.id"
                  v-model="localSelectedForeshadowingIds"
                  class="item-checkbox"
                />
                <div class="item-content">
                  <div class="item-title">
                    <span class="item-name">{{ fs.keyword }}</span>
                    <span
                      v-if="currentChapterNo && fs.payoff_chapter === currentChapterNo"
                      class="item-badge payoff"
                    >
                      本章回收
                    </span>
                    <span v-else class="item-badge status" :class="fs.status">
                      {{ foreshadowingStatusLabel(fs.status) }}
                    </span>
                  </div>
                  <div class="item-desc">{{ fs.description || '—' }}</div>
                </div>
                <div class="item-importance" :class="fs.importance" :title="'重要性：' + fs.importance">
                </div>
              </label>

              <div v-if="filteredForeshadowings.length === 0" class="empty-tip">
                暂无匹配的伏笔
              </div>
            </div>

            <div class="panel-actions">
              <button class="action-btn" @click="selectAllForeshadowings">全选</button>
              <button class="action-btn" @click="clearForeshadowings">取消</button>
              <button class="action-btn primary" @click="resetForeshadowings">重置推荐</button>
            </div>
          </div>
        </transition>
      </div>

      <!-- 5. 大纲信息 -->
      <div class="cs-panel" :class="{ expanded: expanded.outline }">
        <div class="panel-header" @click="togglePanel('outline')">
          <div class="panel-header-left">
            <span class="panel-arrow" :class="{ expanded: expanded.outline }">▸</span>
            <span class="panel-icon">📋</span>
            <span class="panel-name">大纲信息</span>
          </div>
          <div class="panel-count info">
            {{ outline ? '已加载' : '无' }}
          </div>
        </div>

        <transition name="panel-expand">
          <div v-if="expanded.outline" class="panel-body">
            <div v-if="outline" class="outline-card">
              <div class="outline-title">{{ outline.title }}</div>
              <div class="outline-meta">
                <span v-if="outline.chapter_no" class="outline-meta-item">
                  第 {{ outline.chapter_no }} 章
                </span>
                <span class="outline-meta-item status" :class="outline.status">
                  {{ outline.status === 'confirmed' ? '已确认' : '草稿' }}
                </span>
              </div>
              <div class="outline-desc">{{ outline.description }}</div>
              <div class="outline-info-badge">
                <span>📌</span>
                <span>自动纳入上下文</span>
              </div>
            </div>
            <div v-else class="empty-tip">
              暂无大纲信息
            </div>
          </div>
        </transition>
      </div>

      <!-- 6. 前情摘要 -->
      <div class="cs-panel" :class="{ expanded: expanded.summaries }">
        <div class="panel-header" @click="togglePanel('summaries')">
          <div class="panel-header-left">
            <span class="panel-arrow" :class="{ expanded: expanded.summaries }">▸</span>
            <span class="panel-icon">📜</span>
            <span class="panel-name">前情摘要</span>
          </div>
          <div class="panel-count info">
            {{ summaries.length }} 章
          </div>
        </div>

        <transition name="panel-expand">
          <div v-if="expanded.summaries" class="panel-body">
            <div v-if="summaries.length > 0" class="summary-list">
              <div
                v-for="sum in summaries"
                :key="sum.id"
                class="summary-item"
              >
                <div class="summary-header">
                  <span class="summary-chapter">第 {{ sum.chapter_no }} 章</span>
                  <span class="summary-title">{{ sum.title }}</span>
                </div>
                <div class="summary-text">{{ sum.summary }}</div>
                <div v-if="sum.character_changes" class="summary-tag-row">
                  <span class="summary-tag">人物变化</span>
                  <span class="summary-tag-content">{{ sum.character_changes }}</span>
                </div>
              </div>
            </div>
            <div v-else class="empty-tip">
              暂无前情摘要
            </div>

            <div v-if="summaries.length > 0" class="outline-info-badge">
              <span>📌</span>
              <span>自动纳入上下文</span>
            </div>
          </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type {
  CharacterItem,
  OrganizationItem,
  WorldSetting,
  ForeshadowingItem,
  OutlineItem,
  ChapterSummary,
} from '@/types/domain'

// ===== Props =====
interface Props {
  characters: CharacterItem[]
  organizations: OrganizationItem[]
  worldSettings: WorldSetting[]
  foreshadowings: ForeshadowingItem[]
  outline: OutlineItem | null
  summaries: ChapterSummary[]
  selectedCharacterIds: number[]
  selectedOrganizationIds: number[]
  selectedWorldIds: number[]
  selectedForeshadowingIds: number[]
  currentChapterNo?: number | null
}

const props = withDefaults(defineProps<Props>(), {
  characters: () => [],
  organizations: () => [],
  worldSettings: () => [],
  foreshadowings: () => [],
  outline: null,
  summaries: () => [],
  selectedCharacterIds: () => [],
  selectedOrganizationIds: () => [],
  selectedWorldIds: () => [],
  selectedForeshadowingIds: () => [],
  currentChapterNo: null,
})

// ===== Emits =====
const emit = defineEmits<{
  'update:selectedCharacterIds': [ids: number[]]
  'update:selectedOrganizationIds': [ids: number[]]
  'update:selectedWorldIds': [ids: number[]]
  'update:selectedForeshadowingIds': [ids: number[]]
  'auto-recommend': []
}>()

// ===== 面板展开状态 =====
const expanded = ref({
  characters: true,
  organizations: true,
  worldSettings: false,
  foreshadowings: true,
  outline: true,
  summaries: false,
})

function togglePanel(key: keyof typeof expanded.value) {
  expanded.value[key] = !expanded.value[key]
}

// ===== 搜索关键词 =====
const searchKeywords = ref({
  characters: '',
  organizations: '',
  worldSettings: '',
  foreshadowings: '',
})

// ===== 本地选中状态（用于 v-model 双向绑定） =====
const localSelectedCharacterIds = computed({
  get: () => props.selectedCharacterIds,
  set: (val: number[]) => emit('update:selectedCharacterIds', val),
})

const localSelectedOrganizationIds = computed({
  get: () => props.selectedOrganizationIds,
  set: (val: number[]) => emit('update:selectedOrganizationIds', val),
})

const localSelectedWorldIds = computed({
  get: () => props.selectedWorldIds,
  set: (val: number[]) => emit('update:selectedWorldIds', val),
})

const localSelectedForeshadowingIds = computed({
  get: () => props.selectedForeshadowingIds,
  set: (val: number[]) => emit('update:selectedForeshadowingIds', val),
})

// ===== 过滤后的列表 =====
const filteredCharacters = computed(() => {
  if (!searchKeywords.value.characters) return props.characters
  const kw = searchKeywords.value.characters.toLowerCase()
  return props.characters.filter(
    c => c.name.toLowerCase().includes(kw)
      || c.identity?.toLowerCase().includes(kw)
      || c.faction?.toLowerCase().includes(kw)
  )
})

const filteredOrganizations = computed(() => {
  if (!searchKeywords.value.organizations) return props.organizations
  const kw = searchKeywords.value.organizations.toLowerCase()
  return props.organizations.filter(
    o => o.name.toLowerCase().includes(kw)
      || o.org_type?.toLowerCase().includes(kw)
      || o.goal?.toLowerCase().includes(kw)
  )
})

const filteredWorldSettings = computed(() => {
  if (!searchKeywords.value.worldSettings) return props.worldSettings
  const kw = searchKeywords.value.worldSettings.toLowerCase()
  return props.worldSettings.filter(
    w => w.title.toLowerCase().includes(kw)
      || w.category?.toLowerCase().includes(kw)
      || w.rules?.toLowerCase().includes(kw)
  )
})

const filteredForeshadowings = computed(() => {
  if (!searchKeywords.value.foreshadowings) return props.foreshadowings
  const kw = searchKeywords.value.foreshadowings.toLowerCase()
  return props.foreshadowings.filter(
    f => f.keyword.toLowerCase().includes(kw)
      || f.description?.toLowerCase().includes(kw)
      || f.status?.toLowerCase().includes(kw)
  )
})

// ===== 角色操作 =====
function selectAllCharacters() {
  emit('update:selectedCharacterIds', props.characters.map(c => c.id))
}
function clearCharacters() {
  emit('update:selectedCharacterIds', [])
}
function resetCharacters() {
  emit('auto-recommend')
}

// ===== 组织操作 =====
function selectAllOrganizations() {
  emit('update:selectedOrganizationIds', props.organizations.map(o => o.id))
}
function clearOrganizations() {
  emit('update:selectedOrganizationIds', [])
}
function resetOrganizations() {
  emit('auto-recommend')
}

// ===== 世界观操作 =====
function selectAllWorldSettings() {
  emit('update:selectedWorldIds', props.worldSettings.map(w => w.id))
}
function clearWorldSettings() {
  emit('update:selectedWorldIds', [])
}
function resetWorldSettings() {
  emit('auto-recommend')
}

// ===== 伏笔操作 =====
function selectAllForeshadowings() {
  emit('update:selectedForeshadowingIds', props.foreshadowings.map(f => f.id))
}
function clearForeshadowings() {
  emit('update:selectedForeshadowingIds', [])
}
function resetForeshadowings() {
  emit('auto-recommend')
}

// ===== 自动推荐 =====
function handleAutoRecommend() {
  emit('auto-recommend')
}

// ===== 标签辅助函数 =====
function roleTypeLabel(type: string): string {
  const map: Record<string, string> = {
    protagonist: '主角',
    supporting: '配角',
    antagonist: '反派',
  }
  return map[type] || type
}

function categoryLabel(cat: string): string {
  const map: Record<string, string> = {
    era: '时代',
    location: '地理',
    power: '力量',
    rule: '规则',
    taboo: '禁忌',
    term: '术语',
    other: '其他',
  }
  return map[cat] || cat
}

function foreshadowingStatusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: '待埋',
    planted: '已埋',
    developing: '发展中',
    payoff_pending: '待回收',
    resolved: '已回收',
    abandoned: '已废弃',
  }
  return map[status] || status
}
</script>

<style scoped>
.context-selector {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: rgba(15, 22, 41, 0.6);
  border-left: 1px solid var(--border, rgba(255, 255, 255, 0.08));
  color: var(--text-primary, #e2e8f0);
  overflow: hidden;
}

/* ===== 头部 ===== */
.cs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 14px 8px;
  flex-shrink: 0;
}

.cs-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
}

.cs-title-icon {
  font-size: 16px;
}

.cs-recommend-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(139, 92, 246, 0.2));
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 6px;
  color: #c7d2fe;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.cs-recommend-btn:hover {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.3), rgba(139, 92, 246, 0.3));
  border-color: rgba(99, 102, 241, 0.5);
  transform: translateY(-1px);
}

.recommend-icon {
  font-size: 12px;
}

.cs-subtitle {
  padding: 0 14px 10px;
  font-size: 11px;
  color: var(--text-muted, #64748b);
  border-bottom: 1px solid var(--border, rgba(255, 255, 255, 0.08));
  flex-shrink: 0;
}

/* ===== 面板容器 ===== */
.cs-panels {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

/* ===== 折叠面板 ===== */
.cs-panel {
  margin-bottom: 6px;
  background: rgba(30, 42, 69, 0.5);
  border: 1px solid var(--border, rgba(255, 255, 255, 0.08));
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.2s ease;
}

.cs-panel:hover {
  border-color: rgba(255, 255, 255, 0.12);
}

/* 面板头部 */
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 10px;
  cursor: pointer;
  transition: background 0.15s ease;
  user-select: none;
}

.panel-header:hover {
  background: rgba(255, 255, 255, 0.03);
}

.panel-header-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.panel-arrow {
  font-size: 9px;
  color: var(--text-muted, #64748b);
  transition: transform 0.2s ease;
  width: 10px;
  text-align: center;
}

.panel-arrow.expanded {
  transform: rotate(90deg);
}

.panel-icon {
  font-size: 13px;
}

.panel-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary, #94a3b8);
}

.panel-count {
  font-size: 10px;
  color: #a5b4fc;
  font-family: 'JetBrains Mono', monospace;
  padding: 2px 6px;
  background: rgba(99, 102, 241, 0.1);
  border-radius: 4px;
  border: 1px solid rgba(99, 102, 241, 0.15);
}

.panel-count.info {
  color: var(--text-muted, #64748b);
  background: rgba(255, 255, 255, 0.04);
  border-color: var(--border, rgba(255, 255, 255, 0.08));
}

/* 面板主体 */
.panel-body {
  padding: 0 10px 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

/* 搜索框 */
.panel-search {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  margin: 8px 0;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border, rgba(255, 255, 255, 0.08));
  border-radius: 6px;
  transition: all 0.15s ease;
}

.panel-search:focus-within {
  border-color: rgba(99, 102, 241, 0.3);
  background: rgba(99, 102, 241, 0.04);
}

.search-icon {
  font-size: 11px;
  opacity: 0.6;
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: var(--text-primary, #e2e8f0);
  font-size: 11px;
  font-family: inherit;
}

.search-input::placeholder {
  color: var(--text-muted, #64748b);
}

/* 列表 */
.panel-list {
  max-height: 220px;
  overflow-y: auto;
  margin-bottom: 8px;
}

.list-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 7px 8px;
  margin-bottom: 3px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  border: 1px solid transparent;
}

.list-item:hover {
  background: rgba(255, 255, 255, 0.04);
}

.list-item.selected {
  background: rgba(99, 102, 241, 0.1);
  border-color: rgba(99, 102, 241, 0.25);
  box-shadow: 0 0 12px rgba(99, 102, 241, 0.08);
}

/* checkbox */
.item-checkbox {
  margin-top: 2px;
  flex-shrink: 0;
  width: 14px;
  height: 14px;
  appearance: none;
  -webkit-appearance: none;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 3px;
  cursor: pointer;
  position: relative;
  transition: all 0.15s ease;
}

.item-checkbox:checked {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border-color: #6366f1;
  box-shadow: 0 0 6px rgba(99, 102, 241, 0.4);
}

.item-checkbox:checked::after {
  content: '';
  position: absolute;
  top: 1px;
  left: 4px;
  width: 3px;
  height: 7px;
  border: solid #fff;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.item-content {
  flex: 1;
  min-width: 0;
}

.item-title {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 3px;
}

.item-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary, #e2e8f0);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.list-item.selected .item-name {
  color: #c7d2fe;
}

.item-badge {
  font-size: 9px;
  padding: 1px 5px;
  border-radius: 3px;
  font-weight: 500;
  flex-shrink: 0;
}

.item-badge.role.protagonist {
  background: rgba(99, 102, 241, 0.2);
  color: #a5b4fc;
  border: 1px solid rgba(99, 102, 241, 0.3);
}

.item-badge.role.supporting {
  background: rgba(16, 185, 129, 0.15);
  color: #6ee7b7;
  border: 1px solid rgba(16, 185, 129, 0.25);
}

.item-badge.role.antagonist {
  background: rgba(239, 68, 68, 0.15);
  color: #fca5a5;
  border: 1px solid rgba(239, 68, 68, 0.25);
}

.item-badge.org-type {
  background: rgba(139, 92, 246, 0.15);
  color: #c4b5fd;
  border: 1px solid rgba(139, 92, 246, 0.25);
}

.item-badge.category {
  background: rgba(6, 182, 212, 0.12);
  color: #67e8f9;
  border: 1px solid rgba(6, 182, 212, 0.2);
}

.item-badge.status {
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-muted, #64748b);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.item-badge.status.planted {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.25);
}

.item-badge.status.developing {
  background: rgba(139, 92, 246, 0.15);
  color: #c4b5fd;
  border: 1px solid rgba(139, 92, 246, 0.25);
}

.item-badge.status.resolved {
  background: rgba(16, 185, 129, 0.15);
  color: #6ee7b7;
  border: 1px solid rgba(16, 185, 129, 0.25);
}

.item-badge.payoff {
  background: linear-gradient(135deg, rgba(249, 115, 22, 0.2), rgba(239, 68, 68, 0.2));
  color: #fdba74;
  border: 1px solid rgba(249, 115, 22, 0.4);
  animation: payoff-pulse 2s ease-in-out infinite;
}

@keyframes payoff-pulse {
  0%, 100% { box-shadow: 0 0 4px rgba(249, 115, 22, 0.2); }
  50% { box-shadow: 0 0 10px rgba(249, 115, 22, 0.4); }
}

.item-desc {
  font-size: 10px;
  color: var(--text-muted, #64748b);
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

/* 重要性指示点 */
.item-importance {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 5px;
}

.item-importance.high {
  background: #ef4444;
  box-shadow: 0 0 4px #ef4444;
}

.item-importance.medium {
  background: #f59e0b;
  box-shadow: 0 0 4px #f59e0b;
}

.item-importance.low {
  background: #64748b;
}

/* 操作按钮 */
.panel-actions {
  display: flex;
  gap: 6px;
  padding-top: 6px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.action-btn {
  flex: 1;
  padding: 5px 0;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border, rgba(255, 255, 255, 0.08));
  border-radius: 5px;
  color: var(--text-secondary, #94a3b8);
  font-size: 10px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.15);
  color: var(--text-primary, #e2e8f0);
}

.action-btn.primary {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.15));
  border-color: rgba(99, 102, 241, 0.3);
  color: #a5b4fc;
}

.action-btn.primary:hover {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.25), rgba(139, 92, 246, 0.25));
  border-color: rgba(99, 102, 241, 0.5);
}

/* 空提示 */
.empty-tip {
  padding: 20px 0;
  text-align: center;
  font-size: 11px;
  color: var(--text-muted, #64748b);
}

/* ===== 大纲卡片 ===== */
.outline-card {
  padding: 10px;
  margin-top: 8px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
}

.outline-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #e2e8f0);
  margin-bottom: 6px;
}

.outline-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.outline-meta-item {
  font-size: 10px;
  color: var(--text-muted, #64748b);
}

.outline-meta-item.status.confirmed {
  color: #6ee7b7;
}

.outline-meta-item.status.draft {
  color: #fbbf24;
}

.outline-desc {
  font-size: 11px;
  color: var(--text-secondary, #94a3b8);
  line-height: 1.6;
  margin-bottom: 10px;
}

.outline-info-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.15);
  border-radius: 4px;
  font-size: 10px;
  color: #6ee7b7;
}

/* ===== 前情摘要 ===== */
.summary-list {
  margin-top: 8px;
  max-height: 240px;
  overflow-y: auto;
}

.summary-item {
  padding: 8px;
  margin-bottom: 6px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
}

.summary-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 5px;
}

.summary-chapter {
  font-size: 10px;
  color: #a5b4fc;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
}

.summary-title {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary, #94a3b8);
}

.summary-text {
  font-size: 10px;
  color: var(--text-muted, #64748b);
  line-height: 1.5;
  margin-bottom: 6px;
}

.summary-tag-row {
  display: flex;
  align-items: flex-start;
  gap: 6px;
}

.summary-tag {
  flex-shrink: 0;
  font-size: 9px;
  padding: 1px 5px;
  background: rgba(139, 92, 246, 0.12);
  color: #c4b5fd;
  border-radius: 3px;
}

.summary-tag-content {
  font-size: 10px;
  color: var(--text-muted, #64748b);
  line-height: 1.4;
}

/* ===== 展开动画 ===== */
.panel-expand-enter-active,
.panel-expand-leave-active {
  overflow: hidden;
  transition: max-height 0.25s ease, opacity 0.2s ease;
}

.panel-expand-enter-from,
.panel-expand-leave-to {
  max-height: 0;
  opacity: 0;
}

.panel-expand-enter-to,
.panel-expand-leave-from {
  max-height: 500px;
  opacity: 1;
}

/* ===== 滚动条 ===== */
.cs-panels::-webkit-scrollbar,
.panel-list::-webkit-scrollbar,
.summary-list::-webkit-scrollbar {
  width: 4px;
}

.cs-panels::-webkit-scrollbar-track,
.panel-list::-webkit-scrollbar-track,
.summary-list::-webkit-scrollbar-track {
  background: transparent;
}

.cs-panels::-webkit-scrollbar-thumb,
.panel-list::-webkit-scrollbar-thumb,
.summary-list::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
}

.cs-panels::-webkit-scrollbar-thumb:hover,
.panel-list::-webkit-scrollbar-thumb:hover,
.summary-list::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}
</style>
