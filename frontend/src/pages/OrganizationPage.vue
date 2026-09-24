<template>
  <div class="page org-page">
    <!-- 页头 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <span class="title-icon">🏛️</span>
          势力管理台
        </h1>
        <p class="page-subtitle">
          管理组织结构、层级体系、成员与阵营关系
        </p>
      </div>
      <div class="header-right">
        <div class="header-stats">
          <div class="stat">
            <span class="stat-num">{{ totalCount }}</span>
            <span class="stat-label">组织总数</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num">{{ activeCount }}</span>
            <span class="stat-label">活跃中</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num">{{ avgPower }}</span>
            <span class="stat-label">平均实力</span>
          </div>
        </div>
        <n-button type="primary" @click="startCreate">
          <template #icon>＋</template>
          新增势力
        </n-button>
      </div>
    </div>

    <!-- 主体：三栏布局 -->
    <div class="workbench">
      <!-- 左侧：组织树 -->
      <aside class="list-panel">
        <div class="panel-tools">
          <n-input v-model:value="keyword" clearable placeholder="搜索组织...">
            <template #prefix>🔍</template>
          </n-input>
          <n-select
            v-model:value="statusFilter"
            clearable
            :options="orgStatusOptions"
            placeholder="状态筛选"
            style="width: 110px"
          />
        </div>

        <div class="tree-toolbar">
          <n-button
            text
            size="tiny"
            @click="toggleAllOrganizations"
          >
            {{ allOrganizationsExpanded ? '全部折叠' : '全部展开' }}
          </n-button>
          <div class="toolbar-spacer"></div>
          <n-button v-if="editingId" text size="tiny" type="primary" @click="startCreateChild">
            + 子组织
          </n-button>
        </div>

        <n-scrollbar class="list-scroll">
          <div v-if="loading" class="list-loading">
            <n-spin size="small" />
            <span>加载中...</span>
          </div>

          <div v-else-if="flatTreeData.length === 0" class="list-empty">
            <div class="empty-icon">🏛️</div>
            <p>还没有组织</p>
            <p class="empty-sub">点击右上角「新增势力」开始创建</p>
          </div>

          <div v-else class="org-tree">
            <div
              v-for="node in flatTreeData"
              :key="node.data.id"
              class="org-tree-item"
              :class="{ active: editingId === node.data.id }"
              :style="{ paddingLeft: `${node.level * 16 + 10}px` }"
              @click="selectOrganization(node.data)"
            >
              <span
                class="tree-expand-icon"
                :class="{ expanded: expandedIds.has(node.data.id), hidden: !node.hasChildren }"
                @click.stop="toggleExpand(node.data.id)"
              >
                {{ expandedIds.has(node.data.id) ? '▾' : '▸' }}
              </span>
              <span class="tree-org-icon">🏛️</span>
              <div class="tree-org-info">
                <div class="tree-org-name">{{ node.data.name }}</div>
                <div class="tree-org-meta">
                  <span
                    class="tree-status-dot"
                    :style="{ background: statusColorMap[node.data.status] || '#6b7280' }"
                  ></span>
                  <span class="tree-org-type">{{ node.data.org_type || '类型未定' }}</span>
                </div>
              </div>
              <div class="tree-power-bar">
                <div class="tree-power-fill" :style="{ width: `${node.data.power_level * 10}%` }"></div>
              </div>
            </div>
          </div>
        </n-scrollbar>
      </aside>

      <!-- 中间：详情编辑 -->
      <section class="detail-panel">
        <div class="detail-header">
          <div class="detail-title">
            <h2>
              {{ editingId ? '势力详情编辑' : '新势力档案' }}
              <span v-if="isDirty" class="dirty-dot" title="有未保存的修改">●</span>
            </h2>
            <span class="detail-sub">
              <template v-if="editingId">ID {{ editingId }}</template>
              <template v-else>等待保存</template>
              <template v-if="form.parent_id"> · 上级：{{ getParentName() }}</template>
            </span>
          </div>
          <div class="detail-actions">
            <n-button v-if="editingId" type="error" text @click="openDeleteConfirm">🗑️ 删除</n-button>
            <n-button @click="resetCurrent">↺ 重置</n-button>
            <n-button type="primary" @click="save">💾 保存</n-button>
          </div>
        </div>

        <div v-if="!editingId && !isCreating" class="detail-empty">
          <div class="empty-icon">✏️</div>
          <p>从左侧选择一个组织进行编辑</p>
          <p class="empty-sub">或点击右上角新增</p>
        </div>

        <n-scrollbar v-else class="form-scroll">
          <n-form class="detail-form" label-placement="top">
            <!-- 基本信息 -->
            <div class="form-section">
              <div class="section-title">
                基本信息
                <span class="section-hint">组织的身份与定位</span>
              </div>
              <div class="form-grid-3">
                <n-form-item label="组织名称">
                  <n-input v-model:value="form.name" size="large" />
                </n-form-item>
                <n-form-item label="组织类型">
                  <n-select
                    v-model:value="form.org_type"
                    :options="orgTypeOptions"
                    placeholder="选择组织类型"
                    filterable
                    clearable
                    @update:value="onOrgTypeChange"
                  />
                </n-form-item>
                <n-form-item label="状态">
                  <n-select v-model:value="form.status" :options="orgStatusOptions" placeholder="选择组织状态" clearable />
                </n-form-item>
              </div>
              <div class="form-grid-2">
                <n-form-item label="上级组织">
                  <n-select
                    v-model:value="form.parent_id"
                    :options="parentOrgOptions"
                    placeholder="无（顶级组织）"
                    filterable
                    clearable
                  />
                </n-form-item>
                <n-form-item label="地点 / 势力范围">
                  <TagSelectField
                    v-model="form.location"
                    :options="locationOptions"
                    placeholder="选择或输入地点..."
                  />
                </n-form-item>
              </div>
              <div class="form-section-sub">
                <div class="sub-label">
                  <span>宗旨 / 口号</span>
                </div>
                <SingleSelectField
                  v-model:value="form.slogan"
                  :options="sloganOptions"
                  :keep-custom-options="false"
                  placeholder="选择或输入宗旨口号..."
                  filterable
                  allow-create
                />
              </div>
              <div class="form-section-sub">
                <div class="sub-label">
                  <span>背景描述</span>
                  <n-select
                    :value="null"
                    :options="backgroundTemplates"
                    placeholder="📝 选择背景模板..."
                    filterable
                    size="small"
                    style="width: 180px"
                    @update:value="applyBackgroundTemplate"
                  />
                </div>
                <n-input v-model:value="form.description" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" />
              </div>
            </div>

            <!-- 势力属性 -->
            <div class="form-section">
              <div class="section-title">
                势力属性
                <span class="section-hint">组织的硬实力指标</span>
              </div>
              <div class="power-sliders">
                <div class="slider-row">
                  <div class="slider-label">
                    <span>组织层级</span>
                    <strong>{{ form.level }}/10</strong>
                  </div>
                  <n-slider v-model:value="form.level" :min="1" :max="10" :step="1" />
                </div>
                <div class="slider-row">
                  <div class="slider-label">
                    <span>实力等级</span>
                    <strong>{{ form.power_level }}/10</strong>
                  </div>
                  <n-slider v-model:value="form.power_level" :min="1" :max="10" :step="1" />
                </div>
                <div class="slider-row">
                  <div class="slider-label">
                    <span>成员总数</span>
                    <strong>{{ form.member_count }} 人</strong>
                  </div>
                  <n-input-number v-model:value="form.member_count" :min="0" />
                </div>
              </div>
            </div>

            <!-- 层级体系 -->
            <div class="form-section">
              <div class="section-title">
                层级体系
                <span class="section-hint">各体系独立保存，修改只影响当前组织</span>
              </div>
              <div class="hierarchy-system-row">
                <n-form-item label="体系类型" style="margin-bottom: 0; flex: 0 0 200px">
                  <n-select
                    v-model:value="form.hierarchy_system"
                    :options="hierarchySystemOptions"
                    placeholder="选择层级体系"
                    @update:value="onHierarchySystemChange"
                  />
                </n-form-item>
                <n-form-item
                  v-if="form.hierarchy_system === 'custom'"
                  label="套用默认模板"
                  style="margin-bottom: 0; flex: 0 1 260px; margin-left: 12px"
                >
                  <n-select
                    v-model:value="customTemplateSource"
                    :options="customHierarchyTemplateOptions"
                    placeholder="选择模板作为起点"
                    clearable
                    filterable
                    @update:value="applyCustomHierarchyTemplate"
                  />
                </n-form-item>
                <n-button
                  v-if="form.hierarchy_system !== 'none'"
                  type="primary"
                  ghost
                  size="small"
                  @click="addHierarchyLevel"
                  style="margin-left: 12px"
                >
                  + 新增层级
                </n-button>
              </div>
              <div class="hierarchy-level-list">
                <div
                  v-for="(level, index) in displayHierarchyLevels"
                  :key="index"
                  class="hierarchy-level-item"
                  :class="{
                    'is-none': level._isNone,
                    'is-dragging': dragIndex === index
                  }"
                  :draggable="!level._isNone"
                  @dragstart="onDragStart(index, $event)"
                  @dragover.prevent="onDragOver(index, $event)"
                  @drop="onDrop(index, $event)"
                  @dragend="onDragEnd"
                >
                  <span v-if="level._isNone" class="level-badge level-none-badge">—</span>
                  <span v-else class="level-badge">L{{ level.level }}</span>
                  <n-input
                    v-if="!level._isNone"
                    :value="level.name"
                    @update:value="(val: string) => updateLevelName(index, val)"
                    placeholder="层级名称"
                    class="level-name-input"
                  />
                  <span v-else class="level-none-text">无（重置/无职位）</span>
                  <div class="level-actions">
                    <template v-if="!level._isNone">
                      <span v-if="form.hierarchy_system !== 'none'" class="drag-handle" title="拖动排序">⋮⋮</span>
                      <n-button text type="error" size="small" @click="removeHierarchyLevel(index)">
                        删除
                      </n-button>
                    </template>
                    <span v-else class="level-action-hint">不可编辑</span>
                  </div>
                </div>
              </div>
              <div v-if="form.hierarchy_system !== 'none' && displayHierarchyLevels.length <= 1" class="hierarchy-empty">
                暂无层级，点击上方「新增层级」添加
              </div>
            </div>

            <!-- 内部与资源 -->
            <div class="form-section">
              <div class="section-title">
                内部与资源
                <span class="section-hint">组织架构与核心资源</span>
              </div>
              <div class="form-grid-2">
                <n-form-item label="核心资源">
                  <TagSelectField
                    v-model="form.resources"
                    :options="orgResourceOptions"
                    placeholder="选择或输入核心资源..."
                  />
                </n-form-item>
                <n-form-item label="核心成员">
                  <TagSelectField
                    v-model="form.core_members"
                    :options="characterNameOptions"
                    placeholder="选择或输入核心成员..."
                  />
                </n-form-item>
              </div>
              <div class="form-section-sub">
                <div class="sub-label">
                  <span>组织目标</span>
                  <n-select
                    :value="null"
                    :options="goalTemplates"
                    placeholder="🎯 选择目标模板..."
                    filterable
                    size="small"
                    style="width: 180px"
                    @update:value="applyGoalTemplate"
                  />
                </div>
                <n-input v-model:value="form.goal" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" />
              </div>
            </div>

            <!-- 时间维度 -->
            <div class="form-section">
              <div class="section-title">
                时间维度
                <span class="section-hint">组织活跃的章节范围</span>
              </div>
              <div class="form-grid-2">
                <n-form-item label="主效起始章节">
                  <n-input-number v-model:value="form.active_from_chapter" :min="0" placeholder="组织主要活跃的起始章节" clearable style="width: 100%" />
                </n-form-item>
                <n-form-item label="覆灭/解散章节">
                  <n-input-number v-model:value="form.disbanded_chapter" :min="0" placeholder="可选，不填则一直有效" clearable style="width: 100%" />
                </n-form-item>
              </div>
            </div>

            <!-- 隐藏设定 -->
            <div class="form-section">
              <div class="section-title">
                隐藏设定
                <span class="section-hint">仅作者可见的暗线</span>
              </div>
              <div class="form-section-sub">
                <div class="sub-label">
                  <span>暗线模板</span>
                  <n-select
                    :value="null"
                    :options="secretTemplates"
                    placeholder="🗝️ 选择暗线模板..."
                    filterable
                    size="small"
                    style="width: 180px"
                    @update:value="appendSecretTemplate"
                  />
                </div>
              </div>
              <n-input
                v-model:value="form.hidden_secrets"
                type="textarea"
                :autosize="{ minRows: 4, maxRows: 8 }"
                placeholder="组织的秘密、暗线、真实目的、不为人知的内幕..."
              />
            </div>
          </n-form>
        </n-scrollbar>
      </section>

      <!-- 右侧：成员与关系 -->
      <aside class="side-panel">
        <!-- 组织成员 -->
        <div class="insight-card primary-card">
          <div class="card-header">
            <span class="card-icon">👥</span>
            <span class="card-title">组织成员</span>
            <span class="card-badge">{{ orgMembers.length }}</span>
          </div>
          <div v-if="!editingId && !isCreating" class="card-empty">
            选择组织后查看成员
          </div>
          <div v-else-if="orgMembers.length === 0" class="card-empty">
            暂无成员，在人物卡片中添加组织关系
          </div>
          <div v-else class="member-list">
            <div
              v-for="member in orgMembers"
              :key="member.id"
              class="member-item"
            >
              <div class="member-avatar">{{ member.name.charAt(0) }}</div>
              <div class="member-info">
                <div class="member-name">{{ member.name }}</div>
                <div class="member-position">
                  <n-tag size="tiny" :type="positionTagType(member.position)">
                    {{ member.position || '无职位' }}
                  </n-tag>
                </div>
              </div>
              <div class="member-loyalty">
                <div class="loyalty-bar">
                  <div class="loyalty-fill" :style="{ width: `${member.loyalty * 10}%` }"></div>
                </div>
                <span class="loyalty-num">{{ member.loyalty }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 势力雷达 -->
        <div class="insight-card">
          <div class="card-header">
            <span class="card-icon">📊</span>
            <span class="card-title">势力雷达</span>
          </div>
          <div class="radar-list">
            <div class="radar-row">
              <span class="radar-label">组织层级</span>
              <div class="radar-bar">
                <div class="radar-fill" :style="{ width: `${form.level * 10}%` }"></div>
              </div>
              <span class="radar-value">{{ form.level }}/10</span>
            </div>
            <div class="radar-row">
              <span class="radar-label">实力等级</span>
              <div class="radar-bar">
                <div class="radar-fill power" :style="{ width: `${form.power_level * 10}%` }"></div>
              </div>
              <span class="radar-value">{{ form.power_level }}/10</span>
            </div>
            <div class="radar-row">
              <span class="radar-label">成员规模</span>
              <div class="radar-bar">
                <div class="radar-fill members" :style="{ width: `${Math.min(form.member_count / 100, 100)}%` }"></div>
              </div>
              <span class="radar-value">{{ form.member_count }}</span>
            </div>
          </div>
          <div class="risk-level">
            <span class="risk-label">风险等级</span>
            <n-tag :type="riskTagType" size="small">{{ riskLevel }}</n-tag>
          </div>
        </div>

        <!-- 关系管理 -->
        <div class="insight-card">
          <div class="card-header">
            <span class="card-icon">🔗</span>
            <span class="card-title">阵营关系</span>
          </div>
          <div v-if="!editingId" class="relation-empty-tip">保存组织后即可添加关系</div>
          <template v-else>
            <div v-if="organizationRelations.length" class="organization-relation-list">
              <div v-for="relation in organizationRelations" :key="relation.id" class="organization-relation-item">
                <div class="organization-relation-heading">
                  <n-tag :type="relation.relation_type === 'alliance' ? 'success' : 'error'" size="small">
                    {{ relation.relation_type === 'alliance' ? '盟友' : '敌对' }}
                  </n-tag>
                  <strong>{{ relation.target_org_name }}</strong>
                  <div class="organization-relation-actions">
                    <n-button text size="tiny" @click="editOrganizationRelation(relation)">编辑</n-button>
                    <n-button text size="tiny" type="error" @click="removeOrganizationRelation(relation)">移除</n-button>
                  </div>
                </div>
                <div v-if="relation.description" class="organization-relation-description">{{ relation.description }}</div>
                <div v-if="relation.effective_from_chapter || relation.expires_at_chapter" class="organization-relation-range">
                  {{ relation.effective_from_chapter ? `第 ${relation.effective_from_chapter} 章起` : '生效章节未设' }}
                  ·
                  {{ relation.expires_at_chapter ? `第 ${relation.expires_at_chapter} 章止` : '持续有效' }}
                </div>
              </div>
            </div>
            <div v-else class="relation-empty-tip">暂未记录同盟或敌对组织</div>

            <div v-if="legacyRelationText" class="legacy-relation-note">
              尚未匹配到组织卡片的旧关系文本：{{ legacyRelationText }}
            </div>

            <div class="organization-relation-editor">
              <n-select
                v-model:value="relationDraft.target_org_id"
                :options="relationTargetOptions"
                filterable
                clearable
                size="small"
                placeholder="选择关联组织"
              />
              <n-select
                v-model:value="relationDraft.relation_type"
                :options="organizationRelationTypeOptions"
                size="small"
              />
              <n-input
                v-model:value="relationDraft.description"
                size="small"
                type="textarea"
                :autosize="{ minRows: 2, maxRows: 4 }"
                placeholder="关系来由或当前状态（可选）"
              />
              <div class="organization-relation-chapters">
                <n-input-number v-model:value="relationDraft.effective_from_chapter" :min="1" clearable size="small" placeholder="生效章" />
                <span>至</span>
                <n-input-number v-model:value="relationDraft.expires_at_chapter" :min="1" clearable size="small" placeholder="失效章" />
              </div>
              <div class="organization-relation-editor-actions">
                <n-button v-if="editingRelationId" size="small" @click="resetOrganizationRelationDraft">取消编辑</n-button>
                <n-button
                  type="primary"
                  size="small"
                  :loading="relationSaving"
                  :disabled="!relationDraft.target_org_id"
                  @click="saveOrganizationRelationDraft"
                >
                  {{ editingRelationId ? '保存关系' : '添加关系' }}
                </n-button>
              </div>
            </div>
          </template>
        </div>

        <!-- 组织变更历史 -->
        <div class="insight-card">
          <div class="card-header">
            <span class="card-icon">🕘</span>
            <span class="card-title">档案变更记录</span>
            <span class="history-count">{{ organizationHistory.length }}</span>
          </div>
          <div v-if="historyLoading" class="relation-empty-tip">正在读取变更记录…</div>
          <div v-else-if="!organizationHistory.length" class="relation-empty-tip">
            保存组织资料或确认章节变化后，记录会显示在这里
          </div>
          <div v-else class="organization-history-list">
            <article v-for="record in organizationHistory" :key="record.id" class="organization-history-item">
              <div class="organization-history-heading">
                <n-tag :type="record.source_type === 'chapter_analysis' ? 'info' : 'default'" size="tiny">
                  {{ record.source_type === 'chapter_analysis' ? '章节分析' : '手动编辑' }}
                </n-tag>
                <strong>{{ historyRecordTitle(record) }}</strong>
              </div>
              <div class="organization-history-meta">
                <span v-if="record.chapter_no">第 {{ record.chapter_no }} 章{{ record.chapter_title ? ` · ${record.chapter_title}` : '' }}</span>
                <span v-else>未关联章节</span>
                <span>{{ formatHistoryTime(record.created_at) }}</span>
              </div>
              <div v-if="record.operation !== 'create' && record.changed_fields.length" class="organization-history-fields">
                {{ record.changed_fields.map(historyFieldLabel).join('、') }}
              </div>
              <details class="organization-history-details">
                <summary>查看前后变化</summary>
                <div v-for="change in getHistoryFieldChanges(record)" :key="change.field" class="history-field-change">
                  <strong>{{ change.label }}</strong>
                  <div class="history-value-row"><span>之前</span><p>{{ change.before }}</p></div>
                  <div class="history-value-row"><span>之后</span><p>{{ change.after }}</p></div>
                </div>
                <div v-if="record.rationale" class="history-rationale">变化说明：{{ record.rationale }}</div>
                <div v-if="record.evidence" class="history-rationale">章节依据：{{ record.evidence }}</div>
              </details>
            </article>
          </div>
        </div>

        <!-- 剧情影响 -->
        <div class="insight-card">
          <div class="card-header">
            <span class="card-icon">💥</span>
            <span class="card-title">剧情影响</span>
          </div>
          <n-form label-placement="top" size="small">
            <n-form-item label="剧情影响">
              <n-input v-model:value="form.impact" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" />
            </n-form-item>
            <n-form-item label="风险提示">
              <n-input v-model:value="form.risk_notes" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" />
            </n-form-item>
          </n-form>
        </div>
      </aside>
    </div>
  </div>

  <!-- 删除确认弹窗 -->
  <n-modal v-model:show="showDeleteConfirm" preset="dialog" title="确认删除" :positive-text="'强制删除'" :negative-text="'取消'" :positive-button-props="{ type: 'error' }" @positive-click="handleForceDelete" @negative-click="showDeleteConfirm = false">
    <div v-if="orgMembers.length > 0">
      <div style="font-weight: 600; margin-bottom: 8px; color: #d03050">
        ⚠️ 该组织被 {{ orgMembers.length }} 个角色使用
      </div>
      <div style="font-size: 13px; color: #999; margin-bottom: 8px">
        删除后，这些角色的组织势力关系将被清除。
      </div>
      <div style="font-size: 12px; color: #bbb">
        涉及角色：{{ orgMembers.slice(0, 5).map(m => m.name).join('、') }}{{ orgMembers.length > 5 ? ' 等' : '' }}
      </div>
    </div>
    <div v-else>
      确认删除「{{ deletingOrgName }}」？子组织将变为顶级组织。
    </div>
  </n-modal>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
import {
  createResource,
  deleteOrganizationRelation,
  deleteResource,
  listOrganizationHistory,
  listOrganizationRelations,
  listResource,
  saveOrganizationRelation as persistOrganizationRelation,
  updateResource
} from '@/api/resources'
import { useProjectStore } from '@/stores/project'
import { useDictStore } from '@/stores/dict'
import { useOrganizationStore } from '@/stores/organization'
import { useCharacterStore } from '@/stores/character'
import { useProjectDataLoader } from '@/composables/useProjectDataLoader'
import { useDirtySnapshot } from '@/composables/useDirtySnapshot'
import { notify } from '@/utils/notify'
import TagSelectField from '@/components/TagSelectField.vue'
import SingleSelectField from '@/components/SingleSelectField.vue'
import type { SelectOption } from 'naive-ui'
import type {
  CharacterItem,
  OrganizationHistory,
  OrganizationItem,
  OrganizationRelation,
  CharacterOrgRelation
} from '@/types/domain'

const projectStore = useProjectStore()
const dictStore = useDictStore()
const orgStore = useOrganizationStore()
const charStore = useCharacterStore()

const organizations = ref<OrganizationItem[]>([])
const characters = computed(() => charStore.characters)
const keyword = ref('')
const statusFilter = ref<string | null>(null)
const editingId = ref<number | null>(null)
const isCreating = ref(false)
const showDeleteConfirm = ref(false)
const deletingOrgName = ref('')
const loading = ref(false)
const expandedIds = ref<Set<number>>(new Set())
const organizationRelations = ref<OrganizationRelation[]>([])
const organizationHistory = ref<OrganizationHistory[]>([])
const historyLoading = ref(false)
const editingRelationId = ref<number | null>(null)
const relationSaving = ref(false)
const relationDraft = reactive({
  target_org_id: null as number | null,
  relation_type: 'alliance' as OrganizationRelation['relation_type'],
  description: '',
  effective_from_chapter: null as number | null,
  expires_at_chapter: null as number | null
})

const organizationRelationTypeOptions = [
  { label: '盟友', value: 'alliance' },
  { label: '敌对', value: 'hostility' }
]
const relationTargetOptions = computed(() => organizations.value
  .filter((item) => item.id !== editingId.value)
  .map((item) => ({ label: item.name, value: item.id })))

// 只统计存在下级组织的节点，避免叶子节点影响全部展开状态。
const expandableOrganizationIds = computed(() => {
  const parentIds = new Set(
    organizations.value
      .map((item) => item.parent_id)
      .filter((parentId): parentId is number => parentId !== null && parentId !== undefined)
  )
  return organizations.value
    .filter((item) => parentIds.has(item.id))
    .map((item) => item.id)
})
const hasExpandableOrganizations = computed(() => expandableOrganizationIds.value.length > 0)
const allOrganizationsExpanded = computed(() =>
  hasExpandableOrganizations.value &&
  expandableOrganizationIds.value.every((id) => expandedIds.value.has(id))
)

const form = reactive({
  name: '新组织',
  parent_id: null as number | null,
  org_type: '',
  location: '',
  slogan: '',
  description: '',
  hierarchy: '',
  resources: '',
  goal: '',
  level: 1,
  power_level: 5,
  member_count: 0,
  status: '',
  core_members: '',
  allies: '',
  enemies: '',
  impact: '',
  risk_notes: '',
  active_from_chapter: null as number | null,
  disbanded_chapter: null as number | null,
  hidden_secrets: '',
  hierarchy_system: 'none',
  hierarchy_levels: [] as HierarchyLevel[],
  hierarchy_templates: {} as Record<string, HierarchyLevel[]>
})

const legacyRelationText = computed(() => {
  // 只展示尚未映射到组织卡片的旧文本，防止迁移过的关系重复出现。
  const linkedNames = new Set(organizationRelations.value.map((item) => item.target_org_name.trim().toLocaleLowerCase()))
  const tokens = [...form.allies.split(/[、,，;；\n]+/), ...form.enemies.split(/[、,，;；\n]+/)]
    .map((item) => item.trim())
    .filter((item) => item && !linkedNames.has(item.toLocaleLowerCase()))
  return [...new Set(tokens)].join('、')
})

const { isDirty, markClean, confirmIfDirty } = useDirtySnapshot(form, '当前势力档案有未保存的修改，确定要离开吗？')

// ===== 字典：组织类型 =====
const orgTypeOptions = computed(() =>
  dictStore.items('org_type').map(item => ({ label: item.item_label, value: item.item_label }))
)

const orgStatusOptions = [
  { label: '隐世', value: '隐世' },
  { label: '扩张', value: '扩张' },
  { label: '鼎盛', value: '鼎盛' },
  { label: '衰落', value: '衰落' },
  { label: '覆灭', value: '覆灭' },
  { label: '蛰伏', value: '蛰伏' },
  { label: '转型中', value: '转型中' }
]

// ===== 层级体系配置 =====
interface HierarchyLevel {
  name: string
  level: number
}

const HIERARCHY_SYSTEMS: Record<string, { name: string; levels: HierarchyLevel[] }> = {
  none: { name: '无', levels: [] },
  // —— 修仙武侠类 ——
  sect: {
    name: '门派',
    levels: [
      { name: '盟主/掌门', level: 1 },
      { name: '副盟主/副掌门', level: 2 },
      { name: '长老', level: 3 },
      { name: '堂主/殿主', level: 4 },
      { name: '护法', level: 5 },
      { name: '执事', level: 6 },
      { name: '核心弟子', level: 7 },
      { name: '内门弟子', level: 8 },
      { name: '外门弟子', level: 9 },
      { name: '杂役', level: 10 }
    ]
  },
  clan: {
    name: '家族/世家',
    levels: [
      { name: '家主/族长', level: 1 },
      { name: '大长老', level: 2 },
      { name: '长老', level: 3 },
      { name: '嫡系子弟', level: 4 },
      { name: '旁系子弟', level: 5 },
      { name: '管家', level: 6 },
      { name: '仆役', level: 7 }
    ]
  },
  gang: {
    name: '帮派/帮会',
    levels: [
      { name: '帮主/龙头', level: 1 },
      { name: '副帮主/二把手', level: 2 },
      { name: '堂主/香主', level: 3 },
      { name: '护法', level: 4 },
      { name: '执事', level: 5 },
      { name: '核心成员', level: 6 },
      { name: '普通成员', level: 7 },
      { name: '外围成员', level: 8 }
    ]
  },
  // —— 官府军事类 ——
  official: {
    name: '官府/朝廷',
    levels: [
      { name: '皇帝/天子', level: 1 },
      { name: '宰相/首辅', level: 2 },
      { name: '六部尚书', level: 3 },
      { name: '侍郎', level: 4 },
      { name: '郎中', level: 5 },
      { name: '主事', level: 6 },
      { name: '地方总督/巡抚', level: 7 },
      { name: '知府', level: 8 },
      { name: '知县', level: 9 },
      { name: '差役', level: 10 }
    ]
  },
  army: {
    name: '军队',
    levels: [
      { name: '元帅/司令', level: 1 },
      { name: '将军', level: 2 },
      { name: '校官', level: 3 },
      { name: '尉官', level: 4 },
      { name: '士官长', level: 5 },
      { name: '上士', level: 6 },
      { name: '中士', level: 7 },
      { name: '下士', level: 8 },
      { name: '列兵', level: 9 }
    ]
  },
  secret_service: {
    name: '情报/特务机构',
    levels: [
      { name: '指挥使/局座', level: 1 },
      { name: '副使/副局长', level: 2 },
      { name: '行动处长', level: 3 },
      { name: '情报科长', level: 4 },
      { name: '高级特工', level: 5 },
      { name: '普通特工', level: 6 },
      { name: '线人/卧底', level: 7 },
      { name: '外围联络', level: 8 }
    ]
  },
  // —— 现代都市类 ——
  company: {
    name: '公司/企业',
    levels: [
      { name: '董事长', level: 1 },
      { name: 'CEO/总裁', level: 2 },
      { name: '副总裁', level: 3 },
      { name: '总监', level: 4 },
      { name: '经理', level: 5 },
      { name: '主管', level: 6 },
      { name: '高级员工', level: 7 },
      { name: '正式员工', level: 8 },
      { name: '实习生', level: 9 }
    ]
  },
  academy: {
    name: '学院/学校',
    levels: [
      { name: '院长', level: 1 },
      { name: '副院长', level: 2 },
      { name: '系主任', level: 3 },
      { name: '教授', level: 4 },
      { name: '副教授', level: 5 },
      { name: '讲师', level: 6 },
      { name: '助教', level: 7 },
      { name: '研究生', level: 8 },
      { name: '本科生', level: 9 }
    ]
  },
  mafia: {
    name: '黑帮/社团',
    levels: [
      { name: '老大/龙头', level: 1 },
      { name: '二把手/军师', level: 2 },
      { name: '堂主/大哥', level: 3 },
      { name: '二哥/干部', level: 4 },
      { name: '小弟/马仔', level: 5 },
      { name: '外围', level: 6 }
    ]
  },
  // —— 奇幻西方类 ——
  kingdom: {
    name: '王国/帝国',
    levels: [
      { name: '国王/皇帝', level: 1 },
      { name: '亲王/公爵', level: 2 },
      { name: '侯爵/伯爵', level: 3 },
      { name: '子爵/男爵', level: 4 },
      { name: '骑士', level: 5 },
      { name: '贵族侍从', level: 6 },
      { name: '平民/自由民', level: 7 },
      { name: '农奴', level: 8 }
    ]
  },
  knight_order: {
    name: '骑士团',
    levels: [
      { name: '大团长', level: 1 },
      { name: '副团长', level: 2 },
      { name: '圣骑士', level: 3 },
      { name: '正式骑士', level: 4 },
      { name: '见习骑士', level: 5 },
      { name: '侍从', level: 6 },
      { name: '团兵', level: 7 }
    ]
  },
  mage_guild: {
    name: '魔法公会',
    levels: [
      { name: '议长/大魔导师', level: 1 },
      { name: '长老/魔导师', level: 2 },
      { name: '大法师', level: 3 },
      { name: '魔法师', level: 4 },
      { name: '中级法师', level: 5 },
      { name: '初级法师', level: 6 },
      { name: '魔法学徒', level: 7 }
    ]
  },
  church: {
    name: '教会/教廷',
    levels: [
      { name: '教皇/教宗', level: 1 },
      { name: '枢机主教', level: 2 },
      { name: '大主教', level: 3 },
      { name: '主教', level: 4 },
      { name: '神父/司铎', level: 5 },
      { name: '执事', level: 6 },
      { name: '修道士/修女', level: 7 },
      { name: '信徒', level: 8 }
    ]
  },
  adventurer: {
    name: '冒险者公会',
    levels: [
      { name: '公会长', level: 1 },
      { name: '副会长', level: 2 },
      { name: 'S级冒险者', level: 3 },
      { name: 'A级冒险者', level: 4 },
      { name: 'B级冒险者', level: 5 },
      { name: 'C级冒险者', level: 6 },
      { name: 'D级冒险者', level: 7 },
      { name: '见习冒险者', level: 8 }
    ]
  },
  // —— 其他 ——
  tribe: {
    name: '部落/氏族',
    levels: [
      { name: '酋长/族长', level: 1 },
      { name: '大萨满/长老', level: 2 },
      { name: '萨满/战士长', level: 3 },
      { name: '勇士', level: 4 },
      { name: '族民', level: 5 },
      { name: '奴隶', level: 6 }
    ]
  },
  custom: { name: '自定义', levels: [] }
}

const hierarchySystemOptions = Object.entries(HIERARCHY_SYSTEMS).map(([key, val]) => ({
  label: val.name,
  value: key
}))
const customHierarchyTemplateOptions = Object.entries(HIERARCHY_SYSTEMS)
  .filter(([key, value]) => key !== 'none' && key !== 'custom' && value.levels.length > 0)
  .map(([key, value]) => ({ label: value.name, value: key }))
const customTemplateSource = ref<string | null>(null)

// ===== 组织树数据（扁平化） =====
interface FlatTreeNode {
  data: OrganizationItem
  level: number
  hasChildren: boolean
}

const flatTreeData = computed<FlatTreeNode[]>(() => {
  const text = keyword.value.trim().toLowerCase()
  const filtered = organizations.value.filter((item) => {
    const matchedText =
      !text ||
      [item.name, item.location, item.slogan, item.description, item.status, item.org_type]
        .join(' ')
        .toLowerCase()
        .includes(text)
    const matchedStatus = !statusFilter.value || item.status === statusFilter.value
    return matchedText && matchedStatus
  })

  // 构建 children map
  const childrenMap = new Map<number, OrganizationItem[]>()
  filtered.forEach((item) => {
    const pid = item.parent_id || 0
    if (!childrenMap.has(pid)) childrenMap.set(pid, [])
    childrenMap.get(pid)!.push(item)
  })

  // 按实力排序
  childrenMap.forEach((list) => {
    list.sort((a, b) => (b.power_level || 0) - (a.power_level || 0))
  })

  // 扁平化（DFS，根据 expandedIds 决定是否展开子节点）
  const result: FlatTreeNode[] = []
  function traverse(parentId: number, level: number) {
    const children = childrenMap.get(parentId) || []
    children.forEach((item) => {
      const hasChildren = (childrenMap.get(item.id) || []).length > 0
      result.push({ data: item, level, hasChildren })
      if (hasChildren && expandedIds.value.has(item.id)) {
        traverse(item.id, level + 1)
      }
    })
  }
  traverse(0, 0)
  return result
})

// 状态颜色映射
const statusColorMap: Record<string, string> = {
  '鼎盛': '#22c55e',
  '扩张': '#3b82f6',
  '蛰伏': '#6b7280',
  '衰落': '#f59e0b',
  '覆灭': '#ef4444',
  '隐世': '#6b7280',
  '转型中': '#f59e0b'
}

// ===== 可作为上级的组织（排除自己和子组织） =====
const parentOrgOptions = computed(() => {
  if (!editingId.value) {
    return organizations.value.map((o) => ({ label: o.name, value: o.id }))
  }
  // 收集所有子组织 ID（递归）
  const childIds = new Set<number>()
  function collectChildren(parentId: number) {
    organizations.value
      .filter((o) => o.parent_id === parentId)
      .forEach((o) => {
        childIds.add(o.id)
        collectChildren(o.id)
      })
  }
  collectChildren(editingId.value)
  return organizations.value
    .filter((o) => o.id !== editingId.value && !childIds.has(o.id))
    .map((o) => ({ label: o.name, value: o.id }))
})

// ===== 组织成员（从人物数据中反查） =====
interface OrgMember {
  id: number
  name: string
  position: string
  loyalty: number
}

const orgMembers = computed<OrgMember[]>(() => {
  if (!editingId.value) return []
  const result: OrgMember[] = []
  characters.value.forEach((char) => {
    let relations: CharacterOrgRelation[] = []
    try {
      if (char.org_relations && typeof char.org_relations === 'string') {
        relations = JSON.parse(char.org_relations)
      } else if (Array.isArray(char.org_relations)) {
        relations = char.org_relations as CharacterOrgRelation[]
      }
    } catch { /* ignore */ }
    const rel = relations.find((r) => Number(r.org_id) === editingId.value)
    if (rel) {
      result.push({
        id: char.id,
        name: char.name,
        position: rel.position || '',
        loyalty: rel.loyalty || 5
      })
    }
  })
  // 按忠诚度降序
  return result.sort((a, b) => b.loyalty - a.loyalty)
})

function positionTagType(position: string): 'default' | 'success' | 'info' | 'warning' | 'error' {
  if (!position) return 'default'
  // 高层职位用 success
  if (/(掌门|盟主|家主|族长|董事长|CEO|总裁|元帅|司令|老大|龙头|院长)/.test(position)) return 'success'
  if (/(长老|副|总监|将军|堂主|护法)/.test(position)) return 'warning'
  return 'info'
}

// ===== 统计 =====
const totalCount = computed(() => organizations.value.length)
const activeCount = computed(() => organizations.value.filter((o) => o.status && o.status !== '覆灭').length)
const avgPower = computed(() => {
  if (organizations.value.length === 0) return 0
  const total = organizations.value.reduce((sum, o) => sum + (o.power_level || 0), 0)
  return Math.round(total / organizations.value.length)
})

const riskLevel = computed(() => {
  if ((form.enemies || organizationRelations.value.some((item) => item.relation_type === 'hostility')) && form.power_level <= 4) return '高风险'
  if (!form.goal || !form.resources) return '资料不足'
  return '稳定'
})

const riskTagType = computed<'default' | 'success' | 'warning' | 'error' | 'info'>(() => {
  if (riskLevel.value === '高风险') return 'error'
  if (riskLevel.value === '资料不足') return 'warning'
  return 'success'
})

function statusTagType(status: string): 'default' | 'success' | 'info' | 'warning' | 'error' {
  const map: Record<string, 'default' | 'success' | 'info' | 'warning' | 'error'> = {
    '鼎盛': 'success',
    '扩张': 'info',
    '蛰伏': 'default',
    '衰落': 'warning',
    '覆灭': 'error',
    '隐世': 'default',
    '转型中': 'warning'
  }
  return map[status] || 'default'
}

// ===== 字典 & 选项 =====

/**
 * 从字典项 remark 中提取适用类型列表
 * remark 格式如："适用类型: sect,gang" 或多行文本首行是适用类型
 */
function extractApplicableTypes(remark: string | null | undefined): string[] {
  if (!remark) return []
  const match = remark.match(/适用类型[:：]\s*(.+)/)
  if (!match) return []
  return match[1].split(/[,，、\s]+/).map(s => s.trim()).filter(Boolean)
}

/** 获取当前组织类型的 value */
function getCurrentTypeValue(): string {
  const currentType = form.org_type
  if (!currentType) return ''
  const typeItem = dictStore.items('org_type').find(i => i.item_label === currentType)
  return typeItem?.item_value || currentType
}

/**
 * 按组织类型对字典选项分组
 * - 选了组织类型：显示「当前类型专属」+「通用」两组
 * - 没选类型：返回空数组（不展示字典，用户自由编辑）
 */
function getGroupedOptions(dictCode: string): SelectOption[] {
  const all = dictStore.items(dictCode)
  const typeValue = getCurrentTypeValue()
  const typeList = dictStore.items('org_type')

  // 没选类型时，不展示字典选项，用户自由编辑
  if (!typeValue) return []

  // 选了类型时，只显示匹配的 + 通用
  const matched: SelectOption[] = []
  const universal: SelectOption[] = []

  all.forEach(item => {
    const types = extractApplicableTypes(item.remark)
    const opt = { label: item.item_label, value: item.item_label }
    if (types.length === 0) {
      universal.push(opt)
    } else if (types.includes(typeValue)) {
      matched.push(opt)
    }
  })

  const typeLabel = typeList.find(t => t.item_value === typeValue)?.item_label || typeValue
  const result: SelectOption[] = []
  if (matched.length > 0) {
    result.push({
      type: 'group' as const,
      label: `${typeLabel}专属`,
      key: 'matched',
      children: matched
    } as any)
  }
  if (universal.length > 0) {
    result.push({
      type: 'group' as const,
      label: '通用',
      key: 'universal',
      children: universal
    } as any)
  }
  return result
}

// 地点/势力范围选项
const locationOptions = computed(() => getGroupedOptions('org_location'))

// 宗旨口号选项
const sloganOptions = computed(() => {
  const all = dictStore.items('org_slogan')
  const typeValue = getCurrentTypeValue()
  // 没选类型时不展示字典
  if (!typeValue) return []
  return all
    .filter(item => {
      const types = extractApplicableTypes(item.remark)
      return types.length === 0 || types.includes(typeValue)
    })
    .map(item => ({ label: item.item_label, value: item.item_label }))
})

// 核心资源选项
const orgResourceOptions = computed(() => getGroupedOptions('org_resource'))

// 背景描述模板
const backgroundTemplates = computed(() => {
  const all = dictStore.items('org_background')
  const typeValue = getCurrentTypeValue()
  // 没选类型时不展示模板
  if (!typeValue) return []
  return all
    .filter(item => {
      const types = extractApplicableTypes(item.remark)
      return types.length === 0 || types.includes(typeValue)
    })
    .map(item => ({
      label: item.item_label,
      value: item.item_label,
      content: item.remark ? item.remark.replace(/适用类型[:：].*\n?/, '').trim() : ''
    }))
})

// 组织目标模板
const goalTemplates = computed(() => {
  const all = dictStore.items('org_goal_template')
  const typeValue = getCurrentTypeValue()
  if (!typeValue) return []
  return all
    .filter(item => {
      const types = extractApplicableTypes(item.remark)
      return types.length === 0 || types.includes(typeValue)
    })
    .map(item => ({ label: item.item_label, value: item.item_label }))
})

// 隐藏设定模板
const secretTemplates = computed(() => {
  const all = dictStore.items('org_secret_template')
  const typeValue = getCurrentTypeValue()
  if (!typeValue) return []
  return all
    .filter(item => {
      const types = extractApplicableTypes(item.remark)
      return types.length === 0 || types.includes(typeValue)
    })
    .map(item => ({
      label: item.item_label,
      value: item.item_label,
      content: item.remark ? item.remark.replace(/适用类型[:：].*\n?/, '').trim() : ''
    }))
})

// ===== 组织类型切换联动 =====
function onOrgTypeChange(_newType: string | null) {
  // 切换组织类型时，只重置层级体系（因为体系与类型强关联）
  // 其他字段保留用户已编辑的内容，不清空
  // 通过统一切换逻辑先保存当前体系副本，避免类型切换时覆盖用户修改。
  onHierarchySystemChange('none')
}

const characterNameOptions = computed(() =>
  characters.value.map((c) => ({ label: c.name, value: c.name }))
)

// ===== 树节点操作 =====
function toggleExpand(id: number) {
  if (expandedIds.value.has(id)) {
    expandedIds.value.delete(id)
  } else {
    expandedIds.value.add(id)
  }
}

function expandAll() {
  expandableOrganizationIds.value.forEach((id) => expandedIds.value.add(id))
}

function collapseAll() {
  expandedIds.value.clear()
}

// 根据当前状态统一切换组织树的展开状态。
function toggleAllOrganizations() {
  if (!hasExpandableOrganizations.value) {
    notify.info('当前没有下级组织，添加子组织后即可展开或折叠')
    return
  }

  if (allOrganizationsExpanded.value) {
    collapseAll()
  } else {
    expandAll()
  }
}

function getParentName(): string {
  if (!form.parent_id) return ''
  const parent = organizations.value.find((o) => o.id === form.parent_id)
  return parent?.name || ''
}

// ===== 模板填充 =====
function applyBackgroundTemplate(label: string | null) {
  if (!label) return
  const template = backgroundTemplates.value.find(t => t.label === label)
  if (template && template.content) {
    form.description = template.content
  }
}

function applyGoalTemplate(label: string | null) {
  if (!label) return
  form.goal = label
}

function appendSecretTemplate(label: string | null) {
  if (!label) return
  const template = secretTemplates.value.find(t => t.label === label)
  if (template) {
    const content = template.content || template.label
    if (form.hidden_secrets && form.hidden_secrets.trim()) {
      form.hidden_secrets = form.hidden_secrets + '\n\n' + content
    } else {
      form.hidden_secrets = content
    }
  }
}

// ===== 层级体系操作 =====
// 记录当前正在编辑的体系，用于切换时先保存当前体系的组织级副本。
const activeHierarchySystem = ref('none')

// 拖拽状态
const dragIndex = ref<number | null>(null)

// 带「无」的展示层级列表（「无」始终在第一位，不可编辑）
interface DisplayHierarchyLevel extends HierarchyLevel {
  _isNone?: boolean
}

const displayHierarchyLevels = computed<DisplayHierarchyLevel[]>(() => {
  const noneItem: DisplayHierarchyLevel = { name: '无', level: 0, _isNone: true }
  // form.hierarchy_levels 是不含「无」的真实层级
  const realLevels: DisplayHierarchyLevel[] = form.hierarchy_levels.map(l => ({ ...l }))
  return [noneItem, ...realLevels]
})

function cloneHierarchyLevels(levels: HierarchyLevel[]): HierarchyLevel[] {
  // 拷贝每个层级对象，防止编辑组织副本时改动内置模板。
  return levels.map((level) => ({ ...level }))
}

function safeParseHierarchyTemplates(value: unknown): Record<string, HierarchyLevel[]> {
  // 兼容 API 返回对象、JSON 字符串和旧记录空值三种数据形态。
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .filter(([, levels]) => Array.isArray(levels))
        .map(([system, levels]) => [system, cloneHierarchyLevels(levels as HierarchyLevel[])])
    )
  }
  if (typeof value === 'string') {
    try {
      return safeParseHierarchyTemplates(JSON.parse(value))
    } catch {
      return {}
    }
  }
  return {}
}

// 切换体系前保存当前副本；再次切回时优先恢复组织自己的修改。
function onHierarchySystemChange(system: string | null) {
  const nextSystem = system || 'none'
  const previousSystem = activeHierarchySystem.value

  if (previousSystem !== 'none') {
    form.hierarchy_templates[previousSystem] = cloneHierarchyLevels(form.hierarchy_levels)
  }

  form.hierarchy_system = nextSystem
  activeHierarchySystem.value = nextSystem
  customTemplateSource.value = null

  if (nextSystem === 'none') {
    form.hierarchy_levels = []
    return
  }

  const savedLevels = form.hierarchy_templates[nextSystem]
  const defaultLevels = HIERARCHY_SYSTEMS[nextSystem]?.levels || []
  form.hierarchy_levels = cloneHierarchyLevels(savedLevels ?? defaultLevels)
}

// 自定义体系从内置模板复制一份，后续编辑只保存到当前组织的自定义副本。
function applyCustomHierarchyTemplate(system: string | null) {
  if (!system || form.hierarchy_system !== 'custom') return
  const template = HIERARCHY_SYSTEMS[system]
  if (!template) return

  form.hierarchy_levels = cloneHierarchyLevels(template.levels)
  syncActiveHierarchyProfile()
}

// 将当前编辑结果写入组织自己的体系映射，保存或切换时均可恢复。
function syncActiveHierarchyProfile() {
  if (form.hierarchy_system === 'none') return
  form.hierarchy_templates[form.hierarchy_system] = cloneHierarchyLevels(form.hierarchy_levels)
}

function addHierarchyLevel() {
  const nextLevel = form.hierarchy_levels.length > 0
    ? Math.max(...form.hierarchy_levels.map((l) => l.level)) + 1
    : 1
  form.hierarchy_levels.push({ name: '新层级', level: nextLevel })
  _reindexLevels()
  syncActiveHierarchyProfile()
}

function updateLevelName(displayIndex: number, name: string) {
  // displayIndex 是包含「无」的索引，真实索引 = displayIndex - 1
  const realIndex = displayIndex - 1
  if (realIndex < 0 || realIndex >= form.hierarchy_levels.length) return
  form.hierarchy_levels[realIndex].name = name
  syncActiveHierarchyProfile()
}

function removeHierarchyLevel(displayIndex: number) {
  // displayIndex 是包含「无」的索引，真实索引 = displayIndex - 1
  const realIndex = displayIndex - 1
  if (realIndex < 0 || realIndex >= form.hierarchy_levels.length) return
  form.hierarchy_levels.splice(realIndex, 1)
  _reindexLevels()
  syncActiveHierarchyProfile()
}

// ===== 拖拽排序 =====
function onDragStart(index: number, e: DragEvent) {
  const level = displayHierarchyLevels.value[index]
  if (!level || level._isNone) return
  dragIndex.value = index
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(index))
  }
}

function onDragOver(index: number, e: DragEvent) {
  const level = displayHierarchyLevels.value[index]
  if (!level || level._isNone) return
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'move'
  }
}

function onDrop(index: number, e: DragEvent) {
  e.preventDefault()
  if (dragIndex.value === null || dragIndex.value === index) return
  const targetLevel = displayHierarchyLevels.value[index]
  if (!targetLevel || targetLevel._isNone) return

  // 转换为真实索引（-1 跳过「无」）
  const fromRealIdx = dragIndex.value - 1
  const toRealIdx = index - 1
  if (fromRealIdx < 0 || toRealIdx < 0) return

  const item = form.hierarchy_levels.splice(fromRealIdx, 1)[0]
  form.hierarchy_levels.splice(toRealIdx, 0, item)
  _reindexLevels()
  dragIndex.value = null
  syncActiveHierarchyProfile()
}

function onDragEnd() {
  dragIndex.value = null
}

function _reindexLevels() {
  form.hierarchy_levels.forEach((l, idx) => {
    l.level = idx + 1
  })
}

// ===== 表单填充 =====
function fillForm(item?: Partial<OrganizationItem>) {
  function safeParseLevels(value: unknown): HierarchyLevel[] {
    if (Array.isArray(value)) return value as HierarchyLevel[]
    if (typeof value === 'string') {
      try {
        const parsed = JSON.parse(value)
        return Array.isArray(parsed) ? parsed : []
      } catch {
        return []
      }
    }
    return []
  }

  // 读取旧记录时以当前层级字段为准，兼容尚无独立模板映射的数据。
  const hierarchySystem = item?.hierarchy_system || 'none'
  const hierarchyLevels = safeParseLevels(item?.hierarchy_levels)
  const hierarchyTemplates = safeParseHierarchyTemplates(item?.hierarchy_templates)
  if (hierarchySystem !== 'none') {
    hierarchyTemplates[hierarchySystem] = cloneHierarchyLevels(hierarchyLevels)
  }
  activeHierarchySystem.value = hierarchySystem
  customTemplateSource.value = null

  Object.assign(form, {
    name: item?.name ?? '新组织',
    parent_id: item?.parent_id ?? null,
    org_type: item?.org_type ?? '',
    location: item?.location ?? '',
    slogan: item?.slogan ?? '',
    description: item?.description ?? '',
    hierarchy: item?.hierarchy ?? '',
    resources: item?.resources ?? '',
    goal: item?.goal ?? '',
    level: item?.level ?? 1,
    power_level: item?.power_level ?? 5,
    member_count: item?.member_count ?? 0,
    status: item?.status ?? '',
    core_members: item?.core_members ?? '',
    allies: item?.allies ?? '',
    enemies: item?.enemies ?? '',
    impact: item?.impact ?? '',
    risk_notes: item?.risk_notes ?? '',
    active_from_chapter: item?.active_from_chapter ?? null,
    disbanded_chapter: item?.disbanded_chapter ?? null,
    hidden_secrets: item?.hidden_secrets ?? '',
    hierarchy_system: hierarchySystem,
    hierarchy_levels: hierarchyLevels,
    hierarchy_templates: hierarchyTemplates
  })
}

// ===== 操作函数 =====
async function startCreate() {
  if (!(await confirmIfDirty())) return
  editingId.value = null
  isCreating.value = true
  form.parent_id = null
  organizationRelations.value = []
  organizationHistory.value = []
  resetOrganizationRelationDraft()
  fillForm()
  await nextTick()
  markClean()
}

async function startCreateChild() {
  if (!(await confirmIfDirty())) return
  const parent = organizations.value.find((o) => o.id === editingId.value)
  editingId.value = null
  isCreating.value = true
  organizationRelations.value = []
  organizationHistory.value = []
  resetOrganizationRelationDraft()
  fillForm()
  form.parent_id = parent?.id || null
  // 自动展开父组织
  if (parent) expandedIds.value.add(parent.id)
  await nextTick()
  markClean()
}

async function selectOrganization(item: OrganizationItem) {
  if (editingId.value === item.id) return
  if (!(await confirmIfDirty())) return
  editingId.value = item.id
  isCreating.value = false
  fillForm(item)
  await Promise.all([
    loadOrganizationRelations(item.id),
    loadOrganizationHistory(item.id)
  ])
  await nextTick()
  markClean()
}

async function resetCurrent() {
  if (!(await confirmIfDirty('确定要重置当前编辑内容吗？'))) return
  const current = organizations.value.find((item) => item.id === editingId.value)
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

async function loadOrganizationRelations(organizationId: number) {
  // 步骤 1：确认当前项目；步骤 2：按所选组织读取结构化关系；步骤 3：失败时清空旧列表。
  const projectId = await ensureProject()
  if (!projectId) return
  try {
    organizationRelations.value = await listOrganizationRelations(projectId, organizationId)
  } catch {
    organizationRelations.value = []
  }
  resetOrganizationRelationDraft()
}

async function loadOrganizationHistory(organizationId: number) {
  // 步骤 1：限定当前项目和组织；步骤 2：读取最近历史；步骤 3：失败时清空旧组织记录。
  const projectId = await ensureProject()
  if (!projectId) return
  historyLoading.value = true
  try {
    organizationHistory.value = await listOrganizationHistory(projectId, organizationId, 30)
  } catch {
    organizationHistory.value = []
  } finally {
    historyLoading.value = false
  }
}

const organizationHistoryFieldLabels: Record<string, string> = {
  parent_id: '上级组织',
  name: '组织名称',
  org_type: '组织类型',
  location: '所在地',
  slogan: '宗旨口号',
  description: '组织背景',
  level: '组织层级',
  power_level: '实力等级',
  member_count: '成员规模',
  status: '组织状态',
  hierarchy: '层级说明',
  hierarchy_system: '层级体系',
  hierarchy_levels: '职位层级',
  hierarchy_templates: '层级模板',
  resources: '核心资源',
  goal: '组织目标',
  core_members: '核心成员',
  allies: '盟友文本',
  enemies: '敌对文本',
  impact: '剧情影响',
  risk_notes: '风险提示',
  hidden_secrets: '隐藏设定',
  organization_relation: '组织关系',
  active_from_chapter: '活跃起始章节',
  disbanded_chapter: '解散章节'
}

function historyFieldLabel(field: string) {
  // 步骤 1：优先显示中文字段名；步骤 2：未知字段保留原始标识。
  return organizationHistoryFieldLabels[field] || field
}

function historyRecordTitle(record: OrganizationHistory) {
  // 步骤 1：区分组织档案字段与组织关系事件；步骤 2：显示新增、更新或移除动作。
  if (record.changed_fields.includes('organization_relation')) {
    const action = record.operation === 'create'
      ? '新增'
      : record.operation === 'delete' ? '移除' : '更新'
    return `${action}组织关系`
  }
  return record.operation === 'create' ? '创建档案' : '更新档案'
}

function formatHistoryValue(value: unknown) {
  // 步骤 1：把空值显示为统一占位；步骤 2：序列化复杂值并限制单项长度。
  if (value === null || value === undefined || value === '') return '（空）'
  const text = typeof value === 'string' ? value : JSON.stringify(value) ?? String(value)
  return text.length > 180 ? `${text.slice(0, 180)}…` : text
}

function getHistoryFieldChanges(record: OrganizationHistory) {
  // 步骤 1：读取记录标注的变更字段；步骤 2：组合中文名称和前后显示值。
  return record.changed_fields.map((field) => ({
    field,
    label: historyFieldLabel(field),
    before: formatHistoryValue(record.before_snapshot[field]),
    after: formatHistoryValue(record.after_snapshot[field])
  }))
}

function formatHistoryTime(value: string | null) {
  // 步骤 1：处理缺失时间；步骤 2：转成本地时间，无法解析时保留原值。
  if (!value) return '时间未知'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function resetOrganizationRelationDraft() {
  // 重置新增/编辑表单，避免切换组织时把上一条关系带入下一条。
  editingRelationId.value = null
  relationDraft.target_org_id = null
  relationDraft.relation_type = 'alliance'
  relationDraft.description = ''
  relationDraft.effective_from_chapter = null
  relationDraft.expires_at_chapter = null
}

function editOrganizationRelation(relation: OrganizationRelation) {
  // 将已保存关系载入表单，保持关系 ID 用于后续更新。
  editingRelationId.value = relation.id
  relationDraft.target_org_id = relation.target_org_id
  relationDraft.relation_type = relation.relation_type
  relationDraft.description = relation.description
  relationDraft.effective_from_chapter = relation.effective_from_chapter
  relationDraft.expires_at_chapter = relation.expires_at_chapter
}

async function saveOrganizationRelationDraft() {
  // 步骤 1：检查当前组织、目标组织和章节区间；步骤 2：新增或更新；步骤 3：刷新视图。
  const projectId = await ensureProject()
  const organizationId = editingId.value
  const targetOrgId = relationDraft.target_org_id
  const relationId = editingRelationId.value
  if (!projectId || !organizationId || !targetOrgId) return
  if (
    relationDraft.effective_from_chapter !== null &&
    relationDraft.expires_at_chapter !== null &&
    relationDraft.expires_at_chapter < relationDraft.effective_from_chapter
  ) {
    notify.warning('关系失效章节不能早于生效章节')
    return
  }

  relationSaving.value = true
  try {
    await persistOrganizationRelation(
      projectId,
      organizationId,
      {
        target_org_id: targetOrgId,
        relation_type: relationDraft.relation_type,
        description: relationDraft.description,
        effective_from_chapter: relationDraft.effective_from_chapter,
        expires_at_chapter: relationDraft.expires_at_chapter
      },
      relationId ?? undefined
    )
    notify.success(relationId ? '组织关系已更新' : '组织关系已添加')
    await loadOrganizationRelations(organizationId)
  } finally {
    relationSaving.value = false
  }
}

async function removeOrganizationRelation(relation: OrganizationRelation) {
  // 步骤 1：由作者确认移除目标；步骤 2：调用限定项目和组织的删除接口；步骤 3：刷新关系。
  const organizationId = editingId.value
  if (!organizationId || !window.confirm(`确认移除与「${relation.target_org_name}」的关系吗？`)) return
  const projectId = await ensureProject()
  if (!projectId) return
  await deleteOrganizationRelation(projectId, organizationId, relation.id)
  notify.success('组织关系已移除')
  await loadOrganizationRelations(organizationId)
}

async function load() {
  const projectId = projectStore.currentProject!.id
  loading.value = true
  try {
    const [organizationList] = await Promise.all([
      listResource<OrganizationItem>(projectId, 'organizations'),
      charStore.load(projectId),
      dictStore.load('org_type'),
      dictStore.load('org_resource'),
      dictStore.load('org_location'),
      dictStore.load('org_slogan'),
      dictStore.load('org_background'),
      dictStore.load('org_goal_template'),
      dictStore.load('org_secret_template')
    ])
    organizations.value = organizationList
    // 默认展开所有顶级组织
    if (expandedIds.value.size === 0) {
      organizationList
        .filter((o) => !o.parent_id)
        .forEach((o) => expandedIds.value.add(o.id))
    }
    if (!editingId.value && !isCreating.value && organizations.value[0]) {
      editingId.value = organizations.value[0].id
      fillForm(organizations.value[0])
      await nextTick()
      markClean()
    }
    if (editingId.value && !isCreating.value) {
      await Promise.all([
        loadOrganizationRelations(editingId.value),
        loadOrganizationHistory(editingId.value)
      ])
    } else {
      organizationRelations.value = []
      organizationHistory.value = []
      resetOrganizationRelationDraft()
    }
  } finally {
    loading.value = false
  }
}

async function save() {
  const projectId = await ensureProject()
  if (!projectId) return

  // 保存前同步当前体系，确保当前页编辑内容与体系副本一致。
  syncActiveHierarchyProfile()

  const payload = {
    ...form,
    hierarchy_levels: JSON.stringify(form.hierarchy_levels),
    hierarchy_templates: JSON.stringify(form.hierarchy_templates)
  }

  if (editingId.value) {
    const updated = await updateResource<OrganizationItem>('organizations', editingId.value, payload)
    notify.success('势力档案已更新')
    await load()
    const fresh = organizations.value.find((item) => item.id === updated.id)
    if (fresh) {
      fillForm(fresh)
      // 确保父组织展开
      if (fresh.parent_id) expandedIds.value.add(fresh.parent_id)
      // 同步到共享 store，确保其他页面（如人物卡片）能拿到最新数据
      orgStore.update(fresh)
      await nextTick()
      markClean()
    }
  } else {
    const created = await createResource<OrganizationItem>('organizations', { project_id: projectId, ...payload })
    notify.success('势力档案已新增')
    isCreating.value = false
    await load()
    const fresh = organizations.value.find((item) => item.id === created.id)
    if (fresh) {
      editingId.value = fresh.id
      fillForm(fresh)
      if (fresh.parent_id) expandedIds.value.add(fresh.parent_id)
      // 同步到共享 store
      orgStore.add(fresh)
      await nextTick()
      markClean()
    }
  }
}

function openDeleteConfirm() {
  if (!editingId.value) return
  const org = organizations.value.find(o => o.id === editingId.value)
  deletingOrgName.value = org?.name || ''
  showDeleteConfirm.value = true
}

async function handleForceDelete() {
  if (!editingId.value) return
  try {
    const currentIndex = organizations.value.findIndex((item) => item.id === editingId.value)

    // 1. 清除所有角色的组织势力关系
    const relatedChars: CharacterItem[] = []
    characters.value.forEach((char) => {
      let relations: any[] = []
      try {
        if (char.org_relations && typeof char.org_relations === 'string') {
          relations = JSON.parse(char.org_relations)
        } else if (Array.isArray(char.org_relations)) {
          relations = char.org_relations
        }
      } catch { /* ignore */ }
      if (relations.some((r) => Number(r.org_id) === editingId.value)) {
        relatedChars.push(char)
      }
    })
    for (const char of relatedChars) {
      let relations: any[] = []
      try {
        if (char.org_relations && typeof char.org_relations === 'string') {
          relations = JSON.parse(char.org_relations)
        } else if (Array.isArray(char.org_relations)) {
          relations = char.org_relations
        }
      } catch { /* ignore */ }
      const newRelations = relations.filter((r) => Number(r.org_id) !== editingId.value)
      await updateResource('characters', char.id, {
        org_relations: JSON.stringify(newRelations)
      })
    }

    // 2. 子组织的 parent_id 设为 null（变为顶级组织）
    const children = organizations.value.filter((o) => o.parent_id === editingId.value)
    for (const child of children) {
      await updateResource('organizations', child.id, { parent_id: null })
    }

    // 3. 删除组织
    const deletedId = editingId.value
    await deleteResource('organizations', editingId.value)
    // 同步到共享 store
    orgStore.remove(deletedId)
    // 同步更新所有角色的组织关系（角色页面会自动响应）
    charStore.removeOrgFromAll(deletedId)

    if (relatedChars.length > 0) {
      notify.success(`势力档案已删除，已清除 ${relatedChars.length} 个角色的组织关联`)
    } else {
      notify.success('势力档案已删除')
    }

    const nextItem = organizations.value.find((o) => o.id !== editingId.value)
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
    showDeleteConfirm.value = false
  } catch (e: any) {
    console.error('删除失败:', e)
    notify.error(e?.message || '删除失败，请检查控制台')
    showDeleteConfirm.value = false
  }
}

useProjectDataLoader(load)
</script>

<style scoped>
.org-page {
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
  min-width: 60px;
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
  grid-template-columns: 280px minmax(480px, 1fr) 300px;
  gap: 12px;
  min-height: 0;
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

/* ===== 左侧列表 ===== */
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

.tree-toolbar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  flex-shrink: 0;
}

.toolbar-spacer {
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
  padding: 50px 20px;
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

/* 组织树 */
.org-tree {
  padding: 6px 0 12px;
}

.tree-node-wrapper {
  display: flex;
  flex-direction: column;
}

.org-tree-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px 8px 0;
  margin: 0 6px;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.15s;
  position: relative;
}

.org-tree-item:hover {
  background: var(--n-color-hover, #252a33);
}

.org-tree-item.active {
  background: rgba(99, 102, 241, 0.12);
}

.org-tree-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 6px;
  bottom: 6px;
  width: 3px;
  background: #6366f1;
  border-radius: 0 3px 3px 0;
}

.tree-expand-icon {
  width: 16px;
  text-align: center;
  font-size: 10px;
  color: var(--n-text-color-3, #6b7280);
  flex-shrink: 0;
  transition: transform 0.2s;
}

.tree-expand-icon.expanded {
  transform: rotate(0deg);
}

.tree-expand-icon.hidden {
  visibility: hidden;
}

.tree-org-icon {
  font-size: 14px;
  flex-shrink: 0;
}

.tree-org-info {
  flex: 1;
  min-width: 0;
}

.tree-org-name {
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tree-org-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 2px;
  font-size: 10px;
  color: var(--n-text-color-3, #6b7280);
}

.tree-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.tree-org-type {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tree-power-bar {
  width: 30px;
  height: 4px;
  background: var(--n-border-color, #2a2f3a);
  border-radius: 2px;
  overflow: hidden;
  flex-shrink: 0;
}

.tree-power-fill {
  height: 100%;
  background: linear-gradient(90deg, #4f8cff, #f2c97d);
  border-radius: 2px;
}

/* ===== 中间详情 ===== */
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

.form-scroll {
  flex: 1;
  min-height: 0;
}

.detail-form {
  padding: 20px 28px 28px;
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

.form-section-sub {
  margin-top: 8px;
}

.form-section-sub .sub-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
  font-size: 12px;
  color: var(--n-text-color-2, #9ca3af);
  font-weight: 500;
}

/* 势力滑块 */
.power-sliders {
  background: var(--n-color-1, #1e2228);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
  padding: 16px 20px;
}

.slider-row {
  margin-bottom: 16px;
}

.slider-row:last-child {
  margin-bottom: 0;
}

.slider-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
}

.slider-label strong {
  font-size: 14px;
  color: #a5b4fc;
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
  flex: 1;
}

.card-badge {
  background: rgba(59, 130, 246, 0.2);
  color: #93c5fd;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 600;
}

.card-empty {
  padding: 16px;
  text-align: center;
  color: var(--n-text-color-3, #6b7280);
  font-size: 12px;
}

/* 成员列表 */
.member-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 280px;
  overflow-y: auto;
}

.member-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
}

.member-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  color: white;
  flex-shrink: 0;
}

.member-info {
  flex: 1;
  min-width: 0;
}

.member-name {
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 2px;
}

.member-position {
  font-size: 10px;
}

.member-loyalty {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.loyalty-bar {
  width: 40px;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.loyalty-fill {
  height: 100%;
  background: linear-gradient(90deg, #22c55e, #10b981);
  border-radius: 2px;
}

.loyalty-num {
  font-size: 10px;
  color: var(--n-text-color-3, #6b7280);
  width: 14px;
  text-align: right;
}

/* 势力雷达 */
.radar-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;
}

.radar-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.radar-label {
  width: 56px;
  color: var(--n-text-color-2, #9ca3af);
  flex-shrink: 0;
}

.radar-bar {
  flex: 1;
  height: 6px;
  background: var(--n-border-color, #2a2f3a);
  border-radius: 3px;
  overflow: hidden;
}

.radar-fill {
  height: 100%;
  background: var(--n-color-primary, #3b82f6);
  border-radius: 3px;
  transition: width 0.3s;
}

.radar-fill.power {
  background: linear-gradient(90deg, #f59e0b, #ef4444);
}

.radar-fill.members {
  background: linear-gradient(90deg, #22c55e, #10b981);
}

.radar-value {
  width: 42px;
  text-align: right;
  font-weight: 600;
  color: var(--n-text-color-1, #e5e7eb);
  flex-shrink: 0;
}

.risk-level {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 10px;
  border-top: 1px solid var(--n-border-color, #2a2f3a);
}

.risk-label {
  font-size: 12px;
  color: var(--n-text-color-2, #9ca3af);
}

/* ===== 层级体系 ===== */
.hierarchy-system-row {
  display: flex;
  align-items: flex-end;
  margin-bottom: 12px;
}

.hierarchy-empty {
  padding: 20px;
  text-align: center;
  color: var(--n-text-color-3, #6b7280);
  font-size: 12px;
  background: var(--n-color-1, #1e2228);
  border: 1px dashed var(--n-border-color, #2a2f3a);
  border-radius: 8px;
}

.hierarchy-level-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hierarchy-level-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  background: var(--n-color-1, #1e2228);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 6px;
  transition: all 0.2s;
}

.hierarchy-level-item.is-none {
  background: rgba(120, 120, 120, 0.08);
  border-style: dashed;
  opacity: 0.7;
}

.hierarchy-level-item.is-dragging {
  opacity: 0.5;
}

.hierarchy-level-item:not(.is-none) {
  cursor: grab;
}

.hierarchy-level-item:not(.is-none):active {
  cursor: grabbing;
}

.level-badge {
  flex-shrink: 0;
  width: 36px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  color: #a5b4fc;
  background: rgba(99, 102, 241, 0.15);
  border-radius: 4px;
}

.level-none-badge {
  color: #888;
  background: rgba(120, 120, 120, 0.15);
}

.level-none-text {
  flex: 1;
  font-size: 13px;
  color: #888;
}

.level-name-input {
  flex: 1;
}

.level-actions {
  display: flex;
  gap: 2px;
  flex-shrink: 0;
  align-items: center;
}

.drag-handle {
  cursor: grab;
  color: #666;
  font-size: 14px;
  padding: 0 4px;
  user-select: none;
  letter-spacing: -2px;
}

.drag-handle:hover {
  color: #a5b4fc;
}

.level-action-hint {
  font-size: 12px;
  color: #666;
  opacity: 0.6;
}

/* ===== 组织关系 ===== */
.organization-relation-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.organization-relation-item {
  padding: 9px 10px;
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 7px;
  background: var(--n-color-1, #1e2228);
}

.organization-relation-heading,
.organization-relation-actions,
.organization-relation-chapters,
.organization-relation-editor-actions {
  display: flex;
  align-items: center;
}

.organization-relation-heading {
  gap: 7px;
  min-width: 0;
}

.organization-relation-heading strong {
  overflow: hidden;
  flex: 1;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}

.organization-relation-actions {
  gap: 5px;
  flex-shrink: 0;
}

.organization-relation-description,
.organization-relation-range,
.relation-empty-tip,
.legacy-relation-note {
  margin-top: 6px;
  color: var(--n-text-color-3, #8b93a1);
  font-size: 11px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.organization-relation-range {
  color: #7f8da5;
}

.legacy-relation-note {
  margin: 0 0 10px;
  padding: 7px 8px;
  border-radius: 5px;
  background: rgba(245, 158, 11, 0.08);
  color: #d6a84f;
}

.organization-relation-editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid var(--n-border-color, #2a2f3a);
}

.organization-relation-chapters {
  gap: 6px;
  color: var(--n-text-color-3, #8b93a1);
}

.organization-relation-chapters :deep(.n-input-number) {
  flex: 1;
  min-width: 0;
}

.organization-relation-editor-actions {
  justify-content: flex-end;
  gap: 7px;
}

/* ===== 组织档案变更记录 ===== */
.history-count {
  min-width: 22px;
  padding: 2px 7px;
  border-radius: 12px;
  background: rgba(59, 130, 246, 0.16);
  color: #93c5fd;
  font-size: 11px;
  text-align: center;
}

.organization-history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 420px;
  overflow-y: auto;
}

.organization-history-item {
  padding: 9px 10px;
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.02);
}

.organization-history-heading,
.organization-history-meta,
.history-value-row {
  display: flex;
  align-items: center;
  gap: 7px;
}

.organization-history-heading strong {
  color: var(--n-text-color-1, #e5e7eb);
  font-size: 12px;
}

.organization-history-meta {
  justify-content: space-between;
  margin-top: 6px;
  color: var(--n-text-color-3, #8b93a1);
  font-size: 10px;
}

.organization-history-fields,
.history-rationale {
  margin-top: 6px;
  color: var(--n-text-color-2, #b7bfcc);
  font-size: 11px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.organization-history-details {
  margin-top: 7px;
  color: var(--n-text-color-3, #8b93a1);
  font-size: 11px;
}

.organization-history-details summary {
  cursor: pointer;
  user-select: none;
}

.history-field-change {
  margin-top: 7px;
  padding-top: 7px;
  border-top: 1px solid var(--n-border-color, #2a2f3a);
}

.history-field-change > strong {
  color: var(--n-text-color-1, #e5e7eb);
}

.history-value-row {
  align-items: flex-start;
  margin-top: 4px;
}

.history-value-row span {
  flex: 0 0 28px;
  color: var(--n-text-color-3, #8b93a1);
}

.history-value-row p {
  flex: 1;
  min-width: 0;
  margin: 0;
  color: var(--n-text-color-2, #b7bfcc);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
