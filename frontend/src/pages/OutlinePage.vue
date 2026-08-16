<template>
  <div class="page outline-page">
    <!-- 大纲总览横幅 -->
    <div class="outline-hero">
      <div class="hero-left">
        <div class="hero-badge">
          <span class="badge-icon">📋</span>
          <span class="badge-text">{{ project?.name || '加载中' }} · 大纲</span>
        </div>
        <h1 class="hero-title">大纲规划</h1>
        <p class="hero-desc">
          搭建卷章结构，规划每章剧情走向，让创作有条不紊
        </p>
      </div>
      <div class="hero-right">
        <div class="hero-stat">
          <div class="hero-stat-value">{{ volumeCount }}</div>
          <div class="hero-stat-label">分卷</div>
        </div>
        <div class="hero-stat">
          <div class="hero-stat-value">{{ chapterCount }}</div>
          <div class="hero-stat-label">章节</div>
        </div>
        <div class="hero-stat">
          <div class="hero-stat-value">{{ estimatedWords }}</div>
          <div class="hero-stat-label">预估字数</div>
        </div>
        <div class="hero-stat">
          <div class="hero-stat-value success">{{ completionRate }}%</div>
          <div class="hero-stat-label">完成度</div>
        </div>
      </div>
    </div>

    <!-- 大纲总览简易编辑 -->
    <div class="overview-card" :class="{ expanded: overviewExpanded }">
      <div class="overview-head" @click="overviewExpanded = !overviewExpanded">
        <div class="overview-title">
          <span class="ov-icon">📝</span>
          <span>大纲总览</span>
        </div>
        <div class="overview-toggle">
          {{ overviewExpanded ? '收起' : '展开详情' }}
          <span class="toggle-arrow">{{ overviewExpanded ? '▲' : '▼' }}</span>
        </div>
      </div>

      <!-- 总览快速统计（收起时也可见） -->
      <div class="overview-quick-stats">
        <div class="qs-item">
          <span class="qs-label">卷数</span>
          <span class="qs-value">{{ volumeCount }}<span class="qs-target"> / {{ overviewForm.target_volumes || '?' }}</span></span>
        </div>
        <div class="qs-item">
          <span class="qs-label">章节</span>
          <span class="qs-value">{{ chapterCount }}<span class="qs-target"> / {{ overviewForm.target_chapters || '?' }}</span></span>
        </div>
        <div class="qs-item">
          <span class="qs-label">已确认</span>
          <span class="qs-value confirmed">{{ confirmedCount }}</span>
        </div>
        <div class="qs-item">
          <span class="qs-label">草稿</span>
          <span class="qs-value draft">{{ draftCount }}</span>
        </div>
        <div class="qs-item qs-progress">
          <span class="qs-label">整体进度</span>
          <div class="qs-bar">
            <div class="qs-bar-fill" :style="{ width: completionRate + '%' }"></div>
          </div>
          <span class="qs-pct">{{ completionRate }}%</span>
        </div>
      </div>

      <div v-show="overviewExpanded" class="overview-body">
        <div class="overview-grid">
          <div class="ov-field">
            <label class="ov-label">预计总字数</label>
            <n-input v-model:number="overviewForm.target_words" type="number" placeholder="如：1000000" size="small" />
          </div>
          <div class="ov-field">
            <label class="ov-label">预计卷数</label>
            <n-input v-model:number="overviewForm.target_volumes" type="number" placeholder="如：5" size="small" />
          </div>
          <div class="ov-field">
            <label class="ov-label">预计章节</label>
            <n-input v-model:number="overviewForm.target_chapters" type="number" placeholder="如：200" size="small" />
          </div>
          <div class="ov-field">
            <label class="ov-label">整体节奏</label>
            <n-select v-model:value="overviewForm.pace" :options="paceOptions" size="small" />
          </div>
        </div>
        <div class="ov-field ov-full">
          <label class="ov-label">故事主线</label>
          <n-input
            v-model:value="overviewForm.main_plot"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 5 }"
            placeholder="用一句话概括整个故事的主线..."
          />
        </div>
        <div class="ov-field ov-full">
          <label class="ov-label">核心冲突</label>
          <n-input
            v-model:value="overviewForm.core_conflict"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 5 }"
            placeholder="故事的核心矛盾和冲突是什么..."
          />
        </div>
        <div class="ov-field ov-full">
          <label class="ov-label">结局走向</label>
          <n-input
            v-model:value="overviewForm.ending"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 4 }"
            placeholder="故事的最终结局方向..."
          />
        </div>
        <div class="ov-actions">
          <n-button size="small" @click="resetOverview">重置</n-button>
          <n-button type="primary" size="small" :loading="overviewSaving" @click="saveOverview">
            💾 保存总览
          </n-button>
        </div>

        <!-- 各卷概览 -->
        <div class="volumes-overview">
          <div class="vo-title">📚 各卷概览</div>
          <div v-if="volumeList.length === 0" class="vo-empty">
            还没有创建分卷，点击左侧「新卷」开始规划
          </div>
          <div v-else class="vo-list">
            <div
              v-for="vol in volumeList"
              :key="vol.id"
              class="vo-card"
              @click="selectOutline(vol)"
            >
              <div class="vo-card-head">
                <div class="vo-vol-no">第{{ vol.volume_no }}卷</div>
                <n-tag size="tiny" :type="statusTagType(vol.status)">
                  {{ statusLabel(vol.status) }}
                </n-tag>
              </div>
              <div class="vo-card-title">{{ vol.title }}</div>
              <div class="vo-card-desc">{{ shortText(vol.description || '暂无简介', 80) }}</div>
              <div class="vo-card-meta">
                <span>📖 {{ getVolumeChapters(vol.id).length }} 章</span>
                <span v-if="getVolumeExtra(vol.id)?.ai_summary" class="vo-has-ai">🤖 已分析</span>
              </div>
              <!-- 卷内章节列表 -->
              <div v-if="getVolumeChapters(vol.id).length > 0" class="vo-chapters">
                <div
                  v-for="ch in getVolumeChapters(vol.id).slice(0, 5)"
                  :key="ch.id"
                  class="vo-chapter-item"
                  @click.stop="selectOutline(ch)"
                >
                  <span class="vo-ch-title">第{{ ch.chapter_no || ch.sort_index }}章 {{ ch.title || '未命名' }}</span>
                </div>
                <div v-if="getVolumeChapters(vol.id).length > 5" class="vo-ch-more">
                  还有 {{ getVolumeChapters(vol.id).length - 5 }} 章...
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 主体：左树 + 右详情 -->
    <div class="workbench">
      <!-- 左侧：大纲树 -->
      <aside class="tree-panel">
        <div class="panel-tools">
          <n-input v-model:value="keyword" clearable placeholder="搜索大纲..." size="small">
            <template #prefix>🔍</template>
          </n-input>
          <div class="tool-btns">
            <n-button type="primary" size="small" @click="startCreate('volume')">
              <template #icon>📚</template>
              新卷
            </n-button>
            <n-button size="small" @click="handleToolbarNewChapter" :disabled="!selectedVolumeId">
              <template #icon>📖</template>
              新章
            </n-button>
            <n-button size="small" quaternary @click="toggleAllVolumes">
              <template #icon>{{ allExpanded ? '📕' : '📖' }}</template>
              {{ allExpanded ? '全部收起' : '全部展开' }}
            </n-button>
          </div>
        </div>

        <n-scrollbar class="tree-scroll">
          <div class="tree-inner">
            <div v-if="loading" class="tree-loading">
              <n-spin size="small" />
              <span>加载中...</span>
            </div>

            <div v-else-if="treeData.length === 0" class="tree-empty">
              <div class="empty-icon">📑</div>
              <p>还没有大纲</p>
              <p class="empty-sub">点击「新卷」开始规划</p>
            </div>

            <div v-else class="outline-tree">
              <template v-for="group in treeData" :key="group.volumeId">
                <!-- 卷节点 -->
                <div
                  v-if="group.volume"
                  class="tree-node volume-node"
                  :class="{
                    active: editingId === group.volume.id,
                    'search-match': isVolumeMatch(group.volume),
                    'drag-over-before': dragOverId === group.volume.id && dragOverPosition === 'before',
                    'drag-over-after': dragOverId === group.volume.id && dragOverPosition === 'after',
                    'dragging': dragItemId === group.volume.id
                  }"
                  draggable="true"
                  @click="selectOutline(group.volume)"
                  @dragstart="onDragStart($event, group.volume)"
                  @dragend="onDragEnd"
                  @dragover="onDragOver($event, group.volume.id)"
                  @dragleave="onDragLeave"
                  @drop="dragType === 'volume' ? onVolumeDrop(group.volume) : onChapterDropOnVolume(group.volume)"
                >
                  <div class="volume-arrow" @click.stop="toggleVolume(group.volumeId)">
                    {{ expandedVolumes.includes(group.volumeId) ? '▼' : '▶' }}
                  </div>
                  <div class="node-icon vol-icon">📚</div>
                  <div class="node-content">
                    <div class="node-title-row">
                      <span class="node-title" v-html="highlightText('第' + group.volume.volume_no + '卷 ' + group.volume.title, keyword)"></span>
                      <n-tag size="tiny" :type="statusTagType(group.volume.status)">
                        {{ statusLabel(group.volume.status) }}
                      </n-tag>
                    </div>
                    <div class="node-meta">
                      {{ group.chapters.length }} 章
                    </div>
                    <div v-if="group.volume.description" class="node-desc">{{ shortText(group.volume.description, 50) }}</div>
                  </div>
                </div>

                <!-- 章节列表 -->
                <div v-show="expandedVolumes.includes(group.volumeId)" class="chapter-group">
                  <div
                    v-for="item in group.chapters"
                    :key="item.id"
                    class="tree-node chapter-node"
                    :class="{
                      active: editingId === item.id,
                      'search-match': isChapterMatch(item),
                      'drag-over-before': dragOverId === item.id && dragOverPosition === 'before',
                      'drag-over-after': dragOverId === item.id && dragOverPosition === 'after',
                      'dragging': dragItemId === item.id
                    }"
                    draggable="true"
                    @click="selectOutline(item)"
                    @dragstart="onDragStart($event, item)"
                    @dragend="onDragEnd"
                    @dragover="onDragOver($event, item.id)"
                    @dragleave="onDragLeave"
                    @drop="onChapterDrop(item)"
                  >
                    <div class="chapter-indicator"></div>
                    <div class="node-icon ch-icon">📖</div>
                    <div class="node-content">
                      <div class="node-title-row">
                        <span class="node-title" v-html="highlightText('第' + (item.chapter_no ?? item.sort_index) + '章 ' + item.title, keyword)"></span>
                        <n-tag size="tiny" :type="statusTagType(item.status)">
                          {{ statusLabel(item.status) }}
                        </n-tag>
                      </div>
                      <div v-if="item.description" class="node-desc">{{ shortText(item.description, 50) }}</div>
                    </div>
                  </div>

                  <div v-if="group.chapters.length === 0" class="empty-chapters">
                    本卷暂无章节
                  </div>
                </div>
              </template>

              <!-- 未分组章节 -->
              <div v-if="filteredUngroupedChapters.length > 0" class="ungrouped-section">
                <div class="ungrouped-title">📂 未分组章节</div>
                <div
                  v-for="item in filteredUngroupedChapters"
                  :key="item.id"
                  class="tree-node chapter-node"
                  :class="{
                    active: editingId === item.id,
                    'search-match': isChapterMatch(item),
                    'drag-over-before': dragOverId === item.id && dragOverPosition === 'before',
                    'drag-over-after': dragOverId === item.id && dragOverPosition === 'after',
                    'dragging': dragItemId === item.id
                  }"
                  draggable="true"
                  @click="selectOutline(item)"
                  @dragstart="onDragStart($event, item)"
                  @dragend="onDragEnd"
                  @dragover="onDragOver($event, item.id)"
                  @dragleave="onDragLeave"
                  @drop="onChapterDrop(item)"
                >
                  <div class="chapter-indicator"></div>
                  <div class="node-icon ch-icon">📖</div>
                  <div class="node-content">
                    <div class="node-title-row">
                      <span class="node-title" v-html="highlightText('第' + (item.chapter_no ?? item.sort_index) + '章 ' + item.title, keyword)"></span>
                      <n-tag size="tiny" :type="statusTagType(item.status)">
                        {{ statusLabel(item.status) }}
                      </n-tag>
                    </div>
                    <div v-if="item.description" class="node-desc">{{ shortText(item.description, 50) }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </n-scrollbar>
      </aside>

      <!-- 右侧：详情编辑 -->
      <section class="detail-panel">
        <div class="detail-header">
          <div class="detail-title">
            <h2>
              <span v-if="editingNode?.node_type === 'volume'">📚 编辑分卷</span>
              <span v-else-if="editingNode?.node_type === 'chapter'">📖 单章细纲</span>
              <span v-else-if="isCreating && createType === 'volume'">📚 新增分卷</span>
              <span v-else-if="isCreating && createType === 'chapter'">📖 新增章节</span>
              <span v-else>选择节点</span>
              <span v-if="isDirty" class="dirty-dot" title="有未保存的修改">●</span>
            </h2>
          </div>
          <div class="detail-actions" v-if="editingId || isCreating">
            <n-popconfirm v-if="editingId" positive-text="确认删除" negative-text="取消" @positive-click="remove">
              <template #trigger>
                <n-button type="error" text size="small">🗑️ 删除</n-button>
              </template>
              确认删除这个{{ editingNode?.node_type === 'volume' ? '分卷' : '章节' }}？
            </n-popconfirm>
            <n-button text size="small" @click="resetCurrent">↺ 重置</n-button>
            <n-button type="primary" size="small" :disabled="!canSave" @click="save">💾 保存</n-button>
          </div>
        </div>

        <div v-if="!editingId && !isCreating" class="detail-empty">
          <div class="empty-icon">✏️</div>
          <p>从左侧选择卷或章节进行编辑</p>
          <p class="empty-sub">或点击「新卷/新章」创建</p>
        </div>

        <n-scrollbar v-else class="form-scroll">
          <!-- 卷详情 -->
          <div v-if="editingNode?.node_type === 'volume' || (isCreating && createType === 'volume')">
            <n-form class="detail-form" label-placement="top">
            <div class="form-section">
              <div class="section-title">
                <span>基本信息</span>
                <n-button size="tiny" type="primary" :loading="volumeAnalyzing" @click="handleVolumeAnalyze" v-if="editingId">
                  <template #icon>🤖</template>
                  AI 分析并完善总览
                </n-button>
              </div>
              <div class="form-grid-2">
                <n-form-item label="状态">
                  <n-select v-model:value="form.status" :options="statusOptions" />
                </n-form-item>
                <n-form-item label="预计章节数">
                  <n-input v-model:number="volumeExtra.target_chapters" type="number" placeholder="如：30" />
                </n-form-item>
              </div>
              <n-form-item label="卷名">
                <n-input v-model:value="form.title" placeholder="输入卷名" size="large" />
              </n-form-item>
            </div>

            <div class="form-section">
              <div class="section-title">卷规划</div>
              <n-form-item label="卷简介">
                <n-input
                  v-model:value="form.description"
                  type="textarea"
                  :autosize="{ minRows: 4, maxRows: 8 }"
                  placeholder="这一卷的整体剧情走向..."
                />
              </n-form-item>
              <div class="form-grid-2">
                <n-form-item label="核心事件">
                  <n-input
                    v-model:value="volumeExtra.core_events"
                    type="textarea"
                    :autosize="{ minRows: 4, maxRows: 6 }"
                    placeholder="本卷的关键事件节点..."
                  />
                </n-form-item>
                <n-form-item label="出场人物">
                  <n-select
                    v-model:value="volumeExtra.characters"
                    multiple
                    filterable
                    :options="characterOptions"
                    placeholder="选择出场人物"
                  />
                </n-form-item>
              </div>
              <div class="form-grid-2">
                <n-form-item label="主要场景">
                  <n-input
                    v-model:value="volumeExtra.locations"
                    type="textarea"
                    :autosize="{ minRows: 3, maxRows: 5 }"
                    placeholder="本卷主要发生的地点..."
                  />
                </n-form-item>
                <n-form-item label="卷末高潮">
                  <n-input
                    v-model:value="volumeExtra.climax"
                    type="textarea"
                    :autosize="{ minRows: 3, maxRows: 5 }"
                    placeholder="本卷结尾的高潮事件..."
                  />
                </n-form-item>
              </div>
            </div>

            <!-- AI 分析结果 -->
            <div v-if="volumeExtra.ai_summary || volumeExtra.chapter_suggestions" class="form-section">
              <div class="section-title">🤖 AI 分析结果</div>
              <n-form-item v-if="volumeExtra.ai_summary" label="卷定位摘要">
                <n-input
                  v-model:value="volumeExtra.ai_summary"
                  type="textarea"
                  :autosize="{ minRows: 3, maxRows: 6 }"
                  readonly
                />
              </n-form-item>
              <n-form-item v-if="volumeExtra.chapter_suggestions" label="章节生成建议">
                <n-input
                  v-model:value="volumeExtra.chapter_suggestions"
                  type="textarea"
                  :autosize="{ minRows: 4, maxRows: 8 }"
                  readonly
                />
              </n-form-item>
            </div>
          </n-form>

          <!-- 本卷章节列表 -->
          <div class="form-section volume-chapters-section">
            <div class="section-title">
              <span>📖 本卷章节 ({{ currentVolumeChapters.length }} / {{ volumeExtra.target_chapters || '?' }})</span>
              <div class="section-actions">
                <n-button size="tiny" @click="showBatchCreate = !showBatchCreate">
                  <template #icon>📋</template>
                  批量创建
                </n-button>
                <n-button size="tiny" type="primary" ghost @click="startChapterInVolume">
                  <template #icon>➕</template>
                  新增章节
                </n-button>
              </div>
            </div>

            <!-- 章节进度 -->
            <div class="chapter-progress">
              <div class="cp-bar">
                <div class="cp-bar-fill" :style="{ width: chapterProgressPercent + '%' }"></div>
              </div>
              <span class="cp-text">{{ chapterProgressPercent }}%</span>
            </div>

            <!-- 批量创建面板 -->
            <div v-if="showBatchCreate" class="batch-create-panel">
              <div class="bc-title">批量创建章节</div>
              <div class="bc-grid">
                <n-form-item label="起始章号">
                  <n-input v-model:number="batchForm.start_no" type="number" placeholder="如：1" />
                </n-form-item>
                <n-form-item label="创建数量">
                  <n-input v-model:number="batchForm.count" type="number" placeholder="如：10" />
                </n-form-item>
              </div>
              <div class="bc-tip">将创建 {{ batchForm.count }} 个章节，章号从 {{ batchForm.start_no }} 开始</div>
              <div class="bc-actions">
                <n-button size="small" @click="showBatchCreate = false">取消</n-button>
                <n-button type="primary" size="small" :loading="batchCreating" @click="handleBatchCreate">
                  ✅ 确认创建
                </n-button>
              </div>
            </div>

            <div v-if="currentVolumeChapters.length === 0" class="volume-chapters-empty">
              本卷暂无章节，点击「新增章节」或「批量创建」添加
            </div>
            <div v-else class="chapter-list">
              <div
                v-for="ch in currentVolumeChapters"
                :key="ch.id"
                class="chapter-list-item"
                :class="{ active: editingId === ch.id }"
                @click="selectOutline(ch)"
              >
                <div class="cli-title">第{{ ch.chapter_no ?? ch.sort_index }}章 {{ ch.title || '未命名章节' }}</div>
                <div class="cli-actions">
                  <n-tag size="tiny" :type="statusTagType(ch.status)">
                    {{ statusLabel(ch.status) }}
                  </n-tag>
                  <span v-if="ch.description" class="cli-has-detail" title="已有细纲">📝</span>
                </div>
              </div>
            </div>
          </div>
          </div>

          <!-- 章节详情（单章细纲） -->
          <n-form v-else class="detail-form" label-placement="top">
            <div class="form-section">
              <div class="section-title">基本信息</div>
              <div class="form-grid-2">
                <n-form-item label="所属卷">
                  <n-select v-model:value="form.volume_id" :options="volumeOptions" clearable placeholder="选择所属卷" />
                </n-form-item>
                <n-form-item label="状态">
                  <n-select v-model:value="form.status" :options="statusOptions" />
                </n-form-item>
              </div>
              <n-form-item label="章节标题">
                <n-input v-model:value="form.title" placeholder="输入章节标题" size="large" />
              </n-form-item>
            </div>

            <div class="form-section">
              <div class="section-title">单章细纲</div>
              <n-form-item label="本章概述">
                <n-input
                  v-model:value="form.description"
                  type="textarea"
                  :autosize="{ minRows: 3, maxRows: 6 }"
                  placeholder="用一段话概括本章主要内容..."
                />
              </n-form-item>
              <div class="form-grid-2">
                <n-form-item label="场景设定">
                  <n-input
                    v-model:value="chapterExtra.scene"
                    type="textarea"
                    :autosize="{ minRows: 3, maxRows: 5 }"
                    placeholder="本章发生的场景、环境、氛围..."
                  />
                </n-form-item>
                <n-form-item label="出场人物">
                  <n-select
                    v-model:value="chapterExtra.characters"
                    multiple
                    filterable
                    :options="characterOptions"
                    placeholder="选择出场人物"
                  />
                </n-form-item>
              </div>
              <div class="form-grid-2">
                <n-form-item label="核心冲突">
                  <n-input
                    v-model:value="chapterExtra.conflict"
                    type="textarea"
                    :autosize="{ minRows: 3, maxRows: 5 }"
                    placeholder="本章的主要矛盾、冲突点..."
                  />
                </n-form-item>
                <n-form-item label="剧情转折">
                  <n-input
                    v-model:value="chapterExtra.twist"
                    type="textarea"
                    :autosize="{ minRows: 3, maxRows: 5 }"
                    placeholder="本章有什么转折或意外..."
                  />
                </n-form-item>
              </div>
              <div class="form-grid-2">
                <n-form-item label="人物收获">
                  <n-input
                    v-model:value="chapterExtra.gain"
                    type="textarea"
                    :autosize="{ minRows: 3, maxRows: 5 }"
                    placeholder="主角/人物获得了什么、成长了什么..."
                  />
                </n-form-item>
                <n-form-item label="伏笔埋设">
                  <n-select
                    v-model:value="chapterExtra.foreshadowings"
                    multiple
                    filterable
                    :options="foreshadowingOptions"
                    placeholder="关联伏笔"
                  />
                </n-form-item>
              </div>
            </div>
          </n-form>
        </n-scrollbar>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { createResource, deleteResource, listResource, updateResource, renumberOutlines, reorderVolumes, reorderChapter, moveChapterToVolume } from '@/api/resources'
import { analyzeVolume } from '@/api/agents'
import { useProjectStore } from '@/stores/project'
import { useProjectDataLoader } from '@/composables/useProjectDataLoader'
import { useDirtySnapshot } from '@/composables/useDirtySnapshot'
import { notify } from '@/utils/notify'
import type { CharacterItem, ForeshadowingItem, OutlineItem } from '@/types/domain'

const projectStore = useProjectStore()
const outlines = ref<OutlineItem[]>([])
const characters = ref<CharacterItem[]>([])
const foreshadowings = ref<ForeshadowingItem[]>([])
const loading = ref(false)
const keyword = ref('')
const editingId = ref<number | null>(null)
const isCreating = ref(false)
const createType = ref<'volume' | 'chapter'>('chapter')
const expandedVolumes = ref<number[]>([])

const project = computed(() => projectStore.currentProject)

// ===== 大纲总览 =====
const overviewExpanded = ref(false)
const overviewSaving = ref(false)
const overviewId = ref<number | null>(null)
const overviewForm = reactive({
  target_words: 1000000,
  target_volumes: 5,
  target_chapters: 200,
  pace: '3',
  main_plot: '',
  core_conflict: '',
  ending: '',
})
const overviewOrigin = reactive({ ...overviewForm })

const paceOptions = [
  { label: '慢热', value: '1' },
  { label: '偏慢', value: '2' },
  { label: '适中', value: '3' },
  { label: '偏快', value: '4' },
  { label: '高燃', value: '5' },
]

function findOverviewItem(): OutlineItem | undefined {
  return outlines.value.find((o) => o.node_type === 'overview' || o.title === '大纲总览')
}

function loadOverview() {
  const item = findOverviewItem()
  if (item) {
    overviewId.value = item.id
    overviewForm.main_plot = item.description || ''
    try {
      const extra = item.extra ? JSON.parse(item.extra) : {}
      overviewForm.target_words = extra.target_words || 1000000
      overviewForm.target_volumes = extra.target_volumes || 5
      overviewForm.target_chapters = extra.target_chapters || 200
      overviewForm.pace = extra.pace || '3'
      overviewForm.core_conflict = extra.core_conflict || ''
      overviewForm.ending = extra.ending || ''
    } catch { /* ignore */ }
  } else {
    overviewId.value = null
    overviewForm.target_words = 1000000
    overviewForm.target_volumes = 5
    overviewForm.target_chapters = 200
    overviewForm.pace = '3'
    overviewForm.main_plot = ''
    overviewForm.core_conflict = ''
    overviewForm.ending = ''
  }
  Object.assign(overviewOrigin, overviewForm)
}

function resetOverview() {
  Object.assign(overviewForm, overviewOrigin)
}

async function saveOverview() {
  if (!project.value) return
  overviewSaving.value = true
  try {
    const extra = JSON.stringify({
      target_words: overviewForm.target_words,
      target_volumes: overviewForm.target_volumes,
      target_chapters: overviewForm.target_chapters,
      pace: overviewForm.pace,
      core_conflict: overviewForm.core_conflict,
      ending: overviewForm.ending,
    })
    const payload = {
      project_id: project.value.id,
      title: '大纲总览',
      node_type: 'overview',
      status: 'confirmed',
      description: overviewForm.main_plot,
      extra,
      sort_index: 0,
    }
    if (overviewId.value) {
      await updateResource('outlines', overviewId.value, payload)
    } else {
      const created = await createResource<OutlineItem>('outlines', payload)
      overviewId.value = created.id
    }
    Object.assign(overviewOrigin, overviewForm)
    notify.success('总览已保存')
    loadOutlines()
  } catch (e) {
    notify.error('保存失败')
  } finally {
    overviewSaving.value = false
  }
}

// ===== 状态选项 =====
const statusOptions = [
  { label: '草稿', value: 'draft' },
  { label: '规划中', value: 'planning' },
  { label: '已确认', value: 'confirmed' },
  { label: '已完成', value: 'done' },
]

function statusLabel(val: string): string {
  const opt = statusOptions.find((o) => o.value === val)
  return opt?.label || val
}

function statusTagType(val: string): 'default' | 'success' | 'warning' | 'info' | 'error' {
  if (val === 'done') return 'success'
  if (val === 'confirmed') return 'info'
  if (val === 'planning') return 'warning'
  return 'default'
}

const characterOptions = computed(() => characters.value.map((c) => ({ label: c.name, value: c.id })))
const foreshadowingOptions = computed(() => foreshadowings.value.map((f) => ({ label: f.keyword, value: f.id })))
const volumeOptions = computed(() =>
  outlines.value
    .filter((o) => o.node_type === 'volume')
    .sort((a, b) => (a.volume_no || 0) - (b.volume_no || 0))
    .map((o) => ({ label: `第${o.volume_no}卷 ${o.title}`, value: o.id }))
)

// 当前卷的章节列表
const currentVolumeChapters = computed(() => {
  if (!editingId.value || editingNode.value?.node_type !== 'volume') return []
  return outlines.value
    .filter((o) => o.node_type === 'chapter' && o.volume_id === editingId.value)
    .sort((a, b) => (a.chapter_no || a.sort_index || 0) - (b.chapter_no || b.sort_index || 0))
})

// 卷章节完成进度
const chapterProgressPercent = computed(() => {
  const target = volumeExtra.target_chapters || 1
  const current = currentVolumeChapters.value.length
  return Math.min(Math.round((current / target) * 100), 100)
})

// 全局最后一章号（所有卷中最大的 chapter_no）
const globalLastChapterNo = computed(() => {
  const chapters = outlines.value.filter((o) => o.node_type === 'chapter')
  if (chapters.length === 0) return 0
  return Math.max(...chapters.map((c) => c.chapter_no || c.sort_index || 0))
})

// 是否全部展开
const allExpanded = computed(() => {
  const volIds = volumeList.value.map(v => v.id)
  if (volIds.length === 0) return false
  return volIds.every(id => expandedVolumes.value.includes(id))
})

// 全部展开/收起
function toggleAllVolumes() {
  if (allExpanded.value) {
    expandedVolumes.value = []
  } else {
    expandedVolumes.value = volumeList.value.map(v => v.id)
  }
}

// ===== 表单 =====
const form = reactive<Partial<OutlineItem>>({
  id: 0,
  title: '',
  node_type: 'chapter',
  status: 'draft',
  volume_no: null,
  chapter_no: null,
  volume_id: null,
  description: '',
  extra: '',
  sort_index: 0,
})

const volumeExtra = reactive({
  core_events: '',
  characters: [] as number[],
  locations: '',
  climax: '',
  ai_summary: '',
  chapter_suggestions: '',
  target_chapters: 30,
})

const volumeAnalyzing = ref(false)
const showBatchCreate = ref(false)
const batchCreating = ref(false)
const batchForm = reactive({
  start_no: 1,
  count: 10,
})

// 拖拽状态
const dragType = ref<'volume' | 'chapter' | null>(null)
const dragItemId = ref<number | null>(null)
const dragOverId = ref<number | null>(null)
const dragOverPosition = ref<'before' | 'after' | null>(null)

const chapterExtra = reactive({
  scene: '',
  characters: [] as number[],
  conflict: '',
  twist: '',
  gain: '',
  foreshadowings: [] as number[],
})

const { isDirty, markClean, confirmIfDirty } = useDirtySnapshot(form, '当前大纲有未保存的修改，确定要离开吗？')

const editingNode = computed(() => {
  if (!editingId.value) return null
  return outlines.value.find((o) => o.id === editingId.value) || null
})

const canSave = computed(() => (form.title || '').trim().length > 0)

// ===== 统计 =====
const volumeCount = computed(() => outlines.value.filter((o) => o.node_type === 'volume').length)
const chapterCount = computed(() => outlines.value.filter((o) => o.node_type === 'chapter').length)
const confirmedCount = computed(() => outlines.value.filter((o) => o.status === 'confirmed' || o.status === 'done').length)
const draftCount = computed(() => outlines.value.filter((o) => o.status === 'draft').length)
const planningCount = computed(() => outlines.value.filter((o) => o.status === 'planning').length)
const estimatedWords = computed(() => {
  const count = chapterCount.value
  return count > 0 ? `${(count * 2500 / 10000).toFixed(1)}万` : '0'
})
const completionRate = computed(() => {
  const total = chapterCount.value || 1
  const done = outlines.value.filter((o) => o.node_type === 'chapter' && (o.status === 'confirmed' || o.status === 'done')).length
  return Math.round((done / total) * 100)
})

// 卷列表
const volumeList = computed(() =>
  outlines.value
    .filter((o) => o.node_type === 'volume')
    .sort((a, b) => (a.volume_no || 0) - (b.volume_no || 0))
)

// 获取指定卷的章节
function getVolumeChapters(volumeId: number): OutlineItem[] {
  return outlines.value
    .filter((o) => o.node_type === 'chapter' && o.volume_id === volumeId)
    .sort((a, b) => (a.chapter_no || a.sort_index || 0) - (b.chapter_no || b.sort_index || 0))
}

// 获取卷的 extra 数据
function getVolumeExtra(volumeId: number): Record<string, any> | null {
  const vol = outlines.value.find((o) => o.id === volumeId)
  if (!vol || !vol.extra) return null
  try {
    return JSON.parse(vol.extra)
  } catch {
    return null
  }
}

// 搜索高亮
function highlightText(text: string, keyword: string): string {
  if (!keyword || !text) return text
  const kw = keyword.trim()
  if (!kw) return text
  const regex = new RegExp(`(${kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
  return text.replace(regex, '<mark class="hl">$1</mark>')
}

// 搜索时自动展开匹配的卷
watch(keyword, (newKw) => {
  const kw = newKw.trim().toLowerCase()
  if (!kw) return
  const matchedVolumeIds = outlines.value
    .filter((o) => o.node_type === 'volume' && matchKeyword(o, kw))
    .map((o) => o.id)
  // 也展开有匹配章节的卷
  const matchedChapterVolIds = outlines.value
    .filter((o) => o.node_type === 'chapter' && o.volume_id && matchKeyword(o, kw))
    .map((o) => o.volume_id!)
  const allIds = [...new Set([...matchedVolumeIds, ...matchedChapterVolIds])]
  for (const id of allIds) {
    if (!expandedVolumes.value.includes(id)) {
      expandedVolumes.value.push(id)
    }
  }
})

// ===== 树结构 =====
interface VolumeGroup {
  volumeId: number
  volume: OutlineItem | null
  chapters: OutlineItem[]
}

const treeData = computed<VolumeGroup[]>(() => {
  const kw = keyword.value.trim().toLowerCase()
  const volumes = outlines.value
    .filter((o) => o.node_type === 'volume')
    .sort((a, b) => (a.volume_no || 0) - (b.volume_no || 0))

  const groups: VolumeGroup[] = volumes.map((v) => ({
    volumeId: v.id,
    volume: v,
    chapters: [],
  }))

  const chapterList = outlines.value.filter((o) => o.node_type === 'chapter' && o.volume_id)
  for (const ch of chapterList) {
    const group = groups.find((g) => g.volumeId === ch.volume_id)
    if (group) {
      // 搜索时：卷匹配则显示所有章节，章节匹配也显示
      if (kw) {
        const volMatch = matchKeyword(group.volume!, kw)
        const chMatch = matchKeyword(ch, kw)
        if (volMatch || chMatch) {
          group.chapters.push(ch)
        }
      } else {
        group.chapters.push(ch)
      }
    }
  }

  // 章节排序
  for (const g of groups) {
    g.chapters.sort((a, b) => (a.chapter_no || a.sort_index || 0) - (b.chapter_no || b.sort_index || 0))
  }

  // 搜索过滤卷
  if (kw) {
    return groups.filter((g) => {
      if (!g.volume) return false
      if (matchKeyword(g.volume, kw)) return true
      return g.chapters.length > 0
    })
  }

  return groups
})

const ungroupedChapters = computed(() =>
  outlines.value
    .filter((o) => o.node_type === 'chapter' && !o.volume_id)
    .sort((a, b) => (a.chapter_no || a.sort_index || 0) - (b.chapter_no || b.sort_index || 0))
)

const filteredUngroupedChapters = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return ungroupedChapters.value
  return ungroupedChapters.value.filter((c) => matchKeyword(c, kw))
})

// 搜索匹配判断
function isVolumeMatch(volume: OutlineItem): boolean {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return false
  return matchKeyword(volume, kw)
}

function isChapterMatch(chapter: OutlineItem): boolean {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return false
  return matchKeyword(chapter, kw)
}

function matchKeyword(item: OutlineItem, kw: string): boolean {
  return [item.title, item.description].join(' ').toLowerCase().includes(kw)
}

function toggleVolume(volId: number) {
  const idx = expandedVolumes.value.indexOf(volId)
  if (idx >= 0) {
    expandedVolumes.value.splice(idx, 1)
  } else {
    expandedVolumes.value.push(volId)
  }
}

// ===== 方法 =====
function selectOutline(item: OutlineItem) {
  if (!confirmIfDirty()) return
  editingId.value = item.id
  isCreating.value = false
  Object.assign(form, { ...item })
  parseExtra(item)
  // 选中卷时，初始化批量创建参数
  if (item.node_type === 'volume') {
    const chaps = getVolumeChapters(item.id)
    // 起始章号 = 当前卷最后一章号 + 1
    const lastNo = chaps.length > 0
      ? Math.max(...chaps.map(c => c.chapter_no || c.sort_index || 0))
      : 0
    batchForm.start_no = lastNo + 1
    batchForm.count = Math.max(1, (volumeExtra.target_chapters || 30) - chaps.length)
    showBatchCreate.value = false
  }
  markClean()
}

function parseExtra(item: OutlineItem) {
  try {
    const extra = item.extra ? JSON.parse(item.extra) : {}
    if (item.node_type === 'volume') {
      volumeExtra.core_events = extra.core_events || ''
      volumeExtra.characters = extra.characters || []
      volumeExtra.locations = extra.locations || ''
      volumeExtra.climax = extra.climax || ''
      volumeExtra.ai_summary = extra.ai_summary || ''
      volumeExtra.chapter_suggestions = extra.chapter_suggestions || ''
      volumeExtra.target_chapters = extra.target_chapters || 30
    } else {
      chapterExtra.scene = extra.scene || ''
      chapterExtra.characters = extra.characters || []
      chapterExtra.conflict = extra.conflict || ''
      chapterExtra.twist = extra.twist || ''
      chapterExtra.gain = extra.gain || ''
      chapterExtra.foreshadowings = extra.foreshadowings || []
    }
  } catch {
    if (item.node_type === 'volume') {
      volumeExtra.core_events = ''
      volumeExtra.characters = []
      volumeExtra.locations = ''
      volumeExtra.climax = ''
      volumeExtra.ai_summary = ''
      volumeExtra.chapter_suggestions = ''
      volumeExtra.target_chapters = 30
    } else {
      chapterExtra.scene = ''
      chapterExtra.characters = []
      chapterExtra.conflict = ''
      chapterExtra.twist = ''
      chapterExtra.gain = ''
      chapterExtra.foreshadowings = []
    }
  }
}

function buildExtra(): string {
  if (form.node_type === 'volume') {
    return JSON.stringify({
      core_events: volumeExtra.core_events,
      characters: volumeExtra.characters,
      locations: volumeExtra.locations,
      climax: volumeExtra.climax,
      ai_summary: volumeExtra.ai_summary,
      chapter_suggestions: volumeExtra.chapter_suggestions,
      target_chapters: volumeExtra.target_chapters,
    })
  } else {
    return JSON.stringify({
      scene: chapterExtra.scene,
      characters: chapterExtra.characters,
      conflict: chapterExtra.conflict,
      twist: chapterExtra.twist,
      gain: chapterExtra.gain,
      foreshadowings: chapterExtra.foreshadowings,
    })
  }
}

function startCreate(type: 'volume' | 'chapter') {
  if (!confirmIfDirty()) return
  editingId.value = null
  isCreating.value = true
  createType.value = type
  Object.assign(form, {
    id: 0,
    title: '',
    node_type: type,
    status: 'draft',
    volume_no: type === 'volume' ? volumeCount.value + 1 : null,
    chapter_no: type === 'chapter' ? chapterCount.value + 1 : null,
    volume_id: null,
    description: '',
    extra: '',
    sort_index: 0,
  })
  if (type === 'volume') {
    volumeExtra.core_events = ''
    volumeExtra.characters = []
    volumeExtra.locations = ''
    volumeExtra.climax = ''
    volumeExtra.ai_summary = ''
    volumeExtra.chapter_suggestions = ''
  } else {
    chapterExtra.scene = ''
    chapterExtra.characters = []
    chapterExtra.conflict = ''
    chapterExtra.twist = ''
    chapterExtra.gain = ''
    chapterExtra.foreshadowings = []
  }
  markClean()
}

// 在当前卷内新增章节
// 当前选中的卷ID（如果选中的是卷，就是它自己；如果选中的是章节，就是它的所属卷）
const selectedVolumeId = computed(() => {
  if (!editingNode.value) return null
  if (editingNode.value.node_type === 'volume') return editingNode.value.id
  if (editingNode.value.node_type === 'chapter') return editingNode.value.volume_id
  return null
})

// 工具栏的新章按钮
function handleToolbarNewChapter() {
  if (!selectedVolumeId.value) return
  if (!confirmIfDirty()) return
  // 找到卷节点
  const vol = outlines.value.find(o => o.id === selectedVolumeId.value)
  if (!vol) return
  // 展开该卷
  if (!expandedVolumes.value.includes(vol.id)) {
    expandedVolumes.value.push(vol.id)
  }
  // 计算默认章号（当前卷最后一章 + 1）
  const volChapters = outlines.value
    .filter(o => o.node_type === 'chapter' && o.volume_id === vol.id)
  const maxNo = volChapters.length > 0
    ? Math.max(...volChapters.map(c => c.chapter_no || c.sort_index || 0))
    : 0
  const defaultNo = maxNo + 1

  isCreating.value = true
  createType.value = 'chapter'
  editingId.value = null
  Object.assign(form, {
    id: 0,
    title: '',
    node_type: 'chapter',
    status: 'draft',
    volume_no: null,
    chapter_no: defaultNo,
    volume_id: vol.id,
    description: '',
    extra: '',
    sort_index: defaultNo,
  })
  chapterExtra.scene = ''
  chapterExtra.characters = []
  chapterExtra.conflict = ''
  chapterExtra.twist = ''
  chapterExtra.gain = ''
  chapterExtra.foreshadowings = []
}

// 在当前卷内新增章节
function startChapterInVolume() {
  if (!confirmIfDirty()) return
  if (!editingId.value || editingNode.value?.node_type !== 'volume') return
  // 先保存当前卷的ID，再清空 editingId
  const currentVolumeId = editingNode.value.id
  editingId.value = null
  isCreating.value = true
  createType.value = 'chapter'
  // 默认章号 = 当前卷最后一章号 + 1
  const volChapters = getVolumeChapters(currentVolumeId)
  const lastChapterNo = volChapters.length > 0
    ? Math.max(...volChapters.map(c => c.chapter_no || c.sort_index || 0))
    : 0
  const nextChapterNo = lastChapterNo + 1
  Object.assign(form, {
    id: 0,
    title: '',
    node_type: 'chapter',
    status: 'draft',
    volume_no: null,
    chapter_no: nextChapterNo,
    volume_id: currentVolumeId,
    description: '',
    extra: '',
    sort_index: nextChapterNo,
  })
  chapterExtra.scene = ''
  chapterExtra.characters = []
  chapterExtra.conflict = ''
  chapterExtra.twist = ''
  chapterExtra.gain = ''
  chapterExtra.foreshadowings = []
  markClean()
}

// 批量创建章节
async function handleBatchCreate() {
  if (!editingId.value || !project.value || batchForm.count <= 0) return
  batchCreating.value = true
  try {
    const startNo = batchForm.start_no || 1
    const count = batchForm.count || 10
    const promises: Promise<any>[] = []
    for (let i = 0; i < count; i++) {
      const chapterNo = startNo + i
      const payload = {
        project_id: project.value.id,
        title: `第${chapterNo}章`,
        node_type: 'chapter',
        status: 'draft',
        chapter_no: chapterNo,
        volume_id: editingId.value,
        description: '',
        extra: '',
        sort_index: chapterNo,
      }
      promises.push(createResource('outlines', payload))
    }
    await Promise.all(promises)
    notify.success(`已创建 ${count} 个章节`)
    showBatchCreate.value = false
    loadOutlines()
  } catch (e) {
    notify.error('批量创建失败')
  } finally {
    batchCreating.value = false
  }
}

// 全局重新编号
async function handleRenumberChapters() {
  if (!project.value) return
  try {
    await renumberOutlines(project.value.id)
    notify.success('生成编号完成')
    loadOutlines()
  } catch (e) {
    notify.error('生成编号失败')
  }
}

// ==================== 拖拽排序 ====================
function onDragStart(e: DragEvent, item: OutlineItem) {
  dragItemId.value = item.id
  dragType.value = item.node_type as 'volume' | 'chapter'
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(item.id))
  }
}

function onDragEnd() {
  dragItemId.value = null
  dragType.value = null
  dragOverId.value = null
  dragOverPosition.value = null
}

function onDragOver(e: DragEvent, targetId: number) {
  e.preventDefault()
  if (dragItemId.value === targetId) return
  dragOverId.value = targetId
  // 判断是放在前面还是后面
  const target = e.currentTarget as HTMLElement
  const rect = target.getBoundingClientRect()
  const midY = rect.top + rect.height / 2
  dragOverPosition.value = e.clientY < midY ? 'before' : 'after'
}

function onDragLeave() {
  dragOverId.value = null
  dragOverPosition.value = null
}

// 卷拖拽放下
async function onVolumeDrop(targetVolume: OutlineItem) {
  if (!dragItemId.value || dragType.value !== 'volume') return
  if (dragItemId.value === targetVolume.id) return
  try {
    await reorderVolumes(dragItemId.value, targetVolume.id, dragOverPosition.value || 'after')
    loadOutlines()
  } catch (e) {
    notify.error('排序失败')
  } finally {
    onDragEnd()
  }
}

// 章节拖拽放下
async function onChapterDrop(targetChapter: OutlineItem) {
  if (!dragItemId.value || dragType.value !== 'chapter') return
  if (dragItemId.value === targetChapter.id) return
  try {
    await reorderChapter(dragItemId.value, targetChapter.id, dragOverPosition.value || 'after')
    loadOutlines()
  } catch (e) {
    notify.error('排序失败')
  } finally {
    onDragEnd()
  }
}

// 章节拖到卷上（移动到该卷末尾）
async function onChapterDropOnVolume(targetVolume: OutlineItem) {
  if (!dragItemId.value || dragType.value !== 'chapter') return
  try {
    await moveChapterToVolume(dragItemId.value, targetVolume.id)
    loadOutlines()
  } catch (e) {
    notify.error('移动失败')
  } finally {
    onDragEnd()
  }
}

// AI 分析卷并完善总览
async function handleVolumeAnalyze() {
  if (!editingId.value || !project.value) return
  volumeAnalyzing.value = true
  try {
    const result = await analyzeVolume({
      project_id: project.value.id,
      volume_id: editingId.value,
      instruction: '',
    })
    // 更新卷的分析结果
    if (result.volume_summary) volumeExtra.ai_summary = result.volume_summary
    if (result.chapter_suggestions) volumeExtra.chapter_suggestions = result.chapter_suggestions
    // 保存到卷
    await save()
    // 重新加载大纲（总览会更新）
    await loadOutlines()
    notify.success('分析完成，大纲总览已更新')
  } catch (e) {
    notify.error('分析失败')
  } finally {
    volumeAnalyzing.value = false
  }
}

function resetCurrent() {
  if (editingId.value && editingNode.value) {
    Object.assign(form, { ...editingNode.value })
    parseExtra(editingNode.value)
  } else {
    startCreate(createType.value)
  }
  markClean()
}

async function save() {
  if (!canSave.value || !project.value) return
  try {
    const payload = {
      ...form,
      project_id: project.value.id,
      extra: buildExtra(),
    }
    if (editingId.value) {
      await updateResource('outlines', editingId.value, payload)
      notify.success('已保存')
      await loadOutlines()
    } else {
      const created = await createResource<OutlineItem>('outlines', payload)
      notify.success('已创建')
      await loadOutlines()
      // 加载完成后再选中新创建的节点
      editingId.value = created.id
      isCreating.value = false
      // 新卷自动展开
      if (created.node_type === 'volume' && !expandedVolumes.value.includes(created.id)) {
        expandedVolumes.value.push(created.id)
      }
      // 新章节自动展开所属卷
      if (created.node_type === 'chapter' && created.volume_id && !expandedVolumes.value.includes(created.volume_id)) {
        expandedVolumes.value.push(created.volume_id)
      }
    }
    markClean()
  } catch (e) {
    notify.error('保存失败')
  }
}

async function remove() {
  if (!editingId.value) return
  try {
    await deleteResource('outlines', editingId.value)
    editingId.value = null
    isCreating.value = false
    notify.success('已删除')
    loadOutlines()
  } catch (e) {
    notify.error('删除失败')
  }
}

function shortText(text: string, max: number): string {
  if (!text) return ''
  return text.length > max ? text.substring(0, max) + '...' : text
}

async function loadOutlines() {
  if (!project.value) return
  loading.value = true
  try {
    outlines.value = await listResource<OutlineItem>(project.value.id, 'outlines')
    // 默认展开所有卷
    if (expandedVolumes.value.length === 0) {
      expandedVolumes.value = outlines.value
        .filter((o) => o.node_type === 'volume')
        .map((o) => o.id)
    }
    loadOverview()
  } finally {
    loading.value = false
  }
}

async function load() {
  if (!project.value) return
  loading.value = true
  try {
    const [oList, cList, fList] = await Promise.all([
      listResource<OutlineItem>(project.value.id, 'outlines'),
      listResource<CharacterItem>(project.value.id, 'characters'),
      listResource<ForeshadowingItem>(project.value.id, 'foreshadowings'),
    ])
    outlines.value = oList
    characters.value = cList
    foreshadowings.value = fList
    // 默认展开所有卷
    expandedVolumes.value = oList
      .filter((o) => o.node_type === 'volume')
      .map((o) => o.id)
    loadOverview()
  } finally {
    loading.value = false
  }
}

useProjectDataLoader(load)
</script>

<style scoped>
.outline-page {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

/* ===== 总览横幅 ===== */
.outline-hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding: 20px 24px;
  background: linear-gradient(135deg, #2d1b4e 0%, #0f172a 100%);
  border: 1px solid #4c2d6e;
  border-radius: 10px;
}
.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: rgba(139, 92, 246, 0.2);
  border-radius: 20px;
  font-size: 12px;
  color: #a78bfa;
  margin-bottom: 10px;
}
.badge-icon { font-size: 14px; }
.hero-title {
  font-size: 22px;
  font-weight: 700;
  color: #f3f4f6;
  margin: 0 0 6px 0;
}
.hero-desc {
  font-size: 13px;
  color: #9ca3af;
  margin: 0;
}
.hero-right { display: flex; gap: 24px; }
.hero-stat { text-align: center; }
.hero-stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #f3f4f6;
  line-height: 1.2;
}
.hero-stat-value.success { color: #4ade80; }
.hero-stat-label {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 4px;
}

/* ===== 总览卡片 ===== */
.overview-card {
  background: #1c1f23;
  border: 1px solid #2c3035;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.2s;
}
.overview-card.expanded { border-color: #8b5cf6; }
.overview-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}
.overview-head:hover { background: #202328; }
.overview-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #e5e7eb;
}
.ov-icon { font-size: 16px; }
.overview-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #6b7280;
}
.toggle-arrow { font-size: 10px; }

/* 快速统计栏 */
.overview-quick-stats {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 0 16px 12px;
  flex-wrap: wrap;
}
.qs-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.qs-label {
  font-size: 12px;
  color: #6b7280;
}
.qs-value {
  font-size: 14px;
  font-weight: 600;
  color: #e5e7eb;
}
.qs-value.confirmed { color: #4ade80; }
.qs-value.draft { color: #fbbf24; }
.qs-target {
  font-size: 12px;
  font-weight: 400;
  color: #6b7280;
  margin-left: 2px;
}
.qs-progress {
  flex: 1;
  min-width: 200px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.qs-bar {
  flex: 1;
  height: 6px;
  background: #2c3035;
  border-radius: 3px;
  overflow: hidden;
}
.qs-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #8b5cf6, #4ade80);
  border-radius: 3px;
  transition: width 0.3s;
}
.qs-pct {
  font-size: 12px;
  font-weight: 600;
  color: #4ade80;
  min-width: 36px;
  text-align: right;
}

.overview-body {
  padding: 0 16px 16px;
  border-top: 1px solid #2c3035;
  padding-top: 14px;
}
.overview-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}
.ov-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ov-field.ov-full { margin-bottom: 12px; }
.ov-label {
  font-size: 12px;
  color: #9ca3af;
  font-weight: 500;
}
.ov-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}

/* 各卷概览 */
.volumes-overview {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #2c3035;
}
.vo-title {
  font-size: 14px;
  font-weight: 600;
  color: #e5e7eb;
  margin-bottom: 12px;
}
.vo-empty {
  text-align: center;
  padding: 30px 20px;
  color: #6b7280;
  font-size: 13px;
  background: #1a1d21;
  border-radius: 8px;
  border: 1px dashed #374151;
}
.vo-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}
.vo-card {
  background: #1a1d21;
  border: 1px solid #2c3035;
  border-radius: 8px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.2s;
}
.vo-card:hover {
  border-color: #8b5cf6;
  background: #1e1b4b;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.15);
}
.vo-card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.vo-vol-no {
  font-size: 12px;
  font-weight: 600;
  color: #a78bfa;
  background: rgba(139, 92, 246, 0.15);
  padding: 2px 8px;
  border-radius: 4px;
}
.vo-card-title {
  font-size: 15px;
  font-weight: 600;
  color: #f3f4f6;
  margin-bottom: 6px;
}
.vo-card-desc {
  font-size: 12px;
  color: #9ca3af;
  line-height: 1.5;
  margin-bottom: 10px;
  min-height: 36px;
}
.vo-card-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid #2c3035;
}
.vo-has-ai {
  color: #4ade80;
}
.vo-chapters {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.vo-chapter-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  font-size: 12px;
  border-radius: 4px;
  transition: background 0.15s;
}
.vo-chapter-item:hover {
  background: #2c3035;
}
.vo-ch-no {
  color: #6b7280;
  flex-shrink: 0;
  min-width: 50px;
}
.vo-ch-title {
  color: #d1d5db;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.vo-ch-more {
  font-size: 11px;
  color: #6b7280;
  text-align: center;
  padding: 4px;
  font-style: italic;
}

/* ===== 工作台 ===== */
.workbench {
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 12px;
  flex: 1;
  min-height: 0;
}

/* ===== 树面板 ===== */
.tree-panel {
  background: #1c1f23;
  border: 1px solid #2c3035;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.panel-tools {
  padding: 12px;
  border-bottom: 1px solid #2c3035;
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex-shrink: 0;
}
.tool-btns {
  display: flex;
  gap: 8px;
}
.tree-scroll { flex: 1; min-height: 0; }
.tree-inner { height: 100%; }

.outline-tree { padding: 10px; }

.tree-node {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 6px;
  border: 1px solid #2c3035;
  background: #1a1d21;
  transition: all 0.15s;
}
.tree-node:hover {
  background: #202429;
  border-color: #3a3f46;
}
.tree-node.active {
  background: #1e1b4b;
  border-color: #8b5cf6;
  box-shadow: 0 2px 8px rgba(139, 92, 246, 0.15);
}
.tree-node.search-match {
  border-color: #f59e0b;
  background: #1c1917;
}
/* 拖拽样式 */
.tree-node.dragging {
  opacity: 0.4;
  transform: scale(0.98);
}
.tree-node.drag-over-before {
  border-top: 2px solid #8b5cf6 !important;
  margin-top: -1px;
}
.tree-node.drag-over-after {
  border-bottom: 2px solid #8b5cf6 !important;
  margin-bottom: -1px;
}

/* 搜索高亮 */
:deep(.hl) {
  background: #fbbf24;
  color: #1c1917;
  padding: 0 2px;
  border-radius: 2px;
  font-weight: 600;
}

.volume-node {
  background: #1f2335;
  border-color: #374151;
}

.volume-arrow {
  font-size: 10px;
  color: #6b7280;
  padding-top: 4px;
  flex-shrink: 0;
  width: 16px;
  text-align: center;
}

.node-icon { font-size: 18px; flex-shrink: 0; padding-top: 1px; }
.vol-icon { font-size: 20px; }

.node-content { flex: 1; min-width: 0; }
.node-title-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 4px;
}
.node-title {
  font-size: 13px;
  font-weight: 600;
  color: #f3f4f6;
  line-height: 1.4;
}
.node-meta {
  font-size: 11px;
  color: #6b7280;
  margin-bottom: 4px;
}
.node-desc {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.chapter-group {
  padding-left: 28px;
  margin-bottom: 6px;
}
.chapter-node {
  padding: 8px 10px;
  position: relative;
}
.chapter-indicator {
  position: absolute;
  left: -18px;
  top: 50%;
  width: 14px;
  height: 1px;
  background: #374151;
}

.empty-chapters {
  font-size: 12px;
  color: #4b5563;
  padding: 8px 0 8px 28px;
  font-style: italic;
}

.ungrouped-section { margin-top: 12px; }
.ungrouped-title {
  font-size: 12px;
  color: #6b7280;
  padding: 4px 8px;
  margin-bottom: 6px;
}

.tree-loading, .tree-empty, .detail-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #6b7280;
  gap: 8px;
}
.empty-icon { font-size: 36px; margin-bottom: 4px; }
.empty-sub { font-size: 12px; color: #4b5563; }

/* ===== 详情面板 ===== */
.detail-panel {
  background: #1c1f23;
  border: 1px solid #2c3035;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid #2c3035;
  flex-shrink: 0;
  background: linear-gradient(180deg, #1a1d21 0%, #16181c 100%);
}
.detail-title h2 {
  font-size: 16px;
  font-weight: 700;
  color: #f3f4f6;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}
.dirty-dot { color: #f59e0b; font-size: 10px; }
.detail-actions { display: flex; gap: 8px; }

.form-scroll { flex: 1; min-height: 0; padding: 20px; }
.form-section {
  margin-bottom: 24px;
  background: #1a1d21;
  border: 1px solid #2c3035;
  border-radius: 10px;
  padding: 16px;
}
.section-title {
  font-size: 14px;
  font-weight: 700;
  color: #e5e7eb;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid #2c3035;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.form-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.form-grid-3 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 14px;
}

/* 卷详情中的章节列表 */
.volume-chapters-section {
  margin-bottom: 0;
}
.volume-chapters-section .section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.section-actions {
  display: flex;
  gap: 6px;
}
.volume-chapters-empty {
  text-align: center;
  padding: 30px 20px;
  color: #6b7280;
  font-size: 13px;
  background: #1a1d21;
  border-radius: 8px;
  border: 1px dashed #374151;
}
.chapter-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.chapter-list-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: #1a1d21;
  border: 1px solid #2c3035;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}
.chapter-list-item:hover {
  background: #202429;
  border-color: #3a3f46;
}
.chapter-list-item.active {
  background: #1e1b4b;
  border-color: #8b5cf6;
}
.cli-no {
  font-size: 12px;
  color: #6b7280;
  flex-shrink: 0;
  min-width: 50px;
}
.cli-title {
  flex: 1;
  font-size: 13px;
  color: #e5e7eb;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cli-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.cli-has-detail {
  font-size: 12px;
  cursor: help;
}

/* 章节进度条 */
.chapter-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.cp-bar {
  flex: 1;
  height: 6px;
  background: #2c3035;
  border-radius: 3px;
  overflow: hidden;
}
.cp-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #8b5cf6, #4ade80);
  border-radius: 3px;
  transition: width 0.3s;
}
.cp-text {
  font-size: 12px;
  font-weight: 600;
  color: #4ade80;
  min-width: 36px;
  text-align: right;
}

/* 批量创建面板 */
.batch-create-panel {
  background: #1a1d21;
  border: 1px solid #374151;
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 14px;
}
.bc-title {
  font-size: 13px;
  font-weight: 600;
  color: #e5e7eb;
  margin-bottom: 10px;
}
.bc-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 8px;
}
.bc-tip {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 10px;
}
.bc-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

/* ===== 响应式 ===== */
@media (max-width: 1200px) {
  .workbench { grid-template-columns: 300px 1fr; }
  .form-grid-3 { grid-template-columns: 1fr 1fr; }
  .overview-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 900px) {
  .workbench { grid-template-columns: 1fr; }
  .detail-panel { display: none; }
  .form-grid-2, .form-grid-3 { grid-template-columns: 1fr; }
}
</style>
