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
    <div
      class="workbench"
      :class="{ 'left-collapsed': leftPanelCollapsed, 'side-collapsed': sidePanelCollapsed, 'is-resizing': isResizing }"
      :style="{
        '--left-panel-width': leftPanelCollapsed ? '56px' : leftPanelWidth + 'px',
        '--right-panel-width': sidePanelCollapsed ? '56px' : '280px',
      }"
    >
      <!-- 左侧：角色列表 -->
      <aside class="list-panel" :class="{ collapsed: leftPanelCollapsed }">
        <!-- 面板头部 -->
        <div class="list-panel-header">
          <template v-if="!leftPanelCollapsed">
            <span class="list-panel-title">角色列表</span>
            <span class="list-panel-count">{{ totalCount }}</span>
          </template>
          <n-button
            text
            size="tiny"
            class="panel-toggle-btn"
            @click="leftPanelCollapsed = !leftPanelCollapsed"
            :title="leftPanelCollapsed ? '展开列表面板' : '折叠列表面板'"
          >
            <template #icon>
              <n-icon size="16">
                <svg v-if="leftPanelCollapsed" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M9 18l6-6-6-6" />
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M15 18l-6-6 6-6" />
                </svg>
              </n-icon>
            </template>
          </n-button>
        </div>

        <template v-if="!leftPanelCollapsed">
          <div class="panel-tools">
            <n-input v-model:value="keyword" clearable placeholder="搜索角色...">
              <template #prefix>🔍</template>
            </n-input>
            <n-select
              v-model:value="groupFilter"
              clearable
              :options="groupFilterOptions"
              placeholder="分组筛选"
              style="width: 110px"
            />
          </div>

          <!-- 分组操作栏 -->
          <div class="group-actions">
            <span class="group-actions-label">分组</span>
            <div class="group-actions-btns">
              <n-button text size="tiny" @click="toggleAllGroups">
                {{ allGroupsExpanded ? '全部折叠' : '全部展开' }}
              </n-button>
              <span class="group-actions-divider">|</span>
              <n-button text size="tiny" type="primary" @click="startCreateGroup">
                <template #icon>＋</template>
                新建分组
              </n-button>
            </div>
          </div>

          <!-- 新建分组输入框 -->
          <div v-if="isCreatingGroup" class="new-group-form">
            <n-input
              v-model:value="newGroupName"
              size="small"
              placeholder="输入分组名称"
              clearable
              @keyup.enter="confirmCreateGroup"
            />
            <div class="new-group-actions">
              <n-button size="tiny" type="primary" @click="confirmCreateGroup">确认</n-button>
              <n-button size="tiny" @click="cancelCreateGroup">取消</n-button>
            </div>
          </div>
        </template>

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
            <draggable
              v-model="draggableGroups"
              item-key="id"
              handle=".group-drag-handle"
              animation="200"
              @start="isDraggingGroup = true"
              @end="onGroupDragEnd"
              class="groups-draggable"
            >
              <template #item="{ element: group }">
                <div class="group-wrapper" :class="{ 'is-dragging': isDraggingGroup }">
                  <!-- 折叠态：只显示图标 -->
                  <template v-if="leftPanelCollapsed">
                    <div
                      class="group-icon-only"
                      :title="`${groupLabel(group)}（${groupCharacters[group.id]?.length || 0}）`"
                      @click="quickSelectFirstOfGroup({ group, items: groupCharacters[group.id] || [] })"
                    >
                      <span class="group-icon-big">{{ groupIcon(group) }}</span>
                      <n-badge :value="groupCharacters[group.id]?.length || 0" :max="99" size="tiny" />
                    </div>
                  </template>

                  <!-- 展开态：完整分组 -->
                  <template v-else>
                    <!-- 分组标题 -->
                    <div
                      class="group-header"
                      :class="{ collapsed: !expandedGroups.has(group.id), 'is-builtin': group.is_builtin }"
                    >
                      <span class="drag-handle group-drag-handle" title="拖拽排序">
                        <svg viewBox="0 0 24 24" fill="currentColor">
                          <circle cx="9" cy="6" r="1.5" />
                          <circle cx="15" cy="6" r="1.5" />
                          <circle cx="9" cy="12" r="1.5" />
                          <circle cx="15" cy="12" r="1.5" />
                          <circle cx="9" cy="18" r="1.5" />
                          <circle cx="15" cy="18" r="1.5" />
                        </svg>
                      </span>
                      <n-icon
                        size="12"
                        class="group-arrow"
                        :class="{ expanded: expandedGroups.has(group.id) }"
                        @click.stop="toggleGroup(group.id)"
                      >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                          <path d="M6 9l6 6 6-6" />
                        </svg>
                      </n-icon>
                      <span class="group-icon">{{ groupIcon(group) }}</span>

                      <!-- 重命名输入框 -->
                      <n-input
                        v-if="renamingGroupId === group.id"
                        v-model:value="renamingGroupName"
                        size="tiny"
                        class="group-rename-input"
                        @keyup.enter="confirmRenameGroup(group)"
                        @keyup.esc="cancelRenameGroup"
                        @blur="confirmRenameGroup(group)"
                      />
                      <span v-else class="group-name" @click="toggleGroup(group.id)">
                        {{ groupLabel(group) }}
                      </span>

                      <n-tag size="tiny" type="default">{{ groupCharacters[group.id]?.length || 0 }}</n-tag>

                      <!-- 自定义分组操作按钮 -->
                      <div v-if="!group.is_builtin" class="group-actions-right">
                        <n-button
                          text
                          size="tiny"
                          class="group-action-btn"
                          title="重命名"
                          @click.stop="startRenameGroup(group)"
                        >
                          ✏️
                        </n-button>
                        <n-popconfirm positive-text="删除" negative-text="取消" @positive-click="deleteGroup(group)">
                          <template #trigger>
                            <n-button text size="tiny" class="group-action-btn" title="删除分组">
                              🗑️
                            </n-button>
                          </template>
                          确定删除该分组？分组内的角色将自动回到对应类型的默认分组。
                        </n-popconfirm>
                      </div>
                    </div>

                    <!-- 角色列表（可拖拽） -->
                    <div v-show="expandedGroups.has(group.id)" class="group-items">
                      <draggable
                        v-model="groupCharacters[group.id]"
                        item-key="id"
                        handle=".char-drag-handle"
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
                            v-show="matchesFilter(item)"
                            class="character-item"
                            :class="{
                              active: editingId === item.id,
                              inactive: item.status === 'inactive',
                              hidden: item.status === 'hidden',
                              'is-builtin': item.is_builtin
                            }"
                            @click="selectCharacter(item)"
                          >
                            <span class="drag-handle char-drag-handle" title="拖拽排序/移动">
                              <svg viewBox="0 0 24 24" fill="currentColor">
                                <circle cx="9" cy="6" r="1.5" />
                                <circle cx="15" cy="6" r="1.5" />
                                <circle cx="9" cy="12" r="1.5" />
                                <circle cx="15" cy="12" r="1.5" />
                                <circle cx="9" cy="18" r="1.5" />
                                <circle cx="15" cy="18" r="1.5" />
                              </svg>
                            </span>
                            <div class="char-avatar">
                              {{ item.name?.charAt(0) || '?' }}
                              <span v-if="item.is_builtin" class="builtin-badge" title="内置角色">★</span>
                            </div>
                            <div class="char-content">
                              <div class="char-title-row">
                                <span class="char-name">{{ item.name }}</span>
                                <n-tag v-if="item.is_builtin" size="tiny" type="warning" class="builtin-tag">内置</n-tag>
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
                        </template>
                      </draggable>

                      <!-- 空分组提示 -->
                      <div
                        v-if="groupCharacters[group.id]?.length === 0"
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

      <!-- 左侧拖拽条 -->
      <div
        v-if="!leftPanelCollapsed"
        class="panel-resizer"
        :class="{ active: isResizing }"
        @mousedown="startResize"
        title="拖拽调整宽度"
      >
        <div class="resizer-handle"></div>
      </div>

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
            <template v-if="editingId">
              <n-tooltip v-if="isCurrentBuiltin" trigger="hover" placement="bottom">
                <template #trigger>
                  <n-button type="error" text disabled>
                    🗑️ 删除
                  </n-button>
                </template>
                内置角色不可删除
              </n-tooltip>
              <n-popconfirm v-else positive-text="确认删除" negative-text="取消" @positive-click="remove">
                <template #trigger>
                  <n-button type="error" text>🗑️ 删除</n-button>
                </template>
                确认删除这个角色？
              </n-popconfirm>
            </template>
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
                    <n-form-item label="状态">
                      <n-radio-group v-model:value="form.status">
                        <n-radio value="active">启用</n-radio>
                        <n-radio value="inactive">关闭</n-radio>
                        <n-radio value="hidden">隐藏</n-radio>
                      </n-radio-group>
                    </n-form-item>
                    <n-form-item label="主性格类型">
                      <n-tooltip trigger="hover" :disabled="!mbtiPrimaryInfo" placement="bottom">
                        <template #trigger>
                          <n-select
                            v-model:value="form.mbti_primary"
                            filterable
                            :options="mbtiOptions"
                            placeholder="选择主性格类型"
                            clearable
                          />
                        </template>
                        <div v-if="mbtiPrimaryInfo" class="mbti-tooltip-content">
                          <div class="mbti-tooltip-title">
                            <span class="mbti-tooltip-code">{{ mbtiPrimaryInfo.code }}</span>
                            <span class="mbti-tooltip-name">{{ mbtiPrimaryInfo.name }}</span>
                          </div>
                          <div class="mbti-tooltip-desc">{{ mbtiPrimaryInfo.description }}</div>
                        </div>
                      </n-tooltip>
                    </n-form-item>
                  </div>
                  <div class="form-grid-3">
                    <n-form-item label="辅性格类型（可选）">
                      <n-tooltip trigger="hover" :disabled="!mbtiSecondaryInfo" placement="bottom">
                        <template #trigger>
                          <n-select
                            v-model:value="form.mbti_secondary"
                            filterable
                            :options="mbtiOptions"
                            placeholder="外在表现型"
                            clearable
                          />
                        </template>
                        <div v-if="mbtiSecondaryInfo" class="mbti-tooltip-content">
                          <div class="mbti-tooltip-title">
                            <span class="mbti-tooltip-code">{{ mbtiSecondaryInfo.code }}</span>
                            <span class="mbti-tooltip-name">{{ mbtiSecondaryInfo.name }}</span>
                          </div>
                          <div class="mbti-tooltip-desc">{{ mbtiSecondaryInfo.description }}</div>
                        </div>
                      </n-tooltip>
                    </n-form-item>
                    <n-form-item label="身份 / 职业">
                      <TagSelectField
                        v-model:model-value="form.identity"
                        :options="identityOptions"
                        placeholder="选择或输入身份职业..."
                      />
                    </n-form-item>
                    <n-form-item label="阵营 / 所属势力">
                      <TagSelectField
                        v-model:model-value="form.faction"
                        :options="factionOptions"
                        placeholder="选择或输入阵营..."
                      />
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
                      <TagSelectField
                        v-model:model-value="form.appearance"
                        :options="appearanceOptions"
                        placeholder="选择或输入外貌特征..."
                      />
                    </n-form-item>
                    <n-form-item label="性格特征">
                      <TagSelectField
                        v-model:model-value="form.personality"
                        :options="personalityTraitOptions"
                        placeholder="选择或输入性格特征..."
                      />
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
                      <TagSelectField
                        v-model:model-value="form.motivation"
                        :options="motivationOptions"
                        placeholder="选择或输入核心动机..."
                      />
                    </n-form-item>
                    <n-form-item label="弱点 / 缺陷">
                      <TagSelectField
                        v-model:model-value="form.weakness"
                        :options="weaknessOptions"
                        placeholder="选择或输入弱点缺陷..."
                      />
                    </n-form-item>
                  </div>
                </div>

                <div class="form-section">
                  <div class="section-title">
                    背景与成长
                    <span class="section-hint">角色的过去与未来走向</span>
                  </div>
                  <n-form-item label="背景故事">
                    <TagSelectField
                      v-model:model-value="form.background"
                      :options="backgroundOptions"
                      placeholder="选择或输入背景故事..."
                    />
                  </n-form-item>
                  <div class="form-grid-2">
                    <n-form-item label="隐藏秘密">
                      <TagSelectField
                        v-model:model-value="form.secret"
                        :options="secretOptions"
                        placeholder="选择或输入隐藏秘密..."
                      />
                    </n-form-item>
                    <n-form-item label="对白风格">
                      <TagSelectField
                        v-model:model-value="form.dialogue_style"
                        :options="dialogueStyleOptions"
                        placeholder="选择或输入对白风格..."
                      />
                    </n-form-item>
                  </div>
                  <n-form-item label="人物弧光">
                    <TagSelectField
                      v-model:model-value="form.arc"
                      :options="arcOptions"
                      placeholder="选择或输入人物弧光..."
                    />
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
                    :key="tpl.key"
                    class="attr-tpl-tag"
                    :bordered="false"
                    @click="addAttributeFromTemplate(tpl.key, tpl.label)"
                  >
                    + {{ tpl.label }}
                  </n-tag>
                </div>
              </div>

              <div class="attr-list">
                <div v-for="(attr, index) in form.custom_attributes" :key="index" class="attr-item">
                  <div class="attr-row">
                    <SingleSelectField
                      v-model:model-value="attr.key"
                      :options="attributeNameOptions"
                      placeholder="属性"
                      class="attr-name-field"
                      @update:model-value="(val: string) => onAttrKeyChange(index, val)"
                    />
                    <TagSelectField
                      v-model:model-value="attr.value"
                      :options="getAttrValueOptions(attr.key || '')"
                      placeholder="选择或输入属性值..."
                      class="attr-value-field"
                    />
                    <div class="attr-chapter-box" :class="{ 'has-range': parseChapterRange(attr.chapter_no).end != null, 'is-filled': parseChapterRange(attr.chapter_no).start != null }">
                      <span class="attr-chapter-label">第</span>
                      <n-input-number
                        :value="parseChapterRange(attr.chapter_no).start"
                        placeholder="-"
                        :min="0"
                        class="attr-chapter-num"
                        @update:value="(val: number | null) => onChapterChange(index, 'start', val)"
                      />
                      <n-radio-group
                        :value="parseChapterRange(attr.chapter_no).end != null ? 'range' : 'single'"
                        size="tiny"
                        class="attr-chapter-mode"
                        @update:value="(val: string) => onChapterModeChange(index, val)"
                      >
                        <n-radio value="single">单章</n-radio>
                        <n-radio value="range">范围</n-radio>
                      </n-radio-group>
                      <n-input-number
                        v-if="parseChapterRange(attr.chapter_no).end != null"
                        :value="parseChapterRange(attr.chapter_no).end"
                        placeholder="-"
                        :min="0"
                        class="attr-chapter-num"
                        @update:value="(val: number | null) => onChapterChange(index, 'end', val)"
                      />
                      <span class="attr-chapter-label">章</span>
                    </div>
                    <n-button text type="error" @click="removeAttribute(index)">移除</n-button>
                  </div>
                  <div class="attr-sub-row">
                    <n-input
                      v-model:value="attr.description"
                      placeholder="属性描述（可选）"
                      class="attr-desc-input"
                    />
                    <n-input v-model:value="attr.change_reason" placeholder="变更原因（可选）" class="attr-reason-input" />
                  </div>
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

              <div class="add-relation-row">
                <n-button type="primary" ghost :disabled="!canAddMoreOrgs" @click="startAddOrgRelation">+ 添加组织关系</n-button>
              </div>

              <div v-if="form.org_relations.length === 0 && !isAddingOrgRelation" class="empty-inline">
                <n-empty description="暂无组织关系" :show-icon="false" />
              </div>

              <div v-else class="relation-list">
                <div v-for="(rel, index) in form.org_relations" :key="index" class="relation-item">
                  <!-- 查看状态 -->
                  <template v-if="editingOrgRelationIndex !== index">
                    <div class="relation-main">
                      <div class="relation-main-row">
                        <span class="relation-name">{{ getOrgNameById(rel.org_id) }}</span>
                        <span class="relation-position-tag">{{ rel.position || '无' }}</span>
                        <div class="depth-bar">
                          <div class="depth-fill" :style="{ width: `${rel.loyalty * 10}%` }"></div>
                        </div>
                        <span class="loyalty-text">忠诚 {{ rel.loyalty }}/10</span>
                      </div>
                    </div>
                    <div class="relation-actions">
                      <n-button text size="small" @click="startEditOrgRelation(index)">编辑</n-button>
                      <n-button text type="error" size="small" @click="removeOrgRelation(index)">移除</n-button>
                    </div>
                  </template>

                  <!-- 编辑状态 -->
                  <template v-else>
                    <div class="relation-edit-form">
                      <div class="relation-edit-row">
                        <n-select
                          v-model:value="newOrgRelation.org_id"
                          :options="editableOrgOptions(index)"
                          placeholder="选择组织"
                          filterable
                          class="relation-edit-field"
                        />
                        <n-select
                          v-model:value="newOrgRelation.position"
                          :options="currentOrgPositionOptions"
                          allow-create
                          filterable
                          placeholder="职位"
                          class="relation-edit-field"
                        />
                        <n-input-number
                          v-model:value="newOrgRelation.loyalty"
                          :min="1"
                          :max="10"
                          placeholder="忠诚值"
                          class="relation-edit-number"
                        />
                        <div class="relation-edit-actions">
                          <n-button size="small" type="primary" @click="saveEditOrgRelation">保存</n-button>
                          <n-button size="small" @click="cancelEditOrgRelation">取消</n-button>
                        </div>
                      </div>
                    </div>
                  </template>
                </div>

                <!-- 新增行 -->
                <div v-if="isAddingOrgRelation" class="relation-item relation-edit-item">
                  <div class="relation-edit-form">
                    <div class="relation-edit-row">
                      <n-select v-model:value="newOrgRelation.org_id" :options="addableOrgOptions" placeholder="选择组织" filterable class="relation-edit-field" />
                      <n-select v-model:value="newOrgRelation.position" :options="currentOrgPositionOptions" allow-create filterable placeholder="职位" class="relation-edit-field" />
                      <n-input-number v-model:value="newOrgRelation.loyalty" :min="1" :max="10" placeholder="忠诚值" class="relation-edit-number" />
                      <div class="relation-edit-actions">
                        <n-button size="small" type="primary" @click="confirmAddOrgRelation">添加</n-button>
                        <n-button size="small" @click="cancelAddOrgRelation">取消</n-button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </n-tab-pane>

            <!-- 人物关系 -->
            <n-tab-pane name="relations" tab="人物关系">
              <div class="tab-intro">
                <p class="intro-text">记录与其他角色的关系，支持关系随剧情演变（生效/失效章节）。</p>
              </div>

              <div class="add-relation-row">
                <n-button type="primary" ghost :disabled="!canAddMoreRelations" @click="startAddRelation">+ 添加人物关系</n-button>
              </div>

              <div v-if="form.character_relations.length === 0 && !isAddingRelation" class="empty-inline">
                <n-empty description="暂无人际关系" :show-icon="false" />
              </div>

              <div v-else class="relation-list">
                <div v-for="(rel, idx) in form.character_relations" :key="idx" class="relation-item">
                  <!-- 查看状态 -->
                  <template v-if="editingRelationIndex !== idx">
                    <div class="relation-main">
                      <div class="relation-main-row">
                        <span class="relation-name">{{ getCharacterNameById(rel.target_id) }}</span>
                        <span class="relation-position-tag">{{ rel.relation_type || '其他' }}</span>
                        <div class="depth-bar">
                          <div class="depth-fill" :style="{ width: `${rel.depth * 10}%` }"></div>
                        </div>
                        <span class="loyalty-text">深度 {{ rel.depth }}/10</span>
                      </div>
                      <div v-if="rel.effective_from || rel.expires_at" class="relation-chapter-row">
                        <span v-if="rel.effective_from" class="chapter-tag">第{{ rel.effective_from }}章起</span>
                        <span v-if="rel.expires_at" class="chapter-tag danger">第{{ rel.expires_at }}章止</span>
                      </div>
                    </div>
                    <div class="relation-actions">
                      <n-button text size="small" @click="startEditRelation(idx)">编辑</n-button>
                      <n-button text type="error" size="small" @click="removeCharRelation(idx)">移除</n-button>
                    </div>
                  </template>

                  <!-- 编辑状态 -->
                  <template v-else>
                    <div class="relation-edit-form">
                      <div class="relation-edit-row">
                        <n-select
                          v-model:value="newCharRelation.target_id"
                          :options="availableCharacterOptions"
                          placeholder="选择角色"
                          filterable
                          class="relation-edit-field"
                        />
                        <n-select
                          v-model:value="newCharRelation.relation_type"
                          :options="relationTypeOptions"
                          allow-create
                          placeholder="关系类型"
                          class="relation-edit-field"
                        />
                        <n-input-number
                          v-model:value="newCharRelation.depth"
                          :min="1"
                          :max="10"
                          placeholder="深度"
                          class="relation-edit-number"
                        />
                      </div>
                      <div class="relation-edit-row">
                        <n-input-number
                          v-model:value="newCharRelation.effective_from"
                          placeholder="起始章节"
                          :min="1"
                          class="relation-edit-number"
                        />
                        <n-input-number
                          v-model:value="newCharRelation.expires_at"
                          placeholder="终止章节"
                          :min="1"
                          class="relation-edit-number"
                        />
                        <div class="relation-edit-actions">
                          <n-button size="small" type="primary" @click="saveEditRelation">保存</n-button>
                          <n-button size="small" @click="cancelEditRelation">取消</n-button>
                        </div>
                      </div>
                    </div>
                  </template>
                </div>

                <!-- 新增行 -->
                <div v-if="isAddingRelation" class="relation-item relation-edit-item">
                  <div class="relation-edit-form">
                    <div class="relation-edit-row">
                      <n-select v-model:value="newCharRelation.target_id" :options="availableCharacterOptions" placeholder="选择角色" filterable class="relation-edit-field" />
                      <n-select v-model:value="newCharRelation.relation_type" :options="relationTypeOptions" allow-create placeholder="关系类型" class="relation-edit-field" />
                      <n-input-number v-model:value="newCharRelation.depth" :min="1" :max="10" placeholder="深度" class="relation-edit-number" />
                    </div>
                    <div class="relation-edit-row">
                      <n-input-number v-model:value="newCharRelation.effective_from" placeholder="起始章节" :min="1" class="relation-edit-number" />
                      <n-input-number v-model:value="newCharRelation.expires_at" placeholder="终止章节" :min="1" class="relation-edit-number" />
                      <div class="relation-edit-actions">
                        <n-button size="small" type="primary" @click="confirmAddRelation">添加</n-button>
                        <n-button size="small" @click="cancelAddRelation">取消</n-button>
                      </div>
                    </div>
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
                    <div class="chapter-range-manager">
                      <!-- 已添加的章节标签 -->
                      <div class="chapter-tags">
                        <div
                          v-for="(range, index) in chapterRangeList"
                          :key="index"
                          class="chapter-tag"
                          :class="{ 'is-range': range.end != null }"
                        >
                          <span class="chapter-tag-icon">📖</span>
                          <span class="chapter-tag-text">
                            第 {{ range.start }}
                            <template v-if="range.end != null"> — {{ range.end }}</template>
                            章
                          </span>
                          <n-button
                            text
                            size="tiny"
                            class="chapter-tag-remove"
                            @click="removeChapterRange(index)"
                            title="移除"
                          >
                            <template #icon>
                              <n-icon size="11">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                                  <path d="M18 6L6 18M6 6l12 12" />
                                </svg>
                              </n-icon>
                            </template>
                          </n-button>
                        </div>
                        <!-- 添加按钮 -->
                        <div class="chapter-tag chapter-add-tag" @click="startAddChapterRange">
                          <n-icon size="14">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                              <path d="M12 5v14M5 12h14" />
                            </svg>
                          </n-icon>
                          <span>添加章节</span>
                        </div>
                      </div>
                      <!-- 添加章节范围的输入区域 -->
                      <div v-if="isAddingChapterRange" class="chapter-add-panel">
                        <div class="chapter-add-inputs">
                          <span class="chapter-add-label">第</span>
                          <n-input-number
                            v-model:value="newChapterRange.start"
                            placeholder="起始章"
                            :min="0"
                            class="chapter-add-num"
                          />
                          <n-radio-group v-model:value="newChapterRange.mode" size="small" class="chapter-mode-toggle">
                            <n-radio value="single">单章</n-radio>
                            <n-radio value="range">范围</n-radio>
                          </n-radio-group>
                          <template v-if="newChapterRange.mode === 'range'">
                            <span class="chapter-add-label">至</span>
                            <n-input-number
                              v-model:value="newChapterRange.end"
                              placeholder="结束章"
                              :min="0"
                              class="chapter-add-num"
                            />
                          </template>
                          <span class="chapter-add-label">章</span>
                        </div>
                        <div class="chapter-add-actions">
                          <n-button size="small" @click="cancelAddChapterRange">取消</n-button>
                          <n-button size="small" type="primary" @click="confirmAddChapterRange">确认添加</n-button>
                        </div>
                      </div>
                      <!-- 空状态 -->
                      <div v-if="chapterRangeList.length === 0 && !isAddingChapterRange" class="chapter-empty">
                        <span class="chapter-empty-icon">📚</span>
                        <span class="chapter-empty-text">暂未设置出场章节</span>
                        <n-button text type="primary" size="tiny" @click="startAddChapterRange">立即添加</n-button>
                      </div>
                    </div>
                  </n-form-item>
                  <n-form-item label="关系摘要">
                    <TagSelectField
                      v-model:model-value="form.relationships"
                      :options="relationSummaryOptions"
                      placeholder="选择或输入关系摘要..."
                    />
                  </n-form-item>
                </div>
                <div class="form-section">
                  <div class="section-title">
                    AI 一致性备注
                    <span class="section-hint">帮助 AI 保持角色行为一致</span>
                  </div>
                  <n-form-item label="AI 建议 / 一致性备注">
                    <TagSelectField
                      v-model:model-value="form.ai_notes"
                      :options="aiNotesOptions"
                      placeholder="选择或输入 AI 备注..."
                    />
                  </n-form-item>
                </div>
              </n-form>
            </n-tab-pane>
            </n-tabs>
          </n-scrollbar>
        </template>
      </section>

      <!-- 右侧：角色辅助面板 -->
      <aside class="side-panel" :class="{ collapsed: sidePanelCollapsed }">
        <!-- 侧栏头部 -->
        <div class="side-panel-header">
          <template v-if="!sidePanelCollapsed">
            <span class="side-panel-title">洞察助手</span>
          </template>
          <n-button
            text
            size="tiny"
            class="panel-toggle-btn"
            @click="sidePanelCollapsed = !sidePanelCollapsed"
            :title="sidePanelCollapsed ? '展开面板' : '折叠面板'"
          >
            <template #icon>
              <n-icon size="16">
                <svg v-if="sidePanelCollapsed" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M15 18l-6-6 6-6" />
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M9 18l6-6-6-6" />
                </svg>
              </n-icon>
            </template>
          </n-button>
        </div>

        <!-- 折叠态：图标导航 -->
        <div v-if="sidePanelCollapsed" class="side-panel-icons">
          <div
            v-for="section in sidePanelSections"
            :key="section.key"
            class="side-icon-item"
            :class="{ active: activeSideSection === section.key }"
            @click="toggleSideSection(section.key)"
            :title="section.label"
          >
            <span class="side-icon">{{ section.icon }}</span>
          </div>
        </div>

        <!-- 展开态：目录+内容 -->
        <template v-else>
          <!-- 目录导航 -->
          <div class="side-nav">
            <div
              v-for="section in sidePanelSections"
              :key="section.key"
              class="side-nav-item"
              :class="{ active: activeSideSection === section.key }"
              @click="toggleSideSection(section.key)"
            >
              <span class="side-nav-icon">{{ section.icon }}</span>
              <span class="side-nav-label">{{ section.label }}</span>
              <n-icon size="14" class="side-nav-arrow" :class="{ expanded: activeSideSection === section.key }">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M6 9l6 6 6-6" />
                </svg>
              </n-icon>
            </div>
          </div>

          <!-- 内容区域 -->
          <div class="side-content">
            <!-- 档案完整度 -->
            <div v-show="activeSideSection === 'completion'" class="insight-card primary-card side-section-card">
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
            <div v-show="activeSideSection === 'stats'" class="insight-card side-section-card">
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

            <!-- AI 补全建议 -->
            <div v-show="activeSideSection === 'hints'" class="insight-card side-section-card">
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
            <div v-show="activeSideSection === 'relations'" class="insight-card side-section-card">
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
          </div>
        </template>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, h, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { NBadge, NButton, NIcon, NInput, NPopconfirm, NTooltip } from 'naive-ui'
import draggable from 'vuedraggable'
import TagSelectField from '@/components/TagSelectField.vue'
import SingleSelectField from '@/components/SingleSelectField.vue'
import { useDirtySnapshot } from '@/composables/useDirtySnapshot'
import { createResource, deleteResource, listResource, updateResource } from '@/api/resources'
import { useProjectStore } from '@/stores/project'
import { useDictStore } from '@/stores/dict'
import { useProjectDataLoader } from '@/composables/useProjectDataLoader'
import { notify } from '@/utils/notify'
import type {
  CharacterAttribute,
  CharacterGroup,
  CharacterItem,
  CharacterOrgRelation,
  CharacterRelation,
  OrganizationItem,
} from '@/types/domain'

const projectStore = useProjectStore()
const dictStore = useDictStore()
const characters = ref<CharacterItem[]>([])
const organizations = ref<OrganizationItem[]>([])
const characterGroups = ref<CharacterGroup[]>([])
const keyword = ref('')
const groupFilter = ref<number | null>(null)

// 分组筛选选项：从实际分组动态获取
const groupFilterOptions = computed(() => {
  const sorted = [...characterGroups.value].sort((a, b) => a.sort_index - b.sort_index)
  return sorted.map(g => ({
    label: groupLabel(g),
    value: g.id,
  }))
})
const editingId = ref<number | null>(null)
const isCreating = ref(false)
const loading = ref(false)
const activeTab = ref('basic')

// 分组管理状态
const isCreatingGroup = ref(false)
const newGroupName = ref('')
const renamingGroupId = ref<number | null>(null)
const renamingGroupName = ref('')
const isDraggingGroup = ref(false)
const isDraggingCharacter = ref(false)

// 分组角色映射：groupId -> CharacterItem[]，用于 vuedraggable 拖拽
const groupCharacters = reactive<Record<number, CharacterItem[]>>({})

// 从 characters 重建分组角色映射
function rebuildGroupCharacters() {
  // 清空现有映射
  for (const key of Object.keys(groupCharacters)) {
    delete groupCharacters[Number(key)]
  }
  // 按分组重新构建
  for (const group of characterGroups.value) {
    const groupId = group.id
    const items = characters.value.filter(c => {
      if (c.group_id != null) return c.group_id === groupId
      if (group.is_builtin && group.role_type) {
        if (group.role_type === 'other') {
          const matchedDefault = characterGroups.value.some(
            g => g.is_builtin && g.role_type && g.role_type !== 'other' && g.role_type === c.role_type
          )
          return !matchedDefault
        }
        return c.role_type === group.role_type
      }
      return false
    })
    items.sort((a, b) => (a.sort_index ?? 9999) - (b.sort_index ?? 9999))
    groupCharacters[groupId] = items
  }
}

// 左侧面板折叠与宽度
const leftPanelCollapsed = ref(false)
const leftPanelWidth = ref(320) // 展开时的宽度
const minPanelWidth = 240
const maxPanelWidth = 480
const isResizing = ref(false)

function startResize(e: MouseEvent) {
  e.preventDefault()
  isResizing.value = true
  const startX = e.clientX
  const startWidth = leftPanelWidth.value

  function onMove(ev: MouseEvent) {
    let newWidth = startWidth + (ev.clientX - startX)
    newWidth = Math.max(minPanelWidth, Math.min(maxPanelWidth, newWidth))
    leftPanelWidth.value = newWidth
  }

  function onUp() {
    isResizing.value = false
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }

  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

const expandedGroups = ref<Set<number>>(new Set())

// 初始化分组展开状态
function initExpandedGroups() {
  expandedGroups.value = new Set(groupedCharacters.value.map(g => g.group.id))
}

// 切换分组展开/折叠
function toggleGroup(groupId: number) {
  const next = new Set(expandedGroups.value)
  if (next.has(groupId)) {
    next.delete(groupId)
  } else {
    next.add(groupId)
  }
  expandedGroups.value = next
}

// 全部展开
function expandAllGroups() {
  expandedGroups.value = new Set(groupedCharacters.value.map(g => g.group.id))
}

// 全部折叠
function collapseAllGroups() {
  expandedGroups.value = new Set()
}

// 是否所有分组都展开了
const allGroupsExpanded = computed(() => {
  const total = groupedCharacters.value.length
  if (total === 0) return false
  return expandedGroups.value.size === total
})

// 切换全部展开/折叠
function toggleAllGroups() {
  if (allGroupsExpanded.value) {
    collapseAllGroups()
  } else {
    expandAllGroups()
  }
}

// 折叠态点击分组图标：展开面板并选中第一个角色
function quickSelectFirstOfGroup(group: { group: CharacterGroup; items: CharacterItem[] }) {
  leftPanelCollapsed.value = false
  // 确保该分组展开
  const next = new Set(expandedGroups.value)
  next.add(group.group.id)
  expandedGroups.value = next
  // 选中第一个角色
  if (group.items.length > 0) {
    selectCharacter(group.items[0])
  }
}

// 右侧面板折叠状态
const sidePanelCollapsed = ref(false)
const activeSideSection = ref('completion')

// 侧栏目录配置
const sidePanelSections = [
  { key: 'completion', label: '档案完整度', icon: '📊' },
  { key: 'stats', label: '类型分布', icon: '🎭' },
  { key: 'hints', label: 'AI 建议', icon: '💡' },
  { key: 'relations', label: '快速关联', icon: '🔗' },
]

function toggleSideSection(key: string) {
  if (activeSideSection.value === key) {
    // 如果是折叠态点击，先展开面板再显示内容
    if (sidePanelCollapsed.value) {
      sidePanelCollapsed.value = false
    } else {
      activeSideSection.value = ''
    }
  } else {
    activeSideSection.value = key
    if (sidePanelCollapsed.value) {
      sidePanelCollapsed.value = false
    }
  }
}

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
  mbti: '',
  status: 'active'
})

const { isDirty, markClean, confirmIfDirty } = useDirtySnapshot(form, '当前角色档案有未保存内容，继续切换会丢弃这些修改。')

// ===== 出场章节范围管理 =====
interface ChapterRangeItem {
  start: number | null
  end: number | null
}

const isAddingChapterRange = ref(false)
const newChapterRange = reactive({
  start: null as number | null,
  end: null as number | null,
  mode: 'single' as 'single' | 'range'
})

// 解析 form.chapters 字符串为章节范围列表
const chapterRangeList = computed<ChapterRangeItem[]>({
  get() {
    if (!form.chapters) return []
    return form.chapters
      .split(/[,，]/)
      .map(s => s.trim())
      .filter(Boolean)
      .map(s => {
        const parts = s.split('-').map(p => p.trim())
        const start = parts[0] ? Number(parts[0]) : null
        const end = parts.length > 1 && parts[1] ? Number(parts[1]) : null
        return {
          start: isNaN(start as number) ? null : start,
          end: isNaN(end as number) ? null : end
        }
      })
      .filter(r => r.start != null)
  },
  set(list: ChapterRangeItem[]) {
    form.chapters = list
      .filter(r => r.start != null)
      .map(r => {
        const start = r.start as number
        if (r.end != null && r.end > start) {
          return `${start}-${r.end}`
        }
        return String(start)
      })
      .join(', ')
  }
})

function startAddChapterRange() {
  newChapterRange.start = null
  newChapterRange.end = null
  newChapterRange.mode = 'single'
  isAddingChapterRange.value = true
}

function cancelAddChapterRange() {
  isAddingChapterRange.value = false
}

function confirmAddChapterRange() {
  if (newChapterRange.start == null) {
    notify.warning('请输入起始章节')
    return
  }
  if (newChapterRange.mode === 'range') {
    if (newChapterRange.end == null) {
      notify.warning('请输入结束章节')
      return
    }
    if (newChapterRange.end <= newChapterRange.start) {
      notify.warning('结束章节必须大于起始章节')
      return
    }
  }
  const list = [...chapterRangeList.value]
  list.push({
    start: newChapterRange.start,
    end: newChapterRange.mode === 'range' ? newChapterRange.end : null
  })
  // 按起始章节排序
  list.sort((a, b) => (a.start ?? 0) - (b.start ?? 0))
  chapterRangeList.value = list
  isAddingChapterRange.value = false
}

function removeChapterRange(index: number) {
  const list = [...chapterRangeList.value]
  list.splice(index, 1)
  chapterRangeList.value = list
}

// 当前编辑的角色是否为内置角色
const isCurrentBuiltin = computed(() => {
  if (!editingId.value) return false
  const char = characters.value.find(c => c.id === editingId.value)
  return char?.is_builtin ?? false
})

// ===== 选项配置 =====
// MBTI 存英文编码，保持 options 不变
// MBTI 选项：label 用中文名，value 用编码（INTJ 等）
const mbtiOptions = computed(() =>
  dictStore.items('mbti_type').map(item => ({ label: item.item_label, value: item.item_value }))
)

// 描述性多选字段：label 和 value 都用中文（item_label）
// 因为这些字段存的是给人看的描述文本，不需要英文编码
const identityOptions = computed(() =>
  dictStore.items('character_identity').map(item => ({ label: item.item_label, value: item.item_label }))
)
const factionOptions = computed(() =>
  dictStore.items('character_faction').map(item => ({ label: item.item_label, value: item.item_label }))
)
const motivationOptions = computed(() =>
  dictStore.items('character_motivation').map(item => ({ label: item.item_label, value: item.item_label }))
)
const weaknessOptions = computed(() =>
  dictStore.items('character_weakness').map(item => ({ label: item.item_label, value: item.item_label }))
)
const dialogueStyleOptions = computed(() =>
  dictStore.items('dialogue_style').map(item => ({ label: item.item_label, value: item.item_label }))
)

// 标签快速填充字段：追加到 textarea 的内容用中文
const appearanceOptions = computed(() =>
  dictStore.items('character_appearance').map(item => ({ label: item.item_label, value: item.item_label }))
)
const personalityTraitOptions = computed(() =>
  dictStore.items('personality_trait').map(item => ({ label: item.item_label, value: item.item_label }))
)
const backgroundOptions = computed(() =>
  dictStore.items('character_background').map(item => ({ label: item.item_label, value: item.item_label }))
)
const secretOptions = computed(() =>
  dictStore.items('character_secret').map(item => ({ label: item.item_label, value: item.item_label }))
)
const arcOptions = computed(() =>
  dictStore.items('character_arc').map(item => ({ label: item.item_label, value: item.item_label }))
)
const aiNotesOptions = computed(() =>
  dictStore.items('ai_notes').map(item => ({ label: item.item_label, value: item.item_label }))
)
const relationSummaryOptions = computed(() =>
  dictStore.items('relation_summary').map(item => ({ label: item.item_label, value: item.item_label }))
)
const relationTypeOptions = computed(() =>
  dictStore.items('relation_type').map(item => ({ label: item.item_label, value: item.item_label }))
)
// 属性名称：item_value 作为 key，item_label 作为显示名称
const attributeNameOptions = computed(() =>
  dictStore.items('attribute_name').map(item => ({ label: item.item_label, value: item.item_value }))
)

// 获取属性完整信息（通过 key）
function getAttributeInfo(key: string) {
  if (!key) return null
  const items = dictStore.items('attribute_name')
  const item = items.find(i => i.item_value === key)
  if (!item) return null
  return {
    key: item.item_value,
    title: item.item_label,
    // remark 字段存储该属性的可选值列表（顿号分隔）
    valueOptions: parseRemarkValues(item.remark)
  }
}

// 添加范围结束章
function addChapterEnd(index: number) {
  const attr = form.custom_attributes[index]
  if (!attr) return
  const current = parseChapterRange(attr.chapter_no)
  const start = current.start ?? 1
  const end = start + 1
  attr.chapter_no = `${start}-${end}`
}

// 属性章节模式切换（单章/范围）
function onChapterModeChange(index: number, mode: string) {
  const attr = form.custom_attributes[index]
  if (!attr) return
  const current = parseChapterRange(attr.chapter_no)
  if (mode === 'range') {
    // 切换到范围模式
    const start = current.start ?? 1
    const end = start + 1
    attr.chapter_no = `${start}-${end}`
  } else {
    // 切换到单章模式，移除结束章
    if (current.start != null) {
      attr.chapter_no = String(current.start)
    } else {
      attr.chapter_no = null
    }
  }
}

// 从 remark 解析可选值列表（顿号 / 逗号 / 换行分隔）
function parseRemarkValues(remark: string | null | undefined): { label: string; value: string }[] {
  if (!remark) return []
  return remark
    .split(/[、,，\n]/)
    .map(s => s.trim())
    .filter(Boolean)
    .map(v => ({ label: v, value: v }))
}

// 根据属性 key 获取对应的可选值列表
function getAttrValueOptions(key: string): { label: string; value: string }[] {
  const info = getAttributeInfo(key)
  return info?.valueOptions || []
}

// 获取 MBTI 完整信息（代号 + 中文名 + 描述）
function getMbtiInfo(value: string) {
  if (!value) return null
  const items = dictStore.items('mbti_type')
  const item = items.find(i => i.item_value === value)
  if (!item) return null
  return {
    code: item.item_value,
    name: item.item_label,
    description: item.remark
  }
}

const mbtiPrimaryInfo = computed(() => getMbtiInfo(form.mbti_primary))
const mbtiSecondaryInfo = computed(() => getMbtiInfo(form.mbti_secondary))

// 属性模板从字典获取（key + label 形式）
const attributeTemplates = computed(() =>
  attributeNameOptions.value.map(o => ({ key: o.value, label: o.label }))
)

const roleTypes = computed(() => dictStore.options('character_role'))

// 角色状态选项
const characterStatusOptions = [
  { label: '启用', value: 'active' },
  { label: '关闭', value: 'inactive' },
  { label: '隐藏', value: 'hidden' }
]

// ---- 新增关系的临时数据 ----
const newOrgRelation = reactive<{ org_id: number | null; position: string; loyalty: number }>({
  org_id: null,
  position: '',
  loyalty: 5
})

// 组织关系编辑状态
const isAddingOrgRelation = ref(false)
const editingOrgRelationIndex = ref<number | null>(null)

// 是否还能添加更多组织
const canAddMoreOrgs = computed(() => {
  const addedIds = new Set(form.org_relations.map((r) => Number(r.org_id)))
  return organizations.value.some((o) => !addedIds.has(o.id))
})

// 可添加的组织选项（排除已添加的）
const addableOrgOptions = computed(() => {
  const addedIds = new Set(form.org_relations.map((r) => Number(r.org_id)))
  return organizationOptions.value.filter((o) => !addedIds.has(Number(o.value)))
})

// 编辑时可选的组织（排除其他已添加的，保留当前的）
function editableOrgOptions(index: number) {
  const addedIds = new Set(
    form.org_relations.filter((_, i) => i !== index).map((r) => Number(r.org_id))
  )
  return organizationOptions.value.filter((o) => !addedIds.has(Number(o.value)))
}

// 当前选中组织的职位选项（完全来自对应组织的层级体系）
const currentOrgPositionOptions = computed(() => {
  if (!newOrgRelation.org_id) return []
  const org = organizations.value.find((o) => o.id === newOrgRelation.org_id)
  if (!org || !org.hierarchy_levels || org.hierarchy_levels === '[]') {
    return []
  }
  try {
    const levels = JSON.parse(org.hierarchy_levels)
    return levels.map((l: { name: string; level: number }) => ({ label: l.name, value: l.name }))
  } catch {
    return []
  }
})

// 组织变化时职位默认为「无」（第一个选项）
watch(() => newOrgRelation.org_id, (newId) => {
  if (!newId) {
    newOrgRelation.position = ''
    return
  }
  const opts = currentOrgPositionOptions.value
  if (opts.length > 0) {
    newOrgRelation.position = opts[0].value
  } else {
    newOrgRelation.position = ''
  }
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

// ---- 人物关系编辑状态 ----
const isAddingRelation = ref(false)
const editingRelationIndex = ref<number | null>(null)

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
    // 分组筛选
    let matchedGroup = true
    if (groupFilter.value != null) {
      // 判断角色是否属于选中的分组
      matchedGroup = isCharacterInGroup(item, groupFilter.value)
    }
    return matchedText && matchedGroup
  })
})

// 判断角色是否属于某个分组
function isCharacterInGroup(char: CharacterItem, groupId: number): boolean {
  const group = characterGroups.value.find(g => g.id === groupId)
  if (!group) return false
  // 有 group_id 直接匹配
  if (char.group_id != null) {
    return char.group_id === groupId
  }
  // 没有 group_id 的，按 role_type 匹配默认分组
  if (group.is_builtin && group.role_type) {
    if (group.role_type === 'other') {
      const matchedDefault = characterGroups.value.some(
        g => g.is_builtin && g.role_type && g.role_type !== 'other' && g.role_type === char.role_type
      )
      return !matchedDefault
    }
    return char.role_type === group.role_type
  }
  return false
}

// 按分组 ID 分组
const groupedCharacters = computed(() => {
  const sortedGroups = [...characterGroups.value].sort((a, b) => a.sort_index - b.sort_index)

  const result: { group: CharacterGroup; items: CharacterItem[] }[] = []

  for (const group of sortedGroups) {
    const items = filteredCharacters.value.filter(c => {
      // 如果角色有 group_id，直接匹配
      if (c.group_id != null) {
        return c.group_id === group.id
      }
      // 没有 group_id 的角色，根据 role_type 分配到默认分组
      if (group.is_builtin && group.role_type) {
        if (group.role_type === 'other') {
          // 其他分组：放所有不能匹配到其他默认分组的角色
          const matchedDefault = sortedGroups.some(
            g => g.is_builtin && g.role_type && g.role_type !== 'other' && g.role_type === c.role_type
          )
          return !matchedDefault
        }
        return c.role_type === group.role_type
      }
      return false
    })

    // 按 sort_index 排序，没有 sort_index 的放后面
    items.sort((a, b) => (a.sort_index ?? 9999) - (b.sort_index ?? 9999))

    // 所有分组都显示（包括空的自定义分组，方便管理）
    result.push({ group, items })
  }

  return result
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

const availableCharacterOptions = computed(() => {
  const boundIds = new Set(
    form.character_relations
      .filter((_, idx) => idx !== editingRelationIndex.value)
      .map((r) => Number(r.target_id))
      .filter((id) => id > 0)
  )
  return characters.value
    .filter((c) => c.id !== editingId.value)
    .map((c) => ({
      label: c.name,
      value: c.id,
      disabled: boundIds.has(c.id)
    }))
})

const canAddMoreRelations = computed(() => {
  const totalAvailable = characters.value.filter((c) => c.id !== editingId.value).length
  const boundCount = form.character_relations.filter((r) => r.target_id > 0).length
  return boundCount < totalAvailable
})

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
function getOrgNameById(id: number | string | null | undefined): string {
  if (id == null || id === '') return '未知组织'
  const nid = Number(id)
  if (!nid || nid <= 0) return '未知组织'
  return organizations.value.find((o) => o.id === nid)?.name || `组织#${nid}`
}
function getCharacterNameById(id: number | string | null | undefined): string {
  if (id == null || id === '') return '未知角色'
  const nid = Number(id)
  if (!nid || nid <= 0) return '未知角色'
  return characters.value.find((c) => c.id === nid)?.name || `角色#${nid}`
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
  return dictStore.label('character_role', value) || '其他'
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
  form.custom_attributes.push({
    key: '',
    name: '',
    value: '',
    description: '',
    chapter_no: null,
    change_reason: ''
  })
}
function addAttributeFromTemplate(key: string, label: string) {
  form.custom_attributes.push({
    key,
    name: label,
    title: label,
    value: '',
    description: '',
    chapter_no: null,
    change_reason: ''
  })
}
function removeAttribute(index: number) {
  form.custom_attributes.splice(index, 1)
}

// 属性 key 变化时，同步更新 name/title
function onAttrKeyChange(index: number, key: string) {
  const attr = form.custom_attributes[index]
  if (!attr) return
  const dictItems = dictStore.items('attribute_name')
  const found = dictItems.find(i => i.item_value === key)
  if (found) {
    attr.name = found.item_label
    attr.title = found.item_label
  } else {
    attr.name = key
    attr.title = key
  }
}

// 解析章节范围字符串（"3" 或 "3-5"）
function parseChapterRange(chapterNo: string | null | undefined): { start: number | null; end: number | null } {
  if (!chapterNo) return { start: null, end: null }
  const parts = String(chapterNo).split('-').map(s => s.trim())
  const start = parts[0] ? Number(parts[0]) : null
  const end = parts.length > 1 && parts[1] ? Number(parts[1]) : null
  return {
    start: isNaN(start as number) ? null : start,
    end: isNaN(end as number) ? null : end
  }
}

// 章节范围变化
function onChapterChange(index: number, field: 'start' | 'end', val: number | null) {
  const attr = form.custom_attributes[index]
  if (!attr) return
  const current = parseChapterRange(attr.chapter_no)
  if (field === 'start') {
    current.start = val
  } else {
    current.end = val
  }
  // 序列化回字符串
  if (current.start != null && current.end != null && current.end > current.start) {
    attr.chapter_no = `${current.start}-${current.end}`
  } else if (current.start != null) {
    attr.chapter_no = String(current.start)
  } else {
    attr.chapter_no = null
  }
}

// ===== 组织关系操作 =====
function resetNewOrgRelation() {
  newOrgRelation.org_id = null
  newOrgRelation.position = ''
  newOrgRelation.loyalty = 5
}

function startAddOrgRelation() {
  if (!canAddMoreOrgs.value) {
    notify.info('所有可选组织都已添加关系')
    return
  }
  isAddingOrgRelation.value = true
  editingOrgRelationIndex.value = null
  resetNewOrgRelation()
}

function confirmAddOrgRelation() {
  if (!newOrgRelation.org_id) {
    notify.warning('请先选择组织')
    return
  }
  if (form.org_relations.some((r) => r.org_id === newOrgRelation.org_id)) {
    notify.warning('该组织已添加')
    return
  }
  form.org_relations.push({
    org_id: Number(newOrgRelation.org_id) || 0,
    position: newOrgRelation.position || '无',
    loyalty: Number(newOrgRelation.loyalty) || 5
  })
  form.organization_ids = joinIds(form.org_relations.map((r) => r.org_id))
  isAddingOrgRelation.value = false
  resetNewOrgRelation()
}

function cancelAddOrgRelation() {
  isAddingOrgRelation.value = false
  resetNewOrgRelation()
}

function startEditOrgRelation(index: number) {
  const rel = form.org_relations[index]
  editingOrgRelationIndex.value = index
  isAddingOrgRelation.value = false
  newOrgRelation.org_id = Number(rel.org_id) || null
  newOrgRelation.position = rel.position || '无'
  newOrgRelation.loyalty = Number(rel.loyalty) || 5
}

function saveEditOrgRelation() {
  if (editingOrgRelationIndex.value == null) return
  if (!newOrgRelation.org_id) {
    notify.warning('请先选择组织')
    return
  }
  const idx = editingOrgRelationIndex.value
  form.org_relations[idx] = {
    org_id: Number(newOrgRelation.org_id) || 0,
    position: newOrgRelation.position || '无',
    loyalty: Number(newOrgRelation.loyalty) || 5
  }
  form.organization_ids = joinIds(form.org_relations.map((r) => r.org_id))
  editingOrgRelationIndex.value = null
  resetNewOrgRelation()
}

function cancelEditOrgRelation() {
  editingOrgRelationIndex.value = null
  resetNewOrgRelation()
}

function removeOrgRelation(index: number) {
  form.org_relations.splice(index, 1)
  form.organization_ids = joinIds(form.org_relations.map((r) => r.org_id))
}

// ===== 人物关系操作 =====
function resetNewCharRelation() {
  newCharRelation.target_id = null
  newCharRelation.relation_type = '其他'
  newCharRelation.depth = 5
  newCharRelation.effective_from = null
  newCharRelation.expires_at = null
}

function startAddRelation() {
  if (!canAddMoreRelations.value) {
    notify.info('所有可选角色都已添加人物关系')
    return
  }
  isAddingRelation.value = true
  editingRelationIndex.value = null
  resetNewCharRelation()
}

function confirmAddRelation() {
  if (!newCharRelation.target_id) {
    notify.warning('请先选择角色')
    return
  }
  if (form.character_relations.some((r) => r.target_id === newCharRelation.target_id)) {
    notify.warning('该角色已添加关系')
    return
  }
  form.character_relations.push({
    target_id: Number(newCharRelation.target_id) || 0,
    relation_type: newCharRelation.relation_type || '其他',
    depth: Number(newCharRelation.depth) || 5,
    effective_from: newCharRelation.effective_from ? Number(newCharRelation.effective_from) : null,
    expires_at: newCharRelation.expires_at ? Number(newCharRelation.expires_at) : null
  })
  form.related_character_ids = joinIds(form.character_relations.map((r) => r.target_id))
  isAddingRelation.value = false
  resetNewCharRelation()
}

function cancelAddRelation() {
  isAddingRelation.value = false
  resetNewCharRelation()
}

function startEditRelation(index: number) {
  const rel = form.character_relations[index]
  editingRelationIndex.value = index
  isAddingRelation.value = false
  newCharRelation.target_id = Number(rel.target_id) || null
  newCharRelation.relation_type = rel.relation_type || '其他'
  newCharRelation.depth = Number(rel.depth) || 5
  newCharRelation.effective_from = rel.effective_from ? Number(rel.effective_from) : null
  newCharRelation.expires_at = rel.expires_at ? Number(rel.expires_at) : null
}

function saveEditRelation() {
  if (editingRelationIndex.value == null) return
  if (!newCharRelation.target_id) {
    notify.warning('请先选择角色')
    return
  }
  const idx = editingRelationIndex.value
  form.character_relations[idx] = {
    target_id: Number(newCharRelation.target_id) || 0,
    relation_type: newCharRelation.relation_type || '其他',
    depth: Number(newCharRelation.depth) || 5,
    effective_from: newCharRelation.effective_from ? Number(newCharRelation.effective_from) : null,
    expires_at: newCharRelation.expires_at ? Number(newCharRelation.expires_at) : null
  }
  form.related_character_ids = joinIds(form.character_relations.map((r) => r.target_id))
  editingRelationIndex.value = null
  resetNewCharRelation()
}

function cancelEditRelation() {
  editingRelationIndex.value = null
  resetNewCharRelation()
}

function removeCharRelation(index: number) {
  form.character_relations.splice(index, 1)
  form.related_character_ids = joinIds(form.character_relations.map((r) => r.target_id))
}

// ===== 分组图标与标签 =====
function groupIcon(group: CharacterGroup): string {
  if (group.is_builtin && group.role_type) {
    return roleTypeIcon(group.role_type)
  }
  return '📁'
}

function groupLabel(group: CharacterGroup): string {
  if (group.is_builtin && group.role_type) {
    return roleTypeLabel(group.role_type)
  }
  return group.name
}

// ===== 分组管理 =====
function startCreateGroup() {
  newGroupName.value = ''
  isCreatingGroup.value = true
}

function cancelCreateGroup() {
  isCreatingGroup.value = false
  newGroupName.value = ''
}

async function confirmCreateGroup() {
  const name = newGroupName.value.trim()
  if (!name) {
    notify.warning('请输入分组名称')
    return
  }
  const projectId = projectStore.currentProject?.id
  if (!projectId) return

  const maxSort = characterGroups.value.reduce((max, g) => Math.max(max, g.sort_index), 0)

  const newGroup = await createResource<CharacterGroup>('character-groups', {
    project_id: projectId,
    name,
    group_type: 'custom',
    role_type: null,
    sort_index: maxSort + 1,
    color: null,
    is_builtin: false,
  })

  characterGroups.value.push(newGroup)
  // 为新分组初始化空角色列表
  groupCharacters[newGroup.id] = []
  // 展开新建的分组
  const next = new Set(expandedGroups.value)
  next.add(newGroup.id)
  expandedGroups.value = next

  isCreatingGroup.value = false
  newGroupName.value = ''
  notify.success('分组已创建')
}

function startRenameGroup(group: CharacterGroup) {
  if (group.is_builtin) return
  renamingGroupId.value = group.id
  renamingGroupName.value = group.name
}

function cancelRenameGroup() {
  renamingGroupId.value = null
  renamingGroupName.value = ''
}

async function confirmRenameGroup(group: CharacterGroup) {
  const name = renamingGroupName.value.trim()
  if (!name) {
    notify.warning('分组名称不能为空')
    return
  }
  if (name === group.name) {
    cancelRenameGroup()
    return
  }

  const updated = await updateResource<CharacterGroup>('character-groups', group.id, { name })
  const idx = characterGroups.value.findIndex(g => g.id === group.id)
  if (idx !== -1) {
    characterGroups.value[idx] = updated
  }
  renamingGroupId.value = null
  renamingGroupName.value = ''
  notify.success('分组已重命名')
}

async function deleteGroup(group: CharacterGroup) {
  if (group.is_builtin) return
  await deleteResource('character-groups', group.id)
  characterGroups.value = characterGroups.value.filter(g => g.id !== group.id)
  // 将该分组的角色的 group_id 置空（它们会自动按 role_type 回到默认分组）
  characters.value = characters.value.map(c =>
    c.group_id === group.id ? { ...c, group_id: undefined } : c
  )
  // 重建分组角色映射
  delete groupCharacters[group.id]
  rebuildGroupCharacters()
  notify.success('分组已删除')
}

// ===== 拖拽排序 - 分组 =====
async function onGroupDragEnd() {
  isDraggingGroup.value = false
  // 按当前顺序更新 sort_index
  const sortedGroups = [...characterGroups.value].sort((a, b) => a.sort_index - b.sort_index)
  const updates: Promise<CharacterGroup>[] = []
  sortedGroups.forEach((group, index) => {
    if (group.sort_index !== index) {
      group.sort_index = index
      updates.push(updateResource<CharacterGroup>('character-groups', group.id, { sort_index: index }))
    }
  })
  if (updates.length > 0) {
    await Promise.all(updates)
  }
}

// 用于 vuedraggable 的分组列表（响应式，可被拖拽修改顺序）
const draggableGroups = computed({
  get: () => {
    // 返回按 sort_index 排序的分组引用
    return [...characterGroups.value].sort((a, b) => a.sort_index - b.sort_index)
  },
  set: (newList: CharacterGroup[]) => {
    // 拖拽结束时更新 sort_index
    newList.forEach((group, index) => {
      const g = characterGroups.value.find(cg => cg.id === group.id)
      if (g) {
        g.sort_index = index
      }
    })
  }
})

// ===== 拖拽排序 - 角色 =====
// 角色拖拽结束时的处理：同步所有分组角色顺序到后端
async function onCharacterDragEnd(_groupId: number) {
  isDraggingCharacter.value = false
  const updates: Promise<CharacterItem>[] = []

  // 遍历所有分组，更新每个角色的 sort_index 和 group_id
  for (const group of characterGroups.value) {
    const items = groupCharacters[group.id] || []
    items.forEach((item, index) => {
      const originalChar = characters.value.find(c => c.id === item.id)
      if (!originalChar) return

      const newGroupId = group.is_builtin ? null : group.id
      const needsUpdate =
        originalChar.sort_index !== index ||
        originalChar.group_id !== newGroupId

      if (needsUpdate) {
        originalChar.sort_index = index
        originalChar.group_id = newGroupId ?? undefined
        updates.push(
          updateResource<CharacterItem>('characters', item.id, {
            sort_index: index,
            group_id: newGroupId,
          })
        )
      }
    })
  }

  if (updates.length > 0) {
    await Promise.all(updates)
  }
}

// 判断角色是否匹配搜索/筛选条件
function matchesFilter(item: CharacterItem): boolean {
  const text = keyword.value.trim().toLowerCase()
  const matchedText =
    !text || searchableFields.value.map((field) => item[field] ?? '').join(' ').toLowerCase().includes(text)
  const matchedGroup = groupFilter.value == null || isCharacterInGroup(item, groupFilter.value)
  return matchedText && matchedGroup
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
    custom_attributes: safeParseArray<CharacterAttribute>(item?.custom_attributes).map((r) => {
      // 兼容旧数据：如果 key 无效但 name 能匹配字典，反查 key
      let key = r.key || ''
      let title = r.title || r.name || ''
      let name = r.name || r.title || r.key || ''
      const dictItems = dictStore.items('attribute_name')
      const foundByKey = dictItems.find(i => i.item_value === key)
      if (!foundByKey && name) {
        // 尝试用 name 反查
        const foundByName = dictItems.find(i => i.item_label === name || i.item_value === name)
        if (foundByName) {
          key = foundByName.item_value
          title = foundByName.item_label
          name = foundByName.item_label
        } else if (!key) {
          // 自定义属性，没有对应字典，用 name 作 key
          key = name
        }
      } else if (foundByKey) {
        title = foundByKey.item_label
        if (!name) name = foundByKey.item_label
      }
      return {
        key,
        title,
        name,
        value: r.value || '',
        description: r.description || '',
        chapter_no: r.chapter_no != null && r.chapter_no !== '' ? String(r.chapter_no) : null,
        change_reason: r.change_reason || ''
      }
    }),
    org_relations: safeParseArray<CharacterOrgRelation>(item?.org_relations).map((r) => ({
      ...r,
      org_id: Number(r.org_id) || 0,
      loyalty: Number(r.loyalty) || 5
    })),
    character_relations: safeParseArray<CharacterRelation>(item?.character_relations).map((r) => ({
      ...r,
      target_id: Number(r.target_id) || 0,
      depth: Number(r.depth) || 5,
      effective_from: r.effective_from ? Number(r.effective_from) : null,
      expires_at: r.expires_at ? Number(r.expires_at) : null
    })),
    mbti: item?.mbti ?? '',
    status: item?.status ?? 'active'
  })
  markClean()
  // 重置编辑状态
  isAddingOrgRelation.value = false
  editingOrgRelationIndex.value = null
  isAddingRelation.value = false
  editingRelationIndex.value = null
  resetNewOrgRelation()
  resetNewCharRelation()
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
    const [characterList, organizationList, groupList] = await Promise.all([
      listResource<CharacterItem>(projectId, 'characters'),
      listResource<OrganizationItem>(projectId, 'organizations'),
      listResource<CharacterGroup>(projectId, 'character-groups'),
      dictStore.load('character_role'),
      dictStore.load('mbti_type'),
      dictStore.load('character_identity'),
      dictStore.load('character_motivation'),
      dictStore.load('character_weakness'),
      dictStore.load('dialogue_style'),
      dictStore.load('personality_trait'),
      dictStore.load('character_faction'),
      dictStore.load('character_appearance'),
      dictStore.load('character_background'),
      dictStore.load('character_secret'),
      dictStore.load('character_arc'),
      dictStore.load('attribute_name'),
      dictStore.load('relation_type'),
      dictStore.load('ai_notes'),
      dictStore.load('relation_summary'),
    ])
    characters.value = characterList
    organizations.value = organizationList
    characterGroups.value = groupList
    rebuildGroupCharacters()

    // 初始化分组展开状态（首次加载全部展开）
    if (expandedGroups.value.size === 0) {
      initExpandedGroups()
    }

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
  grid-template-columns: var(--left-panel-width, 320px) minmax(520px, 1fr) var(--right-panel-width, 280px);
  gap: 12px;
  min-height: 0;
  min-width: 0;
  position: relative;
  transition: grid-template-columns 0.3s ease;
}

.workbench.is-resizing {
  transition: none !important;
}

.workbench.is-resizing .list-panel,
.workbench.is-resizing .side-panel {
  transition: none !important;
}

.workbench.left-collapsed {
  /* 由 CSS 变量控制 */
}

.workbench.side-collapsed {
  /* 由 CSS 变量控制 */
}

.workbench.left-collapsed.side-collapsed {
  /* 由 CSS 变量控制 */
}

/* 拖拽条 */
.panel-resizer {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 12px;
  left: calc(var(--left-panel-width, 320px) + 6px);
  transform: translateX(-50%);
  cursor: col-resize;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
}

.panel-resizer:hover,
.panel-resizer.active {
  opacity: 1;
}

.resizer-handle {
  width: 3px;
  height: 40px;
  background: var(--n-primary-color, #6366f1);
  border-radius: 2px;
  opacity: 0.6;
}

.panel-resizer:hover .resizer-handle,
.panel-resizer.active .resizer-handle {
  opacity: 1;
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

.list-panel-count {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  background: var(--n-color-2, #2a2f3a);
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
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
  cursor: pointer;
  transition: color 0.2s ease;
  user-select: none;
}

.group-header:hover {
  color: var(--n-text-color-1, #e5e7eb);
}

.group-header:hover .group-actions-right {
  opacity: 1;
}

/* 拖拽手柄 */
.drag-handle {
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: grab;
  color: var(--n-text-color-3, #6b7280);
  flex-shrink: 0;
  opacity: 0.5;
  transition: opacity 0.2s, color 0.2s;
}

.drag-handle:hover {
  opacity: 1;
  color: var(--n-text-color-1, #e5e7eb);
}

.drag-handle:active {
  cursor: grabbing;
}

.drag-handle svg {
  width: 14px;
  height: 14px;
}

.group-drag-handle {
  width: 16px;
  height: 16px;
}

.char-drag-handle {
  width: 14px;
  height: 14px;
  align-self: center;
  margin-right: 2px;
}

/* 分组右侧操作按钮 */
.group-actions-right {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-left: auto;
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

.field-desc {
  margin-top: 6px;
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
  line-height: 1.5;
}

/* MBTI 信息卡片 */
.mbti-info-card {
  margin-top: 8px;
  padding: 10px 12px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(139, 92, 246, 0.08) 100%);
  border: 1px solid rgba(99, 102, 241, 0.25);
  border-radius: 8px;
}

.mbti-info-card.secondary {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(147, 51, 234, 0.06) 100%);
  border-color: rgba(59, 130, 246, 0.2);
}

.mbti-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.mbti-card-code {
  font-size: 14px;
  font-weight: 700;
  color: #a5b4fc;
  letter-spacing: 0.5px;
}

.mbti-card-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--n-text-color-1, #e5e7eb);
}

.mbti-card-desc {
  font-size: 11px;
  color: var(--n-text-color-2, #9ca3af);
  line-height: 1.6;
}

/* MBTI 下拉选项自定义渲染 */
.mbti-option-render {
  font-size: 13px;
  color: var(--n-text-color-1, #e5e7eb);
  font-weight: 500;
  padding: 2px 0;
}

/* MBTI 选中标签渲染 */
.mbti-tag-render {
  font-size: 12px;
  font-weight: 500;
}

/* MBTI 下拉选项 tooltip */
.mbti-option-tooltip {
  max-width: 280px;
}

.mbti-option-tooltip-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.mbti-option-tooltip-code {
  font-size: 13px;
  font-weight: 700;
  color: #a5b4fc;
  letter-spacing: 0.5px;
}

.mbti-option-tooltip-name {
  font-size: 13px;
  font-weight: 600;
  color: #e5e7eb;
}

.mbti-option-tooltip-desc {
  font-size: 12px;
  color: #9ca3af;
  line-height: 1.6;
}

/* MBTI 选中标签 tooltip */
.mbti-tag-tooltip {
  max-width: 260px;
}

.mbti-tag-tooltip-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.mbti-tag-tooltip-code {
  font-size: 12px;
  font-weight: 700;
  color: #a5b4fc;
  letter-spacing: 0.5px;
}

.mbti-tag-tooltip-name {
  font-size: 12px;
  font-weight: 600;
  color: #e5e7eb;
}

.mbti-tag-tooltip-desc {
  font-size: 11px;
  color: #9ca3af;
  line-height: 1.5;
}

/* MBTI 外层 tooltip 内容（保留兼容） */
.mbti-tooltip-content {
  max-width: 280px;
}

.mbti-tooltip-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.mbti-tooltip-code {
  font-size: 13px;
  font-weight: 700;
  color: #a5b4fc;
  letter-spacing: 0.5px;
}

.mbti-tooltip-name {
  font-size: 12px;
  font-weight: 600;
  color: #e5e7eb;
}

.mbti-tooltip-desc {
  font-size: 11px;
  color: #9ca3af;
  line-height: 1.6;
}

/* 标签选择 + textarea 组合布局 */
.tag-select-above {
  margin-bottom: 8px;
}

.personality-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.personality-tag {
  cursor: pointer;
  transition: all 0.2s;
}

.personality-tag:hover {
  opacity: 0.8;
  background: var(--n-color-primary-1-suppl, #1e3a5f) !important;
  color: #a5b4fc !important;
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

/* 出场章节管理器 */
.chapter-range-manager {
  width: 100%;
}

.chapter-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.chapter-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px 6px 8px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  border: 1px solid rgba(102, 126, 234, 0.25);
  border-radius: 16px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.85);
  transition: all 0.2s ease;
}

.chapter-tag:hover {
  border-color: rgba(102, 126, 234, 0.5);
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 100%);
}

.chapter-tag.is-range {
  background: linear-gradient(135deg, rgba(24, 160, 88, 0.1) 0%, rgba(102, 126, 234, 0.1) 100%);
  border-color: rgba(24, 160, 88, 0.25);
}

.chapter-tag.is-range:hover {
  border-color: rgba(24, 160, 88, 0.5);
}

.chapter-tag-icon {
  font-size: 12px;
  flex-shrink: 0;
}

.chapter-tag-text {
  font-weight: 500;
  white-space: nowrap;
}

.chapter-tag-remove {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  padding: 0 !important;
  border-radius: 50% !important;
  opacity: 0.5;
  margin-left: 2px;
  transition: all 0.2s ease !important;
}

.chapter-tag-remove:hover {
  opacity: 1;
  color: #d03050 !important;
  background: rgba(208, 48, 80, 0.15) !important;
}

.chapter-add-tag {
  cursor: pointer;
  border-style: dashed;
  border-color: rgba(255, 255, 255, 0.2);
  background: transparent;
  color: rgba(255, 255, 255, 0.5);
  gap: 4px;
}

.chapter-add-tag:hover {
  border-color: rgba(102, 126, 234, 0.5);
  color: rgba(102, 126, 234, 0.9);
  background: rgba(102, 126, 234, 0.08);
}

.chapter-add-panel {
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  margin-bottom: 12px;
}

.chapter-add-inputs {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.chapter-add-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  flex-shrink: 0;
}

.chapter-add-num {
  width: 80px;
  flex-shrink: 0;
}

.chapter-mode-toggle {
  flex-shrink: 0;
}

.chapter-add-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.chapter-empty {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px dashed rgba(255, 255, 255, 0.1);
  border-radius: 8px;
}

.chapter-empty-icon {
  font-size: 20px;
}

.chapter-empty-text {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.4);
  flex: 1;
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
  align-items: flex-start;
  margin-bottom: 8px;
}

.attr-name-field {
  width: 130px;
  flex-shrink: 0;
}

.attr-value-field {
  flex: 1;
  min-width: 0;
}

.attr-chapter-box {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  height: 34px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  white-space: nowrap;
  transition: all 0.2s ease;
}

.attr-chapter-box:hover {
  border-color: var(--n-border-color-hover, #3a4050);
  background: rgba(255, 255, 255, 0.06);
}

.attr-chapter-box.is-filled {
  border-color: rgba(102, 126, 234, 0.3);
}

.attr-chapter-box.has-range {
  border-color: rgba(24, 160, 88, 0.3);
}

.attr-chapter-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  flex-shrink: 0;
}

.attr-chapter-num {
  width: 50px;
  --n-padding-left: 4px;
  --n-padding-right: 4px;
}

.attr-chapter-num :deep(.n-input) {
  background: transparent;
  border: none;
  height: 26px;
}

.attr-chapter-num :deep(.n-input__border) {
  display: none;
}

.attr-chapter-num :deep(.n-input__input-el) {
  text-align: center;
  font-size: 13px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.9);
}

.attr-chapter-num :deep(.n-input__placeholder) {
  font-size: 11px;
  opacity: 0.4;
}

.attr-chapter-mode {
  flex-shrink: 0;
  margin: 0 2px;
}

.attr-chapter-mode :deep(.n-radio) {
  font-size: 11px;
}

.attr-chapter-mode :deep(.n-radio__dot) {
  width: 12px;
  height: 12px;
}

.attr-chapter-mode :deep(.n-radio__dot svg) {
  width: 8px;
  height: 8px;
}

.attr-reason-input {
  flex: 1;
  min-width: 0;
}

.attr-sub-row {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.attr-desc-input {
  flex: 1;
  min-width: 0;
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
  min-height: 52px;
}

.relation-main {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  justify-content: center;
}

.relation-main-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.relation-chapter-row {
  display: flex;
  align-items: center;
  gap: 6px;
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

/* 添加关系按钮行 */
.add-relation-row {
  margin-bottom: 12px;
  display: flex;
  justify-content: flex-start;
}

/* 行内编辑表单 */
.relation-edit-form {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.relation-edit-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.relation-edit-field {
  flex: 1;
  min-width: 120px;
}

.relation-edit-number {
  width: 120px;
}

.relation-edit-actions {
  margin-left: auto;
  display: flex;
  gap: 6px;
}

.relation-edit-item {
  background: rgba(99, 102, 241, 0.08);
  border-color: rgba(99, 102, 241, 0.3);
}

/* ===== 右侧面板 ===== */
.side-panel {
  padding: 0;
  gap: 0;
  overflow: hidden;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
}

.side-panel.collapsed {
  width: 56px;
  min-width: 56px;
}

.side-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  flex-shrink: 0;
}

.side-panel.collapsed .side-panel-header {
  justify-content: center;
  padding: 10px 8px;
}

.side-panel-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--n-text-color-1, #e5e7eb);
}

.panel-toggle-btn {
  width: 24px;
  height: 24px;
  padding: 0 !important;
  border-radius: 6px !important;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease !important;
}

.panel-toggle-btn:hover {
  background: var(--n-color-hover, #2a2f3a) !important;
}

/* 折叠态图标导航 */
.side-panel-icons {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 6px;
  overflow-y: auto;
}

.side-icon-item {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}

.side-icon-item:hover {
  background: var(--n-color-hover, #2a2f3a);
}

.side-icon-item.active {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.2) 0%, rgba(139, 92, 246, 0.2) 100%);
}

.side-icon-item.active::before {
  content: '';
  position: absolute;
  left: -6px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  background: var(--n-color-primary, #3b82f6);
  border-radius: 0 2px 2px 0;
}

.side-icon {
  font-size: 18px;
}

/* 展开态目录导航 */
.side-nav {
  flex-shrink: 0;
  padding: 8px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.side-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.side-nav-item:hover {
  background: var(--n-color-hover, #2a2f3a);
}

.side-nav-item.active {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(139, 92, 246, 0.15) 100%);
}

.side-nav-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.side-nav-label {
  flex: 1;
  font-size: 12px;
  font-weight: 500;
  color: var(--n-text-color-2, #9ca3af);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.side-nav-item.active .side-nav-label {
  color: var(--n-text-color-1, #e5e7eb);
}

.side-nav-arrow {
  flex-shrink: 0;
  color: var(--n-text-color-3, #6b7280);
  transition: transform 0.2s ease;
}

.side-nav-arrow.expanded {
  transform: rotate(180deg);
}

/* 内容区域 */
.side-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.side-section-card {
  animation: fadeIn 0.25s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
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
