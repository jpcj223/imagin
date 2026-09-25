<template>
  <div class="setting-co-page">
    <!-- 左侧：设定目录 -->
    <aside class="left-panel">
      <div class="panel-header">
        <div class="panel-title">
          <span>📚</span>
          <span>设定目录</span>
          <span class="ver-badge">L3 记忆</span>
        </div>
        <div class="panel-subtitle">提取到字段后写回档案并沉淀记忆</div>
      </div>

      <div class="setting-groups">
        <!-- 角色设定 -->
        <div class="setting-group">
          <div class="group-header" @click="expandedGroups.characters = !expandedGroups.characters">
            <span class="group-arrow" :class="{ expanded: expandedGroups.characters }">▸</span>
            <span class="group-icon">👤</span>
            <span>角色设定</span>
            <span class="group-progress">{{ settingIndex?.character_completeness || 0 }}%</span>
          </div>
          <transition name="expand">
            <div v-if="expandedGroups.characters" class="group-items">
              <div
                v-for="char in settingIndex?.characters || []"
                :key="char.id"
                class="setting-item"
                :class="{ active: activeTargetId === char.id && activeTargetType === 'character' }"
                @click="startChat('character', char.id, char.name)"
              >
                <span class="item-status" :class="char.status"></span>
                <span class="item-name">{{ char.name }}</span>
                <span class="item-completeness">{{ char.completeness }}%</span>
              </div>
              <div v-if="!(settingIndex?.characters || []).length" class="group-empty">暂无人物档案，请先在人物卡片中创建</div>
            </div>
          </transition>
        </div>

        <!-- 世界观 -->
        <div class="setting-group">
          <div class="group-header" @click="expandedGroups.world = !expandedGroups.world">
            <span class="group-arrow" :class="{ expanded: expandedGroups.world }">▸</span>
            <span class="group-icon">🌍</span>
            <span>世界观</span>
            <span class="group-progress">{{ settingIndex?.world?.completeness || 0 }}%</span>
          </div>
          <transition name="expand">
            <div v-if="expandedGroups.world" class="group-items">
              <div
                v-for="item in settingIndex?.world?.items || []"
                :key="item.key"
                class="setting-item"
                :class="{ active: activeTargetType === 'world' && activeTargetId === settingIndex?.world?.target_id }"
                @click="startChat('world', settingIndex?.world?.target_id || 0, settingIndex?.world?.name || '世界观总览')"
              >
                <span class="item-status" :class="item.status"></span>
                <span class="item-name">{{ item.label }}</span>
              </div>
            </div>
          </transition>
        </div>

        <!-- 伏笔 -->
        <div class="setting-group">
          <div class="group-header" @click="expandedGroups.foreshadowing = !expandedGroups.foreshadowing">
            <span class="group-arrow" :class="{ expanded: expandedGroups.foreshadowing }">▸</span>
            <span class="group-icon">🎭</span>
            <span>伏笔线索</span>
            <span class="group-progress">{{ settingIndex?.foreshadowing?.completeness || 0 }}%</span>
          </div>
          <transition name="expand">
            <div v-if="expandedGroups.foreshadowing" class="group-items">
              <div
                v-for="item in settingIndex?.foreshadowing?.items || []"
                :key="item.id"
                class="setting-item"
                :class="{ active: activeTargetId === item.id && activeTargetType === 'foreshadowing' }"
                @click="startChat('foreshadowing', item.id, item.name)"
              >
                <span class="item-status" :class="item.status"></span>
                <span class="item-name">{{ item.name }}</span>
                <span class="item-completeness">{{ item.completeness }}%</span>
              </div>
              <div v-if="!(settingIndex?.foreshadowing?.items || []).length" class="group-empty">暂无伏笔，请先在伏笔看板创建</div>
            </div>
          </transition>
        </div>

        <div class="setting-group">
          <div class="group-header" @click="expandedGroups.sessions = !expandedGroups.sessions">
            <span class="group-arrow" :class="{ expanded: expandedGroups.sessions }">▸</span>
            <span class="group-icon">🕘</span>
            <span>最近对话</span>
            <span class="group-progress">{{ recentSessions.length }}</span>
          </div>
          <transition name="expand">
            <div v-if="expandedGroups.sessions" class="group-items">
              <div
                v-for="session in recentSessions"
                :key="session.session_id"
                class="setting-item session-item"
                :class="{ active: currentSession?.session_id === session.session_id }"
                @click="resumeSession(session)"
              >
                <span class="item-status" :class="session.status === 'active' ? 'partial' : 'empty'"></span>
                <span class="item-name">{{ session.target_name || session.title }}</span>
                <span class="session-type">{{ settingTargetLabel(session.target_type) }}</span>
              </div>
              <div v-if="recentSessions.length === 0" class="group-empty">还没有历史对话</div>
            </div>
          </transition>
        </div>
      </div>

      <button class="new-chat-btn" @click="handleNewChat">
        <span>+</span> 新建设定对话
      </button>

      <div class="sidebar-footer">
        <div class="footer-memory-info">
          <span class="footer-icon">🧠</span>
          <div class="footer-text">
            <div class="footer-title">对话即记忆</div>
            <div class="footer-desc">提取到的字段会写回档案并沉淀为 L3 记忆</div>
          </div>
        </div>
      </div>
    </aside>

    <!-- 中间：对话区 -->
    <div class="chat-panel">
      <div class="chat-header">
        <div class="agent-avatar">
          <div class="avatar-ring"></div>
          <div class="avatar-inner">🧠</div>
        </div>
        <div class="chat-agent-info">
          <div class="chat-agent-name">
            设定共创 Agent
            <span v-if="isSending" class="status-dot thinking"></span>
            <span v-else class="status-dot"></span>
          </div>
          <div class="chat-agent-desc">
            <template v-if="currentSession">
              正在完善「{{ currentSession.target_name }}」的设定 ·
              完整度 {{ currentSession.completeness }}% ·
              {{ sessionHasMemory ? '本会话已沉淀项目记忆' : '等待提取可写入字段' }}
            </template>
            <template v-else>
            选择左侧人物、世界观或伏笔，开始对话式设定完善
            </template>
          </div>
        </div>
        <div class="chat-header-actions">
          <button class="header-btn" title="导出当前对话" :disabled="!currentSession || !messages.length" @click="exportConversation">📤</button>
          <button class="header-btn" title="新建设定对话" @click="handleNewChat">＋</button>
        </div>
      </div>

      <div class="chat-messages" ref="messagesRef">
        <template v-if="messages.length > 0">
          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            class="message"
            :class="msg.role"
          >
            <div class="msg-avatar">
              {{ msg.role === 'user' ? '👤' : '🧠' }}
            </div>
            <div class="msg-body">
              <div class="msg-name">
                {{ msg.role === 'user' ? '你' : '设定共创 Agent' }}
                <span class="time">{{ formatTime(msg.created_at) }}</span>
              </div>
              <div v-if="msg.role === 'user'" class="msg-bubble">{{ msg.content }}</div>
              <div v-else class="msg-bubble" v-html="sanitizeMessageHtml(msg.content)"></div>
              <!-- 快速回复（只在最后一条 agent 消息显示） -->
              <div
                v-if="msg.role === 'assistant' && idx === messages.length - 1 && quickReplies.length > 0 && !isSending"
                class="quick-replies"
              >
                <div
                  v-for="(reply, ri) in quickReplies"
                  :key="ri"
                  class="quick-reply"
                  @click="sendQuickReply(reply)"
                >
                  {{ reply }}
                </div>
              </div>
            </div>
          </div>

          <!-- 正在输入提示 -->
          <div v-if="isSending" class="message agent">
            <div class="msg-avatar">🧠</div>
            <div class="msg-body">
              <div class="msg-bubble thinking-bubble">
                <span class="thinking-icon">💭</span>
                <span>Agent 正在思考...</span>
              </div>
            </div>
          </div>
        </template>

        <div v-else class="empty-state">
          <div class="empty-icon">💬</div>
          <div class="empty-title">开始设定共创</div>
          <div class="empty-desc">
            选择一个目标开始；每次补充都会更新右侧档案，并保留在本项目的对话记忆中。
          </div>
          <div class="empty-start-actions">
            <button class="empty-start-card" @click="openSettingGroup('characters')">
              <span class="empty-start-icon">👤</span>
              <span><strong>完善人物</strong><small>{{ settingIndex?.character_count || 0 }} 个人物档案</small></span>
              <span class="empty-start-arrow">›</span>
            </button>
            <button class="empty-start-card" @click="startWorldSetting">
              <span class="empty-start-icon">🌍</span>
              <span><strong>完善世界观</strong><small>时代、力量体系与核心规则</small></span>
              <span class="empty-start-arrow">›</span>
            </button>
            <button class="empty-start-card" @click="openSettingGroup('foreshadowing')">
              <span class="empty-start-icon">🎭</span>
            <span><strong>完善伏笔</strong><small>{{ (settingIndex?.foreshadowing?.items || []).length }} 条伏笔线索</small></span>
              <span class="empty-start-arrow">›</span>
            </button>
          </div>
          <div v-if="!settingIndex?.character_count && !(settingIndex?.foreshadowing?.items || []).length" class="empty-start-note">
            还没有人物或伏笔档案？可以先从世界观开始，或点击左侧“新建设定对话”。
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="chat-input-area">
        <div v-if="showPromptTemplates && currentSession" class="prompt-template-panel">
          <div class="prompt-template-heading">选择一个切入方向</div>
          <button v-for="template in promptTemplates" :key="template" class="prompt-template" @click="insertPromptTemplate(template)">
            {{ template }}
          </button>
        </div>
        <div class="input-wrapper">
          <textarea
            ref="textareaRef"
            v-model="inputMessage"
            class="input-textarea"
            :rows="1"
            placeholder="和 Agent 聊聊你的设定想法..."
            @keydown.enter.exact.prevent="handleSend"
            @input="autoResize"
            :disabled="!currentSession || isSending"
          ></textarea>
          <div class="input-tools">
            <button class="tool-btn" title="插入设定提问模板" :disabled="!currentSession" @click="showPromptTemplates = !showPromptTemplates">📋</button>
            <button
              class="send-btn"
              title="发送"
              :disabled="!inputMessage.trim() || !currentSession || isSending"
              @click="handleSend"
            >
              ➤
            </button>
          </div>
        </div>
        <div class="input-hint">
          <span>💡 提示：你可以描述任何想法，Agent 会自动整理成结构化设定</span>
          <span style="margin-left: auto">
            Enter 发送 · <kbd>Shift</kbd>+<kbd>Enter</kbd> 换行
          </span>
        </div>
      </div>
    </div>

    <!-- 右侧：实时设定卡片 -->
    <div class="right-panel">
      <div class="right-header">
        <div class="right-title">
          <span class="live-dot" v-if="currentSession"></span>
          实时设定卡片
        </div>
        <div class="right-subtitle">
          {{ settingDetail?.name || '选择人物、世界观或伏笔查看' }}
        </div>
      </div>

      <div class="right-body">
        <template v-if="settingDetail && currentSession?.target_type === 'world'">
          <div class="completeness">
            <div class="completeness-header">
              <span class="completeness-label">世界观完整度</span>
              <span class="completeness-value">{{ settingDetail.completeness || 0 }}%</span>
            </div>
            <div class="completeness-bar">
              <div class="completeness-fill" :style="{ width: (settingDetail.completeness || 0) + '%' }"></div>
            </div>
          </div>
          <div
            v-for="field in worldDetailFields"
            :key="field.key"
            class="setting-card"
            :class="{ 'just-updated': lastUpdatedField === field.key }"
          >
            <div class="card-header">
              <span class="card-icon">{{ field.icon }}</span>
              <span class="card-title">{{ field.label }}</span>
              <span v-if="lastUpdatedField === field.key" class="card-badge">刚更新</span>
            </div>
            <div class="card-field">
              <div class="field-value" :class="{ partial: !settingDetail[field.key] }">
                {{ settingDetail[field.key] || '待补充...' }}
              </div>
            </div>
          </div>
          <div class="card-footer-badge">
            <span class="memory-level-badge l3">📁 L3 项目记忆</span>
          </div>
        </template>

        <template v-else-if="settingDetail && currentSession?.target_type === 'foreshadowing'">
          <div class="completeness">
            <div class="completeness-header">
              <span class="completeness-label">伏笔设定完整度</span>
              <span class="completeness-value">{{ settingDetail.completeness || 0 }}%</span>
            </div>
            <div class="completeness-bar">
              <div class="completeness-fill" :style="{ width: (settingDetail.completeness || 0) + '%' }"></div>
            </div>
          </div>
          <div v-for="field in foreshadowingDetailFields" :key="field.key" class="setting-card" :class="{ 'just-updated': lastUpdatedField === field.key }">
            <div class="card-header">
              <span class="card-icon">{{ field.icon }}</span>
              <span class="card-title">{{ field.label }}</span>
              <span v-if="lastUpdatedField === field.key" class="card-badge">刚更新</span>
            </div>
            <div class="card-field">
              <div class="field-value" :class="{ partial: !settingDetail[field.key] }">
                {{ settingDetail[field.key] || '待补充...' }}
              </div>
            </div>
          </div>
          <div class="setting-card">
            <div class="card-header"><span class="card-icon">⏳</span><span class="card-title">生命周期</span></div>
            <div class="card-field">
              <div class="field-value">{{ foreshadowingStatusLabel(settingDetail.status) }}</div>
              <div class="field-label">计划回收章节：{{ settingDetail.payoff_chapter ? `第 ${settingDetail.payoff_chapter} 章` : '尚未安排' }}</div>
            </div>
          </div>
          <div class="card-footer-badge">
            <span class="memory-level-badge l3">📁 L3 项目记忆</span>
          </div>
        </template>

        <template v-else-if="settingDetail">
          <!-- 完整度 -->
          <div class="completeness">
            <div class="completeness-header">
              <span class="completeness-label">设定完整度</span>
              <span class="completeness-value">{{ settingDetail.completeness || 0 }}%</span>
            </div>
            <div class="completeness-bar">
              <div
                class="completeness-fill"
                :style="{ width: (settingDetail.completeness || 0) + '%' }"
              ></div>
            </div>
          </div>

          <!-- 外貌设定 -->
          <div class="setting-card" :class="{ 'just-updated': lastUpdatedField === 'appearance' }">
            <div class="card-header">
              <span class="card-icon">👤</span>
              <span class="card-title">外貌特征</span>
              <span v-if="lastUpdatedField === 'appearance'" class="card-badge">刚更新</span>
            </div>
            <div class="card-field">
              <div class="field-label">整体气质</div>
              <div class="field-value" :class="{ partial: !settingDetail.appearance }">
                {{ settingDetail.appearance ? extractAppearanceSummary(settingDetail.appearance).temperament : '待补充...' }}
              </div>
            </div>
            <div v-if="settingDetail.appearance" class="card-field">
              <div class="field-label">
                标志性特征
                <span v-if="lastUpdatedField === 'appearance'" class="new-tag">NEW</span>
              </div>
              <div class="field-value">{{ extractAppearanceSummary(settingDetail.appearance).features }}</div>
            </div>
            <div v-if="settingDetail.appearance" class="card-field">
              <div class="field-label">
                穿着习惯
                <span v-if="lastUpdatedField === 'appearance'" class="new-tag">NEW</span>
              </div>
              <div class="field-value">{{ extractAppearanceSummary(settingDetail.appearance).outfit }}</div>
            </div>
            <div v-if="settingDetail.appearance" class="card-field">
              <div class="field-label">情感信物</div>
              <div class="field-value">
                {{ extractAppearanceSummary(settingDetail.appearance).keepsake }}
                <div v-if="extractAppearanceSummary(settingDetail.appearance).keepsake !== '待补充...'" class="field-tags">
                  <span class="field-tag">情感锚点</span>
                  <span class="field-tag">伏笔潜力</span>
                </div>
              </div>
            </div>
            <div class="card-footer-badge">
              <span class="memory-level-badge l3">📁 L3 项目记忆</span>
            </div>
          </div>

          <!-- 性格设定 -->
          <div class="setting-card" :class="{ 'just-updated': lastUpdatedField === 'personality' }">
            <div class="card-header">
              <span class="card-icon">💫</span>
              <span class="card-title">性格特质</span>
              <span v-if="lastUpdatedField === 'personality'" class="card-badge">刚更新</span>
            </div>
            <div class="card-field">
              <div class="field-label">核心性格</div>
              <div v-if="settingDetail.personality" class="field-tags">
                <span v-for="(tag, i) in extractPersonalityTags(settingDetail.personality)" :key="i" class="field-tag">{{ tag }}</span>
              </div>
              <div v-else class="field-value partial">待补充...</div>
            </div>
            <div class="card-field">
              <div class="field-label">行为模式</div>
              <div class="field-value partial">待补充...</div>
            </div>
          </div>

          <!-- 背景设定 -->
          <div class="setting-card" :class="{ 'just-updated': lastUpdatedField === 'background' || lastUpdatedField === 'identity' || lastUpdatedField === 'motivation' }">
            <div class="card-header">
              <span class="card-icon">📖</span>
              <span class="card-title">背景故事</span>
              <span v-if="lastUpdatedField === 'background' || lastUpdatedField === 'identity' || lastUpdatedField === 'motivation'" class="card-badge">刚更新</span>
            </div>
            <div class="card-field">
              <div class="field-label">出身</div>
              <div class="field-value" :class="{ partial: !settingDetail.identity }">
                {{ settingDetail.identity || '待补充...' }}
              </div>
            </div>
            <div class="card-field">
              <div class="field-label">背景</div>
              <div class="field-value" :class="{ partial: !settingDetail.background }">
                {{ settingDetail.background || '待补充...' }}
              </div>
            </div>
            <div class="card-field">
              <div class="field-label">核心动机</div>
              <div class="field-value partial" :class="{ partial: !settingDetail.motivation }">
                {{ settingDetail.motivation || '待探索...' }}
              </div>
            </div>
          </div>
        </template>

        <div v-else class="right-empty">
          <div class="right-empty-icon">📋</div>
          <div>选择左侧人物、世界观或伏笔查看设定</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { useProjectStore } from '@/stores/project'
import {
  getSettingIndex,
  createSession,
  getSession,
  listSessions,
  sendMessage,
  getSettingDetail,
  type SettingChatSession,
  type SettingChatMessage,
  type SettingIndexResponse,
} from '@/api/settingCo'
import { notify } from '@/utils/notify'

const projectStore = useProjectStore()
const projectId = computed(() => projectStore.currentProject?.id ?? null)

// 状态
const settingIndex = ref<SettingIndexResponse | null>(null)
const recentSessions = ref<SettingChatSession[]>([])
const currentSession = ref<SettingChatSession | null>(null)
const messages = ref<SettingChatMessage[]>([])
const quickReplies = ref<string[]>([])
const inputMessage = ref('')
const isSending = ref(false)
const showPromptTemplates = ref(false)
const activeTargetType = ref('character')
const activeTargetId = ref<number | null>(null)
const settingDetail = ref<Record<string, any> | null>(null)
const lastUpdatedField = ref<string | null>(null)
const sessionHasMemory = computed(() => messages.value.some(
  (message) => message.role === 'assistant' && message.memory_written === 1
))
let sessionRequestSequence = 0
let workspaceRequestSequence = 0

const promptTemplates = computed(() => {
  const templates: Record<string, string[]> = {
    character: [
      '我们先完善外貌特征：这个角色给人的第一印象是什么？有什么容易被记住的细节？',
      '聊聊性格和行为：他遇到压力、利益冲突或亲近的人时通常会怎么做？',
      '梳理角色背景：他的出身经历如何影响现在的目标？',
      '补充角色关系：他最信任、最忌惮或最想保护的人是谁？为什么？',
    ],
    world: [
      '先聊时代背景：故事发生在什么时代，普通人的日常生活是什么样？',
      '完善核心力量体系：力量从哪里来，使用它要付出什么代价？',
      '设定世界规则：哪些事情绝对不可能发生？规则被打破会带来什么后果？',
      '描述整体基调：读者进入这个世界时，你希望感受到什么？',
    ],
    foreshadowing: [
      '这条线索最初会以什么细节出现？读者第一次看到时应该注意到什么？',
      '线索背后隐藏的真相是什么？哪些信息要暂时保留？',
      '这条线索计划在什么阶段回收？回收时会改变什么？',
      '哪些角色知道这件事，哪些角色会误解它？',
    ],
  }
  return templates[currentSession.value?.target_type || 'character'] || templates.character
})

const expandedGroups = ref({
  characters: true,
  world: false,
  foreshadowing: false,
  sessions: false,
})

const messagesRef = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const worldDetailFields = [
  { key: 'name', label: '世界名称', icon: '🌍' },
  { key: 'era', label: '时代背景', icon: '📜' },
  { key: 'power_system', label: '核心力量体系', icon: '⚡' },
  { key: 'atmosphere', label: '整体基调', icon: '🎭' },
  { key: 'synopsis', label: '世界观简介', icon: '🗺️' },
  { key: 'core_rules', label: '核心规则', icon: '📏' },
]
const foreshadowingDetailFields = [
  { key: 'keyword', label: '线索关键词', icon: '🔎' },
  { key: 'description', label: '线索内容', icon: '🧩' },
  { key: 'notes', label: '作者备注', icon: '🗒️' },
]

function foreshadowingStatusLabel(status: string) {
  const labels: Record<string, string> = {
    pending: '待埋设', planted: '已埋设', developing: '发展中',
    payoff_pending: '待回收', resolved: '已回收', abandoned: '已废弃',
  }
  return labels[status] || status || '未设置'
}

function settingTargetLabel(targetType: string) {
  const labels: Record<string, string> = { character: '人物', world: '世界', foreshadowing: '伏笔' }
  return labels[targetType] || '设定'
}

// 加载设定目录
async function loadSettingIndex() {
  // 步骤 1：确认当前项目已就绪；步骤 2：仅应用当前项目对应的目录响应。
  const requestedProjectId = projectId.value
  if (!requestedProjectId) {
    settingIndex.value = null
    return
  }
  try {
    const data = await getSettingIndex(requestedProjectId)
    if (projectId.value === requestedProjectId) settingIndex.value = data
  } catch (e) {
    console.error('加载设定目录失败', e)
  }
}

// 加载最近会话，方便离开页面后继续之前的设定讨论。
async function loadRecentSessions() {
  // 步骤 1：以当前项目为范围加载会话；步骤 2：丢弃项目切换后的过期响应。
  const requestedProjectId = projectId.value
  if (!requestedProjectId) {
    recentSessions.value = []
    return
  }
  try {
    const result = await listSessions(requestedProjectId)
    if (projectId.value === requestedProjectId) recentSessions.value = result.sessions
  } catch (e) {
    console.error('加载最近设定对话失败', e)
  }
}

function openSettingGroup(group: 'characters' | 'foreshadowing') {
  // 步骤 1：展开对应设定目录；步骤 2：提示作者从具体档案开始对话。
  expandedGroups.value[group] = true
  notify.info(group === 'characters' ? '已展开左侧人物列表，请选择要完善的人物' : '已展开左侧伏笔列表，请选择要完善的线索')
}

function startWorldSetting() {
  // 步骤 1：读取项目世界观总览；步骤 2：不存在总览时让后端在当前项目内创建。
  const world = settingIndex.value?.world
  void startChat('world', world?.target_id || 0, world?.name || '世界观总览')
}

// 开始对话
async function startChat(targetType: string, targetId: number, targetName: string) {
  // 步骤 1：校验项目并标记本次切换；步骤 2：创建会话；步骤 3：载入档案与历史列表。
  const requestedProjectId = projectId.value
  if (!requestedProjectId) {
    notify.warning('项目仍在加载，请稍后再开始设定共创')
    return
  }
  const requestSequence = ++sessionRequestSequence
  activeTargetType.value = targetType
  activeTargetId.value = targetId

  try {
    const result = await createSession({
      project_id: requestedProjectId,
      target_type: targetType,
      target_id: targetId,
      target_name: targetName,
    })
    if (requestSequence !== sessionRequestSequence || projectId.value !== requestedProjectId) return

    currentSession.value = result.session
    activeTargetId.value = result.session.target_id
    messages.value = [
      {
        id: 0,
        session_id: result.session.session_id,
        role: 'assistant',
        content: result.opening.message,
        thought: '',
        extracted_fields: '[]',
        memory_written: 0,
        created_at: new Date().toISOString(),
      },
    ]
    quickReplies.value = result.opening.quick_replies || []

    // 步骤 1：新会话立即出现在历史列表；步骤 2：继续加载关联档案。
    await Promise.all([loadRecentSessions(), loadSettingDetail()])

    // 滚动到底部
    await nextTick(scrollToBottom)
  } catch (e) {
    console.error('创建会话失败', e)
    if (requestSequence === sessionRequestSequence) {
      activeTargetType.value = currentSession.value?.target_type || 'character'
      activeTargetId.value = currentSession.value?.target_id || null
    }
  }
}

// 恢复历史会话与它绑定的人物、世界观或伏笔档案。
async function resumeSession(session: SettingChatSession) {
  // 步骤 1：确认会话属于当前项目；步骤 2：读取消息；步骤 3：忽略过期的切换响应。
  const requestedProjectId = projectId.value
  if (!requestedProjectId || session.project_id !== requestedProjectId) {
    notify.warning('这条对话不属于当前项目，请刷新设定目录')
    return
  }
  const requestSequence = ++sessionRequestSequence
  try {
    const result = await getSession(session.session_id)
    if (requestSequence !== sessionRequestSequence || projectId.value !== requestedProjectId) return
    if (result.session.project_id !== requestedProjectId) {
      notify.warning('会话所属项目已变化，请重新选择')
      return
    }
    currentSession.value = result.session
    messages.value = result.messages
    activeTargetType.value = result.session.target_type
    activeTargetId.value = result.session.target_id
    quickReplies.value = []
    showPromptTemplates.value = false
    await loadSettingDetail()
    await nextTick(scrollToBottom)
  } catch (e) {
    console.error('恢复设定对话失败', e)
  }
}

// 加载设定详情
async function loadSettingDetail() {
  // 步骤 1：固定当前会话和项目；步骤 2：读取其档案；步骤 3：避免旧响应覆盖新目标。
  const session = currentSession.value
  const requestedProjectId = projectId.value
  if (!session?.target_id || !requestedProjectId) {
    settingDetail.value = null
    return
  }
  try {
    const result = await getSettingDetail(
      session.target_type,
      session.target_id,
      requestedProjectId
    )
    if (currentSession.value?.session_id === session.session_id && projectId.value === requestedProjectId) {
      settingDetail.value = result.detail
    }
  } catch (e) {
    console.error('加载设定详情失败', e)
  }
}

// 发送消息
async function handleSend() {
  const msg = inputMessage.value.trim()
  if (!msg || !currentSession.value || isSending.value) return
  const sendingSession = currentSession.value
  const sendingProjectId = projectId.value
  if (!sendingProjectId) return

  // 添加用户消息
  messages.value.push({
    id: Date.now(),
    session_id: sendingSession.session_id,
    role: 'user',
    content: msg,
    thought: '',
    extracted_fields: '[]',
    memory_written: 0,
    created_at: new Date().toISOString(),
  })

  inputMessage.value = ''
  isSending.value = true
  quickReplies.value = []
  nextTick(() => {
    scrollToBottom()
    autoResize()
  })

  try {
    const result = await sendMessage(sendingSession.session_id, msg)
    await loadRecentSessions()
    if (currentSession.value?.session_id !== sendingSession.session_id || projectId.value !== sendingProjectId) return

    // 添加 Agent 回复
    messages.value.push({
      id: Date.now() + 1,
      session_id: sendingSession.session_id,
      role: 'assistant',
      content: result.reply.content,
      thought: result.reply.thought || '',
      extracted_fields: JSON.stringify(result.reply.extracted_fields || []),
      memory_written: result.reply.memory_written ? 1 : 0,
      created_at: result.reply.created_at || new Date().toISOString(),
    })

    quickReplies.value = result.quick_replies || []
    currentSession.value = result.session

    // 更新设定详情
    if (result.setting_detail && Object.keys(result.setting_detail).length > 0) {
      // 找出更新的字段，高亮显示
      const extracted = result.reply.extracted_fields || []
      if (extracted.length > 0 && extracted[0]?.key) {
        lastUpdatedField.value = extracted[0].key
        setTimeout(() => {
          lastUpdatedField.value = null
        }, 2000)
      }
      settingDetail.value = result.setting_detail
    }

    // 刷新目录（完整度可能变了）
    await loadSettingIndex()
  } catch (e) {
    console.error('发送消息失败', e)
    if (currentSession.value?.session_id === sendingSession.session_id && projectId.value === sendingProjectId) {
      messages.value.push({
        id: Date.now() + 1,
        session_id: sendingSession.session_id,
        role: 'assistant',
        content: '本轮没有收到服务端回复。你刚才的内容已保留在当前界面，请检查连接后重试。',
        thought: '',
        extracted_fields: '[]',
        memory_written: 0,
        created_at: new Date().toISOString(),
      })
    }
  } finally {
    isSending.value = false
    nextTick(scrollToBottom)
  }
}

// 快速回复
function sendQuickReply(text: string) {
  inputMessage.value = text
  handleSend()
}

function insertPromptTemplate(text: string) {
  // 步骤 1：把提问模板放入输入框而不是直接发送；步骤 2：聚焦输入框供作者继续改写。
  inputMessage.value = text
  showPromptTemplates.value = false
  void nextTick(() => {
    autoResize()
    textareaRef.value?.focus()
  })
}

function exportConversation() {
  // 步骤 1：把消息转换为纯文本 Markdown；步骤 2：生成本地下载，不上传对话内容。
  const session = currentSession.value
  if (!session || !messages.value.length) return
  const lines = [
    `# ${session.target_name}｜设定共创`,
    '',
    `目标类型：${settingTargetLabel(session.target_type)}`,
    `导出时间：${new Date().toLocaleString('zh-CN')}`,
    '',
  ]
  messages.value.forEach((message) => {
    const role = message.role === 'user' ? '作者' : '设定共创 Agent'
    const content = message.role === 'user' ? message.content : htmlToPlainText(message.content)
    lines.push(`## ${role} · ${formatTime(message.created_at)}`, content, '')
  })
  const blob = new Blob([`\uFEFF${lines.join('\n')}`], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  const safeName = session.target_name.replace(/[\\/:*?"<>|]/g, '_') || '设定对话'
  link.href = url
  link.download = `${safeName}-设定共创.md`
  link.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function htmlToPlainText(value: string) {
  // 步骤 1：使用 HTML 解析器移除消息标签；步骤 2：整理空行并保留可读文本。
  if (typeof DOMParser === 'undefined') return value.replace(/<[^>]*>/g, '')
  const parsed = new DOMParser().parseFromString(value, 'text/html')
  parsed.body.querySelectorAll('br').forEach((node) => node.replaceWith(document.createTextNode('\n')))
  parsed.body.querySelectorAll('li').forEach((node) => node.insertBefore(document.createTextNode('• '), node.firstChild))
  parsed.body.querySelectorAll('div, p, li').forEach((node) => node.appendChild(document.createTextNode('\n')))
  return (parsed.body.textContent || '').replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim()
}

function sanitizeMessageHtml(value: string) {
  // 步骤 1：只保留对话排版需要的标签与样式类；步骤 2：剥除脚本、事件属性和链接。
  if (typeof DOMParser === 'undefined') {
    return htmlToPlainText(value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  }
  const parsed = new DOMParser().parseFromString(value, 'text/html')
  const safeTags = new Set(['DIV', 'P', 'UL', 'LI', 'STRONG', 'BR', 'SPAN'])
  const safeClasses = new Set(['thought-tag', 'question-highlight', 'question-list', 'memory-note', 'icon'])
  const removedTags = new Set(['SCRIPT', 'STYLE', 'IFRAME', 'OBJECT', 'SVG', 'MATH'])
  const output = document.createElement('div')

  const appendSafeNode = (parent: HTMLElement, node: Node) => {
    if (node.nodeType === Node.TEXT_NODE) {
      parent.appendChild(document.createTextNode(node.textContent || ''))
      return
    }
    if (!(node instanceof HTMLElement)) return
    if (removedTags.has(node.tagName)) return
    if (!safeTags.has(node.tagName)) {
      Array.from(node.childNodes).forEach((child) => appendSafeNode(parent, child))
      return
    }
    const clean = document.createElement(node.tagName.toLowerCase())
    const allowedClasses = (node.getAttribute('class') || '').split(/\s+/).filter((name) => safeClasses.has(name))
    if (allowedClasses.length) clean.className = allowedClasses.join(' ')
    Array.from(node.childNodes).forEach((child) => appendSafeNode(clean, child))
    parent.appendChild(clean)
  }

  Array.from(parsed.body.childNodes).forEach((node) => appendSafeNode(output, node))
  return output.innerHTML
}

// 新建对话
function handleNewChat() {
  // 步骤 1：使未完成的会话切换响应失效；步骤 2：清理输入、消息和实时设定状态。
  sessionRequestSequence += 1
  currentSession.value = null
  messages.value = []
  quickReplies.value = []
  settingDetail.value = null
  activeTargetId.value = null
  activeTargetType.value = 'character'
  inputMessage.value = ''
  showPromptTemplates.value = false
}

// 滚动到底部
function scrollToBottom() {
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

// 输入框自适应高度
function autoResize() {
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
    textareaRef.value.style.height = Math.min(textareaRef.value.scrollHeight, 120) + 'px'
  }
}

// 时间格式化
function formatTime(dateStr: string) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

// 从外貌描述中提取摘要信息
function extractAppearanceSummary(text: string) {
  const lines = text.split(/[，。；\n]/).filter(Boolean)
  let temperament = '待补充...'
  let features = '待补充...'
  let outfit = '待补充...'
  let keepsake = '待补充...'

  for (const line of lines) {
    if (line.includes('气质') || line.includes('耐看') || line.includes('普通') || line.includes('眼神')) {
      temperament = line.trim()
    }
    if (line.includes('疤') || line.includes('标志') || line.includes('特征') || line.includes('眉')) {
      features = line.trim()
    }
    if (line.includes('衣') || line.includes('服') || line.includes('穿') || line.includes('布')) {
      outfit = line.trim()
    }
    if (line.includes('玉佩') || line.includes('信物') || line.includes('遗物') || line.includes('师父')) {
      keepsake = line.trim()
    }
  }

  // 简单 fallback
  if (temperament === '待补充...' && lines.length > 0) {
    temperament = lines[0].trim().slice(0, 30)
  }

  return { temperament, features, outfit, keepsake }
}

// 从性格描述中提取标签
function extractPersonalityTags(text: string): string[] {
  if (!text) return []
  const keywords = ['沉稳', '内敛', '重情义', '坚韧', '冷静', '热情', '开朗', '孤傲', '温柔', '腹黑', '耿直', '机敏', '果断', '谨慎']
  const tags: string[] = []
  for (const kw of keywords) {
    if (text.includes(kw)) {
      tags.push(kw)
    }
  }
  if (tags.length === 0 && text) {
    // 实在没匹配到，按标点切分取前3个片段
    const parts = text.split(/[，。；、\n]/).filter(s => s.trim().length <= 6).slice(0, 3)
    return parts.length > 0 ? parts.map(p => p.trim()) : [text.slice(0, 6)]
  }
  return tags.slice(0, 6)
}

async function loadWorkspace(restoreLatestSession: boolean) {
  // 步骤 1：固定当前项目并并行加载目录、历史；步骤 2：可选恢复最近一条会话。
  const requestedProjectId = projectId.value
  if (!requestedProjectId) return
  const requestSequence = ++workspaceRequestSequence
  await Promise.all([loadSettingIndex(), loadRecentSessions()])
  if (requestSequence !== workspaceRequestSequence || projectId.value !== requestedProjectId) return
  if (restoreLatestSession && !currentSession.value && recentSessions.value.length) {
    await resumeSession(recentSessions.value[0])
  }
}

onMounted(async () => {
  // 步骤 1：确保项目状态已恢复；步骤 2：加载共创目录并恢复最近会话。
  if (!projectStore.currentProject) await projectStore.loadDefaultProject()
  if (!projectStore.currentProject) {
    notify.warning('请先创建或选择一个小说项目')
    return
  }
  await loadWorkspace(true)
})

watch(projectId, (newProjectId, oldProjectId) => {
  if (newProjectId === oldProjectId) return
  // 步骤 1：切换项目后清空上一项目会话状态；步骤 2：重新加载新项目目录和历史。
  sessionRequestSequence += 1
  workspaceRequestSequence += 1
  currentSession.value = null
  messages.value = []
  quickReplies.value = []
  settingDetail.value = null
  activeTargetId.value = null
  activeTargetType.value = 'character'
  recentSessions.value = []
  settingIndex.value = null
  inputMessage.value = ''
  showPromptTemplates.value = false
  if (newProjectId) void loadWorkspace(true)
})
</script>

<style scoped>
.setting-co-page {
  display: flex;
  height: calc(100vh - 40px);
  background: var(--bg-0);
  color: var(--text-primary);
  overflow: hidden;
}

/* ===== 左侧面板 ===== */
.left-panel {
  width: 260px;
  background: rgba(15, 22, 41, 0.6);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.panel-header {
  padding: 14px 14px 12px;
  border-bottom: 1px solid var(--border);
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.ver-badge {
  font-size: 9px;
  padding: 2px 6px;
  background: rgba(139, 92, 246, 0.2);
  color: #c4b5fd;
  border-radius: 8px;
  font-weight: 500;
  border: 1px solid rgba(139, 92, 246, 0.3);
  margin-left: auto;
}

.panel-subtitle {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
}

.setting-groups {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.setting-group {
  margin-bottom: 6px;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.15s ease;
}

.group-header:hover {
  background: rgba(255, 255, 255, 0.04);
}

.group-arrow {
  font-size: 10px;
  color: var(--text-muted);
  transition: transform 0.2s ease;
  width: 12px;
  text-align: center;
}

.group-arrow.expanded {
  transform: rotate(90deg);
}

.group-icon { font-size: 13px; }

.group-progress {
  margin-left: auto;
  font-size: 10px;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
}

.group-items {
  padding-left: 24px;
}

.group-empty {
  padding: 7px 8px;
  color: var(--text-muted);
  font-size: 10px;
  line-height: 1.5;
}

.setting-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  margin-bottom: 2px;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.15s ease;
  font-size: 11px;
}

.setting-item:hover {
  background: rgba(255, 255, 255, 0.04);
}

.setting-item.active {
  background: rgba(99, 102, 241, 0.12);
  color: #c7d2fe;
}

.setting-item.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.item-status {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.item-status.complete { background: #10b981; box-shadow: 0 0 4px #10b981; }
.item-status.partial { background: #f59e0b; box-shadow: 0 0 4px #f59e0b; }
.item-status.empty { background: #475569; }

.item-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-completeness {
  font-size: 9px;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
}

.session-type {
  flex-shrink: 0;
  color: var(--text-muted);
  font-size: 9px;
}

.new-chat-btn {
  margin: 12px;
  padding: 10px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(139, 92, 246, 0.2));
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 8px;
  color: #c7d2fe;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-family: inherit;
}

.new-chat-btn:hover {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.3), rgba(139, 92, 246, 0.3));
  border-color: rgba(99, 102, 241, 0.5);
}

.sidebar-footer {
  padding: 10px;
  border-top: 1px solid var(--border);
  background: rgba(15, 22, 41, 0.5);
}

.footer-memory-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.15);
  border-radius: 6px;
}

.footer-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.footer-text {
  flex: 1;
  min-width: 0;
}

.footer-title {
  font-size: 10px;
  font-weight: 600;
  color: #6ee7b7;
  margin-bottom: 2px;
}

.footer-desc {
  font-size: 9px;
  color: var(--text-muted);
  line-height: 1.4;
}

/* ===== 中间对话区 ===== */
.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: rgba(10, 14, 26, 0.4);
}

.chat-header {
  padding: 12px 20px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
  background: rgba(15, 22, 41, 0.6);
  backdrop-filter: blur(8px);
}

.agent-avatar {
  position: relative;
  width: 38px;
  height: 38px;
  flex-shrink: 0;
}

.avatar-ring {
  position: absolute;
  inset: -3px;
  border: 2px solid rgba(139, 92, 246, 0.4);
  border-radius: 11px;
  border-top-color: transparent;
  border-left-color: transparent;
  animation: ring-spin 4s linear infinite;
}

@keyframes ring-spin {
  to { transform: rotate(360deg); }
}

.avatar-inner {
  width: 38px;
  height: 38px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.chat-agent-info { flex: 1; min-width: 0; }

.chat-agent-name {
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  width: 7px;
  height: 7px;
  background: #10b981;
  border-radius: 50%;
  box-shadow: 0 0 6px #10b981;
  animation: status-pulse 2s ease-in-out infinite;
}

.status-dot.thinking {
  background: #f59e0b;
  box-shadow: 0 0 6px #f59e0b;
}

@keyframes status-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.chat-agent-desc {
  font-size: 10px;
  color: var(--text-muted);
  margin-top: 2px;
}

.chat-header-actions {
  display: flex;
  gap: 6px;
}

.header-btn {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border);
  border-radius: 7px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
  color: var(--text-secondary);
}

.header-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: var(--border-strong);
}

.header-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 消息区 */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px 28px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.message {
  display: flex;
  gap: 10px;
  max-width: 85%;
  animation: msg-in 0.3s ease-out;
}

@keyframes msg-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.msg-avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  flex-shrink: 0;
}

.message.agent .msg-avatar {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
}

.message.user .msg-avatar {
  background: linear-gradient(135deg, #f59e0b, #ef4444);
}

.msg-body { flex: 1; min-width: 0; }

.msg-name {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.message.user .msg-name {
  justify-content: flex-end;
}

.msg-name .time {
  font-size: 9px;
  font-weight: normal;
  color: var(--text-muted);
}

.msg-bubble {
  padding: 12px 14px;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-primary);
  position: relative;
  overflow-wrap: anywhere;
}

.message.agent .msg-bubble {
  background: rgba(30, 42, 69, 0.8);
  border: 1px solid var(--border);
  border-top-left-radius: 4px;
}

.message.user .msg-bubble {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.3), rgba(139, 92, 246, 0.3));
  border: 1px solid rgba(99, 102, 241, 0.4);
  border-top-right-radius: 4px;
  white-space: pre-wrap;
}

/* Agent 消息内的富文本样式 */
.msg-bubble :deep(.thought-tag) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  padding: 2px 8px;
  background: rgba(139, 92, 246, 0.2);
  color: #c4b5fd;
  border-radius: 10px;
  margin-bottom: 8px;
  border: 1px solid rgba(139, 92, 246, 0.3);
}

.msg-bubble :deep(.question-highlight) {
  background: rgba(245, 158, 11, 0.12);
  border-left: 3px solid #f59e0b;
  padding: 10px 12px;
  margin-top: 10px;
  border-radius: 0 6px 6px 0;
  font-weight: 500;
}

.msg-bubble :deep(.question-list) {
  margin-top: 10px;
  padding-left: 0;
  list-style: none;
}

.msg-bubble :deep(.question-list li) {
  padding: 6px 0 6px 20px;
  position: relative;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.6;
}

.msg-bubble :deep(.question-list li::before) {
  content: '？';
  position: absolute;
  left: 0;
  top: 6px;
  width: 14px;
  height: 14px;
  background: rgba(245, 158, 11, 0.2);
  color: #fbbf24;
  font-size: 9px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

.msg-bubble :deep(.memory-note) {
  margin-top: 12px;
  padding: 8px 12px;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.25);
  border-radius: 7px;
  font-size: 11px;
  color: #6ee7b7;
  display: flex;
  align-items: center;
  gap: 6px;
}

.msg-bubble :deep(.memory-note .icon) {
  font-size: 13px;
}

/* 消息内的快速回复 */
.quick-replies {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
  padding: 0 4px;
}

.quick-reply {
  padding: 5px 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  font-size: 11px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.quick-reply:hover {
  background: rgba(99, 102, 241, 0.15);
  border-color: rgba(99, 102, 241, 0.4);
  color: #c7d2fe;
}

.thinking-bubble {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: 12px;
}

.thinking-icon {
  font-size: 14px;
  animation: bounce 1s ease-in-out infinite;
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-3px); }
}

/* 空状态 */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  gap: 10px;
}

.empty-icon {
  font-size: 48px;
  opacity: 0.3;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-secondary);
}

.empty-desc {
  font-size: 12px;
  text-align: center;
  line-height: 1.6;
  opacity: 0.7;
  max-width: 520px;
}

.empty-start-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  width: min(680px, 100%);
  margin-top: 8px;
}

.empty-start-card {
  min-height: 76px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  text-align: left;
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid var(--border);
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
}

.empty-start-card:hover {
  background: rgba(99, 102, 241, 0.1);
  border-color: rgba(99, 102, 241, 0.45);
  transform: translateY(-1px);
}

.empty-start-card:focus-visible,
.prompt-template:focus-visible {
  outline: 2px solid var(--border-strong);
  outline-offset: 2px;
}

.empty-start-icon {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  background: rgba(99, 102, 241, 0.12);
  border-radius: 9px;
  font-size: 17px;
}

.empty-start-card strong,
.empty-start-card small {
  display: block;
}

.empty-start-card strong {
  font-size: 12px;
  font-weight: 600;
}

.empty-start-card small {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 10px;
  line-height: 1.4;
}

.empty-start-arrow {
  margin-left: auto;
  color: var(--text-muted);
  font-size: 20px;
}

.empty-start-note {
  max-width: 560px;
  color: var(--text-muted);
  font-size: 10px;
  text-align: center;
}

/* 输入区 */
.chat-input-area {
  padding: 12px 20px 14px;
  border-top: 1px solid var(--border);
  background: rgba(15, 22, 41, 0.6);
  backdrop-filter: blur(8px);
  flex-shrink: 0;
}

.prompt-template-panel {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin: 0 0 9px;
  padding: 9px 10px;
  background: rgba(99, 102, 241, 0.07);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 8px;
}

.prompt-template-heading {
  width: 100%;
  color: var(--text-muted);
  font-size: 10px;
}

.prompt-template {
  padding: 6px 9px;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid var(--border);
  border-radius: 14px;
  font-size: 10px;
  line-height: 1.45;
  text-align: left;
  cursor: pointer;
}

.prompt-template:hover {
  color: var(--text-primary);
  border-color: var(--border-strong);
  background: rgba(99, 102, 241, 0.12);
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border);
  border-radius: 9px;
  padding: 8px 10px;
  transition: all 0.2s ease;
}

.input-wrapper:focus-within {
  border-color: var(--border-strong);
  background: rgba(99, 102, 241, 0.04);
}

.input-textarea {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: var(--text-primary);
  font-size: 13px;
  line-height: 1.6;
  resize: none;
  max-height: 120px;
  min-height: 22px;
  font-family: inherit;
}

.input-textarea::placeholder { color: var(--text-muted); }
.input-textarea:disabled { opacity: 0.5; cursor: not-allowed; }

.input-tools {
  display: flex;
  gap: 4px;
  align-items: center;
}

.tool-btn {
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 13px;
  cursor: pointer;
  border-radius: 5px;
  transition: all 0.15s ease;
}

.tool-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-secondary);
}

.tool-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.send-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border: none;
  border-radius: 7px;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
}

.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.input-hint {
  font-size: 10px;
  color: var(--text-muted);
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.input-hint kbd {
  padding: 1px 4px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 3px;
  font-size: 9px;
  font-family: 'JetBrains Mono', monospace;
}

@media (max-width: 900px) {
  .empty-start-actions {
    grid-template-columns: 1fr;
    max-width: 420px;
  }
}

/* ===== 右侧面板 ===== */
.right-panel {
  width: 300px;
  background: rgba(15, 22, 41, 0.6);
  border-left: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.right-header {
  padding: 14px;
  border-bottom: 1px solid var(--border);
}

.right-title {
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.live-dot {
  width: 6px;
  height: 6px;
  background: #10b981;
  border-radius: 50%;
  animation: live-pulse 2s ease-in-out infinite;
  box-shadow: 0 0 6px #10b981;
}

@keyframes live-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.right-subtitle {
  font-size: 10px;
  color: var(--text-muted);
  margin-top: 3px;
}

.right-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.right-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
  font-size: 12px;
  gap: 10px;
}

.right-empty-icon {
  font-size: 36px;
  opacity: 0.3;
}

/* 完整度 */
.completeness {
  margin-bottom: 12px;
}

.completeness-header {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  margin-bottom: 5px;
}

.completeness-label { color: var(--text-secondary); }
.completeness-value {
  color: #a5b4fc;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
}

.completeness-bar {
  height: 6px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 3px;
  overflow: hidden;
}

.completeness-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #8b5cf6, #a855f7);
  border-radius: 3px;
  transition: width 0.5s ease;
  position: relative;
  overflow: hidden;
}

.completeness-fill::after {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.15),
    transparent
  );
  animation: shimmer 2.5s infinite;
}

@keyframes shimmer {
  100% { left: 100%; }
}

/* 设定卡片 */
.setting-card {
  background: rgba(30, 42, 69, 0.5);
  border: 1px solid var(--border);
  border-radius: 9px;
  padding: 12px;
  margin-bottom: 10px;
  transition: all 0.3s ease;
}

.setting-card.just-updated {
  animation: card-flash 1.5s ease-out;
  border-color: rgba(16, 185, 129, 0.5);
  box-shadow: 0 0 16px rgba(16, 185, 129, 0.15);
}

@keyframes card-flash {
  0% { background: rgba(16, 185, 129, 0.2); }
  100% { background: rgba(30, 42, 69, 0.5); }
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.card-icon { font-size: 14px; }

.card-title {
  font-size: 12px;
  font-weight: 600;
  flex: 1;
}

.card-badge {
  font-size: 9px;
  padding: 1px 6px;
  background: rgba(239, 68, 68, 0.2);
  color: #fca5a5;
  border-radius: 4px;
  font-weight: 500;
  animation: badge-pulse 2s ease-in-out infinite;
}

@keyframes badge-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.new-tag {
  display: inline-block;
  font-size: 8px;
  padding: 0 4px;
  background: linear-gradient(135deg, #f97316, #ef4444);
  color: #fff;
  border-radius: 3px;
  font-weight: 700;
  margin-left: 4px;
  vertical-align: middle;
  line-height: 14px;
}

.card-field {
  margin-bottom: 8px;
}

.card-field:last-child { margin-bottom: 0; }

.field-label {
  font-size: 10px;
  color: var(--text-muted);
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.field-value {
  font-size: 11px;
  color: var(--text-primary);
  line-height: 1.6;
}

.field-value.partial {
  color: var(--text-muted);
  font-style: italic;
}

.field-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}

.field-tag {
  font-size: 9px;
  padding: 2px 6px;
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
  border-radius: 3px;
  border: 1px solid rgba(99, 102, 241, 0.25);
}

.card-footer-badge {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  justify-content: flex-end;
}

/* 记忆层级徽章 */
.memory-level-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 9px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.memory-level-badge.l3 {
  background: rgba(16, 185, 129, 0.15);
  color: #6ee7b7;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.memory-hint {
  font-size: 9px;
  color: var(--text-muted);
}

/* 展开动画 */
.expand-enter-active,
.expand-leave-active {
  overflow: hidden;
  transition: max-height 0.2s ease, opacity 0.2s ease;
}

.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  opacity: 0;
}

.expand-enter-to,
.expand-leave-from {
  max-height: 500px;
  opacity: 1;
}

/* 滚动条 */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.2); }
</style>
