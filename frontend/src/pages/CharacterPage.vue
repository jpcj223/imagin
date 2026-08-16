<template>
  <div class="page character-page">
    <!-- 页头 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <span class="title-icon">👥</span>
          人物卡片
        </h1>
        <p class="page-subtitle">
          构建立体人物档案，记录性格、动机、关系与成长轨迹
        </p>
      </div>
      <div class="header-right">
        <div class="header-stats">
          <div class="stat">
            <span class="stat-num">{{ totalCount }}</span>
            <span class="stat-label">角色总数</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num">{{ protagonistCount }}</span>
            <span class="stat-label">主角</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num">{{ avgCompletion }}</span>
            <span class="stat-label">平均完整度</span>
          </div>
        </div>
        <n-button type="primary" @click="startCreate">
          <template #icon>＋</template>
          新建角色
        </n-button>
      </div>
    </div>

    <!-- 主体：三栏布局 -->
    <div class="workbench">
      <!-- 左侧：角色列表 -->
      <aside class="list-panel">
        <div class="panel-tools">
          <n-input v-model:value="keyword" clearable placeholder="搜索角色...">
            <template #prefix>🔍</template>
          </n-input>
          <n-select
            v-model:value="roleFilter"
            clearable
            :options="roleTypes"
            placeholder="类型筛选"
            style="width: 100px"
          />
        </div>

        <n-scrollbar class="list-scroll">
          <div v-if="loading" class="list-loading">
            <n-spin size="small" />
            <span>加载中...</span>
          </div>

          <div v-else-if="groupedCharacters.length === 0" class="list-empty">
            <div class="empty-icon">👤</div>
            <p>还没有角色</p>
            <p class="empty-sub">点击右上角「新建角色」开始创建</p>
          </div>

          <div v-else class="character-groups">
            <template v-for="group in groupedCharacters" :key="group.roleType">
              <!-- 分组标题 -->
              <div class="group-header">
                <span class="group-icon">{{ roleTypeIcon(group.roleType) }}</span>
                <span class="group-name">{{ roleTypeLabel(group.roleType) }}</span>
                <n-tag size="tiny" type="default">{{ group.items.length }}</n-tag>
              </div>

              <!-- 角色列表 -->
              <div class="group-items">
                <div
                  v-for="item in group.items"
                  :key="item.id"
                  class="character-item"
                  :class="{ active: editingId === item.id }"
                  @click="selectCharacter(item)"
                >
                  <div class="char-avatar">
                    {{ item.name?.charAt(0) || '?' }}
                  </div>
                  <div class="char-content">
                    <div class="char-title-row">
                      <span class="char-name">{{ item.name }}</span>
                      <n-tag size="tiny" :type="roleTagType(item.role_type)">
                        {{ roleTypeLabel(item.role_type) }}
                      </n-tag>
                    </div>
                    <div class="char-meta">
                      {{ item.identity || '身份未定' }}
                      <span v-if="item.faction"> · {{ item.faction }}</span>
                    </div>
                    <div class="char-progress-row">
                      <div class="mini-progress">
                        <span :style="{ width: `${completionOf(item)}%` }"></span>
                      </div>
                      <span class="progress-text">{{ completionOf(item) }}%</span>
                    </div>
                    <div v-if="item.mbti_primary || item.mbti" class="char-tags">
                      <span class="tag-chip mbti-chip">{{ item.mbti_primary || item.mbti }}</span>
                      <span v-if="item.motivation" class="tag-chip">
                        {{ shortText(item.motivation, 12) }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </n-scrollbar>
      </aside>

      <!-- 中间：角色档案编辑 -->
      <section class="detail-panel">
        <div class="detail-header">
          <div class="detail-title">
            <h2>
              {{ editingId ? '编辑角色档案' : '新建角色档案' }}
              <span v-if="isDirty" class="dirty-dot" title="有未保存的修改">●</span>
            </h2>
            <span class="detail-sub">
              {{ editingId ? `ID ${editingId}` : '未保存' }}
            </span>
          </div>
          <div class="detail-actions">
            <n-popconfirm v-if="editingId" positive-text="确认删除" negative-text="取消" @positive-click="remove">
              <template #trigger>
                <n-button type="error" text>🗑️ 删除</n-button>
              </template>
              确认删除这个角色？
            </n-popconfirm>
            <n-button @click="resetCurrent">↺ 重置</n-button>
            <n-button type="primary" :disabled="!canSave" @click="save">
              💾 保存
            </n-button>
          </div>
        </div>

        <div v-if="!editingId && !isCreating" class="detail-empty">
          <div class="empty-icon">✏️</div>
          <p>从左侧选择一个角色进行编辑</p>
          <p class="empty-sub">或点击右上角新建</p>
        </div>

        <template v-else>
          <!-- MBTI 提示卡 -->
          <div class="mbti-hint">
            <span class="bulb-icon">💡</span>
            <span>MBTI 帮助塑造性格一致的角色行为、预测情境反应、创造有深度的角色关系。</span>
          </div>

          <!-- 标签页 -->
          <n-scrollbar class="tabs-scroll">
            <n-tabs v-model:value="activeTab" type="line" size="medium" class="char-tabs">
              <!-- 基本信息 -->
            <n-tab-pane name="basic" tab="基本信息">
              <n-form label-placement="top" class="tab-form">
                <div class="form-section">
                  <div class="section-title">
                    身份信息
                    <span class="section-hint">角色的基本标识与定位</span>
                  </div>
                  <div class="form-grid-3">
                    <n-form-item label="角色名称">
                      <n-input v-model:value="form.name" size="large" />
                    </n-form-item>
                    <n-form-item label="角色类型">
                      <n-select v-model:value="form.role_type" :options="roleTypes" />
                    </n-form-item>
                    <n-form-item label="主 MBTI">
                      <n-select v-model:value="form.mbti_primary" filterable :options="mbtiOptions" placeholder="如 INTJ" clearable />
                    </n-form-item>
                  </div>
                  <div class="form-grid-3">
                    <n-form-item label="辅 MBTI（可选）">
                      <n-select v-model:value="form.mbti_secondary" filterable :options="mbtiOptions" placeholder="外在表现型" clearable />
                    </n-form-item>
                    <n-form-item label="身份 / 职业">
                      <n-input v-model:value="form.identity" placeholder="表层身份、职业、称号" />
                    </n-form-item>
                    <n-form-item label="阵营 / 所属势力">
                      <n-input v-model:value="form.faction" placeholder="主角团、敌对组织..." />
                    </n-form-item>
                  </div>
                </div>

                <div class="form-section">
                  <div class="section-title">
                    外貌与性格
                    <span class="section-hint">角色的外在形象与内在特质</span>
                  </div>
                  <div class="form-grid-2">
                    <n-form-item label="外貌特征">
                      <n-input v-model:value="form.appearance" type="textarea" :autosize="{ minRows: 4, maxRows: 6 }" />
                    </n-form-item>
                    <n-form-item label="性格特征">
                      <n-input v-model:value="form.personality" type="textarea" :autosize="{ minRows: 4, maxRows: 6 }" />
                    </n-form-item>
                  </div>
                </div>

                <div class="form-section">
                  <div class="section-title">
                    核心驱动力
                    <span class="section-hint">角色行为的深层原因</span>
                  </div>
                  <div class="form-grid-2">
                    <n-form-item label="核心动机">
                      <n-input v-model:value="form.motivation" type="textarea" :autosize="{ minRows: 4, maxRows: 6 }" />
                    </n-form-item>
                    <n-form-item label="弱点 / 缺陷">
                      <n-input v-model:value="form.weakness" type="textarea" :autosize="{ minRows: 4, maxRows: 6 }" />
                    </n-form-item>
                  </div>
                </div>

                <div class="form-section">
                  <div class="section-title">
                    背景与成长
                    <span class="section-hint">角色的过去与未来走向</span>
                  </div>
                  <n-form-item label="背景故事">
                    <n-input v-model:value="form.background" type="textarea" :autosize="{ minRows: 4, maxRows: 8 }" />
                  </n-form-item>
                  <div class="form-grid-2">
                    <n-form-item label="隐藏秘密">
                      <n-input v-model:value="form.secret" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" />
                    </n-form-item>
                    <n-form-item label="对白风格">
                      <n-input v-model:value="form.dialogue_style" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" />
                    </n-form-item>
                  </div>
                  <n-form-item label="人物弧光">
                    <n-input v-model:value="form.arc" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" placeholder="从什么状态走向什么状态，关键转折是什么" />
                  </n-form-item>
                </div>
              </n-form>
            </n-tab-pane>

            <!-- 动态属性管理 -->
            <n-tab-pane name="attributes" tab="属性管理">
              <div class="tab-intro">
                <p class="intro-text">自定义角色属性，不受固定字段限制——玄幻加武功、都市加职位、科幻加装备。</p>
              </div>

              <div class="attr-templates">
                <span class="attr-label">常用属性：</span>
                <div class="attr-tpl-btns">
                  <n-tag
                    v-for="tpl in attributeTemplates"
                    :key="tpl"
                    class="attr-tpl-tag"
                    :bordered="false"
                    @click="addAttributeFromTemplate(tpl)"
                  >
                    + {{ tpl }}
                  </n-tag>
                </div>
              </div>

              <div class="attr-list">
                <div v-for="(attr, index) in form.custom_attributes" :key="index" class="attr-item">
                  <div class="attr-row">
                    <n-input v-model:value="attr.name" placeholder="属性名" class="attr-name-input" />
                    <n-input v-model:value="attr.value" placeholder="属性值" class="attr-value-input" />
                    <n-input-number v-model:value="attr.chapter_no" placeholder="章节" :min="0" class="attr-chapter-input" />
                    <n-button text type="error" @click="removeAttribute(index)">移除</n-button>
                  </div>
                  <n-input v-model:value="attr.change_reason" placeholder="变更原因（可选）" class="attr-reason-input" />
                </div>
              </div>

              <n-button v-if="form.custom_attributes.length === 0" block @click="addEmptyAttribute">
                添加第一条属性
              </n-button>

              <div class="add-attr-row">
                <n-button type="primary" ghost @click="addEmptyAttribute">+ 添加属性</n-button>
              </div>
            </n-tab-pane>

            <!-- 组织关系 -->
            <n-tab-pane name="orgs" tab="组织关系">
              <div class="tab-intro">
                <p class="intro-text">记录角色在各组织中的身份、职位和忠诚度，支持一个角色加入多个组织。</p>
              </div>

              <div class="relation-add-row">
                <n-select v-model:value="newOrgRelation.org_id" filterable :options="organizationOptions" placeholder="选择组织" class="relation-select" />
                <n-input v-model:value="newOrgRelation.position" placeholder="职位" class="relation-position" />
                <n-input-number v-model:value="newOrgRelation.loyalty" :min="1" :max="10" placeholder="忠诚值" class="relation-loyalty" />
                <n-button type="primary" @click="addOrgRelation">添加</n-button>
              </div>

              <div v-if="form.org_relations.length === 0" class="empty-inline">
                <n-empty description="暂无组织关系" :show-icon="false" />
              </div>

              <div v-else class="relation-list">
                <div v-for="(rel, index) in form.org_relations" :key="index" class="relation-item">
                  <div class="relation-main">
                    <span class="relation-name">{{ getOrgNameById(rel.org_id) }}</span>
                    <span class="relation-position-tag">{{ rel.position || '成员' }}</span>
                    <div class="loyalty-bar">
                      <div class="loyalty-fill" :style="{ width: `${rel.loyalty * 10}%` }"></div>
                    </div>
                    <span class="loyalty-text">忠诚 {{ rel.loyalty }}/10</span>
                  </div>
                  <n-button text type="error" size="small" @click="removeOrgRelation(index)">移除</n-button>
                </div>
              </div>
            </n-tab-pane>

            <!-- 人物关系 -->
            <n-tab-pane name="relations" tab="人物关系">
              <div class="tab-intro">
                <p class="intro-text">记录与其他角色的关系，支持关系随剧情演变（生效/失效章节）。</p>
              </div>

              <div class="relation-add-row">
                <n-select v-model:value="newCharRelation.target_id" filterable :options="characterOptions" placeholder="选择角色" class="relation-select" />
                <n-select v-model:value="newCharRelation.relation_type" :options="relationTypeOptions" placeholder="关系类型" class="relation-type-select" />
                <n-input-number v-model:value="newCharRelation.depth" :min="1" :max="10" placeholder="深度" class="relation-loyalty" />
                <n-button type="primary" @click="addCharRelation">添加</n-button>
              </div>

              <div v-if="form.character_relations.length === 0" class="empty-inline">
                <n-empty description="暂无人际关系" :show-icon="false" />
              </div>

              <div v-else class="relation-list">
                <div v-for="(rel, index) in form.character_relations" :key="index" class="relation-item">
                  <div class="relation-main">
                    <span class="relation-name">{{ getCharacterNameById(rel.target_id) }}</span>
                    <n-tag size="small" :bordered="false">{{ rel.relation_type || '其他' }}</n-tag>
                    <div class="depth-bar">
                      <div class="depth-fill" :style="{ width: `${rel.depth * 10}%` }"></div>
                    </div>
                    <span class="muted">深度 {{ rel.depth }}/10</span>
                    <span v-if="rel.effective_from" class="chapter-tag">第{{ rel.effective_from }}章起</span>
                    <span v-if="rel.expires_at" class="chapter-tag danger">第{{ rel.expires_at }}章止</span>
                  </div>
                  <div class="relation-actions">
                    <n-button text size="small" @click="editCharRelation(index)">编辑</n-button>
                    <n-button text type="error" size="small" @click="removeCharRelation(index)">移除</n-button>
                  </div>
                </div>
              </div>
            </n-tab-pane>

            <!-- AI 备注 -->
            <n-tab-pane name="ai" tab="AI 备注">
              <n-form label-placement="top" class="tab-form">
                <div class="form-section">
                  <div class="section-title">
                    出场与关系
                    <span class="section-hint">用于章节生成时的上下文参考</span>
                  </div>
                  <n-form-item label="出场章节">
                    <n-input v-model:value="form.chapters" placeholder="例如：1, 3-5, 12" />
                  </n-form-item>
                  <n-form-item label="关系摘要">
                    <n-input v-model:value="form.relationships" type="textarea" :autosize="{ minRows: 4, maxRows: 6 }" placeholder="师徒、亲族、宿敌、暧昧、亏欠..." />
                  </n-form-item>
                </div>
                <div class="form-section">
                  <div class="section-title">
                    AI 一致性备注
                    <span class="section-hint">帮助 AI 保持角色行为一致</span>
                  </div>
                  <n-form-item label="AI 建议 / 一致性备注">
                    <n-input v-model:value="form.ai_notes" type="textarea" :autosize="{ minRows: 8, maxRows: 12 }" />
                  </n-form-item>
                </div>
              </n-form>
            </n-tab-pane>
            </n-tabs>
          </n-scrollbar>
        </template>
      </section>

      <!-- 右侧：角色辅助面板 -->
      <aside class="side-panel">
        <!-- 完整度卡片 -->
        <div class="insight-card primary-card">
          <div class="card-header">
            <span class="card-icon">📊</span>
            <span class="card-title">档案完整度</span>
          </div>
          <div class="completion-display">
            <div class="completion-ring">
              <svg viewBox="0 0 80 80" class="ring-svg">
                <circle cx="40" cy="40" r="34" class="ring-bg" />
                <circle cx="40" cy="40" r="34" class="ring-fill" :style="{ strokeDasharray: `${currentCompletion * 2.136} 213.6` }" />
              </svg>
              <div class="ring-center">
                <span class="ring-num">{{ currentCompletion }}</span>
                <span class="ring-unit">%</span>
              </div>
            </div>
          </div>
          <p class="completion-advice">{{ completionAdvice }}</p>
        </div>

        <!-- 角色类型分布 -->
        <div class="insight-card">
          <div class="card-header">
            <span class="card-icon">🎭</span>
            <span class="card-title">角色类型分布</span>
          </div>
          <div class="role-stats">
            <div v-for="rt in roleTypes" :key="rt.value" class="role-stat-row">
              <span class="role-icon">{{ roleTypeIcon(rt.value) }}</span>
              <span class="role-name">{{ rt.label }}</span>
              <div class="role-bar">
                <div class="role-bar-fill" :style="{ width: `${rolePercent(rt.value)}%` }"></div>
              </div>
              <span class="role-count">{{ roleCount(rt.value) }}</span>
            </div>
          </div>
        </div>

        <!-- 快速检查 -->
        <div class="insight-card">
          <div class="card-header">
            <span class="card-icon">💡</span>
            <span class="card-title">AI 补全建议</span>
          </div>
          <div class="check-list">
            <div v-for="(hint, idx) in assistantHints" :key="idx" class="check-row" :class="{ ready: hint.done }">
              <span class="check-icon">{{ hint.done ? '✓' : '○' }}</span>
              <span class="check-text">{{ hint.text }}</span>
            </div>
          </div>
        </div>

        <!-- 快速关联 -->
        <div class="insight-card">
          <div class="card-header">
            <span class="card-icon">🔗</span>
            <span class="card-title">快速关联</span>
          </div>
          <n-form label-placement="top" size="small">
            <n-form-item label="关联组织">
              <n-select v-model:value="selectedOrganizationIds" multiple clearable filterable :options="organizationOptions" placeholder="选择组织" />
            </n-form-item>
            <n-form-item label="关联人物">
              <n-select v-model:value="selectedCharacterIds" multiple clearable filterable :options="characterOptions" placeholder="选择重要关系人" />
            </n-form-item>
          </n-form>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref } from 'vue'
import { useDirtySnapshot } from '@/composables/useDirtySnapshot'
import { createResource, deleteResource, listResource, updateResource } from '@/api/resources'
import { useProjectStore } from '@/stores/project'
import { useProjectDataLoader } from '@/composables/useProjectDataLoader'
import { notify } from '@/utils/notify'
import type { CharacterAttribute, CharacterItem, CharacterOrgRelation, CharacterRelation, OrganizationItem } from '@/types/domain'

const projectStore = useProjectStore()
const characters = ref<CharacterItem[]>([])
const organizations = ref<OrganizationItem[]>([])
const keyword = ref('')
const roleFilter = ref<string | null>(null)
const editingId = ref<number | null>(null)
const isCreating = ref(false)
const loading = ref(false)
const activeTab = ref('basic')

// ---- 表单数据 ----
const form = reactive({
  name: '新角色',
  role_type: 'supporting',
  identity: '',
  faction: '',
  mbti_primary: '',
  mbti_secondary: '',
  appearance: '',
  personality: '',
  background: '',
  motivation: '',
  weakness: '',
  secret: '',
  dialogue_style: '',
  arc: '',
  relationships: '',
  chapters: '',
  organization_ids: '',
  related_character_ids: '',
  ai_notes: '',
  custom_attributes: [] as CharacterAttribute[],
  org_relations: [] as CharacterOrgRelation[],
  character_relations: [] as CharacterRelation[],
  mbti: ''
})

const { isDirty, markClean, confirmIfDirty } = useDirtySnapshot(form, '当前角色档案有未保存内容，继续切换会丢弃这些修改。')

// ===== 选项配置 =====
const mbtiOptions = [
  'INTJ', 'INTP', 'ENTJ', 'ENTP',
  'INFJ', 'INFP', 'ENFJ', 'ENFP',
  'ISTJ', 'ISFJ', 'ESTJ', 'ESFJ',
  'ISTP', 'ISFP', 'ESTP', 'ESFP'
].map((v) => ({ label: v, value: v }))

const relationTypeOptions = [
  { label: '师徒', value: '师徒' },
  { label: '父子', value: '父子' },
  { label: '母女', value: '母女' },
  { label: '兄弟', value: '兄弟' },
  { label: '姐妹', value: '姐妹' },
  { label: '恋人', value: '恋人' },
  { label: '挚友', value: '挚友' },
  { label: '仇敌', value: '仇敌' },
  { label: '竞争对手', value: '竞争对手' },
  { label: '上下级', value: '上下级' },
  { label: '其他', value: '其他' }
]

const attributeTemplates = ['武功', '宝物', '职称', '技能', '装备', '异能', '功法', '身份']

const roleTypes = [
  { label: '主角', value: 'protagonist' },
  { label: '配角', value: 'supporting' },
  { label: '反派', value: 'antagonist' }
]

// ---- 新增关系的临时数据 ----
const newOrgRelation = reactive<{ org_id: number | null; position: string; loyalty: number }>({
  org_id: null,
  position: '',
  loyalty: 5
})
const newCharRelation = reactive<{
  target_id: number | null
  relation_type: string
  depth: number
  effective_from: number | null
  expires_at: number | null
}>({
  target_id: null,
  relation_type: '其他',
  depth: 5,
  effective_from: null,
  expires_at: null
})

// ===== 计算属性 =====
const searchableFields = computed(() => [
  'name', 'role_type', 'identity', 'faction', 'mbti', 'appearance',
  'personality', 'background', 'motivation', 'weakness', 'secret',
  'dialogue_style', 'arc', 'relationships', 'chapters', 'ai_notes'
] as const)

const filteredCharacters = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return characters.value.filter((item) => {
    const matchedText =
      !text || searchableFields.value.map((field) => item[field] ?? '').join(' ').toLowerCase().includes(text)
    const matchedRole = !roleFilter.value || item.role_type === roleFilter.value
    return matchedText && matchedRole
  })
})

// 按角色类型分组
const groupedCharacters = computed(() => {
  const groups: { roleType: string; items: CharacterItem[] }[] = []
  for (const rt of roleTypes) {
    const items = filteredCharacters.value.filter((c) => c.role_type === rt.value)
    if (items.length > 0) {
      groups.push({ roleType: rt.value, items })
    }
  }
  // 其他类型
  const others = filteredCharacters.value.filter(
    (c) => !roleTypes.some((rt) => rt.value === c.role_type)
  )
  if (others.length > 0) {
    groups.push({ roleType: 'other', items: others })
  }
  return groups
})

// 统计数据
const totalCount = computed(() => characters.value.length)
const protagonistCount = computed(() => characters.value.filter((c) => c.role_type === 'protagonist').length)
const avgCompletion = computed(() => {
  if (characters.value.length === 0) return 0
  const total = characters.value.reduce((sum, c) => sum + completionOf(c), 0)
  return Math.round(total / characters.value.length)
})

const canSave = computed(() => form.name.trim().length > 0)

const currentCompletion = computed(() => completionOf(form))

const completionAdvice = computed(() => {
  if (currentCompletion.value >= 80) return '角色已经能支撑章节生成，可继续补充关系变化。'
  if (currentCompletion.value >= 50) return '建议补齐动机、弱点、秘密和人物弧光。'
  return '先写清身份、阵营、动机和背景，角色才不会在正文里漂移。'
})

const assistantHints = computed(() => [
  { done: !!form.motivation, text: form.motivation ? '核心动机可进入章节目标' : '缺少核心动机' },
  { done: !!form.weakness, text: form.weakness ? '弱点可转化为冲突' : '缺少弱点描述' },
  { done: !!form.dialogue_style, text: form.dialogue_style ? '对白风格可用于精修' : '缺少对白风格' },
  { done: !!form.arc, text: form.arc ? '人物弧光已规划' : '建议补充人物弧光' }
])

const organizationOptions = computed(() => organizations.value.map((item) => ({ label: item.name, value: item.id })))
const characterOptions = computed(() =>
  characters.value.filter((item) => item.id !== editingId.value).map((item) => ({ label: item.name, value: item.id }))
)

const selectedOrganizationIds = computed({
  get: () => parseIds(form.organization_ids),
  set: (value: number[]) => {
    form.organization_ids = joinIds(value)
  }
})
const selectedCharacterIds = computed({
  get: () => parseIds(form.related_character_ids),
  set: (value: number[]) => {
    form.related_character_ids = joinIds(value)
  }
})

// ===== 工具函数 =====
function getOrgNameById(id: number): string {
  return organizations.value.find((o) => o.id === id)?.name || `组织#${id}`
}
function getCharacterNameById(id: number): string {
  return characters.value.find((c) => c.id === id)?.name || `角色#${id}`
}

function parseIds(value: string) {
  return value
    .split(',')
    .map((item) => Number(item.trim()))
    .filter((item) => Number.isFinite(item) && item > 0)
}

function joinIds(value: number[]) {
  return value.join(',')
}

function shortText(value: string, max = 50) {
  return value?.length > max ? `${value.slice(0, max)}...` : value || ''
}

function completionOf(item: Partial<CharacterItem> | typeof form) {
  const fields = [
    'name', 'role_type', 'identity', 'faction', 'mbti', 'appearance',
    'personality', 'background', 'motivation', 'weakness', 'secret',
    'dialogue_style', 'arc'
  ]
  const finished = fields.filter((field) => String(item[field as keyof typeof item] ?? '').trim()).length
  return Math.round((finished / fields.length) * 100)
}

function roleTypeLabel(value: string) {
  return roleTypes.find((item) => item.value === value)?.label ?? '其他'
}

function roleTypeIcon(roleType: string): string {
  const icons: Record<string, string> = {
    protagonist: '⭐',
    supporting: '👤',
    antagonist: '💀',
    other: '📁'
  }
  return icons[roleType] || '👤'
}

function roleTagType(roleType: string): 'default' | 'success' | 'info' | 'warning' | 'error' {
  const map: Record<string, 'default' | 'success' | 'info' | 'warning' | 'error'> = {
    protagonist: 'success',
    supporting: 'info',
    antagonist: 'error'
  }
  return map[roleType] || 'default'
}

function roleCount(roleValue: string) {
  return characters.value.filter((c) => c.role_type === roleValue).length
}

function rolePercent(roleValue: string) {
  if (characters.value.length === 0) return 0
  return Math.round((roleCount(roleValue) / characters.value.length) * 100)
}

// ===== 动态属性操作 =====
function addEmptyAttribute() {
  form.custom_attributes.push({ name: '', value: '', chapter_no: null, change_reason: '' })
}
function addAttributeFromTemplate(name: string) {
  form.custom_attributes.push({ name, value: '', chapter_no: null, change_reason: '' })
}
function removeAttribute(index: number) {
  form.custom_attributes.splice(index, 1)
}

// ===== 组织关系操作 =====
function addOrgRelation() {
  if (!newOrgRelation.org_id) {
    notify.warning('请先选择组织')
    return
  }
  if (form.org_relations.some((r) => r.org_id === newOrgRelation.org_id)) {
    notify.warning('该组织已添加')
    return
  }
  form.org_relations.push({
    org_id: newOrgRelation.org_id,
    position: newOrgRelation.position || '成员',
    loyalty: newOrgRelation.loyalty
  })
  newOrgRelation.org_id = null
  newOrgRelation.position = ''
  newOrgRelation.loyalty = 5
  form.organization_ids = joinIds(form.org_relations.map((r) => r.org_id))
}
function removeOrgRelation(index: number) {
  form.org_relations.splice(index, 1)
  form.organization_ids = joinIds(form.org_relations.map((r) => r.org_id))
}

// ===== 人物关系操作 =====
function addCharRelation() {
  if (!newCharRelation.target_id) {
    notify.warning('请先选择角色')
    return
  }
  if (form.character_relations.some((r) => r.target_id === newCharRelation.target_id)) {
    notify.warning('该角色已添加关系')
    return
  }
  form.character_relations.push({
    target_id: newCharRelation.target_id,
    relation_type: newCharRelation.relation_type,
    depth: newCharRelation.depth,
    effective_from: newCharRelation.effective_from,
    expires_at: newCharRelation.expires_at
  })
  newCharRelation.target_id = null
  newCharRelation.relation_type = '其他'
  newCharRelation.depth = 5
  newCharRelation.effective_from = null
  newCharRelation.expires_at = null
  form.related_character_ids = joinIds(form.character_relations.map((r) => r.target_id))
}
function removeCharRelation(index: number) {
  form.character_relations.splice(index, 1)
  form.related_character_ids = joinIds(form.character_relations.map((r) => r.target_id))
}
function editCharRelation(index: number) {
  const rel = form.character_relations[index]
  newCharRelation.target_id = rel.target_id
  newCharRelation.relation_type = rel.relation_type
  newCharRelation.depth = rel.depth
  newCharRelation.effective_from = rel.effective_from ?? null
  newCharRelation.expires_at = rel.expires_at ?? null
  form.character_relations.splice(index, 1)
  form.related_character_ids = joinIds(form.character_relations.map((r) => r.target_id))
}

// ===== 表单操作 =====
function fillForm(item?: Partial<CharacterItem>) {
  function safeParseArray<T>(value: unknown, fallback: T[] = []): T[] {
    if (Array.isArray(value)) return value
    if (typeof value === 'string') {
      try {
        const parsed = JSON.parse(value)
        return Array.isArray(parsed) ? parsed : fallback
      } catch {
        return fallback
      }
    }
    return fallback
  }

  Object.assign(form, {
    name: item?.name ?? '新角色',
    role_type: item?.role_type ?? 'supporting',
    identity: item?.identity ?? '',
    faction: item?.faction ?? '',
    mbti_primary: item?.mbti_primary || item?.mbti || '',
    mbti_secondary: item?.mbti_secondary ?? '',
    appearance: item?.appearance ?? '',
    personality: item?.personality ?? '',
    background: item?.background ?? '',
    motivation: item?.motivation ?? '',
    weakness: item?.weakness ?? '',
    secret: item?.secret ?? '',
    dialogue_style: item?.dialogue_style ?? '',
    arc: item?.arc ?? '',
    relationships: item?.relationships ?? '',
    chapters: item?.chapters ?? '',
    organization_ids: item?.organization_ids ?? '',
    related_character_ids: item?.related_character_ids ?? '',
    ai_notes: item?.ai_notes ?? '',
    custom_attributes: safeParseArray<CharacterAttribute>(item?.custom_attributes),
    org_relations: safeParseArray<CharacterOrgRelation>(item?.org_relations),
    character_relations: safeParseArray<CharacterRelation>(item?.character_relations),
    mbti: item?.mbti ?? ''
  })
  markClean()
}

async function startCreate() {
  if (!(await confirmIfDirty())) return
  editingId.value = null
  isCreating.value = true
  activeTab.value = 'basic'
  fillForm()
  await nextTick()
  markClean()
}

async function selectCharacter(item: CharacterItem) {
  if (editingId.value === item.id) return
  if (!(await confirmIfDirty())) return
  editingId.value = item.id
  isCreating.value = false
  fillForm(item)
  await nextTick()
  markClean()
}

async function resetCurrent() {
  if (!(await confirmIfDirty('确定要重置当前角色档案吗？'))) return
  const current = characters.value.find((item) => item.id === editingId.value)
  if (current) {
    fillForm(current)
  } else {
    editingId.value = null
    isCreating.value = false
    fillForm()
  }
  await nextTick()
  markClean()
}

async function ensureProject() {
  if (!projectStore.currentProject) await projectStore.loadDefaultProject()
  return projectStore.currentProject?.id
}

// ===== 数据加载 =====
async function load() {
  const projectId = projectStore.currentProject!.id
  loading.value = true
  try {
    const [characterList, organizationList] = await Promise.all([
      listResource<CharacterItem>(projectId, 'characters'),
      listResource<OrganizationItem>(projectId, 'organizations')
    ])
    characters.value = characterList
    organizations.value = organizationList

    if (!editingId.value && !isCreating.value && characters.value[0]) {
      editingId.value = characters.value[0].id
      fillForm(characters.value[0])
      await nextTick()
      markClean()
    }
  } finally {
    loading.value = false
  }
}

// ===== CRUD =====
async function save() {
  if (!canSave.value) return
  const projectId = await ensureProject()
  if (!projectId) return

  const payload = {
    ...form,
    mbti: form.mbti_primary,
    custom_attributes: JSON.stringify(form.custom_attributes),
    org_relations: JSON.stringify(form.org_relations),
    character_relations: JSON.stringify(form.character_relations)
  }

  if (editingId.value) {
    const updated = await updateResource<CharacterItem>('characters', editingId.value, payload)
    notify.success('角色档案已更新')
    await load()
    const fresh = characters.value.find((item) => item.id === updated.id)
    if (fresh) {
      fillForm(fresh)
      await nextTick()
      markClean()
    }
  } else {
    const created = await createResource<CharacterItem>('characters', { project_id: projectId, ...payload })
    notify.success('角色档案已新增')
    isCreating.value = false
    await load()
    const fresh = characters.value.find((item) => item.id === created.id)
    if (fresh) {
      editingId.value = fresh.id
      fillForm(fresh)
      await nextTick()
      markClean()
    }
  }
}

async function remove() {
  if (!editingId.value) return
  const currentIndex = characters.value.findIndex((item) => item.id === editingId.value)
  await deleteResource('characters', editingId.value)
  notify.success('角色档案已删除')
  const nextItem = characters.value[currentIndex + 1] || characters.value[currentIndex - 1]
  if (nextItem) {
    editingId.value = nextItem.id
    fillForm(nextItem)
  } else {
    editingId.value = null
    isCreating.value = false
    fillForm()
  }
  await load()
  await nextTick()
  markClean()
}

useProjectDataLoader(load)
</script>

<style scoped>
.character-page {
  height: calc(100vh - 60px);
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-bottom: 12px;
}

/* ===== 页头 ===== */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.page-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0px;
}

.title-icon {
  font-size: 18px;
  margin-right: -2px;
}

.page-subtitle {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-stats {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 14px;
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 55px;
}

.stat-num {
  font-size: 16px;
  font-weight: 700;
  color: var(--n-color-primary, #3b82f6);
  line-height: 1.2;
}

.stat-label {
  font-size: 10px;
  color: var(--n-text-color-3, #6b7280);
  margin-top: 2px;
}

.stat-divider {
  width: 1px;
  height: 24px;
  background: var(--n-border-color, #2a2f3a);
}

/* ===== 工作区 ===== */
.workbench {
  flex: 1;
  display: grid;
  grid-template-columns: 320px minmax(520px, 1fr) 280px;
  gap: 12px;
  min-height: 0;
  min-width: 0;
}

/* ===== 通用面板 ===== */
.list-panel,
.detail-panel,
.side-panel {
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ===== 左侧列表面板 ===== */
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

.group-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 8px 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--n-text-color-2, #9ca3af);
  position: sticky;
  top: 0;
  background: var(--n-color-card, #1a1d21);
  z-index: 1;
}

.group-header:first-child {
  padding-top: 4px;
}

.group-icon {
  font-size: 14px;
}

.group-name {
  flex: 1;
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
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid transparent;
}

.character-item:hover {
  background: var(--n-color-hover, #23272f);
}

.character-item.active {
  background: var(--n-color-primary-1-suppl, #1e3a5f);
  border-color: var(--n-color-primary-3, #3b82f6);
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
.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  flex-shrink: 0;
}

.detail-title h2 {
  font-size: 15px;
  font-weight: 600;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-sub {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  margin-top: 2px;
}

.dirty-dot {
  color: #f59e0b;
  font-size: 12px;
  animation: dirtyPulse 1.5s ease-in-out infinite;
}

@keyframes dirtyPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.detail-actions {
  display: flex;
  gap: 8px;
}

.detail-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--n-text-color-3, #6b7280);
  padding: 40px;
  text-align: center;
}

.detail-empty .empty-icon {
  font-size: 48px;
  margin-bottom: 8px;
}

.detail-empty p {
  margin: 0;
  font-size: 14px;
}

.detail-empty .empty-sub {
  font-size: 12px;
}

/* MBTI 提示卡 */
.mbti-hint {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin: 14px 20px 0;
  padding: 10px 14px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 8px;
  font-size: 12px;
  color: #a5b4fc;
  flex-shrink: 0;
}

.mbti-hint .bulb-icon {
  font-size: 14px;
  flex-shrink: 0;
}

/* 标签页滚动容器 */
.tabs-scroll {
  flex: 1;
  min-height: 0;
}

/* 标签页 */
.char-tabs {
  padding: 0 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.char-tabs :deep(.n-tabs-nav) {
  flex-shrink: 0;
}

.char-tabs :deep(.n-tabs-tab) {
  padding: 10px 16px;
}

.char-tabs :deep(.n-tabs-panels) {
  flex: 1;
  min-height: 0;
}

.char-tabs :deep(.n-tabs-panel) {
  height: 100%;
  padding: 0 !important;
}

.tab-form {
  padding: 8px 0 24px;
}

.form-section {
  margin-bottom: 24px;
}

.form-section:last-child {
  margin-bottom: 0;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 14px;
  padding-left: 10px;
  border-left: 3px solid #6366f1;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-hint {
  font-size: 11px;
  font-weight: 400;
  color: var(--n-text-color-3, #6b7280);
  border-left: none;
  padding-left: 0;
}

.form-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 16px;
}

.form-grid-3 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px 16px;
}

/* 标签页介绍 */
.tab-intro {
  margin: 16px 0;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
}

.intro-text {
  margin: 0;
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
}

/* 动态属性 */
.attr-templates {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.attr-label {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  margin-right: 4px;
}

.attr-tpl-btns {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.attr-tpl-tag {
  cursor: pointer;
  transition: all 0.2s;
}

.attr-tpl-tag:hover {
  opacity: 0.8;
}

.attr-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}

.attr-item {
  background: var(--n-color-1, #1e2228);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
  padding: 12px;
}

.attr-row {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 8px;
}

.attr-name-input {
  flex: 0 0 120px;
}

.attr-value-input {
  flex: 1;
}

.attr-chapter-input {
  flex: 0 0 100px;
}

.attr-reason-input {
  width: 100%;
}

.add-attr-row {
  margin-top: 8px;
  display: flex;
  justify-content: center;
}

/* 关系添加行 */
.relation-add-row {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.relation-select {
  flex: 0 0 180px;
}

.relation-type-select {
  flex: 0 0 140px;
}

.relation-position {
  flex: 0 0 120px;
}

.relation-loyalty {
  flex: 0 0 100px;
}

/* 关系列表 */
.relation-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.relation-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  background: var(--n-color-1, #1e2228);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
}

.relation-main {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  flex: 1;
}

.relation-name {
  font-weight: 600;
  font-size: 13px;
}

.relation-position-tag {
  padding: 2px 8px;
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
  border-radius: 4px;
  font-size: 11px;
}

/* 忠诚值/深度进度条 */
.loyalty-bar,
.depth-bar {
  width: 80px;
  height: 6px;
  background: var(--n-border-color, #2a2f3a);
  border-radius: 3px;
  overflow: hidden;
}

.loyalty-fill {
  height: 100%;
  background: linear-gradient(90deg, #22c55e, #eab308, #ef4444);
  border-radius: 3px;
}

.depth-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #ec4899);
  border-radius: 3px;
}

.loyalty-text {
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
  min-width: 60px;
}

.muted {
  color: var(--n-text-color-3, #6b7280);
  font-size: 11px;
}

.chapter-tag {
  padding: 2px 6px;
  background: rgba(34, 211, 238, 0.15);
  color: #67e8f9;
  border-radius: 4px;
  font-size: 10px;
}

.chapter-tag.danger {
  background: rgba(239, 68, 68, 0.15);
  color: #fca5a5;
}

.relation-actions {
  display: flex;
  gap: 4px;
}

.empty-inline {
  padding: 24px 0;
  text-align: center;
}

/* ===== 右侧面板 ===== */
.side-panel {
  padding: 12px;
  gap: 12px;
  overflow-y: auto;
}

.insight-card {
  padding: 14px;
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
  background: var(--n-color-1, #1e2228);
}

.primary-card {
  background: linear-gradient(135deg, var(--n-color-primary-1-suppl, #1e3a5f) 0%, var(--n-color-1, #1e2228) 100%);
  border-color: var(--n-color-primary-3, #3b82f6);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.card-icon {
  font-size: 16px;
}

.card-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--n-text-color-1, #e5e7eb);
}

/* 完整度圆环 */
.completion-display {
  display: flex;
  justify-content: center;
  margin-bottom: 12px;
}

.completion-ring {
  position: relative;
  width: 80px;
  height: 80px;
}

.ring-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.ring-bg {
  fill: none;
  stroke: var(--n-border-color, #2a2f3a);
  stroke-width: 6;
}

.ring-fill {
  fill: none;
  stroke: var(--n-color-primary, #3b82f6);
  stroke-width: 6;
  stroke-linecap: round;
  transition: stroke-dasharray 0.5s ease;
}

.ring-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: baseline;
  gap: 1px;
}

.ring-num {
  font-size: 20px;
  font-weight: 700;
  color: var(--n-text-color-1, #e5e7eb);
  line-height: 1;
}

.ring-unit {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
}

.completion-advice {
  margin: 0;
  font-size: 11px;
  color: var(--n-text-color-2, #9ca3af);
  line-height: 1.6;
  text-align: center;
}

/* 角色类型统计 */
.role-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.role-stat-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.role-icon {
  font-size: 14px;
  width: 18px;
  text-align: center;
}

.role-name {
  width: 36px;
  color: var(--n-text-color-2, #9ca3af);
}

.role-bar {
  flex: 1;
  height: 6px;
  background: var(--n-border-color, #2a2f3a);
  border-radius: 3px;
  overflow: hidden;
}

.role-bar-fill {
  height: 100%;
  background: var(--n-color-primary, #3b82f6);
  border-radius: 3px;
  transition: width 0.3s;
}

.role-count {
  width: 20px;
  text-align: right;
  font-weight: 600;
  color: var(--n-text-color-2, #9ca3af);
}

/* 检查清单 */
.check-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.check-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
}

.check-row.ready {
  color: var(--n-text-color-2, #9ca3af);
}

.check-icon {
  flex-shrink: 0;
  width: 16px;
  text-align: center;
  font-size: 11px;
}

.check-row.ready .check-icon {
  color: var(--n-color-success, #36d399);
}

.check-text {
  line-height: 1.5;
}
</style>
