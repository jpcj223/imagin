<template>
  <div class="page chapter-generate-page">
    <!-- 页头 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <span class="title-icon">✨</span>
          章节生成工作台
        </h1>
        <p class="page-subtitle">
          选择大纲 → 调整参数 → 生成正文 → 分析沉淀
        </p>
      </div>
      <div class="header-right">
        <div class="header-stats">
          <div class="stat">
            <span class="stat-num">{{ outlines.length }}</span>
            <span class="stat-label">大纲</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num">{{ chapters.length }}</span>
            <span class="stat-label">章节草稿</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num success">{{ wordCount }}</span>
            <span class="stat-label">当前字数</span>
          </div>
        </div>
        <n-button size="small" @click="loadResources" :loading="loading">
          <template #icon>🔄</template>
          刷新资料
        </n-button>
      </div>
    </div>

    <!-- 工作流流水线 - 页面架构主轴 -->
    <div v-if="pipelineSteps.length > 0" class="pipeline-section">
      <WorkflowPipeline
        :steps="pipelineSteps"
        :active-step-id="currentWorkflowStep"
        :template-name="selectedWorkflow"
        :template-label="workflowTemplates.find(t => t.name === selectedWorkflow)?.label"
        @step-click="handlePipelineStepClick"
        @restart="handleRestartFromStep"
      />
    </div>

    <!-- 三栏主体 -->
    <div class="workbench">
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
              <span class="brief-count">{{ totalSelectedCount }}</span> 项资料
            </span>
          </div>
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
              :title="keyword.trim() ? `${tab.label}：${tab.matchCount} 个匹配` : tab.label"
            >
              <span class="tab-icon">{{ tab.icon }}</span>
              <span v-if="tab.count > 0" class="tab-badge" :class="{ 'match-badge': keyword.trim() && tab.matchCount > 0 }">
                {{ keyword.trim() ? tab.matchCount : tab.count }}
              </span>
            </div>
          </div>

          <n-scrollbar class="resource-tab-content">
            <!-- 大纲 Tab -->
            <div v-if="leftActiveTab === 'outline'" class="tab-list">
              <div v-if="filteredOutlines.length === 0" class="list-empty">
                <template v-if="keyword.trim()">🔍 未找到匹配「{{ keyword }}」的大纲</template>
                <template v-else>暂无大纲</template>
              </div>
              <div
                v-for="item in filteredOutlines"
                :key="item.id"
                class="resource-item"
                :class="{ active: form.outline_id === item.id }"
                @click="selectOutline(item)"
              >
                <div class="item-main">
                  <div class="item-title" v-html="safeHighlight(item.title)"></div>
                  <div class="item-meta">
                    <span class="chapter-no-badge">#{{ item.chapter_no ?? item.sort_index }}</span>
                    <span v-html="safeHighlight(item.description)"></span>
                  </div>
                </div>
              </div>
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

      <!-- ===== 中间：正文编辑器 ===== -->
      <section class="editor-panel">
        <!-- 编辑器工具栏 -->
        <div class="editor-toolbar">
          <div class="toolbar-left">
            <n-input
              v-model:value="chapterTitle"
              class="title-input"
              placeholder="章节标题..."
              size="large"
              :bordered="false"
            />
          </div>
          <div class="toolbar-right">
            <div class="word-count">
              <span class="count-num">{{ wordCount }}</span>
              <span class="count-label">字</span>
            </div>
            <n-divider vertical />
            <span class="save-status" :class="{ saved: chapterId }">
              {{ chapterId ? '💾 已保存' : '📝 未保存' }}
            </span>
            <n-divider v-if="chapterId" vertical />
            <span v-if="chapterId" class="chapter-id">ID {{ chapterId }}</span>
          </div>
        </div>

        <!-- 正文编辑器 -->
        <div class="editor-container">
          <n-input
            v-model:value="draft"
            type="textarea"
            class="chapter-textarea"
            :autosize="{ minRows: 20 }"
            :bordered="false"
            placeholder="在这里写你的小说正文...

提示：
1. 从左侧选择大纲，生成参数会自动填充
2. 调整右侧参数后点击「生成章节」
3. 生成后可进行分析、精修、一致性检查"
          />
        </div>

        <!-- 精修高亮对比面板 -->
        <div v-if="hasPolishHighlights" class="polish-panel">
          <div class="polish-header">
            <span class="polish-title">🎨 精修对比</span>
            <n-tag size="tiny" type="warning">高亮段落为精修后变化的内容</n-tag>
            <n-button size="tiny" text @click="polishOriginal = ''">关闭对比</n-button>
          </div>
          <div class="polish-content">
            <p
              v-for="(segment, index) in polishSegments"
              :key="`${index}-${segment.status}`"
              :class="['polish-segment', segment.status]"
            >
              {{ segment.text }}
            </p>
          </div>
        </div>
      </section>

      <!-- ===== 右侧：Tab 面板 ===== -->
      <aside class="right-panel">
        <n-tabs v-model:value="activeTab" type="line" size="small" class="side-tabs">
          <!-- Tab: 生成参数 -->
          <n-tab-pane name="params" tab="参数">
            <div class="tab-content">
              <!-- Agent 插件卡片 - 架构可视化 -->
              <div class="form-block">
                <AgentPluginCard
                  agent-name="写作师 Agent"
                  agent-description="v3.0 插件化架构"
                  agent-icon="✍️"
                  :variant-id="userPrefs.default_writer_variant"
                  :variant-name="activeVariantName"
                  :variants="writerVariants"
                  :skills="agentSkills"
                  :temperature="userPrefs.default_temperature"
                  @variant-change="handleVariantChange"
                  @skill-toggle="handleSkillToggle"
                />
              </div>

              <!-- 工作流进度（生成中/生成后显示） -->
              <div v-if="showWorkflowPanel" class="form-block workflow-progress-block">
                <div class="block-title">
                  生成进度
                  <span class="progress-percent">{{ Math.round(workflowProgress) }}%</span>
                  <n-button text size="tiny" @click="showWorkflowPanel = false">收起</n-button>
                </div>
                <WorkflowProgress
                  :steps="workflowSteps"
                  :current-step-id="currentWorkflowStep"
                  :overall-progress="workflowProgress"
                  @restart="handleRestartFromStep"
                />
              </div>

              <!-- 章节设置 -->
              <div class="form-block">
                <div class="block-title">章节设置</div>
                <n-form label-placement="top" :show-label="true">
                  <div class="form-row">
                    <n-form-item label="章节号" style="flex: 0 0 100px">
                      <n-input-number v-model:value="form.chapter_no" :min="1" style="width: 100%" />
                    </n-form-item>
                    <n-form-item label="节奏等级">
                      <n-select v-model:value="form.rhythm_level" :options="rhythmOptions" />
                    </n-form-item>
                  </div>
                  <n-form-item label="本章目标">
                    <n-input
                      v-model:value="form.instruction"
                      type="textarea"
                      :autosize="{ minRows: 4, maxRows: 6 }"
                      placeholder="选择大纲后会自动带入，也可以手动修改"
                    />
                  </n-form-item>
                  <n-form-item label="本章重点伏笔">
                    <n-select
                      v-model:value="selectedForeshadowingIds"
                      multiple
                      filterable
                      tag
                      :options="foreshadowingOptions"
                      placeholder="选择本章要埋设或回收的伏笔"
                    />
                    <div class="field-hint">
                      选中的伏笔会优先进入上下文包，帮助 AI 在本章精准推进剧情线。
                    </div>
                  </n-form-item>
                </n-form>
              </div>

              <!-- 生成模式选择 -->
              <div class="form-block">
                <div class="block-title">生成模式</div>
                <div class="workflow-template-list">
                  <div
                    v-for="tpl in workflowTemplates"
                    :key="tpl.name"
                    :class="['workflow-template-card', { selected: selectedWorkflow === tpl.name }]"
                    @click="selectedWorkflow = tpl.name"
                  >
                    <div class="tpl-icon">{{ tpl.icon }}</div>
                    <div class="tpl-info">
                      <div class="tpl-name">{{ tpl.label }}</div>
                      <div class="tpl-desc">{{ tpl.description }}</div>
                    </div>
                    <div class="tpl-steps">{{ tpl.step_count }} 步</div>
                  </div>
                </div>
              </div>

              <!-- 生成操作 -->
              <div class="form-block">
                <div class="block-title">生成操作</div>
                <div class="action-buttons">
                  <n-button
                    v-if="isInterrupted && interruptedRunId"
                    type="warning"
                    block
                    size="large"
                    :loading="loading"
                    :disabled="loading"
                    @click="resumeGenerateV3"
                  >
                    <template #icon>⏯️</template>
                    继续生成（断点续传）
                  </n-button>
                  <n-button
                    v-if="currentRunId && !isInterrupted && !showWorkflowPanel"
                    block
                    :disabled="loading"
                    @click="showWorkflowPanel = true"
                  >
                    <template #icon>📊</template>
                    查看生成进度 / 重跑步骤
                  </n-button>
                  <n-button
                    type="primary"
                    block
                    size="large"
                    :loading="loading"
                    :disabled="loading"
                    @click="requestGenerate('generate')"
                  >
                    <template #icon>✨</template>
                    {{ isInterrupted ? '从头重新生成' : (hasExistingDraft ? '重新生成章节' : '生成章节') }}
                  </n-button>
                  <n-button
                    v-if="!useV3Workflow"
                    block
                    :loading="loading"
                    :disabled="loading"
                    @click="requestGenerate('generateAndAnalyze')"
                  >
                    <template #icon>🔄</template>
                    生成 + 分析沉淀
                  </n-button>
                </div>
              </div>

              <!-- 辅助操作 -->
              <div class="form-block">
                <div class="block-title">辅助操作</div>
                <div class="secondary-actions">
                  <n-button block :disabled="!draft" @click="saveCurrentChapter">
                    💾 保存当前章节
                  </n-button>
                  <n-button block :disabled="!draft" @click="analyze">
                    📊 分析当前章节
                  </n-button>
                  <n-button block :disabled="!draft" @click="openPolishMenu">
                    ✨ 精修当前章节
                  </n-button>
                  <n-button block :disabled="!draft" @click="runConsistencyCheck">
                    🔍 检查一致性
                  </n-button>
                  <n-popconfirm
                    v-if="chapterId"
                    positive-text="确认删除"
                    negative-text="取消"
                    @positive-click="removeChapter(chapterId)"
                  >
                    <template #trigger>
                      <n-button type="error" block>🗑️ 删除当前章节</n-button>
                    </template>
                    确认删除当前章节草稿？此操作不可恢复。
                  </n-popconfirm>
                </div>
              </div>

              <!-- 上下文预检 -->
              <div class="form-block">
                <div class="block-title">
                  上下文预检
                  <span class="score-badge" :class="{ good: contextScore >= 5 }">
                    {{ contextScore }}/{{ contextChecks.length }}
                  </span>
                </div>
                <div class="check-grid">
                  <div
                    v-for="item in contextChecks"
                    :key="item.label"
                    class="check-item"
                    :class="{ ready: item.ready }"
                  >
                    <span class="check-icon">{{ item.ready ? '✓' : '○' }}</span>
                    <span class="check-label">{{ item.label }}</span>
                  </div>
                </div>
              </div>
            </div>
          </n-tab-pane>

          <!-- Tab: 上下文包 -->
          <n-tab-pane name="context" tab="上下文">
            <div class="tab-content">
              <!-- 上下文选择器 -->
              <ContextSelector
                :characters="characters"
                :organizations="organizations"
                :world-settings="worlds"
                :foreshadowings="foreshadowings"
                :outline="selectedOutline"
                :summaries="summaries"
                v-model:selected-character-ids="selectedCharacterIds"
                v-model:selected-organization-ids="selectedOrganizationIds"
                v-model:selected-world-ids="selectedWorldIds"
                v-model:selected-foreshadowing-ids="selectedForeshadowingIds"
                :current-chapter-no="form.chapter_no"
                @auto-recommend="autoRecommendContext"
              />

              <!-- 上下文统计卡片 -->
              <div class="context-stats-card">
                <div class="stats-title">
                  <span class="stats-icon">📊</span>
                  <span>上下文概览</span>
                </div>
                <div class="stats-grid">
                  <div class="stat-item">
                    <span class="stat-num">{{ selectedCharacterIds.length }}</span>
                    <span class="stat-label">角色</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-num">{{ selectedOrganizationIds.length }}</span>
                    <span class="stat-label">组织</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-num">{{ selectedWorldIds.length }}</span>
                    <span class="stat-label">世界观</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-num">{{ selectedForeshadowingIds.length }}</span>
                    <span class="stat-label">伏笔</span>
                  </div>
                </div>
                <div class="stats-tip">
                  💡 AI 生成时将读取以上所有选中的资料作为上下文
                </div>
              </div>
            </div>
          </n-tab-pane>

          <!-- Tab: 分析结果 -->
          <n-tab-pane name="analysis" tab="分析">
            <div class="tab-content">
              <!-- 生成后沉淀 -->
              <div class="form-block">
                <div class="block-title">生成后沉淀</div>
                <div v-if="!analysisSections.summary && !analysis" class="empty-analysis">
                  <div class="empty-icon">📊</div>
                  <p>生成并分析后，这里会展示章节摘要、人物变化、伏笔线索等</p>
                </div>
                <div v-else class="analysis-cards">
                  <div class="analysis-card">
                    <div class="card-label">📝 章节摘要</div>
                    <p>{{ analysisSections.summary || '暂无' }}</p>
                  </div>
                  <div class="analysis-card">
                    <div class="card-label">👤 人物变化</div>
                    <p>{{ analysisSections.character_changes || '暂无' }}</p>
                  </div>
                  <div class="analysis-card">
                    <div class="card-label">🌍 世界观变化</div>
                    <p>{{ analysisSections.world_changes || '暂无' }}</p>
                  </div>
                  <div class="analysis-card">
                    <div class="card-label">🎭 新增伏笔</div>
                    <p>{{ analysisSections.new_foreshadowings || '暂无' }}</p>
                  </div>
                  <div class="analysis-card">
                    <div class="card-label">⏱️ 时间线事件</div>
                    <p>{{ analysisSections.timeline_events || '暂无' }}</p>
                  </div>
                </div>
              </div>

              <!-- 章节分析只产生提案；作者确认后才写回人物、关系、组织等正式资料。 -->
              <div class="form-block">
                <div class="block-title">
                  资料变化审核
                  <n-tag size="tiny" :type="pendingProposalCount ? 'warning' : 'default'">
                    {{ pendingProposalCount }} 条待审核
                  </n-tag>
                  <n-button
                    size="tiny"
                    quaternary
                    :loading="proposalLoading"
                    :disabled="!chapterId"
                    @click="loadChapterChangeProposals"
                  >
                    刷新
                  </n-button>
                </div>
                <n-spin :show="proposalLoading">
                  <div v-if="changeProposals.length === 0" class="empty-proposals">
                    分析章节后，人物、关系、组织、伏笔和时间线变化会出现在这里；确认后才会更新正式资料。
                  </div>
                  <div v-else class="proposal-list">
                    <article
                      v-for="proposal in changeProposals"
                      :key="proposal.proposal_id"
                      class="proposal-card"
                      :class="'proposal-' + proposal.status"
                    >
                      <div class="proposal-heading">
                        <div class="proposal-title">
                          <strong>{{ proposalEntityLabel(proposal.entity_type) }} · {{ proposal.target_label || '未命名' }}</strong>
                          <n-tag size="small" :type="proposalStatusType(proposal.status)">
                            {{ proposalStatusLabel(proposal.status) }}
                          </n-tag>
                          <n-tag v-if="proposal.operation === 'create'" size="small" type="info">新增</n-tag>
                        </div>
                        <span v-if="proposal.version_id" class="proposal-source">来源版本 {{ proposal.version_id.slice(0, 8) }}</span>
                      </div>
                      <p v-if="proposal.rationale" class="proposal-rationale">{{ proposal.rationale }}</p>
                      <blockquote v-if="proposal.evidence" class="proposal-evidence">{{ proposal.evidence }}</blockquote>
                      <div class="proposal-diff">
                        <div v-for="change in proposalChanges(proposal)" :key="change.field" class="proposal-diff-row">
                          <span class="proposal-field">{{ change.field }}</span>
                          <span class="proposal-before">{{ change.before }}</span>
                          <span class="proposal-arrow">→</span>
                          <span class="proposal-after">{{ change.after }}</span>
                        </div>
                      </div>
                      <p v-if="proposal.review_note" class="proposal-review-note">{{ proposal.review_note }}</p>
                      <div v-if="proposal.status === 'pending'" class="proposal-actions">
                        <n-button
                          size="small"
                          quaternary
                          :disabled="proposalBusyIds.includes(proposal.proposal_id)"
                          @click="startProposalEdit(proposal)"
                        >
                          修改内容
                        </n-button>
                        <n-button
                          size="small"
                          type="error"
                          quaternary
                          :disabled="proposalBusyIds.includes(proposal.proposal_id)"
                          @click="reviewChangeProposal(proposal, 'reject')"
                        >
                          拒绝
                        </n-button>
                        <n-button
                          size="small"
                          type="success"
                          :loading="proposalBusyIds.includes(proposal.proposal_id)"
                          @click="reviewChangeProposal(proposal, 'approve')"
                        >
                          确认并写回
                        </n-button>
                      </div>
                      <div v-else-if="proposal.status === 'conflict'" class="proposal-actions">
                        <n-button size="small" @click="analyze()">按当前资料重新分析</n-button>
                      </div>
                    </article>
                  </div>
                </n-spin>
              </div>

              <!-- 一致性检查 -->
              <div class="form-block">
                <div class="block-title">一致性检查</div>
                <div v-if="!consistencyResult" class="empty-consistency">
                  点击「检查一致性」后查看资料缺口和潜在冲突
                </div>
                <div v-else class="consistency-result" :class="consistencyResult.risk_level">
                  <div class="risk-header">
                    <span class="risk-icon">
                      {{ consistencyResult.risk_level === 'low' ? '✅' : consistencyResult.risk_level === 'medium' ? '⚠️' : '❌' }}
                    </span>
                    <span class="risk-label">{{ riskLabel(consistencyResult.risk_level) }}</span>
                  </div>
                  <ul class="suggestion-list">
                    <li v-for="(s, i) in consistencyResult.suggestions" :key="i">{{ s }}</li>
                  </ul>
                </div>
              </div>

              <!-- 长期记忆 -->
              <div class="form-block">
                <div class="block-title">
                  长期记忆
                  <n-tag size="tiny" type="info">{{ summaries.length }} 条</n-tag>
                </div>
                <div v-if="summaries.length === 0" class="empty-memory">
                  暂无章节摘要，分析章节后会自动沉淀
                </div>
                <div v-else class="memory-list">
                  <div v-for="item in summaries.slice(0, 5)" :key="item.id" class="memory-item">
                    <div class="memory-chapter">第 {{ item.chapter_no }} 章 · {{ item.title }}</div>
                    <p>{{ shortText(item.summary) }}</p>
                  </div>
                </div>
              </div>
            </div>
          </n-tab-pane>

          <!-- Tab: 版本管理 -->
          <n-tab-pane name="versions" tab="版本">
            <div class="tab-content">
              <div class="versions-header">
                <span class="block-title">生成版本</span>
                <n-button size="tiny" :loading="versionsLoading" @click="loadVersions">刷新</n-button>
              </div>

              <!-- 版本时间线 - 架构可视化 -->
              <div v-if="chapterId && generationVersions.length > 0" class="version-timeline-wrap">
                <VersionTimeline
                  :versions="timelineVersions"
                  :current-version-id="currentVersionId"
                  @select="handleTimelineVersionSelect"
                  @compare="handleVersionCompare"
                />
              </div>

              <div v-if="!chapterId" class="empty-versions">
                请先生成或选择章节
              </div>
              <div v-else-if="generationVersions.length === 0" class="empty-versions">
                暂无历史版本
              </div>
              <div v-else class="version-list">
                <div
                  v-for="ver in generationVersions"
                  :key="ver.version_id"
                  :class="['version-item', { current: ver.is_current }]"
                >
                  <div class="version-header">
                    <div class="version-badge">
                      v{{ ver.version_number }}
                      <n-tag v-if="ver.is_current" size="tiny" type="success">当前</n-tag>
                      <n-tag v-if="ver.is_favorite" size="tiny" type="warning">收藏</n-tag>
                    </div>
                    <div class="version-words">{{ ver.word_count }} 字</div>
                  </div>
                  <div class="version-summary">{{ ver.summary }}</div>
                  <div class="version-meta">
                    <span>{{ formatVersionDate(ver.created_at) }}</span>
                    <span v-if="ver.rating" class="version-rating">
                      评分：{{ '★'.repeat(ver.rating) }}{{ '☆'.repeat(5 - ver.rating) }}
                    </span>
                  </div>
                  <div class="version-actions">
                    <n-button size="tiny" text :disabled="ver.is_current" @click="switchVersion(ver)">
                      切换到此版本
                    </n-button>
                  </div>
                </div>
              </div>
            </div>
          </n-tab-pane>

          <!-- Tab: 记忆偏好 -->
          <n-tab-pane name="preferences" tab="偏好">
            <div class="tab-content">
              <div class="prefs-header">
                <span class="block-title">写作偏好记忆</span>
                <n-button size="tiny" :loading="prefsLoading" @click="loadPreferences">刷新</n-button>
              </div>
              <div class="prefs-desc">
                Agent 会记住你的偏好，下次生成时自动应用，无需重复设置。
              </div>

              <n-form label-placement="top" :show-label="true" class="prefs-form">
                <n-form-item label="默认生成模式">
                  <n-select v-model:value="userPrefs.default_template" :options="templateOptions" />
                </n-form-item>
                <n-form-item label="默认写作风格">
                  <n-select v-model:value="userPrefs.default_writer_variant" :options="writerVariantOptions" />
                </n-form-item>
                <n-form-item label="模型创造性">
                  <n-slider v-model:value="userPrefs.default_temperature" :min="0" :max="200" :step="10" />
                  <div class="slider-labels">
                    <span>严谨</span>
                    <span>{{ (userPrefs.default_temperature / 100).toFixed(1) }}</span>
                    <span>创意</span>
                  </div>
                </n-form-item>
                <n-form-item label="目标字数">
                  <n-input-number v-model:value="userPrefs.default_target_word_count" :min="500" :max="10000" :step="500" style="width: 100%" />
                </n-form-item>
                <n-form-item label="自动沉淀等级">
                  <n-select v-model:value="userPrefs.auto_sync_level" :options="autoSyncOptions" />
                </n-form-item>
                <n-form-item label="编辑器字号">
                  <n-input-number v-model:value="userPrefs.editor_font_size" :min="12" :max="24" style="width: 100%" />
                </n-form-item>
              </n-form>

              <div class="prefs-actions">
                <n-button type="primary" block :loading="prefsSaving" @click="savePreferences">
                  保存偏好
                </n-button>
              </div>

              <!-- 统计信息 -->
              <div class="prefs-stats">
                <div class="prefs-stat-card">
                  <span class="stat-num">{{ userPrefs.total_generations ?? 0 }}</span>
                  <span class="stat-label">累计生成</span>
                </div>
                <div class="prefs-stat-card">
                  <span class="stat-num">{{ formatWordCount(userPrefs.total_words_generated) }}</span>
                  <span class="stat-label">累计字数</span>
                </div>
              </div>
            </div>
          </n-tab-pane>

          <!-- Tab: 运行轨迹 -->
          <n-tab-pane name="logs" tab="轨迹">
            <div class="tab-content">
              <div class="logs-header">
                <span class="block-title">Agent 运行轨迹</span>
                <n-button size="tiny" @click="loadAgentLogs">刷新</n-button>
              </div>
              <div v-if="visibleEvents.length === 0" class="empty-logs">
                暂无运行记录
              </div>
              <div v-else class="timeline">
                <div
                  v-for="event in visibleEvents"
                  :key="event.id"
                  class="timeline-item"
                  :class="event.status"
                >
                  <div class="timeline-dot"></div>
                  <div class="timeline-content">
                    <div class="timeline-title">{{ event.title }}</div>
                    <div class="timeline-detail">{{ event.detail }}</div>
                    <div class="timeline-time">{{ event.time }}</div>
                  </div>
                </div>
              </div>
            </div>
          </n-tab-pane>
        </n-tabs>
      </aside>
    </div>

    <!-- 提案先在审核草稿中调整，提交确认时由后端再次校验字段与原值。 -->
    <n-modal v-model:show="proposalEditVisible" preset="card" title="调整资料变化" style="width: min(720px, 92vw)">
      <p class="proposal-edit-hint">只修改 JSON 对象中的字段值；更新提案不能增加或删除字段。</p>
      <n-input
        v-model:value="proposalEditText"
        type="textarea"
        :autosize="{ minRows: 8, maxRows: 18 }"
        spellcheck="false"
      />
      <template #footer>
        <n-button @click="proposalEditVisible = false">取消</n-button>
        <n-button type="primary" :loading="proposalEditSaving" @click="saveEditedProposal">
          确认并写回
        </n-button>
      </template>
    </n-modal>

    <!-- 精修模式选择弹窗 -->
    <n-modal v-model:show="showPolishModal" preset="card" title="选择精修模式" style="width: 480px">
      <div class="polish-modes">
        <div
          v-for="mode in polishModes"
          :key="mode.value"
          class="polish-mode-card"
          :class="{ selected: selectedPolishMode === mode.value }"
          @click="selectedPolishMode = mode.value"
        >
          <div class="mode-icon">{{ mode.icon }}</div>
          <div class="mode-info">
            <div class="mode-name">{{ mode.name }}</div>
            <div class="mode-desc">{{ mode.desc }}</div>
          </div>
          <div v-if="selectedPolishMode === mode.value" class="mode-check">✓</div>
        </div>
      </div>
      <template #footer>
        <n-button @click="showPolishModal = false">取消</n-button>
        <n-button type="primary" :loading="loading" @click="doPolish">开始精修</n-button>
      </template>
    </n-modal>

    <!-- 重新生成确认弹窗 -->
    <n-modal v-model:show="regenerateConfirmVisible" :mask-closable="!loading">
      <div class="confirm-modal">
        <div class="confirm-icon">⚠️</div>
        <div class="confirm-title">{{ regenerateConfirmTitle }}</div>
        <p class="confirm-text">{{ regenerateConfirmText }}</p>
        <p class="confirm-note">{{ regenerateConfirmNote }}</p>
        <div class="confirm-actions">
          <n-button :disabled="loading" @click="cancelRegenerate">取消</n-button>
          <n-button type="primary" :loading="loading" @click="confirmRegenerate">
            {{ pendingGenerateMode === 'generateAndAnalyze' ? '确认重新生成并分析' : '确认重新生成' }}
          </n-button>
        </div>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useMessage } from 'naive-ui'
import {
  analyzeChapter,
  checkConsistency,
  draftChapterStream,
  getAgentLogs,
  getChapterSummaries,
  getContextPreview,
  polishChapter,
} from '@/api/agents'
import {
  getWorkflowTemplates,
  workflowGenerateStream,
  workflowResumeStream,
  getGenerationVersions,
  getChapterChangeProposals,
  reviewChapterChangeProposal,
  setCurrentVersion,
  getUserPreferences,
  updateUserPreferences,
  type WorkflowTemplate,
  type GenerationVersion,
  type ChapterChangeProposal,
  type ChangeProposalEntityType,
  type ChangeProposalStatus,
  type WorkflowStreamEvent,
} from '@/api/agentsV3'
import WorkflowProgress from '@/components/WorkflowProgress.vue'
import type { StepInfo } from '@/components/WorkflowProgress.vue'
import WorkflowPipeline from '@/components/WorkflowPipeline.vue'
import type { PipelineStep } from '@/components/WorkflowPipeline.vue'
import MemoryLayer from '@/components/MemoryLayer.vue'
import type { MemoryLevel } from '@/components/MemoryLayer.vue'
import AgentPluginCard from '@/components/AgentPluginCard.vue'
import type { SkillInfo } from '@/components/AgentPluginCard.vue'
import ContextSelector from '@/components/ContextSelector.vue'
import VersionTimeline from '@/components/VersionTimeline.vue'
import { createResource, deleteResource, listResource, updateResource } from '@/api/resources'
import { useProjectStore } from '@/stores/project'
import { useProjectDataLoader } from '@/composables/useProjectDataLoader'
import type {
  ChapterItem,
  ChapterSummary,
  CharacterItem,
  ConsistencyCheckResult,
  ContextPreview,
  ForeshadowingItem,
  GenerationLog,
  OrganizationItem,
  OutlineItem,
  WorldSetting,
} from '@/types/domain'

const message = useMessage()
const projectStore = useProjectStore()

// ---- 基础状态 ----
const loading = ref(false)
const keyword = ref('')
const draft = ref('')
const chapterTitle = ref('')
const analysis = ref('')
const activeTab = ref('params')

// ---- 资料数据 ----
const outlines = ref<OutlineItem[]>([])
const chapters = ref<ChapterItem[]>([])
const worlds = ref<WorldSetting[]>([])
const characters = ref<CharacterItem[]>([])
const organizations = ref<OrganizationItem[]>([])
const foreshadowings = ref<ForeshadowingItem[]>([])
const summaries = ref<ChapterSummary[]>([])
const changeProposals = ref<ChapterChangeProposal[]>([])
const proposalLoading = ref(false)
const proposalBusyIds = ref<string[]>([])
const proposalEditVisible = ref(false)
const proposalEditSaving = ref(false)
const proposalEditText = ref('')
const editingProposal = ref<ChapterChangeProposal | null>(null)
const pendingProposalCount = computed(() => changeProposals.value.filter(item => item.status === 'pending').length)
const agentLogs = ref<GenerationLog[]>([])
const localEvents = ref<
  Array<{ id: string; title: string; detail: string; time: string; status: string }>
>([])
const contextPreview = ref<ContextPreview | null>(null)
const previewLoading = ref(false)

// 上下文选择器状态
const selectedCharacterIds = ref<number[]>([])
const selectedOrganizationIds = ref<number[]>([])
const selectedWorldIds = ref<number[]>([])
const selectedForeshadowingIds = ref<number[]>([])

// 左侧资源浏览器 Tab
const leftActiveTab = ref<'outline' | 'chapter' | 'character' | 'organization' | 'world' | 'foreshadowing'>('outline')

// 资源 Tab 配置
type TabKey = 'outline' | 'chapter' | 'character' | 'organization' | 'world' | 'foreshadowing'
const resourceTabs = computed<{ key: TabKey; label: string; icon: string; count: number; matchCount: number }[]>(() => {
  const searching = keyword.value.trim().length > 0
  return [
    { key: 'outline', label: '大纲', icon: '📋', count: outlines.value.length, matchCount: filteredOutlines.value.length },
    { key: 'chapter', label: '章节', icon: '📝', count: chapters.value.length, matchCount: filteredChapters.value.length },
    { key: 'character', label: '人物', icon: '👤', count: characters.value.length, matchCount: filteredCharacters.value.length },
    { key: 'organization', label: '组织', icon: '🏛️', count: organizations.value.length, matchCount: filteredOrganizations.value.length },
    { key: 'world', label: '世界观', icon: '🌍', count: worlds.value.length, matchCount: filteredWorlds.value.length },
    { key: 'foreshadowing', label: '伏笔', icon: '🎭', count: foreshadowings.value.length, matchCount: filteredForeshadowings.value.length },
  ]
})

// 搜索总匹配数
const totalMatchCount = computed(() => {
  if (!keyword.value.trim()) return 0
  return resourceTabs.value.reduce((sum, t) => sum + t.matchCount, 0)
})

// 搜索占位符
const searchPlaceholder = computed(() => {
  const map: Record<string, string> = {
    outline: '搜索大纲...',
    chapter: '搜索章节...',
    character: '搜索角色...',
    organization: '搜索组织...',
    world: '搜索世界观...',
    foreshadowing: '搜索伏笔...',
  }
  return map[leftActiveTab.value] || '搜索...'
})

// 总选中数量
const totalSelectedCount = computed(() =>
  selectedCharacterIds.value.length +
  selectedOrganizationIds.value.length +
  selectedWorldIds.value.length +
  selectedForeshadowingIds.value.length
)

// 过滤后的角色/组织/世界观/伏笔（按关键词搜索）
const filteredCharacters = computed(() => {
  if (!keyword.value) return characters.value
  const kw = keyword.value.toLowerCase()
  return characters.value.filter(c =>
    c.name?.toLowerCase().includes(kw) ||
    c.identity?.toLowerCase().includes(kw) ||
    c.personality?.toLowerCase().includes(kw)
  )
})

const filteredOrganizations = computed(() => {
  if (!keyword.value) return organizations.value
  const kw = keyword.value.toLowerCase()
  return organizations.value.filter(o =>
    o.name?.toLowerCase().includes(kw) ||
    o.slogan?.toLowerCase().includes(kw) ||
    o.description?.toLowerCase().includes(kw)
  )
})

const filteredWorlds = computed(() => {
  if (!keyword.value) return worlds.value
  const kw = keyword.value.toLowerCase()
  return worlds.value.filter(w =>
    w.title?.toLowerCase().includes(kw) ||
    w.rules?.toLowerCase().includes(kw) ||
    w.category?.toLowerCase().includes(kw)
  )
})

const filteredForeshadowings = computed(() => {
  if (!keyword.value) return foreshadowings.value
  const kw = keyword.value.toLowerCase()
  return foreshadowings.value.filter(f =>
    f.keyword?.toLowerCase().includes(kw) ||
    f.description?.toLowerCase().includes(kw)
  )
})

// 切换选中
function toggleCharacter(id: number) {
  const idx = selectedCharacterIds.value.indexOf(id)
  if (idx >= 0) selectedCharacterIds.value.splice(idx, 1)
  else selectedCharacterIds.value.push(id)
}

function toggleOrganization(id: number) {
  const idx = selectedOrganizationIds.value.indexOf(id)
  if (idx >= 0) selectedOrganizationIds.value.splice(idx, 1)
  else selectedOrganizationIds.value.push(id)
}

function toggleWorld(id: number) {
  const idx = selectedWorldIds.value.indexOf(id)
  if (idx >= 0) selectedWorldIds.value.splice(idx, 1)
  else selectedWorldIds.value.push(id)
}

function toggleForeshadowing(id: number) {
  const idx = selectedForeshadowingIds.value.indexOf(id)
  if (idx >= 0) selectedForeshadowingIds.value.splice(idx, 1)
  else selectedForeshadowingIds.value.push(id)
}

// 角色类型标签
function charRoleTagType(role?: string): 'success' | 'warning' | 'error' | 'info' {
  switch (role) {
    case 'protagonist': return 'success'
    case 'supporting': return 'info'
    case 'antagonist': return 'error'
    default: return 'info'
  }
}

function charRoleLabel(role?: string): string {
  switch (role) {
    case 'protagonist': return '主角'
    case 'supporting': return '配角'
    case 'antagonist': return '反派'
    default: return '未分类'
  }
}

// 头像颜色（基于名字生成）
function avatarColor(name?: string): string {
  if (!name) return '#6366f1'
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  const colors = [
    'linear-gradient(135deg, #6366f1, #8b5cf6)',
    'linear-gradient(135deg, #ec4899, #f472b6)',
    'linear-gradient(135deg, #f59e0b, #fbbf24)',
    'linear-gradient(135deg, #10b981, #34d399)',
    'linear-gradient(135deg, #3b82f6, #60a5fa)',
    'linear-gradient(135deg, #ef4444, #f87171)',
    'linear-gradient(135deg, #8b5cf6, #a78bfa)',
    'linear-gradient(135deg, #14b8a6, #2dd4bf)',
  ]
  return colors[Math.abs(hash) % colors.length]
}

// 实力百分比
function powerPercent(level: string | number | null | undefined): number {
  if (level == null) return 0
  const n = typeof level === 'number' ? level : parseInt(String(level), 10)
  if (isNaN(n)) return 30
  return Math.min(100, Math.max(5, n * 20))
}

// 世界观分类标签
function worldCategoryLabel(cat?: string): string {
  const map: Record<string, string> = {
    era: '时代背景',
    location: '地理环境',
    power: '力量体系',
    rule: '世界规则',
    taboo: '禁忌设定',
    term: '专有名词',
  }
  return map[cat || ''] || '其他'
}

// 伏笔状态标签
function foreshadowStatusLabel(status?: string): string {
  const map: Record<string, string> = {
    pending: '待埋设',
    planted: '已埋设',
    developing: '发展中',
    payoff_pending: '待回收',
    resolved: '已回收',
    abandoned: '已废弃',
  }
  return map[status || ''] || status || '未知'
}

// 关键词高亮：将文本中的匹配词用 <mark> 包裹
function highlightText(text: string | null | undefined): string {
  if (!text) return ''
  const kw = keyword.value.trim()
  if (!kw) return text
  const safeKw = kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const regex = new RegExp(`(${safeKw})`, 'gi')
  return text.replace(regex, '<mark class="search-highlight">$1</mark>')
}

// 安全转义 + 高亮（用于 v-html 绑定）
function safeHighlight(text: string | null | undefined): string {
  if (!text) return ''
  // 先转义 HTML
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
  const kw = keyword.value.trim()
  if (!kw) return escaped
  const safeKw = kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const regex = new RegExp(`(${safeKw})`, 'gi')
  return escaped.replace(regex, '<mark class="search-highlight">$1</mark>')
}

// 自动推荐上下文
function autoRecommendContext() {
  if (!selectedOutline.value) {
    selectedCharacterIds.value = []
    selectedOrganizationIds.value = []
    selectedWorldIds.value = []
    selectedForeshadowingIds.value = []
    return
  }

  const outline = selectedOutline.value
  const chapterNo = form.chapter_no

  // 角色：主角 + 名字出现在大纲描述中的角色
  const charIds: number[] = []
  for (const c of characters.value) {
    if (c.role_type === 'protagonist') {
      charIds.push(c.id)
      continue
    }
    if (outline.description && c.name && outline.description.includes(c.name)) {
      charIds.push(c.id)
    }
  }
  // 最多推荐 6 个角色
  selectedCharacterIds.value = charIds.slice(0, 6)

  // 组织：主角所属的组织
  const orgIds: number[] = []
  for (const c of characters.value) {
    if (selectedCharacterIds.value.includes(c.id) && c.org_relations) {
      try {
        const rels = Array.isArray(c.org_relations) ? c.org_relations : JSON.parse(c.org_relations as any)
        for (const r of rels) {
          if (r.org_id && !orgIds.includes(r.org_id)) {
            orgIds.push(r.org_id)
          }
        }
      } catch {}
    }
  }
  selectedOrganizationIds.value = orgIds.slice(0, 4)

  // 世界观：高重要性的
  selectedWorldIds.value = worlds.value
    .filter(w => w.importance === 'high' || w.importance === '核心')
    .slice(0, 5)
    .map(w => w.id)

  // 伏笔：本章应回收的 + 已埋设未回收的
  const fIds: number[] = []
  for (const f of foreshadowings.value) {
    if (f.payoff_chapter === chapterNo) {
      fIds.push(f.id)
      continue
    }
    if ((f.status === 'planted' || f.status === 'developing' || f.status === 'payoff_pending') && fIds.length < 5) {
      fIds.push(f.id)
    }
  }
  selectedForeshadowingIds.value = fIds
}
const chapterId = ref<number | null>(null)
const polishOriginal = ref('')
const regenerateConfirmVisible = ref(false)
const pendingGenerateMode = ref<'generate' | 'generateAndAnalyze' | null>(null)
const consistencyResult = ref<ConsistencyCheckResult | null>(null)

const analysisSections = reactive({
  summary: '',
  character_changes: '',
  world_changes: '',
  new_foreshadowings: '',
  timeline_events: '',
})

// ---- 生成表单 ----
const form = reactive({
  outline_id: null as number | null,
  chapter_id: null as number | null,
  chapter_no: 1,
  rhythm_level: '3 - 适中',
  instruction: '',
})

const rhythmOptions = [
  { label: '1 - 慢热', value: '1 - 慢热' },
  { label: '2 - 平稳', value: '2 - 平稳' },
  { label: '3 - 适中', value: '3 - 适中' },
  { label: '4 - 紧凑', value: '4 - 紧凑' },
  { label: '5 - 高燃', value: '5 - 高燃' },
]

// ---- v3 工作流相关 ----
const useV3Workflow = ref(true)  // 默认使用 v3 工作流
const workflowTemplates = ref<WorkflowTemplate[]>([])
const selectedWorkflow = ref('smart_mode')  // 默认智能模式
const workflowSteps = ref<StepInfo[]>([])
const currentWorkflowStep = ref<string | null>(null)
const workflowProgress = ref(0)
const currentRunId = ref<string | null>(null)
const generationVersions = ref<GenerationVersion[]>([])
const versionsLoading = ref(false)
const showWorkflowPanel = ref(false)  // 生成中显示步骤面板
const isInterrupted = ref(false)  // 是否为中断状态
const interruptedRunId = ref<string | null>(null)  // 中断的 run_id

// ---- 架构可视化 ----
const pipelineSteps = computed<PipelineStep[]>(() => {
  const stepAgentMap: Record<string, { agent: string; skills: number; desc: string }> = {
    planner:  { agent: '规划师 Agent',  skills: 4, desc: '拆解剧情，生成写作蓝图' },
    writer:   { agent: '写作师 Agent',  skills: 6, desc: '按规划撰写章节正文' },
    polisher: { agent: '精修师 Agent',  skills: 3, desc: '润色打磨，提升文采' },
    analyzer: { agent: '分析师 Agent',  skills: 5, desc: '沉淀记忆，一致性检查' },
  }
  return workflowSteps.value.map(s => ({
    id: s.id,
    label: s.label,
    icon: s.icon,
    description: stepAgentMap[s.id]?.desc || s.label,
    status: (s.status === 'skipped' ? 'completed' : s.status) as PipelineStep['status'],
    durationMs: s.durationMs,
    agentName: stepAgentMap[s.id]?.agent,
    skillCount: stepAgentMap[s.id]?.skills,
    canRestart: s.status === 'completed',
  }))
})

const memoryLevels = ref<MemoryLevel[]>([
  {
    level: 'working',
    name: '工作记忆',
    subtitle: '当前生成上下文',
    icon: '⚡',
    color: '#f59e0b',
    items: [
      { id: 'w1', title: '等待生成指令', type: '状态', importance: 100, description: '选择大纲和章节后，点击生成按钮开始创作。工作记忆将实时保存当前生成的中间结果。' },
      { id: 'w2', title: '当前上下文为空', type: '提示', importance: 60, description: '生成过程中，规划结果、草稿内容、精修结果都会暂存在这里。' },
    ],
    capacity: '动态',
    retention: '本次生成',
    expanded: true,
  },
  {
    level: 'session',
    name: '会话记忆',
    subtitle: '本次会话的交互历史',
    icon: '💬',
    color: '#3b82f6',
    items: [
      { id: 's1', title: '会话已建立', type: '系统', importance: 50, description: '页面加载后自动建立会话，记录本次操作轨迹。' },
    ],
    capacity: '50 条',
    retention: '会话期间',
    expanded: false,
  },
  {
    level: 'project',
    name: '项目记忆',
    subtitle: '当前项目的角色/世界观/伏笔',
    icon: '📁',
    color: '#8b5cf6',
    items: [
      { id: 'p1', title: '加载项目资料中...', type: '状态', importance: 80, description: '正在从数据库加载角色、世界观、伏笔等项目记忆...' },
    ],
    capacity: '项目级',
    retention: '项目周期',
    expanded: false,
  },
  {
    level: 'longterm',
    name: '长期记忆',
    subtitle: '沉淀的写作偏好和经验',
    icon: '🏛️',
    color: '#10b981',
    items: [
      { id: 'l1', title: '写作风格偏好', type: '偏好', importance: 95, description: '记录你的写作风格倾向，每次生成自动应用。可在右侧「偏好」Tab 中修改。', tags: ['风格', '个性化'] },
      { id: 'l2', title: '生成模板偏好', type: '偏好', importance: 90, description: '默认使用的工作流模板，可在参数区切换。', tags: ['模板', '效率'] },
      { id: 'l3', title: '累计生成统计', type: '统计', importance: 70, description: '追踪你的创作产出，激励持续写作。', tags: ['统计'] },
    ],
    capacity: '用户级',
    retention: '永久',
    expanded: false,
  },
])

const agentSkills = ref<SkillInfo[]>([
  { id: 'outline',   name: '大纲理解', icon: '📋', description: '解析章节大纲结构', active: true },
  { id: 'character', name: '角色演绎', icon: '👤', description: '保持人物性格一致', active: true },
  { id: 'world',     name: '世界观',   icon: '🌍', description: '遵循设定约束',     active: true },
  { id: 'foreshadow', name: '伏笔埋入', icon: '🔮', description: '埋设和回收伏笔',   active: false },
  { id: 'rhythm',    name: '节奏控制', icon: '🎵', description: '把控叙事节奏',     active: true },
  { id: 'emotion',   name: '情感渲染', icon: '💝', description: '情感氛围营造',     active: false },
])

const activeVariantName = computed(() => {
  const map: Record<string, string> = {
    default: '均衡风格',
    shuangwen: '爽文风',
    wenqing: '文青风',
    fastpaced: '快节奏',
    wuxia: '武侠风',
  }
  return map[userPrefs.default_writer_variant] || '均衡风格'
})

const writerVariants = [
  { id: 'default',   name: '均衡风格', description: '叙事平稳，适合大多数题材', icon: '⚖️' },
  { id: 'shuangwen', name: '爽文风',   description: '节奏紧凑，打脸升级快感强', icon: '🔥' },
  { id: 'wenqing',   name: '文青风',   description: '文笔细腻，情感氛围浓厚',   icon: '🎨' },
  { id: 'fastpaced', name: '快节奏',   description: '情节密集，悬念迭起',       icon: '⚡' },
  { id: 'wuxia',     name: '武侠风',   description: '江湖气重，古风古韵',       icon: '⚔️' },
]

async function handleVariantChange(variantId: string) {
  userPrefs.default_writer_variant = variantId
  await savePreferences()
  addEvent('风格切换', `切换为 ${activeVariantName.value}`, 'info')
  message.success(`已切换为 ${activeVariantName.value}`)
  updateMemoryLevels()
}

// ---- 记忆层级更新 ----
function updateMemoryLevels() {
  // L3 项目记忆：角色、世界观、伏笔、组织
  const projectItems = [
    ...characters.value.slice(0, 5).map(c => ({
      id: `char-${c.id}`,
      title: c.name,
      type: '角色',
      importance: 90,
    })),
    ...worlds.value.slice(0, 3).map(w => ({
      id: `world-${w.id}`,
      title: w.title,
      type: '世界观',
      importance: 85,
    })),
    ...foreshadowings.value.slice(0, 4).map(f => ({
      id: `foreshadow-${f.id}`,
      title: f.keyword,
      type: '伏笔',
      importance: 75,
    })),
    ...organizations.value.slice(0, 2).map(o => ({
      id: `org-${o.id}`,
      title: o.name,
      type: '组织',
      importance: 70,
    })),
  ]
  const projectLevel = memoryLevels.value.find(l => l.level === 'project')
  if (projectLevel) {
    projectLevel.items = projectItems
  }

  // L2 会话记忆：最近的摘要
  const sessionLevel = memoryLevels.value.find(l => l.level === 'session')
  if (sessionLevel) {
    sessionLevel.items = summaries.value.slice(0, 5).map(s => ({
      id: `summary-${s.chapter_no}`,
      title: `第${s.chapter_no}章 摘要`,
      type: '摘要',
      importance: 60,
    }))
  }

  // L4 长期记忆：偏好 + 统计
  const longtermLevel = memoryLevels.value.find(l => l.level === 'longterm')
  if (longtermLevel) {
    longtermLevel.items = [
      { id: 'prefs-style', title: `写作风格: ${activeVariantName.value}`, type: '偏好', importance: 95 },
      { id: 'prefs-template', title: `默认模板: ${selectedWorkflow.value}`, type: '偏好', importance: 90 },
      { id: 'stats-count', title: `累计生成 ${userPrefs.total_generations ?? 0} 次`, type: '统计', importance: 70 },
      { id: 'stats-words', title: `累计 ${userPrefs.total_words_generated ?? 0} 字`, type: '统计', importance: 65 },
    ]
  }

  // L1 工作记忆：当前选中的大纲和章节
  const workingLevel = memoryLevels.value.find(l => l.level === 'working')
  if (workingLevel && selectedOutline.value) {
    workingLevel.items = [
      { id: 'current-outline', title: selectedOutline.value.title, type: '当前大纲', importance: 100 },
      { id: 'current-chapter', title: chapterTitle.value || `第${form.chapter_no}章`, type: '当前章节', importance: 100 },
    ]
  }
}

function handleMemoryLevelClick(level: string) {
  const lvl = memoryLevels.value.find(l => l.level === level)
  if (lvl) lvl.expanded = !lvl.expanded
}

// ---- 记忆偏好 ----
const prefsLoading = ref(false)
const prefsSaving = ref(false)
const userPrefs = reactive({
  default_template: 'smart_mode',
  default_writer_variant: 'default',
  default_temperature: 80,
  default_target_word_count: 3000,
  auto_sync_level: 'low_risk_only',
  editor_font_size: 16,
  total_generations: 0,
  total_words_generated: 0,
})

const templateOptions = computed(() =>
  workflowTemplates.value.map(t => ({ label: t.label, value: t.name }))
)

const writerVariantOptions = [
  { label: '默认（均衡）', value: 'default' },
  { label: '爽文风', value: 'shuangwen' },
  { label: '文青风', value: 'wenqing' },
  { label: '快节奏', value: 'fast' },
]

const autoSyncOptions = [
  { label: '仅低风险变更', value: 'low_risk_only' },
  { label: '标准模式', value: 'standard' },
  { label: '全量沉淀', value: 'full' },
]

// 工作流步骤映射（根据模板名称构建步骤列表）
function buildWorkflowSteps(templateName: string): StepInfo[] {
  const templates: Record<string, StepInfo[]> = {
    quick_write: [
      { id: 'writer', label: '正文写作', icon: '✍️', status: 'pending' },
    ],
    smart_mode: [
      { id: 'planner', label: '情节规划', icon: '📋', status: 'pending' },
      { id: 'writer', label: '正文写作', icon: '✍️', status: 'pending' },
      { id: 'analyzer', label: '分析沉淀', icon: '🔍', status: 'pending' },
    ],
    deep_creation: [
      { id: 'planner', label: '详细规划', icon: '📋', status: 'pending' },
      { id: 'writer', label: '正文写作', icon: '✍️', status: 'pending' },
      { id: 'polisher', label: '精修润色', icon: '✨', status: 'pending' },
      { id: 'analyzer', label: '深度分析', icon: '🔍', status: 'pending' },
    ],
  }
  return templates[templateName] ?? templates.smart_mode
}

// ---- 精修模式 ----
const showPolishModal = ref(false)
const selectedPolishMode = ref('conflict')
const polishModes = [
  {
    value: 'conflict',
    name: '增强冲突',
    icon: '⚔️',
    desc: '强化戏剧冲突、增加对白张力、提升结尾钩子',
  },
  {
    value: 'emotion',
    name: '情感深化',
    icon: '💖',
    desc: '丰富内心戏、增强角色情感表达和场景氛围',
  },
  {
    value: 'rhythm',
    name: '节奏优化',
    icon: '🎵',
    desc: '调整叙述节奏，让张弛更有度，读起来更流畅',
  },
  {
    value: 'polish',
    name: '文字润色',
    icon: '✨',
    desc: '优化措辞、句式和修辞，提升文笔质感',
  },
]

// ---- 伏笔选项 ----
const foreshadowingOptions = computed(() =>
  foreshadowings.value.map((item) => ({
    label: `${item.keyword}（埋${item.planted_chapter ?? '?'}）`,
    value: item.id,
  }))
)

// ---- 计算属性 ----
const project = computed(() => projectStore.currentProject)

const filteredOutlines = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return outlines.value
  return outlines.value.filter((item) =>
    [item.title, item.description].join(' ').toLowerCase().includes(text)
  )
})

const filteredChapters = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return chapters.value
  return chapters.value.filter((item) =>
    [item.title, item.content].join(' ').toLowerCase().includes(text)
  )
})

const selectedOutline = computed(
  () => outlines.value.find((item) => item.id === form.outline_id) ?? null
)
const selectedChapter = computed(
  () => chapters.value.find((item) => item.id === chapterId.value) ?? null
)
const wordCount = computed(() => draft.value.replace(/\s/g, '').length)
const hasExistingDraft = computed(() => Boolean(draft.value.trim()))

const regenerateConfirmTitle = computed(() =>
  pendingGenerateMode.value === 'generateAndAnalyze' ? '确认重新生成并分析？' : '确认重新生成？'
)
const regenerateConfirmText = computed(() =>
  `当前正文区已有 ${wordCount.value} 字，确认清空并重新生成第 ${form.chapter_no} 章？`
)
const regenerateConfirmNote = computed(() => {
  const instruction = form.instruction.trim()
  return instruction
    ? `本次会沿用当前本章目标：${shortText(instruction)}`
    : '当前没有本章目标，建议先选择大纲或填写目标后再重新生成。'
})

const polishSegments = computed(() => {
  const before = splitParagraphs(polishOriginal.value)
  return splitParagraphs(draft.value).map((text, index) => ({
    text,
    status: text.trim() !== (before[index] ?? '').trim() ? 'changed' : 'same',
  }))
})
const hasPolishHighlights = computed(
  () => polishOriginal.value.trim().length > 0 && polishSegments.value.length > 0
)

const contextChecks = computed(() => [
  { label: '已选择大纲', ready: Boolean(form.outline_id) },
  { label: '已有本章目标', ready: Boolean(form.instruction.trim()) },
  { label: '世界观可用', ready: worlds.value.length > 0 },
  { label: '角色资料可用', ready: characters.value.length > 0 },
  { label: '组织/伏笔上下文', ready: organizations.value.length + foreshadowings.value.length > 0 },
  { label: '最近摘要可检索', ready: summaries.value.length > 0 },
  { label: '正文可分析', ready: Boolean(draft.value.trim()) },
])
const contextScore = computed(() => contextChecks.value.filter((item) => item.ready).length)

const visibleEvents = computed(() => {
  const persisted = agentLogs.value.slice(0, 8).map((log) => ({
    id: `log-${log.id}`,
    title: taskTypeLabel(log.task_type),
    detail: log.error || log.response || log.request || '任务已记录',
    time: log.created_at,
    status: log.status === 'success' ? 'success' : 'error',
  }))
  return [...localEvents.value, ...persisted].slice(0, 15)
})

// ---- 工具函数 ----
function shortText(value: string, max = 58) {
  return value?.length > max ? `${value.slice(0, max)}...` : value || '暂无正文'
}

function formatChars(content: string): string {
  const len = content?.replace(/\s/g, '').length || 0
  if (len >= 10000) return (len / 10000).toFixed(1) + '万'
  return len.toString()
}

function splitParagraphs(value: string) {
  return value
    .split(/\n{2,}/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function taskTypeLabel(value: string) {
  const labels: Record<string, string> = {
    chapter_draft: '章节生成',
    chapter_analyze: '章节分析',
    chapter_polish: '章节精修',
    consistency_check: '一致性检查',
  }
  return labels[value] ?? value
}

function riskLabel(value: string) {
  const labels: Record<string, string> = {
    low: '低风险',
    medium: '中风险',
    high: '高风险',
  }
  return labels[value] ?? value
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    draft: '草稿',
    confirmed: '已确认',
    published: '已发布',
  }
  return map[status] || status
}

function statusTagType(status: string): 'default' | 'success' | 'info' | 'warning' | 'error' {
  const map: Record<string, 'default' | 'success' | 'info' | 'warning' | 'error'> = {
    draft: 'default',
    confirmed: 'success',
    published: 'info',
  }
  return map[status] || 'default'
}

function foreshadowTagType(status: string): 'default' | 'success' | 'info' | 'warning' | 'error' {
  const map: Record<string, 'default' | 'success' | 'info' | 'warning' | 'error'> = {
    pending: 'warning',
    planted: 'info',
    developing: 'info',
    payoff_pending: 'warning',
    resolved: 'success',
    abandoned: 'default',
  }
  return map[status] || 'default'
}

// ---- 分析结果处理 ----
function setAnalysisSections(result: Record<string, unknown>) {
  analysisSections.summary = String(result.summary ?? '')
  analysisSections.character_changes = String(result.character_changes ?? '')
  analysisSections.world_changes = String(result.world_changes ?? '')
  analysisSections.new_foreshadowings = String(result.new_foreshadowings ?? '')
  analysisSections.timeline_events = String(result.timeline_events ?? '')
}

function clearAnalysisSections() {
  setAnalysisSections({})
}

const proposalEntityLabels: Record<ChangeProposalEntityType, string> = {
  character: '人物',
  relationship: '人物关系',
  organization: '组织',
  organization_relation: '组织关系',
  foreshadowing: '伏笔',
  world_setting: '世界观',
  memory: '长期记忆',
}

function proposalEntityLabel(entityType: ChangeProposalEntityType) {
  return proposalEntityLabels[entityType] ?? entityType
}

function proposalStatusLabel(status: ChangeProposalStatus) {
  const labels: Record<ChangeProposalStatus, string> = {
    pending: '待审核',
    applied: '已写回',
    rejected: '已拒绝',
    conflict: '资料有变化',
  }
  return labels[status]
}

function proposalStatusType(status: ChangeProposalStatus): 'warning' | 'success' | 'error' | 'default' {
  if (status === 'pending') return 'warning'
  if (status === 'applied') return 'success'
  if (status === 'rejected') return 'default'
  return 'error'
}

function formatProposalValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'string') return value
  return JSON.stringify(value) ?? String(value)
}

function proposalChanges(proposal: ChapterChangeProposal) {
  const fields = Object.entries(proposal.proposed_value ?? {})
  if (proposal.entity_type === 'organization_relation') {
    const summarize = (value: Record<string, unknown>) => {
      const source = value.source_org_id
        ? organizations.value.find((item) => item.id === Number(value.source_org_id))?.name
        : ''
      const target = value.target_org_id
        ? organizations.value.find((item) => item.id === Number(value.target_org_id))?.name
        : ''
      const endpoints = source && target ? `${source} → ${target}` : proposal.target_label
      const relationType = value.relation_type === 'alliance'
        ? '同盟'
        : value.relation_type === 'hostility' ? '敌对' : ''
      const range = []
      if ('effective_from_chapter' in value) {
        range.push(value.effective_from_chapter == null ? '起始不限' : `第 ${String(value.effective_from_chapter)} 章起`)
      }
      if ('expires_at_chapter' in value) {
        range.push(value.expires_at_chapter == null ? '持续有效' : `至第 ${String(value.expires_at_chapter)} 章`)
      }
      return [endpoints, relationType, range.join('，'), value.description]
        .filter((part) => part !== '' && part !== undefined && part !== null)
        .join(' · ')
    }
    return [{
      field: proposal.operation === 'create' ? '新增组织关系' : '组织关系调整',
      before: proposal.operation === 'create'
        ? '无既有关系'
        : summarize(proposal.before_value),
      after: summarize(proposal.proposed_value),
    }]
  }
  if (proposal.entity_type === 'relationship') {
    const existing = proposal.before_value.relationships
    const targetId = proposal.proposed_value.target_id
    const oldRelation = Array.isArray(existing)
      ? existing.find((item) => {
          if (!item || typeof item !== 'object') return false
          return (item as Record<string, unknown>).target_id === targetId
        }) as Record<string, unknown> | undefined
      : undefined
    const relationText = (value: Record<string, unknown> | undefined) => {
      if (!value) return '无既有关系'
      const depth = value.depth === undefined ? '' : ' · 深度 ' + String(value.depth)
      return formatProposalValue(value.relation_type) + depth
    }
    return [{
      field: proposal.operation === 'update' ? '关系更新' : '新增关系',
      before: relationText(oldRelation),
      after: relationText(proposal.proposed_value),
    }]
  }
  if (proposal.operation === 'create') {
    return fields.map(([field, value]) => ({
      field,
      before: '—',
      after: formatProposalValue(value),
    }))
  }
  return fields.map(([field, value]) => ({
    field,
    before: formatProposalValue(proposal.before_value[field]),
    after: formatProposalValue(value),
  }))
}

async function loadChapterChangeProposals() {
  const projectId = projectStore.currentProject?.id
  const currentChapterId = chapterId.value
  if (!projectId || !currentChapterId) {
    changeProposals.value = []
    return
  }
  proposalLoading.value = true
  try {
    const result = await getChapterChangeProposals(projectId, currentChapterId)
    changeProposals.value = result.items
  } catch {
    // 章节刚切换或后端尚未升级时，保留页面其他功能并允许手动重试。
    changeProposals.value = []
  } finally {
    proposalLoading.value = false
  }
}

async function reviewChangeProposal(
  proposal: ChapterChangeProposal,
  decision: 'approve' | 'reject',
  proposedValue?: Record<string, unknown>,
) {
  const projectId = projectStore.currentProject?.id
  if (!projectId) return false
  const prompt = decision === 'approve'
    ? '确认将这条变化写回正式资料？'
    : '确认拒绝这条变化提案？'
  if (!window.confirm(prompt)) return false

  proposalBusyIds.value = [...proposalBusyIds.value, proposal.proposal_id]
  try {
    const result = await reviewChapterChangeProposal(projectId, proposal.chapter_id, proposal.proposal_id, {
      decision,
      proposed_value: proposedValue,
    })
    changeProposals.value = changeProposals.value.map(item =>
      item.proposal_id === proposal.proposal_id ? result.proposal : item,
    )
    if (decision === 'approve') {
      await loadResources()
      message.success('已确认并更新正式资料')
    } else {
      message.success('已拒绝这条提案')
    }
    await loadChapterChangeProposals()
    return true
  } catch (error) {
    message.error(errorMessage(error))
    await loadChapterChangeProposals()
    return false
  } finally {
    proposalBusyIds.value = proposalBusyIds.value.filter(id => id !== proposal.proposal_id)
  }
}

function startProposalEdit(proposal: ChapterChangeProposal) {
  // 步骤 1：把候选值复制到本地审核草稿，编辑期间不修改服务端记录。
  editingProposal.value = proposal
  proposalEditText.value = JSON.stringify(proposal.proposed_value, null, 2)
  proposalEditVisible.value = true
}

async function saveEditedProposal() {
  // 步骤 1：解析并限制审核草稿为 JSON 对象。
  const proposal = editingProposal.value
  if (!proposal) return
  let proposedValue: Record<string, unknown>
  try {
    const parsed: unknown = JSON.parse(proposalEditText.value)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error('内容必须是 JSON 对象')
    }
    proposedValue = parsed as Record<string, unknown>
  } catch (error) {
    message.error(errorMessage(error))
    return
  }

  // 步骤 2：复用审核写回流程；后端仍会检查字段白名单和提案前值。
  proposalEditSaving.value = true
  try {
    const saved = await reviewChangeProposal(proposal, 'approve', proposedValue)
    if (saved) {
      proposalEditVisible.value = false
      editingProposal.value = null
    }
  } finally {
    proposalEditSaving.value = false
  }
}

// ---- 运行轨迹 ----
function addEvent(title: string, detail: string, status = 'success') {
  localEvents.value.unshift({
    id: `local-${Date.now()}-${localEvents.value.length}`,
    title,
    detail,
    status,
    time: new Date().toLocaleTimeString(),
  })
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : '未知错误'
}

// ---- 项目相关 ----
async function ensureProject() {
  if (!projectStore.currentProject) await projectStore.loadDefaultProject()
  return projectStore.currentProject?.id
}

// ---- 数据加载 ----
async function loadAgentLogs() {
  const projectId = await ensureProject()
  if (!projectId) return
  agentLogs.value = await getAgentLogs(projectId, 20)
}

async function loadResources() {
  const projectId = projectStore.currentProject!.id
  const [
    outlineList,
    chapterList,
    worldList,
    characterList,
    organizationList,
    foreshadowingList,
    summaryList,
    logList,
  ] = await Promise.all([
    listResource<OutlineItem>(projectId, 'outlines'),
    listResource<ChapterItem>(projectId, 'chapters'),
    listResource<WorldSetting>(projectId, 'world'),
    listResource<CharacterItem>(projectId, 'characters'),
    listResource<OrganizationItem>(projectId, 'organizations'),
    listResource<ForeshadowingItem>(projectId, 'foreshadowings'),
    getChapterSummaries(projectId, 20),
    getAgentLogs(projectId, 20),
  ])
  outlines.value = outlineList
  chapters.value = chapterList
  worlds.value = worldList
  characters.value = characterList
  organizations.value = organizationList
  foreshadowings.value = foreshadowingList
  summaries.value = summaryList
  agentLogs.value = logList
  addEvent('读取资料', `大纲 ${outlineList.length}，角色 ${characterList.length}，摘要 ${summaryList.length}`)

  // 更新记忆层级可视化数据
  updateMemoryLevels()

  hydrateInstructionFromSelection()
  ensureActiveOutline()
  await refreshContextPreview({ silent: true })
}

async function refreshContextPreview(options: { silent?: boolean } = {}) {
  const projectId = await ensureProject()
  if (!projectId) return

  previewLoading.value = true
  try {
    contextPreview.value = await getContextPreview(projectId, form.chapter_no, form.outline_id)
    if (!options.silent)
      addEvent(
        '拼装上下文',
        `角色 ${contextPreview.value.characters.length}，组织 ${contextPreview.value.organizations.length}，伏笔 ${contextPreview.value.foreshadowings.length}，长期记忆 ${contextPreview.value.long_term_memories.length}`
      )
  } catch (error) {
    if (!options.silent) {
      addEvent('上下文预览失败', errorMessage(error), 'error')
      message.error('上下文预览失败')
    }
  } finally {
    previewLoading.value = false
  }
}

// ---- 生成相关 ----
function requestGenerate(mode: 'generate' | 'generateAndAnalyze') {
  if (loading.value) return
  hydrateInstructionFromSelection()
  ensureActiveOutline()
  if (!hasGenerationGoal()) {
    message.warning('请先选择大纲或填写本章目标')
    addEvent('生成拦截', '缺少大纲或本章目标，已取消生成', 'error')
    return
  }
  if (hasExistingDraft.value) {
    pendingGenerateMode.value = mode
    regenerateConfirmVisible.value = true
    return
  }
  void runGenerateMode(mode)
}

async function runGenerateMode(mode: 'generate' | 'generateAndAnalyze') {
  if (useV3Workflow.value) {
    // v3 模式：全部走工作流
    await generateV3()
    return
  }
  // v1 模式
  if (mode === 'generateAndAnalyze') {
    await generateAndAnalyze()
    return
  }
  await generate()
}

function cancelRegenerate() {
  pendingGenerateMode.value = null
  regenerateConfirmVisible.value = false
}

async function confirmRegenerate() {
  const mode = pendingGenerateMode.value
  pendingGenerateMode.value = null
  regenerateConfirmVisible.value = false
  if (!mode) return
  hydrateInstructionFromSelection()
  ensureActiveOutline()
  await runGenerateMode(mode)
}

function findOutlineForChapter(item: ChapterItem) {
  return (
    outlines.value.find((outline) => outline.id === item.outline_id) ??
    outlines.value.find((outline) => outline.chapter_no === item.chapter_no) ??
    null
  )
}

function hydrateInstructionFromSelection() {
  const currentChapter = selectedChapter.value
  if (!currentChapter) return

  const relatedOutline = findOutlineForChapter(currentChapter)
  if (relatedOutline) {
    form.outline_id = relatedOutline.id
    if (!form.instruction.trim() || form.instruction === currentChapter.title) {
      form.instruction = relatedOutline.description
    }
  } else if (!form.instruction.trim()) {
    form.instruction = currentChapter.title
  }
}

function applyOutlineToForm(item: OutlineItem, options: { forceInstruction?: boolean } = {}) {
  form.outline_id = item.id
  form.chapter_no = item.chapter_no ?? item.sort_index
  if (options.forceInstruction || !form.instruction.trim()) {
    form.instruction = item.description
  }
}

function ensureActiveOutline() {
  if (form.outline_id && outlines.value.some((item) => item.id === form.outline_id)) return
  if (selectedChapter.value) return

  const firstOutline = outlines.value[0]
  if (!firstOutline) return
  applyOutlineToForm(firstOutline)
}

function hasGenerationGoal() {
  return Boolean(form.outline_id || form.instruction.trim())
}

function selectOutline(item: OutlineItem) {
  applyOutlineToForm(item, { forceInstruction: true })
  addEvent('选择大纲', `${item.title} 已进入生成上下文`)
  void refreshContextPreview({ silent: true })
  nextTick(() => {
    autoRecommendContext()
  })
}

function selectChapter(item: ChapterItem) {
  const relatedOutline = findOutlineForChapter(item)
  chapterId.value = item.id
  form.chapter_id = item.id
  form.outline_id = relatedOutline?.id ?? item.outline_id
  form.chapter_no = item.chapter_no
  form.instruction = relatedOutline?.description || form.instruction || item.title
  draft.value = item.content
  chapterTitle.value = item.title
  analysis.value = ''
  polishOriginal.value = ''
  consistencyResult.value = null
  addEvent(
    '载入章节',
    relatedOutline ? `${item.title} 已载入，并恢复章纲目标` : `${item.title} 已进入正文编辑区`
  )
  void refreshContextPreview({ silent: true })
  void loadVersions()  // 加载版本列表
  nextTick(() => {
    autoRecommendContext()
  })
}

// ---- 生成章节 ----
async function generate(options: { showToast?: boolean } = {}) {
  const { showToast = true } = options
  if (loading.value) return false

  const projectId = await ensureProject()
  if (!projectId) return false

  loading.value = true
  hydrateInstructionFromSelection()
  ensureActiveOutline()
  if (!hasGenerationGoal()) {
    loading.value = false
    message.warning('请先选择大纲或填写本章目标')
    addEvent('生成拦截', '缺少大纲或本章目标，已取消生成', 'error')
    return false
  }
  await refreshContextPreview()
  const previousDraft = draft.value
  const previousAnalysis = analysis.value
  const previousPolishOriginal = polishOriginal.value
  addEvent('生成启动', `第 ${form.chapter_no} 章，节奏 ${form.rhythm_level}`, 'running')
  draft.value = ''
  analysis.value = ''
  polishOriginal.value = ''
  consistencyResult.value = null
  clearAnalysisSections()
  try {
    const result = await draftChapterStream(
      {
        project_id: projectId,
        outline_id: form.outline_id,
        chapter_id: form.chapter_id,
        chapter_no: form.chapter_no,
        instruction: form.instruction,
        rhythm_level: form.rhythm_level,
      },
      {
        onStart: (detail, startedChapterId) => {
          if (startedChapterId) {
            chapterId.value = startedChapterId
            form.chapter_id = startedChapterId
          }
          addEvent('流式生成', detail, 'running')
        },
        onDelta: (content) => {
          draft.value += content
        },
        onError: (detail) => addEvent('生成中断', detail, 'error'),
      }
    )
    if (!result) throw new Error('流式生成未返回完成事件')
    chapterId.value = result.chapter_id
    form.chapter_id = result.chapter_id
    // 自动生成标题
    if (!chapterTitle.value) {
      chapterTitle.value = `第${form.chapter_no}章`
    }
    addEvent('保存章节', `章节 ID ${result.chapter_id} 已写入草稿库`)
    await loadResources()
    addEvent('生成完成', result.source === 'llm' ? '真实模型已返回正文' : result.source, 'success')
    if (showToast) message.success(result.source === 'llm' ? '章节已生成' : '已生成开发模式草稿')
    // 生成完成后自动切到分析 Tab
    activeTab.value = 'analysis'
    return true
  } catch (error) {
    if (!draft.value.trim()) draft.value = previousDraft
    analysis.value = previousAnalysis
    polishOriginal.value = previousPolishOriginal
    addEvent('生成失败', errorMessage(error), 'error')
    message.error(draft.value.trim() ? '生成中断，已保留当前输出' : '章节生成失败')
    return false
  } finally {
    loading.value = false
  }
}

async function generateAndAnalyze() {
  const generated = await generate({ showToast: false })
  if (generated) {
    const analyzed = await analyze({ showToast: false })
    message.success(analyzed ? '章节已生成并分析完成' : '章节已生成，分析未完成')
  }
}

// ---- v3 工作流生成 ----
async function generateV3(options: { showToast?: boolean } = {}) {
  const { showToast = true } = options
  if (loading.value) return false

  const projectId = await ensureProject()
  if (!projectId) return false

  loading.value = true
  hydrateInstructionFromSelection()
  ensureActiveOutline()
  if (!hasGenerationGoal()) {
    loading.value = false
    message.warning('请先选择大纲或填写本章目标')
    addEvent('生成拦截', '缺少大纲或本章目标，已取消生成', 'error')
    return false
  }
  await refreshContextPreview()

  const previousDraft = draft.value
  const previousAnalysis = analysis.value
  draft.value = ''
  analysis.value = ''
  polishOriginal.value = ''
  consistencyResult.value = null
  clearAnalysisSections()

  // 初始化工作流步骤
  workflowSteps.value = buildWorkflowSteps(selectedWorkflow.value)
  currentWorkflowStep.value = null
  workflowProgress.value = 0
  showWorkflowPanel.value = true
  activeTab.value = 'params'

  addEvent(
    'v3 工作流启动',
    `模板：${workflowTemplates.value.find(t => t.name === selectedWorkflow.value)?.label ?? selectedWorkflow.value}，第 ${form.chapter_no} 章`,
    'running'
  )

  try {
    const result = await workflowGenerateStream(
      {
        project_id: projectId,
        outline_id: form.outline_id,
        chapter_id: form.chapter_id,
        chapter_no: form.chapter_no,
        instruction: form.instruction,
        rhythm_level: form.rhythm_level,
        template_name: selectedWorkflow.value,
      },
      {
        onStepStart: (stepId, label) => {
          currentWorkflowStep.value = stepId
          const step = workflowSteps.value.find(s => s.id === stepId)
          if (step) {
            step.status = 'running'
          }
          addEvent('步骤开始', label, 'running')
        },
        onDelta: (stepId, content) => {
          // 只有写作步骤的 delta 写入正文
          if (stepId === 'writer') {
            draft.value += content
          }
        },
        onStepDone: (stepId, result) => {
          const step = workflowSteps.value.find(s => s.id === stepId)
          if (step) {
            step.status = 'completed'
            step.durationMs = 0  // 后端可补充
          }
          // 更新进度
          const completedCount = workflowSteps.value.filter(s => s.status === 'completed').length
          workflowProgress.value = (completedCount / workflowSteps.value.length) * 100
          addEvent('步骤完成', step?.label ?? stepId, 'success')

          // 如果是分析步骤，保存分析结果
          if (stepId === 'analyzer' && result) {
            const summary = result.summary || result.content
            if (summary) analysis.value = summary as string
            if (result.character_changes) analysisSections.character_changes = result.character_changes as string
            if (result.world_changes) analysisSections.world_changes = result.world_changes as string
            if (result.new_foreshadowings) analysisSections.new_foreshadowings = result.new_foreshadowings as string
            if (result.timeline_events) analysisSections.timeline_events = result.timeline_events as string
            if (summary) analysisSections.summary = summary as string
          }

          // 如果是精修步骤，把精修结果写入草稿
          if (stepId === 'polisher' && result?.content) {
            draft.value = result.content as string
          }
        },
        onWorkflowDone: (status, runId, sessionContext) => {
          currentRunId.value = runId
          workflowProgress.value = 100
          currentWorkflowStep.value = null
          addEvent('工作流完成', `状态：${status}`, 'success')

          // 从 session_context 获取章节 ID
          if (sessionContext?.chapter_id) {
            chapterId.value = sessionContext.chapter_id as number
            form.chapter_id = sessionContext.chapter_id as number
          }
        },
        onChangeProposalsReady: (savedChapterId, pendingCount) => {
          chapterId.value = savedChapterId
          form.chapter_id = savedChapterId
          addEvent('变化提案就绪', pendingCount + ' 条待审核', 'success')
          void loadChapterChangeProposals()
        },
        onError: (messageStr, stepId) => {
          const step = workflowSteps.value.find(s => s.id === stepId)
          if (step) {
            step.status = 'failed'
            step.errorMessage = messageStr
          }
          addEvent('步骤失败', `${step?.label ?? stepId}: ${messageStr}`, 'error')
        },
      }
    )

    if (!result) throw new Error('工作流未返回完成事件')

    // 自动生成标题
    if (!chapterTitle.value) {
      chapterTitle.value = `第${form.chapter_no}章`
    }

    addEvent('保存章节', `章节已写入草稿库`)
    await loadResources()
    await loadVersions()  // 刷新版本列表
    await loadChapterChangeProposals()
    addEvent('生成完成', 'v3 工作流已完成', 'success')
    if (showToast) message.success('章节已生成')

    // 生成完成后自动切到分析 Tab
    if (analysis.value) {
      activeTab.value = 'analysis'
    }
    // 生成完成后保持面板打开，方便用户查看和重跑
    // showWorkflowPanel.value = false
    return true
  } catch (error) {
    if (!draft.value.trim()) draft.value = previousDraft
    else {
      // 有内容说明生成到一半中断了，保存中断状态
      isInterrupted.value = true
      interruptedRunId.value = currentRunId.value
    }
    analysis.value = previousAnalysis
    addEvent('生成失败', errorMessage(error), 'error')
    message.error(draft.value.trim() ? '生成中断，可点击「继续生成」或从步骤处重跑' : '章节生成失败')
    // showWorkflowPanel.value = false
    return false
  } finally {
    loading.value = false
  }
}

// ---- v3 断点续传 ----
async function resumeGenerateV3() {
  if (loading.value || !interruptedRunId.value) return false

  const projectId = await ensureProject()
  if (!projectId) return false

  loading.value = true
  showWorkflowPanel.value = true

  addEvent('续传启动', `从 ${currentWorkflowStep.value ?? '中断处'} 继续生成`, 'running')

  try {
    const result = await workflowResumeStream(
      {
        run_id: interruptedRunId.value,
        chapter_no: form.chapter_no,
        outline_id: form.outline_id ?? undefined,
        instruction: form.instruction,
        rhythm_level: form.rhythm_level,
      },
      {
        onStepStart: (stepId, label) => {
          currentWorkflowStep.value = stepId
          const step = workflowSteps.value.find(s => s.id === stepId)
          if (step) {
            step.status = 'running'
          }
          addEvent('步骤开始', label, 'running')
        },
        onDelta: (stepId, content) => {
          if (stepId === 'writer') {
            draft.value += content
          }
        },
        onStepDone: (stepId, stepResult) => {
          const step = workflowSteps.value.find(s => s.id === stepId)
          if (step) {
            step.status = 'completed'
          }
          const completedCount = workflowSteps.value.filter(s => s.status === 'completed').length
          workflowProgress.value = (completedCount / workflowSteps.value.length) * 100
          addEvent('步骤完成', step?.label ?? stepId, 'success')

          if (stepId === 'analyzer' && stepResult) {
            const summary = stepResult.summary || stepResult.content
            if (summary) analysis.value = summary as string
            if (stepResult.character_changes) analysisSections.character_changes = stepResult.character_changes as string
            if (stepResult.world_changes) analysisSections.world_changes = stepResult.world_changes as string
            if (summary) analysisSections.summary = summary as string
          }

          if (stepId === 'polisher' && stepResult?.content) {
            draft.value = stepResult.content as string
          }
        },
        onWorkflowDone: (status, runId, sessionContext) => {
          currentRunId.value = runId
          workflowProgress.value = 100
          currentWorkflowStep.value = null
          isInterrupted.value = false
          interruptedRunId.value = null
          addEvent('续传完成', `状态：${status}`, 'success')
          if (sessionContext?.chapter_id) {
            chapterId.value = sessionContext.chapter_id as number
            form.chapter_id = sessionContext.chapter_id as number
          }
        },
        onChangeProposalsReady: (savedChapterId, pendingCount) => {
          chapterId.value = savedChapterId
          form.chapter_id = savedChapterId
          addEvent('变化提案就绪', pendingCount + ' 条待审核', 'success')
          void loadChapterChangeProposals()
        },
        onError: (messageStr, stepId) => {
          const step = workflowSteps.value.find(s => s.id === stepId)
          if (step) {
            step.status = 'failed'
            step.errorMessage = messageStr
          }
          addEvent('续传失败', `${step?.label ?? stepId}: ${messageStr}`, 'error')
        },
      }
    )

    if (!result) throw new Error('续传未返回完成事件')

    if (!chapterTitle.value) {
      chapterTitle.value = `第${form.chapter_no}章`
    }

    addEvent('保存章节', `章节已写入草稿库`)
    await loadResources()
    await loadVersions()
    await loadChapterChangeProposals()
    addEvent('续传成功', '工作流已从中断处完成', 'success')
    message.success('续传完成')

    if (analysis.value) {
      activeTab.value = 'analysis'
    }
    showWorkflowPanel.value = false
    return true
  } catch (error) {
    addEvent('续传失败', errorMessage(error), 'error')
    message.error('续传失败，请重试')
    showWorkflowPanel.value = false
    return false
  } finally {
    loading.value = false
  }
}

// 从指定步骤重跑
async function handleRestartFromStep(stepId: string) {
  if (loading.value || !interruptedRunId.value) {
    // 如果不是中断状态，但用户想重跑某个步骤，需要有 run_id
    if (!currentRunId.value) {
      message.warning('当前没有可重跑的工作流')
      return
    }
  }

  const step = workflowSteps.value.find(s => s.id === stepId)
  if (!step) return

  const runId = interruptedRunId.value || currentRunId.value
  if (!runId) return

  // 确认提示
  const downstreamCount = getDownstreamStepCount(stepId)
  const stepName = step.label
  const msg = downstreamCount > 0
    ? `从「${stepName}」开始重跑，将重新执行该步骤及其后续 ${downstreamCount} 个步骤，确认吗？`
    : `重新执行「${stepName}」步骤，确认吗？`

  if (!window.confirm(msg)) return

  // 使用续传接口 + restart_from_step_id 实现重跑
  isInterrupted.value = false
  loading.value = true
  showWorkflowPanel.value = true

  addEvent('重跑步骤', `从 ${stepName} 开始重跑`, 'running')

  try {
    const result = await workflowResumeStream(
      {
        run_id: runId,
        chapter_no: form.chapter_no,
        outline_id: form.outline_id ?? undefined,
        instruction: form.instruction,
        rhythm_level: form.rhythm_level,
        restart_from_step_id: stepId,
      },
      {
        onStepStart: (sid, label) => {
          currentWorkflowStep.value = sid
          const s = workflowSteps.value.find(x => x.id === sid)
          if (s) s.status = 'running'
        },
        onDelta: (sid, content) => {
          if (sid === 'writer') draft.value += content
        },
        onStepDone: (sid, stepResult) => {
          const s = workflowSteps.value.find(x => x.id === sid)
          if (s) s.status = 'completed'
          const completedCount = workflowSteps.value.filter(x => x.status === 'completed').length
          workflowProgress.value = (completedCount / workflowSteps.value.length) * 100
          addEvent('步骤完成', s?.label ?? sid, 'success')

          if (sid === 'analyzer' && stepResult) {
            const summary = stepResult.summary || stepResult.content
            if (summary) analysis.value = summary as string
            if (stepResult.character_changes) analysisSections.character_changes = stepResult.character_changes as string
            if (summary) analysisSections.summary = summary as string
          }
          if (sid === 'polisher' && stepResult?.content) {
            draft.value = stepResult.content as string
          }
        },
        onWorkflowDone: (status, newRunId, sessionContext) => {
          currentRunId.value = newRunId
          workflowProgress.value = 100
          currentWorkflowStep.value = null
          addEvent('重跑完成', `状态：${status}`, 'success')
          if (sessionContext?.chapter_id) {
            chapterId.value = sessionContext.chapter_id as number
            form.chapter_id = sessionContext.chapter_id as number
          }
        },
        onChangeProposalsReady: (savedChapterId, pendingCount) => {
          chapterId.value = savedChapterId
          form.chapter_id = savedChapterId
          addEvent('变化提案就绪', pendingCount + ' 条待审核', 'success')
          void loadChapterChangeProposals()
        },
        onError: (messageStr, sid) => {
          const s = workflowSteps.value.find(x => x.id === sid)
          if (s) { s.status = 'failed'; s.errorMessage = messageStr }
          addEvent('重跑失败', `${s?.label ?? sid}: ${messageStr}`, 'error')
        },
      }
    )

    if (!result) throw new Error('重跑未返回完成事件')
    await loadResources()
    await loadVersions()
    message.success('重跑完成')
    showWorkflowPanel.value = false
  } catch (error) {
    addEvent('重跑失败', errorMessage(error), 'error')
    message.error('重跑失败')
    showWorkflowPanel.value = false
  } finally {
    loading.value = false
  }
}

// 获取下游步骤数量（用于提示）
function getDownstreamStepCount(stepId: string): number {
  // 根据模板的依赖关系计算下游步骤数
  const deps: Record<string, string[]> = {}
  for (const step of workflowSteps.value) {
    deps[step.id] = []
  }
  // 简单处理：按顺序，后面的都是下游
  const idx = workflowSteps.value.findIndex(s => s.id === stepId)
  return idx >= 0 ? workflowSteps.value.length - idx - 1 : 0
}

// 取消中断状态（重新开始时）
function clearInterruptedState() {
  isInterrupted.value = false
  interruptedRunId.value = null
}

// 加载工作流模板
async function loadWorkflowTemplates() {
  try {
    workflowTemplates.value = await getWorkflowTemplates()
    // 如果有模板，选择第一个默认模板
    if (workflowTemplates.value.length > 0) {
      const defaultTemplate = workflowTemplates.value.find(t => t.name === 'smart_mode') ?? workflowTemplates.value[0]
      selectedWorkflow.value = defaultTemplate.name
    }
    // 初始化工作流步骤，让流水线始终可见
    workflowSteps.value = buildWorkflowSteps(selectedWorkflow.value)
  } catch (error) {
    console.warn('加载工作流模板失败，使用内置默认值', error)
    // 使用内置默认模板
    workflowTemplates.value = [
      { name: 'quick_write', label: '快速写作', description: '单步写作，最快出稿', icon: '⚡', category: 'writing', step_count: 1 },
      { name: 'smart_mode', label: '智能模式', description: '分析 + 规划 + 写作，质量均衡', icon: '🎯', category: 'writing', step_count: 3 },
      { name: 'deep_creation', label: '深度创作', description: '分析 + 规划 + 写作 + 精修', icon: '🎨', category: 'writing', step_count: 4 },
    ]
    workflowSteps.value = buildWorkflowSteps(selectedWorkflow.value)
  }
}

// 加载用户偏好
async function loadPreferences() {
  if (!projectStore.currentProject) return
  prefsLoading.value = true
  try {
    const prefs = await getUserPreferences(projectStore.currentProject.id)
    Object.assign(userPrefs, prefs)
    // 如果偏好中有默认模板，同步到选中状态
    const defaultTpl = prefs.default_template as string | undefined
    if (defaultTpl && workflowTemplates.value.some(t => t.name === defaultTpl)) {
      selectedWorkflow.value = defaultTpl
    }
  } catch (error) {
    console.warn('加载用户偏好失败', error)
  } finally {
    prefsLoading.value = false
  }
}

// 保存用户偏好
async function savePreferences() {
  if (!projectStore.currentProject) return
  prefsSaving.value = true
  try {
    await updateUserPreferences(projectStore.currentProject.id, { ...userPrefs })
    addEvent('偏好保存', '写作偏好已更新，下次生成自动应用', 'success')
    message.success('偏好已保存')
    // 同步默认模板到选中状态
    if (userPrefs.default_template) {
      selectedWorkflow.value = userPrefs.default_template
    }
  } catch (error) {
    addEvent('偏好保存失败', errorMessage(error), 'error')
    message.error('偏好保存失败')
  } finally {
    prefsSaving.value = false
  }
}

// 格式化字数显示
function formatWordCount(count?: number): string {
  if (!count) return '0'
  if (count >= 10000) return (count / 10000).toFixed(1) + '万'
  if (count >= 1000) return (count / 1000).toFixed(1) + 'k'
  return String(count)
}

// 加载版本列表
async function loadVersions() {
  if (!chapterId.value) return
  versionsLoading.value = true
  try {
    generationVersions.value = await getGenerationVersions(chapterId.value)
  } catch (error) {
    console.warn('加载版本列表失败', error)
  } finally {
    versionsLoading.value = false
  }
}

// 格式化版本日期
function formatVersionDate(dateStr: string) {
  try {
    const d = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - d.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return '刚刚'
    if (diffMins < 60) return `${diffMins} 分钟前`
    if (diffHours < 24) return `${diffHours} 小时前`
    if (diffDays < 7) return `${diffDays} 天前`
    return d.toLocaleDateString('zh-CN')
  } catch {
    return dateStr
  }
}

// 切换版本
async function switchVersion(ver: GenerationVersion) {
  if (!chapterId.value || ver.is_current) return
  try {
    const result = await setCurrentVersion(chapterId.value, ver.version_id)
    if (result.success) {
      draft.value = result.content
      addEvent('切换版本', `已切换到 v${ver.version_number} 版本（${ver.word_count} 字）`, 'success')
      message.success(`已切换到 v${ver.version_number} 版本`)
      await loadVersions()  // 刷新版本列表状态
      await loadResources()
    } else {
      message.error('版本切换失败')
    }
  } catch (error) {
    addEvent('切换版本失败', errorMessage(error), 'error')
    message.error('版本切换失败')
  }
}

// ---- 版本时间线 ----
const timelineVersions = computed(() =>
  generationVersions.value.map(v => ({
    id: v.version_id,
    version_no: `v${v.version_number}`,
    word_count: v.word_count,
    created_at: v.created_at,
    is_current: !!v.is_current,
    is_favorite: !!v.is_favorite,
    summary: v.summary,
    rating: v.rating ?? undefined,
    template_used: '',
  }))
)

const currentVersionId = computed(() =>
  generationVersions.value.find(v => v.is_current)?.version_id
)

function handleTimelineVersionSelect(versionId: string) {
  const ver = generationVersions.value.find(v => v.version_id === versionId)
  if (ver) switchVersion(ver)
}

function handleVersionCompare(versionId: string) {
  message.info('版本对比功能开发中')
}

// ---- 流水线步骤点击 ----
function handlePipelineStepClick(stepId: string) {
  const step = workflowSteps.value.find(s => s.id === stepId)
  if (!step) return
  // 点击步骤切换到对应 Tab 查看产物
  const tabMap: Record<string, string> = {
    planner: 'context',
    writer: 'params',
    polisher: 'params',
    analyzer: 'analysis',
  }
  if (tabMap[stepId]) {
    activeTab.value = tabMap[stepId]
  }
}

// ---- 技能开关 ----
function handleSkillToggle(skillId: string) {
  const skill = agentSkills.value.find(s => s.id === skillId)
  if (skill) skill.active = !skill.active
  addEvent('技能切换', `${skill?.name}: ${skill?.active ? '启用' : '禁用'}`, 'info')
}

// ---- 保存章节 ----
async function saveCurrentChapter() {
  const projectId = await ensureProject()
  if (!projectId) return

  const payload = {
    project_id: projectId,
    outline_id: form.outline_id,
    chapter_no: form.chapter_no,
    title: chapterTitle.value || `第${form.chapter_no}章`,
    content: draft.value,
    status: 'draft',
  }

  if (chapterId.value) {
    await updateResource<ChapterItem>('chapters', chapterId.value, payload)
    addEvent('保存章节', `章节 ID ${chapterId.value} 已更新`)
    message.success('章节草稿已更新')
  } else {
    const created = await createResource<ChapterItem>('chapters', payload)
    chapterId.value = created.id
    form.chapter_id = created.id
    addEvent('保存章节', `新章节 ID ${created.id} 已创建`)
    message.success('章节草稿已保存')
  }
  await loadResources()
}

// ---- 分析章节 ----
async function analyze(options: { showToast?: boolean } = {}) {
  const { showToast = true } = options
  if (!chapterId.value || !projectStore.currentProject) {
    message.warning('请先生成或保存章节后再分析')
    return false
  }
  addEvent('分析启动', `章节 ID ${chapterId.value} 正在沉淀摘要`, 'running')
  activeTab.value = 'analysis'
  try {
    const result = await analyzeChapter({
      project_id: projectStore.currentProject.id,
      chapter_id: chapterId.value,
      content: draft.value,
    })
    analysis.value = result.analysis
    setAnalysisSections(result)
    await loadAgentLogs()
    await loadResources()
    await loadChapterChangeProposals()
    addEvent('分析完成', '摘要、人物变化、伏笔线索已生成')
    if (showToast) message.success('章节分析已完成')
    return true
  } catch (error) {
    addEvent('分析失败', errorMessage(error), 'error')
    message.error('章节分析失败')
    return false
  }
}

// ---- 一致性检查 ----
async function runConsistencyCheck() {
  if (!projectStore.currentProject) {
    message.warning('请先加载项目')
    return
  }
  addEvent('一致性检查', '正在核对大纲、世界观、角色、组织和伏笔', 'running')
  activeTab.value = 'analysis'
  try {
    consistencyResult.value = await checkConsistency({
      project_id: projectStore.currentProject.id,
      chapter_id: chapterId.value,
      content: draft.value,
    })
    await loadAgentLogs()
    addEvent(
      '检查完成',
      `${riskLabel(consistencyResult.value.risk_level)}，${consistencyResult.value.suggestions[0]}`
    )
    message.success('一致性检查完成')
  } catch (error) {
    addEvent('检查失败', errorMessage(error), 'error')
    message.error('一致性检查失败')
  }
}

// ---- 精修 ----
function openPolishMenu() {
  if (!chapterId.value || !projectStore.currentProject) {
    message.warning('请先生成或保存章节后再精修')
    return
  }
  showPolishModal.value = true
}

async function doPolish() {
  if (!chapterId.value || !projectStore.currentProject) return
  const mode = polishModes.find((m) => m.value === selectedPolishMode.value)
  if (!mode) return

  showPolishModal.value = false
  addEvent('精修启动', `模式：${mode.name}`, 'running')
  try {
    const beforePolish = draft.value
    const result = await polishChapter({
      project_id: projectStore.currentProject.id,
      chapter_id: chapterId.value,
      mode: mode.name,
      instruction: mode.desc,
    })
    polishOriginal.value = beforePolish
    draft.value = result.content
    await loadResources()
    addEvent('精修完成', '正文已覆盖为精修版本，变化段落已高亮')
    message.success('章节已精修')
  } catch (error) {
    addEvent('精修失败', errorMessage(error), 'error')
    message.error('章节精修失败')
  }
}

// ---- 删除章节 ----
async function removeChapter(id: number) {
  await deleteResource('chapters', id)
  if (chapterId.value === id) {
    chapterId.value = null
    form.chapter_id = null
    draft.value = ''
    chapterTitle.value = ''
    analysis.value = ''
    polishOriginal.value = ''
    consistencyResult.value = null
    clearAnalysisSections()
  }
  addEvent('删除章节', `章节 ID ${id} 已删除`)
  message.success('章节已删除')
  await loadResources()
}

// ---- 初始化 ----
useProjectDataLoader(loadResources)

// v3 工作流初始化
loadWorkflowTemplates()

// 加载用户偏好（项目加载完成后）
watch(
  () => projectStore.currentProject,
  (proj) => {
    if (proj) {
      loadPreferences()
    }
  },
  { immediate: true }
)

// 步骤 1：章节或项目切换时刷新对应的审核队列，避免沿用上一章提案。
watch(
  () => String(projectStore.currentProject?.id ?? '') + ':' + String(chapterId.value ?? ''),
  () => {
    void loadChapterChangeProposals()
  },
  { immediate: true },
)

// 切换模板时同步更新流水线步骤
watch(
  () => selectedWorkflow.value,
  (tpl) => {
    if (tpl && !loading.value) {
      workflowSteps.value = buildWorkflowSteps(tpl)
      workflowProgress.value = 0
      currentWorkflowStep.value = null
    }
  }
)
</script>

<style scoped>
.chapter-generate-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 14px;
  box-sizing: border-box;
  overflow-y: auto;
  overflow-x: hidden;
  --bg-primary: #0f1629;
  --bg-secondary: rgba(30, 42, 69, 0.6);
  --bg-card: rgba(30, 42, 69, 0.5);
  --border: rgba(255, 255, 255, 0.08);
  --text-primary: #e5e7eb;
  --text-secondary: #9ca3af;
  --text-muted: #6b7280;
  --accent-primary: #6366f1;
  --accent-secondary: #8b5cf6;
  --accent-gradient: linear-gradient(135deg, #6366f1, #8b5cf6, #a855f7);
}

/* 自定义滚动条 */
.chapter-generate-page::-webkit-scrollbar {
  width: 6px;
}
.chapter-generate-page::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.03);
  border-radius: 3px;
}
.chapter-generate-page::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.12);
  border-radius: 3px;
}
.chapter-generate-page::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}

/* ===== 页头 ===== */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  padding: 0 2px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.title-icon {
  font-size: 18px;
}

.page-subtitle {
  font-size: 12px;
  color: var(--text-muted);
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
  gap: 14px;
  padding: 8px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  backdrop-filter: blur(10px);
}

.header-stats .stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 50px;
}

.header-stats .stat-num {
  font-size: 16px;
  font-weight: 700;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1.2;
}

.header-stats .stat-num.success {
  background: linear-gradient(135deg, #10b981, #34d399);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-stats .stat-label {
  font-size: 10px;
  color: var(--text-muted);
  margin-top: 2px;
}

.header-stats .stat-divider {
  width: 1px;
  height: 24px;
  background: var(--border);
}

/* ===== 三栏工作台 ===== */
/* ===== 工作流流水线 ===== */
.pipeline-section {
  flex-shrink: 0;
}

.workbench {
  flex: 1;
  display: grid;
  grid-template-columns: 280px 1fr 360px;
  gap: 14px;
  min-height: 600px;
}

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

/* ===== 资源 Tab 浏览器 ===== */
.resource-tabs {
  flex: 1 0 220px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border-top: 1px solid var(--border);
}

.resource-tab-bar {
  display: flex;
  padding: 0 6px;
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  overflow-x: auto;
  scrollbar-width: none;
}

.resource-tab-bar::-webkit-scrollbar {
  display: none;
}

.resource-tab-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 10px 12px 8px;
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
  font-size: 18px;
  line-height: 1;
}

.tab-badge {
  position: absolute;
  top: 6px;
  right: 6px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  background: var(--accent-gradient);
  color: #fff;
  font-size: 10px;
  font-weight: 600;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
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

/* ===== 中间编辑器 ===== */
.editor-panel {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  backdrop-filter: blur(10px);
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.toolbar-left {
  flex: 1;
  min-width: 0;
}

.title-input {
  font-size: 16px;
  font-weight: 600;
}

.title-input :deep(input) {
  font-size: 16px !important;
  font-weight: 600 !important;
  color: var(--text-primary) !important;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.word-count {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.count-num {
  font-size: 18px;
  font-weight: 700;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.count-label {
  font-size: 12px;
  color: var(--text-muted);
}

.save-status {
  font-size: 12px;
  color: var(--text-muted);
}

.save-status.saved {
  color: #6ee7b7;
}

.chapter-id {
  font-size: 11px;
  color: var(--text-muted);
}

.editor-container {
  flex: 1;
  min-height: 0;
  padding: 16px;
  overflow-x: hidden;
  overflow-y: auto;
}

.editor-container::-webkit-scrollbar {
  width: 6px;
}

.editor-container::-webkit-scrollbar-track {
  background: transparent;
}

.editor-container::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.12);
  border-radius: 3px;
}

.editor-container::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}

.chapter-textarea {
  min-height: 100%;
  background: transparent !important;
}

.chapter-textarea :deep(textarea) {
  line-height: 1.9;
  font-size: 15px;
  padding: 16px !important;
  color: var(--text-primary) !important;
  background: transparent !important;
  overflow-y: hidden !important;
  scrollbar-width: none;
}

.chapter-textarea :deep(textarea)::-webkit-scrollbar {
  display: none;
}

/* 精修对比面板 */
.polish-panel {
  border-top: 1px solid var(--border);
  max-height: 200px;
  overflow-y: auto;
  flex-shrink: 0;
}

.polish-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.02);
}

.polish-title {
  font-size: 13px;
  font-weight: 600;
  flex: 1;
  color: var(--text-primary);
}

.polish-content {
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.polish-segment {
  margin: 0;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  line-height: 1.7;
  white-space: pre-wrap;
  background: rgba(255, 255, 255, 0.02);
  font-size: 13px;
  color: var(--text-secondary);
}

.polish-segment.changed {
  border-color: rgba(245, 158, 11, 0.4);
  color: #fef3c7;
  background: rgba(245, 158, 11, 0.1);
}

/* ===== 右侧面板 ===== */
.right-panel {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  backdrop-filter: blur(10px);
}

.side-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.side-tabs :deep(.n-tabs-nav) {
  padding: 0 8px;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.02) !important;
  border-bottom: 1px solid var(--border) !important;
}

.side-tabs :deep(.n-tabs-tab) {
  padding: 10px 14px;
  font-size: 12px;
  color: var(--text-secondary) !important;
}

.side-tabs :deep(.n-tabs-tab--active) {
  color: #c7d2fe !important;
}

.side-tabs :deep(.n-tabs-pane-wrapper) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.side-tabs :deep(.n-tab-pane) {
  flex: 1;
  min-height: 0;
  height: 100%;
  overflow-y: auto;
  padding: 0 !important;
}

/* 右侧面板滚动条 */
.side-tabs :deep(.n-tab-pane)::-webkit-scrollbar {
  width: 4px;
}
.side-tabs :deep(.n-tab-pane)::-webkit-scrollbar-track {
  background: transparent;
}
.side-tabs :deep(.n-tab-pane)::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
}
.side-tabs :deep(.n-tab-pane)::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}

.tab-content {
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border);
}

.form-block:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.block-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.field-hint {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 6px;
  line-height: 1.5;
}

.form-row {
  display: flex;
  gap: 10px;
}

/* 生成按钮组 */
.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.secondary-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.secondary-actions > :nth-child(5),
.secondary-actions > :nth-child(6) {
  grid-column: span 2;
}

/* 上下文预检 */
.score-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--n-color-2, #2a2f3a);
  color: var(--n-text-color-2, #9ca3af);
  font-weight: 500;
}

.score-badge.good {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.check-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.check-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 6px;
  background: var(--n-color-1, #1e2228);
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
}

.check-item.ready {
  border-color: rgba(16, 185, 129, 0.3);
  color: #6ee7b7;
  background: rgba(16, 185, 129, 0.08);
}

.check-icon {
  font-size: 12px;
  width: 14px;
  text-align: center;
}

.check-label {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ===== 上下文 Tab ===== */
.context-stats-card {
  margin-top: 12px;
  padding: 12px;
  background: rgba(99, 102, 241, 0.06);
  border: 1px solid rgba(99, 102, 241, 0.15);
  border-radius: 10px;
}

.stats-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 10px;
}

.stats-icon { font-size: 14px; }

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 10px;
}

.stats-grid .stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 8px 4px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 6px;
}

.stats-grid .stat-num {
  font-size: 16px;
  font-weight: 700;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.stats-grid .stat-label {
  font-size: 10px;
  color: var(--text-muted);
}

.stats-tip {
  font-size: 11px;
  color: var(--text-muted);
  text-align: center;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

/* ===== 分析 Tab ===== */
.empty-analysis,
.empty-consistency,
.empty-memory,
.empty-logs {
  padding: 24px 16px;
  text-align: center;
  color: var(--n-text-color-3, #6b7280);
  font-size: 12px;
  background: var(--n-color-1, #1e2228);
  border-radius: 8px;
}

.empty-icon {
  font-size: 28px;
  margin-bottom: 8px;
}

.analysis-cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.analysis-card {
  padding: 10px 12px;
  background: var(--n-color-1, #1e2228);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
}

.card-label {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--n-text-color-2, #9ca3af);
}

.analysis-card p {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--n-text-color-1, #e5e7eb);
}

.empty-proposals {
  padding: 16px;
  color: var(--n-text-color-3, #6b7280);
  background: var(--n-color-1, #1e2228);
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.6;
}

.proposal-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.proposal-card {
  padding: 12px;
  background: var(--n-color-1, #1e2228);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
}

.proposal-applied {
  border-color: rgba(16, 185, 129, 0.3);
}

.proposal-conflict {
  border-color: rgba(239, 68, 68, 0.45);
}

.proposal-heading,
.proposal-title,
.proposal-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.proposal-heading {
  justify-content: space-between;
  flex-wrap: wrap;
}

.proposal-title {
  flex-wrap: wrap;
}

.proposal-title strong {
  font-size: 13px;
}

.proposal-source {
  color: var(--n-text-color-3, #6b7280);
  font-size: 10px;
}

.proposal-rationale,
.proposal-review-note {
  margin: 8px 0;
  font-size: 12px;
  line-height: 1.5;
}

.proposal-evidence {
  margin: 8px 0;
  padding: 7px 9px;
  border-left: 2px solid #6366f1;
  background: rgba(99, 102, 241, 0.07);
  color: var(--n-text-color-2, #9ca3af);
  font-size: 11px;
  line-height: 1.5;
}

.proposal-diff {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 8px;
}

.proposal-diff-row {
  display: grid;
  grid-template-columns: minmax(72px, 0.7fr) minmax(0, 1fr) 20px minmax(0, 1fr);
  align-items: start;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.025);
  font-size: 11px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.proposal-field {
  color: var(--n-text-color-2, #9ca3af);
}

.proposal-before {
  color: #f59e0b;
}

.proposal-arrow {
  color: var(--n-text-color-3, #6b7280);
  text-align: center;
}

.proposal-after {
  color: #34d399;
}

.proposal-review-note {
  color: #f87171;
}

.proposal-edit-hint {
  margin: 0 0 10px;
  color: var(--n-text-color-2, #9ca3af);
  font-size: 12px;
  line-height: 1.5;
}

.proposal-actions {
  justify-content: flex-end;
  margin-top: 10px;
}

.consistency-result {
  padding: 12px;
  border-radius: 8px;
  border: 1px solid var(--n-border-color, #2a2f3a);
  background: var(--n-color-1, #1e2228);
}

.consistency-result.low {
  border-color: rgba(16, 185, 129, 0.3);
  background: rgba(16, 185, 129, 0.05);
}

.consistency-result.medium {
  border-color: rgba(245, 158, 11, 0.3);
  background: rgba(245, 158, 11, 0.05);
}

.consistency-result.high {
  border-color: rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.05);
}

.risk-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  margin-bottom: 10px;
  font-size: 14px;
}

.risk-icon {
  font-size: 18px;
}

.suggestion-list {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  line-height: 1.8;
  color: var(--n-text-color-2, #9ca3af);
}

.memory-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.memory-item {
  padding: 8px 10px;
  background: var(--n-color-1, #1e2228);
  border-radius: 6px;
}

.memory-chapter {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 4px;
}

.memory-item p {
  margin: 0;
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
  line-height: 1.5;
}

/* ===== 运行轨迹 ===== */
.logs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.timeline-item {
  display: grid;
  grid-template-columns: 12px minmax(0, 1fr);
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
  background: var(--n-color-1, #1e2228);
}

.timeline-dot {
  width: 10px;
  height: 10px;
  margin-top: 5px;
  border-radius: 50%;
  background: #64748b;
}

.timeline-item.success .timeline-dot {
  background: #10b981;
}

.timeline-item.running .timeline-dot {
  background: #f59e0b;
  animation: pulse 1.5s ease-in-out infinite;
}

.timeline-item.error .timeline-dot {
  background: #ef4444;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.timeline-content {
  min-width: 0;
}

.timeline-title {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 3px;
}

.timeline-detail {
  font-size: 11px;
  color: var(--n-text-color-2, #9ca3af);
  line-height: 1.5;
  word-break: break-all;
}

.timeline-time {
  font-size: 10px;
  color: var(--n-text-color-3, #6b7280);
  margin-top: 3px;
}

/* ===== 精修模式弹窗 ===== */
.polish-modes {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.polish-mode-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
  background: var(--n-color-1, #1e2228);
}

.polish-mode-card:hover {
  border-color: var(--n-color-primary-3, #3b82f6);
}

.polish-mode-card.selected {
  border-color: var(--n-color-primary, #3b82f6);
  background: rgba(59, 130, 246, 0.1);
}

.mode-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.mode-info {
  flex: 1;
  min-width: 0;
}

.mode-name {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 2px;
}

.mode-desc {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
}

.mode-check {
  color: var(--n-color-primary, #3b82f6);
  font-weight: bold;
  font-size: 16px;
}

/* ===== 重新生成确认弹窗 ===== */
.confirm-modal {
  width: min(480px, calc(100vw - 40px));
  padding: 24px;
  border-radius: 12px;
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  text-align: center;
}

.confirm-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

.confirm-title {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 10px;
}

.confirm-text {
  margin: 0 0 8px 0;
  line-height: 1.6;
  color: var(--n-text-color-1, #e5e7eb);
}

.confirm-note {
  margin: 0;
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  line-height: 1.6;
}

.confirm-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 20px;
}

/* ===== v3 工作流模板选择 ===== */
.workflow-template-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.workflow-template-card {
  display: flex;
  align-items: center;
  padding: 12px;
  border: 2px solid var(--n-border-color, #e0e0e0);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: var(--n-color, #fff);
}

.workflow-template-card:hover {
  border-color: var(--n-primary-color, #6366f1);
  background: var(--n-color-hover, #f8f9ff);
}

.workflow-template-card.selected {
  border-color: var(--n-primary-color, #6366f1);
  background: var(--n-color-info, #eef2ff);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.15);
}

.tpl-icon {
  font-size: 24px;
  margin-right: 12px;
  width: 36px;
  text-align: center;
}

.tpl-info {
  flex: 1;
}

.tpl-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--n-text-color, #333);
  margin-bottom: 2px;
}

.tpl-desc {
  font-size: 12px;
  color: var(--n-text-color-2, #666);
}

.tpl-steps {
  font-size: 12px;
  color: var(--n-text-color-3, #999);
  background: var(--n-color, #f5f5f5);
  padding: 2px 8px;
  border-radius: 10px;
}

/* ===== 工作流进度面板 ===== */
.workflow-progress-block {
  background: linear-gradient(135deg, #f8f9ff 0%, #f5f3ff 100%);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid var(--n-border-color, #e0e7ff);
}

.workflow-progress-block .block-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.progress-percent {
  font-size: 14px;
  font-weight: 600;
  color: var(--n-primary-color, #6366f1);
}

/* ===== 版本管理 ===== */
.versions-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.empty-versions {
  text-align: center;
  padding: 40px 20px;
  color: var(--n-text-color-3, #999);
  font-size: 13px;
}

.version-timeline-wrap {
  margin-bottom: 12px;
}

.version-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.version-item {
  padding: 12px;
  border: 1px solid var(--n-border-color, #e0e0e0);
  border-radius: 10px;
  background: var(--n-color, #fff);
  transition: all 0.2s ease;
}

.version-item:hover {
  border-color: var(--n-primary-color, #6366f1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.version-item.current {
  border-color: #10b981;
  background: #f0fdf4;
}

.version-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.version-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 14px;
  color: var(--n-text-color, #333);
}

.version-words {
  font-size: 12px;
  color: var(--n-text-color-3, #999);
}

.version-summary {
  font-size: 13px;
  color: var(--n-text-color-2, #666);
  line-height: 1.5;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.version-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  color: var(--n-text-color-3, #999);
  margin-bottom: 8px;
}

.version-rating {
  color: #f59e0b;
}

.version-actions {
  display: flex;
  justify-content: flex-end;
}

/* ===== 记忆偏好面板 ===== */
.prefs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.prefs-desc {
  font-size: 12px;
  color: var(--n-text-color-2, #666);
  margin-bottom: 16px;
  padding: 8px 12px;
  background: var(--n-color-info, #eef2ff);
  border-radius: 8px;
  border-left: 3px solid var(--n-primary-color, #6366f1);
}

.prefs-form {
  margin-bottom: 16px;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--n-text-color-3, #999);
  margin-top: -4px;
}

.prefs-actions {
  margin-bottom: 20px;
}

.prefs-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.prefs-stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 14px 8px;
  background: linear-gradient(135deg, #f8f9ff 0%, #f5f3ff 100%);
  border-radius: 10px;
  border: 1px solid var(--n-border-color, #e0e7ff);
}

.prefs-stat-card .stat-num {
  font-size: 20px;
  font-weight: 700;
  color: var(--n-primary-color, #6366f1);
  margin-bottom: 4px;
}

.prefs-stat-card .stat-label {
  font-size: 11px;
  color: var(--n-text-color-2, #666);
}

/* ===== 响应式 ===== */
@media (max-width: 1400px) {
  .workbench {
    grid-template-columns: 240px 1fr 320px;
  }
}
</style>
