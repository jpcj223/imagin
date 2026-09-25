<template>
  <aside class="list-panel" :class="{ collapsed: props.collapsed }">
    <!-- 面板头部 -->
    <div class="list-panel-header">
      <template v-if="!props.collapsed">
        <span class="list-panel-title">角色列表</span>
        <span class="list-panel-count">{{ props.totalCount }}</span>
      </template>
      <n-button
        text
        size="tiny"
        class="panel-toggle-btn"
        @click="emit('toggleCollapsed')"
        :title="props.collapsed ? '展开列表面板' : '折叠列表面板'"
      >
        <template #icon>
          <n-icon size="16">
            <svg v-if="props.collapsed" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 18l6-6-6-6" />
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </n-icon>
        </template>
      </n-button>
    </div>

    <template v-if="!props.collapsed">
      <div class="panel-tools">
        <n-input v-model:value="keywordModel" clearable placeholder="搜索角色...">
          <template #prefix>🔍</template>
        </n-input>
        <n-select
          v-model:value="groupFilterModel"
          clearable
          :options="props.groupFilterOptions"
          placeholder="分组筛选"
          style="width: 110px"
        />
      </div>

      <!-- 分组操作栏 -->
      <div class="group-actions">
        <span class="group-actions-label">分组</span>
        <div class="group-actions-btns">
          <n-button text size="tiny" @click="emit('toggleAllGroups')">
            {{ props.allGroupsExpanded ? '全部折叠' : '全部展开' }}
          </n-button>
          <span class="group-actions-divider">|</span>
          <n-button text size="tiny" type="primary" @click="emit('startCreateGroup')">
            <template #icon>＋</template>
            新建分组
          </n-button>
        </div>
      </div>

      <!-- 新建分组输入框 -->
      <div v-if="props.isCreatingGroup" class="new-group-form">
        <n-input
          v-model:value="newGroupNameModel"
          size="small"
          placeholder="输入分组名称"
          clearable
          @keyup.enter="emit('confirmCreateGroup')"
        />
        <div class="new-group-actions">
          <n-button size="tiny" type="primary" @click="emit('confirmCreateGroup')">确认</n-button>
          <n-button size="tiny" @click="emit('cancelCreateGroup')">取消</n-button>
        </div>
      </div>
    </template>

    <n-scrollbar class="list-scroll">
      <div v-if="props.loading" class="list-loading">
        <n-spin size="small" />
        <span>加载中...</span>
      </div>

      <div v-else-if="props.groupedCharacters.length === 0" class="list-empty">
        <div class="empty-icon">👤</div>
        <p>还没有角色</p>
        <p class="empty-sub">点击右上角「新建角色」开始创建</p>
      </div>

      <div v-else class="character-groups">
        <draggable
          v-model="localGroupOrderModel"
          item-key="id"
          animation="200"
          @start="isDraggingGroup = true"
          @end="onGroupDragEnd"
          class="groups-draggable"
        >
          <template #item="{ element: group }">
            <div class="group-wrapper" :class="{ 'is-dragging': isDraggingGroup }">
              <!-- 折叠态：只显示图标 -->
              <template v-if="props.collapsed">
                <div
                  class="group-icon-only"
                  :title="`${group.name}（${props.groupCharacters[group.id]?.length || 0}）`"
                  @click="emit('quickSelectFirstOfGroup', { group, items: props.groupCharacters[group.id] || [] })"
                >
                  <span class="group-icon-big">{{ props.roleTypeIcon(group.role_type) }}</span>
                  <n-badge :value="props.groupCharacters[group.id]?.length || 0" :max="99" size="tiny" />
                </div>
              </template>

              <!-- 展开态：完整分组 -->
              <template v-else>
                <!-- 分组标题 -->
                <div
                  class="group-header"
                  :class="{ collapsed: !props.expandedGroups.has(group.id), 'is-builtin': group.is_builtin }"
                  @click="emit('toggleGroup', group.id)"
                >
                  <n-icon
                    size="12"
                    class="group-arrow"
                    :class="{ expanded: props.expandedGroups.has(group.id) }"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                      <path d="M6 9l6 6 6-6" />
                    </svg>
                  </n-icon>
                  <span class="group-icon">{{ props.roleTypeIcon(group.role_type) }}</span>

                  <!-- 重命名输入框 -->
                  <n-input
                    v-if="props.renamingGroupId === group.id"
                    v-model:value="renamingGroupNameModel"
                    size="tiny"
                    class="group-rename-input"
                    @keyup.enter="emit('confirmRenameGroup', group)"
                    @keyup.esc="emit('cancelRenameGroup')"
                    @click.stop
                  />
                  <span v-else class="group-name">
                    {{ group.name }}
                  </span>

                  <span class="group-count">{{ props.groupCharacters[group.id]?.length || 0 }}</span>

                  <!-- 自定义分组操作按钮 -->
                  <div v-if="!group.is_builtin && !group.is_virtual" class="group-actions-right">
                    <n-button
                      text
                      size="tiny"
                      class="group-action-btn"
                      title="重命名"
                      @click.stop="emit('startRenameGroup', group)"
                    >
                      ✏️
                    </n-button>
                    <n-popconfirm positive-text="删除" negative-text="取消" @positive-click="emit('deleteGroup', group)">
                      <template #trigger>
                        <n-button text size="tiny" class="group-action-btn" title="删除分组">
                          🗑️
                        </n-button>
                      </template>
                      确定删除该分组？有角色的分组不可删除。
                    </n-popconfirm>
                  </div>
                </div>

                <!-- 角色列表（可拖拽） -->
                <div v-show="props.expandedGroups.has(group.id)" class="group-items">
                  <draggable
                    v-model="props.groupCharacters[group.id]"
                    item-key="id"
                    group="characters"
                    animation="150"
                    ghost-class="char-ghost"
                    drag-class="char-dragging"
                    @start="isDraggingCharacter = true"
                    @end="onCharacterDragEnd(group.id)"
                    class="chars-draggable"
                  >
                    <template #item="{ element: item }">
                      <div
                        v-show="props.matchesFilter(item)"
                        class="character-item"
                        :class="{
                          active: props.editingId === item.id,
                          inactive: item.status === 'inactive',
                          hidden: item.status === 'hidden',
                          'is-builtin': item.is_builtin
                        }"
                        @click="emit('selectCharacter', item)"
                      >
                        <div class="char-avatar">
                          {{ item.name?.charAt(0) || '?' }}
                          <span v-if="item.is_builtin" class="builtin-badge" title="内置角色">★</span>
                        </div>
                        <div class="char-content">
                          <div class="char-title-row">
                            <span class="char-name">{{ item.name }}</span>
                            <n-tag v-if="item.is_builtin" size="tiny" type="warning" class="builtin-tag">内置</n-tag>
                            <n-tag size="tiny" :type="props.roleTagType(item.role_type)">
                              {{ props.roleTypeLabel(item.role_type) }}
                            </n-tag>
                          </div>
                          <div class="char-meta">
                            {{ item.identity || '身份未定' }}
                            <span v-if="item.faction"> · {{ item.faction }}</span>
                          </div>
                          <div class="char-progress-row">
                            <div class="mini-progress">
                              <span :style="{ width: `${props.completionOf(item)}%` }"></span>
                            </div>
                            <span class="progress-text">{{ props.completionOf(item) }}%</span>
                          </div>
                          <div v-if="item.mbti_primary || item.mbti" class="char-tags">
                            <span class="tag-chip mbti-chip">{{ item.mbti_primary || item.mbti }}</span>
                            <span v-if="item.motivation" class="tag-chip">
                              {{ props.shortText(item.motivation, 12) }}
                            </span>
                          </div>
                        </div>
                      </div>
                    </template>
                  </draggable>

                  <!-- 空分组提示 -->
                  <div
                    v-if="props.groupCharacters[group.id]?.length === 0"
                    class="group-empty"
                  >
                    <span>暂无角色</span>
                  </div>
                </div>
              </template>
            </div>
          </template>
        </draggable>
      </div>
    </n-scrollbar>
  </aside>
</template>

<script setup lang="ts">
/**
 * 人物卡片左侧的分组与角色列表。
 * 步骤 1：接收父页面整理后的分组和角色数据。
 * 步骤 2：通过事件回报筛选、选择、拖拽和分组操作。
 * 注：拖拽列表由 vuedraggable 对父页面提供的响应式分组数组原地排序。
 */
import { computed, ref } from 'vue'
import { NBadge, NButton, NIcon, NInput, NPopconfirm } from 'naive-ui'
import draggable from 'vuedraggable'
import type { CharacterItem } from '@/types/domain'

export interface RoleGroup {
  id: string
  dictItemId: number
  name: string
  role_type: string
  sort_order: number
  is_builtin: boolean
  is_virtual: boolean
}

export interface GroupedCharacter {
  group: RoleGroup
  items: CharacterItem[]
}

interface Props {
  loading: boolean
  collapsed: boolean
  totalCount: number
  keyword: string
  groupFilter: string | null
  groupFilterOptions: Array<{ label: string; value: string }>
  allGroupsExpanded: boolean
  isCreatingGroup: boolean
  newGroupName: string
  groupedCharacters: GroupedCharacter[]
  localGroupOrder: RoleGroup[]
  groupCharacters: Record<string, CharacterItem[]>
  expandedGroups: Set<string>
  renamingGroupId: string | null
  renamingGroupName: string
  editingId: number | null
  matchesFilter: (item: CharacterItem) => boolean
  roleTypeIcon: (roleType: string) => string
  roleTypeLabel: (roleType: string) => string
  roleTagType: (roleType: string) => 'default' | 'success' | 'info' | 'warning' | 'error'
  completionOf: (item: Partial<CharacterItem>) => number
  shortText: (value: string, max?: number) => string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:collapsed': [value: boolean]
  'update:keyword': [value: string]
  'update:groupFilter': [value: string | null]
  'update:newGroupName': [value: string]
  'update:renamingGroupName': [value: string]
  'update:localGroupOrder': [value: RoleGroup[]]
  toggleCollapsed: []
  toggleAllGroups: []
  startCreateGroup: []
  confirmCreateGroup: []
  cancelCreateGroup: []
  quickSelectFirstOfGroup: [value: GroupedCharacter]
  toggleGroup: [groupId: string]
  confirmRenameGroup: [group: RoleGroup]
  cancelRenameGroup: []
  startRenameGroup: [group: RoleGroup]
  deleteGroup: [group: RoleGroup]
  groupDragEnd: []
  characterDragEnd: [groupId: string]
  selectCharacter: [item: CharacterItem]
}>()

const keywordModel = computed({
  get: () => props.keyword,
  set: (value: string) => emit('update:keyword', value),
})
const groupFilterModel = computed({
  get: () => props.groupFilter,
  set: (value: string | null) => emit('update:groupFilter', value),
})
const newGroupNameModel = computed({
  get: () => props.newGroupName,
  set: (value: string) => emit('update:newGroupName', value),
})
const renamingGroupNameModel = computed({
  get: () => props.renamingGroupName,
  set: (value: string) => emit('update:renamingGroupName', value),
})
const localGroupOrderModel = computed({
  get: () => props.localGroupOrder,
  set: (value: RoleGroup[]) => emit('update:localGroupOrder', value),
})
const isDraggingGroup = ref(false)
const isDraggingCharacter = ref(false)

function onGroupDragEnd() {
  // 拖拽状态属于列表展示；顺序持久化由父页面完成。
  isDraggingGroup.value = false
  emit('groupDragEnd')
}

function onCharacterDragEnd(groupId: string) {
  isDraggingCharacter.value = false
  emit('characterDragEnd', groupId)
}
</script>

<style scoped>
.list-panel {
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ===== 左侧列表面板 ===== */
.list-panel {
  overflow: hidden;
  transition: all 0.3s ease;
}

.list-panel.collapsed {
  padding: 0;
}

.list-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  flex-shrink: 0;
}

.list-panel.collapsed .list-panel-header {
  justify-content: center;
  padding: 10px 8px;
}

.list-panel-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--n-text-color-1, #e5e7eb);
}

/* 角色总数徽标固定高度并居中数字，避免两位数挤压标题。 */
.list-panel-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 34px;
  height: 26px;
  box-sizing: border-box;
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  background: var(--n-color-2, #2a2f3a);
  padding: 0 8px;
  border-radius: 999px;
  font-weight: 500;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  flex-shrink: 0;
  margin-left: auto;
  margin-right: 8px;
}

/* 分组操作栏 */
.group-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  flex-shrink: 0;
}

.group-actions-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--n-text-color-2, #9ca3af);
}

.group-actions-btns {
  display: flex;
  align-items: center;
  gap: 2px;
}

.group-actions-divider {
  font-size: 11px;
  color: var(--n-border-color, #2a2f3a);
  margin: 0 2px;
}

/* 新建分组表单 */
.new-group-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  background: var(--n-color-2, #222730);
}

.new-group-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.panel-tools {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  flex-shrink: 0;
}

.panel-tools > :first-child {
  flex: 1;
}

.list-scroll {
  flex: 1;
  min-height: 0;
}

.list-loading,
.list-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 10px;
  color: var(--n-text-color-3, #6b7280);
  font-size: 13px;
}

.empty-icon {
  font-size: 36px;
}

.list-empty p {
  margin: 0;
}

.empty-sub {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
}

/* 角色分组 */
.character-groups {
  padding: 8px 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* 分组行占满列表宽度，确保不同分组的计数徽标使用同一右侧基准。 */
.group-header {
  display: flex;
  width: 100%;
  box-sizing: border-box;
  align-items: center;
  gap: 8px;
  padding: 12px 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--n-text-color-2, #9ca3af);
  position: sticky;
  top: 0;
  background: var(--n-color-card, #1a1d21);
  z-index: 1;
  cursor: pointer;
  transition: color 0.2s ease, background 0.2s ease;
  user-select: none;
  border-radius: 6px;
}

.group-header:hover {
  color: var(--n-text-color-1, #e5e7eb);
  background: var(--n-color-hover, #23272f);
}

.group-header:hover .group-actions-right {
  opacity: 1;
}

/* 分组标题行整行可拖拽 */
.group-header {
  cursor: grab;
}

.group-header:active {
  cursor: grabbing;
}

/* 分组右侧操作按钮 */
.group-actions-right {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-left: 6px;
  opacity: 0;
  transition: opacity 0.2s;
}

.group-action-btn {
  padding: 2px 4px !important;
  font-size: 12px !important;
}

/* 重命名输入框 */
.group-rename-input {
  flex: 1;
  min-width: 0;
}

.group-rename-input :deep(.n-input__input-el) {
  padding: 2px 8px !important;
  height: 24px !important;
  font-size: 12px !important;
}

/* 空分组提示 */
.group-empty {
  padding: 12px;
  text-align: center;
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  font-style: italic;
}

/* 拖拽视觉反馈 */
.char-ghost {
  opacity: 0.4;
  background: var(--n-color-primary-1-suppl, #1e3a5f) !important;
  border: 1px dashed var(--n-color-primary-3, #3b82f6) !important;
}

.char-dragging {
  opacity: 0.9;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
  transform: scale(1.02);
}

.groups-draggable {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.chars-draggable {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.group-arrow {
  color: var(--n-text-color-3, #6b7280);
  transition: transform 0.2s ease;
  flex-shrink: 0;
}

.group-arrow.expanded {
  transform: rotate(180deg);
}

.group-header.collapsed + .group-items {
  display: none;
}

.group-header:first-child {
  padding-top: 4px;
}

/* 折叠态：分组图标 */
.group-icon-only {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  margin: 6px auto;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.group-icon-only:hover {
  background: var(--n-color-hover, #2a2f3a);
}

.group-icon-big {
  font-size: 20px;
}

.group-icon-only :deep(.n-badge) {
  position: absolute;
  top: 2px;
  right: 2px;
}

.group-icon {
  font-size: 14px;
}

.group-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.group-name.editable {
  cursor: text;
}

.group-name.editable:hover {
  text-decoration: underline;
  text-decoration-style: dotted;
  text-underline-offset: 2px;
}

/* 角色数量 - 右对齐设计 */
/* 计数徽标固定宽度并使用等宽数字，保证单/双位数视觉对齐。 */
.group-count {
  display: inline-flex;
  flex: 0 0 34px;
  align-items: center;
  justify-content: center;
  width: 34px;
  min-width: 34px;
  height: 22px;
  box-sizing: border-box;
  padding: 0;
  font-size: 12px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  color: var(--n-text-color-3, #6b7280);
  background: var(--n-color, #23272f);
  border-radius: 999px;
  line-height: 1;
  margin-left: auto;
  font-family: 'SF Mono', 'Menlo', 'Consolas', monospace;
  white-space: nowrap;
}

.group-header:hover .group-count {
  color: var(--n-text-color-2, #9ca3af);
  background: var(--n-color-hover-pressed, #2a2f37);
}

.group-items {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.character-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: grab;
  transition: all 0.15s;
  border: 1px solid transparent;
}

.character-item:active {
  cursor: grabbing;
}

.character-item:hover {
  background: var(--n-color-hover, #23272f);
}

.character-item.active {
  background: var(--n-color-primary-1-suppl, #1e3a5f);
  border-color: var(--n-color-primary-3, #3b82f6);
}

.character-item.inactive .char-name,
.character-item.inactive .char-meta,
.character-item.inactive .progress-text {
  color: var(--n-text-color-3, #6b7280);
}

.character-item.inactive .char-name {
  text-decoration: line-through;
}

.character-item.hidden {
  opacity: 0.5;
}

.character-item.hidden .char-name {
  font-style: italic;
}

.char-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  flex-shrink: 0;
  position: relative;
}

.builtin-badge {
  position: absolute;
  bottom: -2px;
  right: -2px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: linear-gradient(135deg, #f59e0b, #f97316);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 8px;
  color: #fff;
  border: 2px solid #1a1d24;
  line-height: 1;
}

.builtin-tag {
  flex-shrink: 0;
}

.character-item.is-builtin .char-avatar {
  background: linear-gradient(135deg, #f59e0b, #ef4444);
}

.char-content {
  flex: 1;
  min-width: 0;
}

.char-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 3px;
}

.char-name {
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.char-meta {
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.char-progress-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.mini-progress {
  flex: 1;
  height: 4px;
  background: var(--n-border-color, #2a2f3a);
  border-radius: 2px;
  overflow: hidden;
}

.mini-progress span {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #36d399, #3b82f6);
  border-radius: 2px;
  transition: width 0.3s;
}

.progress-text {
  font-size: 10px;
  color: var(--n-text-color-3, #6b7280);
  min-width: 28px;
  text-align: right;
}

.char-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.tag-chip {
  padding: 1px 6px;
  font-size: 10px;
  border-radius: 4px;
  background: var(--n-color-1, #1e2228);
  color: var(--n-text-color-2, #9ca3af);
  border: 1px solid var(--n-border-color, #2a2f3a);
}

.mbti-chip {
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
  border-color: rgba(99, 102, 241, 0.3);
  font-weight: 600;
}

/* ===== 中间详情面板 ===== */
</style>
