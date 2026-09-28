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
          选择章节与资料 → 生成新稿或对话优化 → 预览修改并保存版本
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

    <!-- 默认只展示流程摘要；需要查看执行细节时再展开，给正文和资料选择留出空间。 -->
    <div v-if="pipelineSteps.length > 0" class="pipeline-section">
      <div class="pipeline-summary">
        <button class="pipeline-summary-main" type="button" @click="pipelineExpanded = !pipelineExpanded">
          <span class="pipeline-summary-title">{{ workflowTemplates.find(t => t.name === selectedWorkflow)?.label || '章节流程' }}</span>
          <span
            v-for="step in pipelineSteps"
            :key="step.id"
            class="pipeline-summary-step"
            :class="step.status"
          >
            <i></i>{{ step.label }}
          </span>
          <span v-if="currentRunId" class="pipeline-summary-usage">
            {{ formatTokenCount(workflowUsage.totalTokens) }} Token · {{ workflowUsage.llmCalls }} 次请求
          </span>
          <span v-if="generationPhaseLabel" class="pipeline-phase">{{ generationPhaseLabel }}</span>
          <span class="pipeline-summary-toggle">{{ pipelineExpanded ? '收起流程' : '查看流程详情' }}⌄</span>
        </button>
        <button
          v-if="currentRunId || workflowRunDetail"
          class="pipeline-summary-details"
          type="button"
          @click="openWorkflowRunDetails"
        >本次详情</button>
      </div>
      <WorkflowPipeline
        v-if="pipelineExpanded"
        :steps="pipelineSteps"
        :active-step-id="currentWorkflowStep"
        :template-name="selectedWorkflow"
        :template-label="workflowTemplates.find(t => t.name === selectedWorkflow)?.label"
        @step-click="handlePipelineStepClick"
        @restart="handleRestartFromStep"
      />
      <section v-if="writingPlanText" class="integrated-plan-panel">
        <div class="integrated-plan-heading">
          <strong>本章剧情节拍</strong>
          <span>与正文同次请求生成</span>
        </div>
        <pre>{{ writingPlanText }}</pre>
      </section>
    </div>

    <!-- 三栏主体 -->
    <div class="workbench">
      <GenerationResourceBrowser
        :memory-levels="memoryLevels"
        :outlines="outlines"
        :chapters="chapters"
        :characters="characters"
        :organizations="organizations"
        :worlds="worlds"
        :foreshadowings="foreshadowings"
        :selected-outline="selectedOutline"
        :selected-chapter="selectedChapter"
        :outline-id="form.outline_id"
        :chapter-id="chapterId"
        :chapter-no="form.chapter_no"
        :selected-character-ids="selectedCharacterIds"
        :selected-organization-ids="selectedOrganizationIds"
        :selected-world-ids="selectedWorldIds"
        :selected-foreshadowing-ids="selectedForeshadowingIds"
        @select-outline="selectOutline"
        @select-chapter="selectChapter"
        @select-chapter-outline="selectChapterOutline"
        @toggle-character="toggleCharacter"
        @toggle-organization="toggleOrganization"
        @toggle-world="toggleWorld"
        @toggle-foreshadowing="toggleForeshadowing"
        @memory-level-click="handleMemoryLevelClick"
      />

      <ChapterEditorPanel
        v-model:chapter-title="chapterTitle"
        v-model:draft="draft"
        :chapter-no="editorChapterNo"
        outline-label="所属卷"
        :outline-title="editorVolumeOutline?.title || ''"
        :chapter-outline-title="editorChapterOutline?.title || ''"
        :word-count="wordCount"
        :chapter-id="chapterId"
        :editor-font-size="userPrefs.editor_font_size"
        :save-status="draftSaveStatus"
        :has-polish-highlights="hasPolishHighlights"
        :polish-segments="polishSegments"
        @close-polish-comparison="polishOriginal = ''"
        @selection-change="handleEditorSelection"
      />

      <!-- ===== 右侧：Tab 面板 ===== -->
      <aside class="right-panel">
        <n-tabs v-model:value="activeTab" type="line" size="small" class="side-tabs" @update:value="handleTabChange">
          <!-- Tab: 生成参数 -->
          <n-tab-pane name="params" tab="生成">
            <div class="tab-content">
              <!-- Agent 插件卡片 - 架构可视化 -->
              <div class="form-block">
                <AgentPluginCard
                  agent-name="写作师 Agent"
                  agent-description="v3.0 插件化架构"
                  agent-icon="✍️"
                  :variant-id="selectedWriterVariant"
                  :variant-name="activeVariantName"
                  :variants="writerVariants"
                  :skills="agentSkills"
                  :temperature="generationControls.temperature"
                  @variant-change="handleVariantChange"
                  @skill-toggle="handleSkillToggle"
                />
              </div>

              <div class="form-block generation-controls">
                <div class="block-title">本次生成参数 <n-tag size="tiny" type="info">仅本次</n-tag></div>
                <div class="generation-controls-grid">
                  <n-form-item label="创造性">
                    <n-slider v-model:value="generationControls.temperature" :min="0" :max="200" :step="10" />
                    <small>{{ (generationControls.temperature / 100).toFixed(1) }} · 默认 {{ (userPrefs.default_temperature / 100).toFixed(1) }}</small>
                  </n-form-item>
                  <n-form-item label="目标字数">
                    <n-input-number v-model:value="generationControls.targetWordCount" :min="500" :max="10000" :step="500" style="width: 100%" />
                    <small>
                      目标 {{ generationControls.targetWordCount }} 字，允许 ±10%（{{ targetWordRange.min }}–{{ targetWordRange.max }} 字）；按正文去除空白后的字符数统计。
                    </small>
                  </n-form-item>
                </div>
              </div>

              <!-- 工作流进度（生成中/生成后显示） -->
              <div v-if="showWorkflowPanel" class="form-block workflow-progress-block">
                <div class="block-title">
                  <span>生成进度 <span class="progress-percent">{{ Math.round(workflowProgress) }}%</span></span>
                  <div class="workflow-panel-actions">
                    <n-button v-if="currentRunId || workflowRunDetail" text size="tiny" @click="openWorkflowRunDetails">查看完整记录</n-button>
                    <n-button text size="tiny" @click="showWorkflowPanel = false">收起</n-button>
                  </div>
                </div>
                <WorkflowProgress
                  :steps="workflowSteps"
                  :current-step-id="currentWorkflowStep"
                  :overall-progress="workflowProgress"
                  @restart="handleRestartFromStep"
                />
                <div v-if="backgroundAnalysisStatus && backgroundAnalysisChapterId === chapterId" class="background-analysis-status" :class="backgroundAnalysisStatus">
                  <span>{{ backgroundAnalysisStatus === 'running' ? '分析沉淀正在后台进行；正文已保存，可以继续编辑或生成下一章。' : backgroundAnalysisStatus === 'completed' ? '分析沉淀已完成。' : '分析沉淀未完成；正文已保存，可稍后手动重试。' }}</span>
                </div>
                <div v-if="currentRunId || workflowRunDetail" class="workflow-run-metrics">
                  <div class="workflow-metrics-heading">
                    <strong>本次生成消耗</strong>
                    <span>{{ workflowRunDetail?.run.status === 'completed' ? '已完成' : workflowRunDetail?.run.status || (loading ? '执行中' : '已暂停') }}</span>
                  </div>
                  <div class="workflow-metrics-grid">
                    <div><strong>{{ workflowUsage.llmCalls }}</strong><span>模型请求</span></div>
                    <div><strong>{{ formatTokenCount(workflowUsage.inputTokens) }}</strong><span>输入 Token</span></div>
                    <div><strong>{{ formatTokenCount(workflowUsage.outputTokens) }}</strong><span>输出 Token</span></div>
                    <div><strong>{{ formatTokenCount(workflowUsage.totalTokens) }}</strong><span>合计 Token</span></div>
                    <div><strong>{{ workflowUsage.costLabel }}</strong><span>估算费用</span></div>
                    <div><strong>{{ formatWorkflowDuration(workflowUsage.durationMs) }}</strong><span>步骤耗时</span></div>
                  </div>
                  <p class="workflow-usage-note">统计包含失败请求与重跑；{{ workflowUsage.costNote }}</p>
                </div>
              </div>

              <!-- 章节设置 -->
              <div class="form-block">
                <div class="block-title">章节设置</div>
                <n-form label-placement="top" :show-label="true">
                  <div class="form-row chapter-target-row">
                    <n-form-item label="本次生成目标" class="generation-target-field">
                      <div class="generation-target-card" :class="{ unavailable: !currentGenerationOutline }">
                        <strong v-if="currentGenerationOutline">
                          第 {{ currentGenerationChapterNo }} 章 · {{ currentGenerationOutline.title || '未命名章节' }}
                        </strong>
                        <strong v-else>请先选择单章细纲</strong>
                        <small v-if="currentGenerationOutline">
                          生成或重生成当前选中的章节；已有版本会保留在版本记录中。
                        </small>
                        <small v-else>从左侧章节列表选择要生成的章节细纲。</small>
                      </div>
                    </n-form-item>
                    <n-form-item label="节奏等级" class="rhythm-field">
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
                  <n-form-item label="本章重点伏笔" class="foreshadow-field">
                    <div class="foreshadow-control">
                      <n-select
                        v-model:value="selectedForeshadowingIds"
                        multiple
                        filterable
                        clearable
                        :max-tag-count="0"
                        :options="foreshadowingOptions"
                        class="foreshadow-select"
                        placeholder="搜索并选择本章要处理的伏笔"
                      />
                      <div v-if="selectedForeshadowings.length" class="selected-foreshadowings" aria-label="已选重点伏笔">
                        <div class="selected-foreshadowings-header">
                          <span>已选 {{ selectedForeshadowings.length }} 条</span>
                          <span>点击标签移除</span>
                        </div>
                        <div class="selected-foreshadowing-list">
                          <button
                            v-for="item in selectedForeshadowings"
                            :key="item.id"
                            type="button"
                            class="selected-foreshadowing-chip"
                            :title="`${item.keyword} · 点击移除`"
                            :aria-label="`移除重点伏笔：${item.keyword}`"
                            @click="removeSelectedForeshadowing(item.id)"
                          >
                            <span>{{ item.keyword }}</span>
                            <span class="chip-remove" aria-hidden="true">×</span>
                          </button>
                        </div>
                      </div>
                      <div class="field-hint">
                        系统会按章节大纲推荐相关伏笔；手动选中的伏笔会优先进入本次生成上下文。
                      </div>
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
                    v-if="workflowStreamActive"
                    type="warning"
                    block
                    :loading="stopRequested"
                    :disabled="stopRequested || !currentRunId"
                    @click="stopCurrentGeneration"
                  >
                    {{ stopRequested ? '正在断开模型请求…' : '中断并保留进度' }}
                  </n-button>
                  <n-button
                    v-if="isInterrupted && interruptedRunId && canResumeInterruptedRun"
                    type="warning"
                    block
                    size="large"
                    :loading="workflowAction === 'resume'"
                    :disabled="loading"
                    @click="resumeGenerateV3"
                  >
                    <template #icon>⏯️</template>
                    {{ workflowAction === 'resume' ? '正在断点续传…' : '继续生成（断点续传）' }}
                  </n-button>
                  <div v-if="isInterrupted && interruptedRunId && !canResumeInterruptedRun" class="interrupted-target-hint">
                    生成已暂停在第 {{ interruptedGenerationTarget?.chapterNo }} 章；切回该章后可继续生成
                  </div>
                  <n-button
                    v-if="currentRunId && !isInterrupted && !showWorkflowPanel"
                    block
                    :disabled="loading"
                    @click="showWorkflowPanel = true"
                  >
                    <template #icon>📊</template>
                    查看生成进度 / 重跑步骤
                  </n-button>
                  <n-popconfirm
                    v-if="draft.trim()"
                    positive-text="生成新版本"
                    negative-text="取消"
                    @positive-click="requestGenerate('generate')"
                  >
                    <template #trigger>
                      <n-button
                        type="primary"
                        block
                        size="large"
                        :loading="workflowAction === 'generate' || (loading && !workflowAction && !useV3Workflow)"
                        :disabled="loading || !canGenerateCurrentChapter"
                      >
                        <template #icon>🔄</template>
                        重新生成正文
                      </n-button>
                    </template>
                    将按当前章节细纲生成新版本，现有正文会保留在版本记录中。
                  </n-popconfirm>
                  <n-button
                    v-else
                    type="primary"
                    block
                    size="large"
                    :loading="workflowAction === 'generate' || (loading && !workflowAction && !useV3Workflow)"
                    :disabled="loading || !canGenerateCurrentChapter"
                    @click="requestGenerate('generate')"
                  >
                    <template #icon>✨</template>
                    生成正文
                  </n-button>
                  <n-button
                    v-if="!useV3Workflow"
                    block
                    :loading="loading && !workflowAction"
                    :disabled="loading || !canGenerateCurrentChapter"
                    @click="requestGenerate('generateAndAnalyze')"
                  >
                    <template #icon>🔄</template>
                    生成正文并分析
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

          <!-- 对话改稿单独呈现；候选稿确认后才写入章节并创建版本。 -->
          <n-tab-pane name="dialogue" tab="对话改稿">
            <ChapterDialoguePanel
              :chapter-title="chapterTitle"
              :scope="dialogueScope"
              :messages="dialogueMessages"
              :candidate="dialogueCandidate"
              :selection-text="editorSelection?.text || ''"
              :busy="dialogueBusy"
              :busy-status="dialogueBusyStatus"
              :applying="dialogueApplying"
              :can-send="Boolean(projectStore.currentProject && draft.trim())"
              :can-apply="canApplyDialogueCandidate"
              :sessions="dialogueSessions"
              :session-id="dialogueSessionId"
              :session-loading="dialogueSessionLoading"
              :can-manage-sessions="Boolean(chapterId)"
              @send="sendChapterDialogue"
              @apply="applyChapterDialogueCandidate"
              @update:scope="changeDialogueScope"
              @discard="discardDialogueCandidate"
              @new-session="newChapterDialogueSession"
              @select-session="selectChapterDialogueSession"
              @stop="stopChapterDialogue"
            />
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
                :volume-outline="selectedVolumeOutline"
                :outline="selectedOutline"
                :summaries="summaries"
                v-model:selected-character-ids="selectedCharacterIds"
                v-model:selected-organization-ids="selectedOrganizationIds"
                v-model:selected-world-ids="selectedWorldIds"
                v-model:selected-foreshadowing-ids="selectedForeshadowingIds"
                :current-chapter-no="form.chapter_no"
                @auto-recommend="autoRecommendContext"
                @manual-selection-change="handleManualContextSelectionChange"
                @manual-selection-replace="replaceManualContextSelection"
              />

              <!-- 后端实际读取结果，核对选择器和模型输入是否一致 -->
              <div class="resolved-context-card">
                <div class="resolved-context-header">
                  <div class="stats-title"><span class="stats-icon">📦</span><span>本次生成实际读取</span></div>
                  <n-button size="tiny" quaternary :loading="previewLoading" @click="refreshContextPreview()">
                    刷新预览
                  </n-button>
                </div>
                <div class="resolved-context-footnote">
                  手动选择与智能推荐项优先注入；自动匹配和系统记忆按本章大纲补充。
                </div>
                <n-spin :show="previewLoading">
                  <div v-if="contextPreview" class="resolved-context-groups">
                    <div class="resolved-context-required">
                      <div class="resolved-context-section-title">每次生成必读</div>
                      <article v-for="item in contextPreview.required_context" :key="item.label" class="resolved-context-required-item">
                        <strong>{{ item.label }} · {{ item.title || '未命名' }}</strong>
                        <small v-if="item.updated_at" class="resolved-context-updated">设定更新于 {{ formatDateTime(item.updated_at) }}</small>
                        <p>{{ item.content || '暂无补充说明' }}</p>
                      </article>
                    </div>
                    <div class="resolved-context-group">
                      <span class="resolved-context-label">人物</span>
                      <n-tag v-for="item in contextPreview.characters" :key="`character-${item.id}`" size="small">
                        {{ item.name }} · {{ contextSourceLabel(item.selection_source) }}
                      </n-tag>
                      <span v-if="!contextPreview.characters.length" class="resolved-context-empty">暂无相关资料</span>
                    </div>
                    <div class="resolved-context-group">
                      <span class="resolved-context-label">组织</span>
                      <n-tag v-for="item in contextPreview.organizations" :key="`organization-${item.id}`" size="small">
                        {{ item.name }} · {{ contextSourceLabel(item.selection_source) }}
                      </n-tag>
                      <span v-if="!contextPreview.organizations.length" class="resolved-context-empty">暂无相关资料</span>
                    </div>
                    <div class="resolved-context-group">
                      <span class="resolved-context-label">世界观</span>
                      <n-tag v-for="item in contextPreview.world_settings" :key="`world-${item.id}`" size="small">
                        {{ item.title }} · {{ contextSourceLabel(item.selection_source) }}
                      </n-tag>
                      <span v-if="!contextPreview.world_settings.length" class="resolved-context-empty">暂无相关资料</span>
                    </div>
                    <div class="resolved-context-group">
                      <span class="resolved-context-label">伏笔</span>
                      <n-tag v-for="item in contextPreview.foreshadowings" :key="`foreshadowing-${item.id}`" size="small">
                        {{ item.keyword }} · {{ contextSourceLabel(item.selection_source) }}
                      </n-tag>
                      <span v-if="!contextPreview.foreshadowings.length" class="resolved-context-empty">暂无相关资料</span>
                    </div>
                    <div class="resolved-context-group system-context-group">
                      <span class="resolved-context-label">系统记忆</span>
                      <span v-if="!contextPreview.recent_summaries.length && !contextPreview.long_term_memories.length" class="resolved-context-empty">暂无前情摘要或长期记忆</span>
                      <div v-for="item in contextPreview.recent_summaries" :key="`summary-${item.id}`" class="resolved-context-memory">
                        <strong>前情摘要</strong><p>{{ item.summary || '暂无摘要' }}</p>
                      </div>
                      <div v-for="item in contextPreview.long_term_memories" :key="`memory-${item.memory_id}`" class="resolved-context-memory">
                        <strong>{{ item.title || '长期记忆' }}</strong><p>{{ item.content_summary || '暂无内容' }}</p>
                      </div>
                    </div>
                  </div>
                  <div v-else class="resolved-context-empty">选择大纲后可查看实际检索结果</div>
                </n-spin>
              </div>

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
                  💡 勾选资料会优先进入上下文；系统也会按本章大纲和要求补充相关设定与前情
                </div>
              </div>
            </div>
          </n-tab-pane>

          <!-- 分析内容独立成组件；章节生成和资料写回仍由工作台统一编排。 -->
          <n-tab-pane name="analysis" tab="分析">
            <ChapterAnalysisPanel
              :analysis="analysis"
              :analysis-status="analysisStatus"
              :analysis-is-stale="analysisIsStale"
              :analysis-freshness-unknown="analysisFreshnessUnknown"
              :analysis-sections="analysisSections"
              :pending-proposal-count="pendingProposalCount"
              :proposal-loading="proposalLoading"
              :proposal-busy-ids="proposalBusyIds"
              :change-proposals="visibleChangeProposals"
              :has-chapter="Boolean(chapterId)"
              :consistency-result="consistencyResult"
              :summaries="summaries"
              :organizations="organizations"
              @reload-proposals="loadChapterChangeProposals"
              @start-proposal-edit="startProposalEdit"
              @review-proposal="reviewChangeProposal"
              @reanalyze="analyze"
            />
          </n-tab-pane>

          <!-- Tab: 版本管理 -->
          <n-tab-pane name="versions" tab="版本">
            <ChapterVersionsPanel
              ref="chapterVersionsPanel"
              :chapter-id="chapterId"
              :draft="draft"
              :persist-draft="() => persistChapterDraft(false)"
              @restore="handleChapterVersionRestored"
            />
          </n-tab-pane>

          <!-- Tab: 记忆偏好 -->
          <n-tab-pane name="preferences" tab="偏好">
            <ChapterPreferencesPanel
              :preferences="userPrefs"
              :template-options="templateOptions"
              :writer-variant-options="writerVariantOptions"
              :auto-sync-options="autoSyncOptions"
              :loading="prefsLoading"
              :saving="prefsSaving"
              :editor-saving="editorPrefsSaving"
              @update:preferences="Object.assign(userPrefs, $event)"
              @refresh="loadPreferences"
              @save="savePreferences"
              @save-editor="saveEditorPreference"
            />
          </n-tab-pane>

          <!-- Tab: 运行轨迹 -->
          <n-tab-pane name="logs" tab="轨迹">
            <ChapterTracePanel
              ref="chapterTracePanel"
              :project-id="projectStore.currentProject?.id ?? null"
              :chapter-id="chapterId"
              :chapters="chapters"
              :templates="workflowTemplates"
              :local-events="localEvents"
            />
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

    <WorkflowRunDetailsModal
      v-model:visible="showWorkflowRunDetails"
      :run-id="currentRunId"
      :run-detail="workflowRunDetail"
      :steps="workflowSteps"
      :current-step-id="currentWorkflowStep"
      :progress="workflowProgress"
      :clock="workflowClock"
    />

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


  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useMessage } from 'naive-ui'
import {
  analyzeChapter,
  checkConsistency,
  draftChapterStream,
  getChapterSummaries,
  getNextChapterTarget,
  getContextPreview,
  polishChapter,
  chatChapterEditStream,
  applyChapterEdit,
  listChapterEditSessions,
  createChapterEditSession,
  getChapterEditSession,
  saveChapterEditSession,
} from '@/api/agents'
import type { ChapterEditSession, ChapterEditSessionSummary, NextChapterTarget } from '@/api/agents'
import {
  getWorkflowTemplates,
  getWorkflowRunDetail,
  workflowGenerateStream,
  workflowResumeStream,
  pauseWorkflowRun,
  getChapterChangeProposals,
  reviewChapterChangeProposal,
  getUserPreferences,
  updateUserPreferences,
  type WorkflowTemplate,
  type WorkflowRunRecord,
  type WorkflowStepRecord,
  type GenerationVersion,
  type ChapterChangeProposal,
  type WorkflowStreamEvent,
} from '@/api/agentsV3'
import WorkflowProgress from '@/components/WorkflowProgress.vue'
import type { StepInfo } from '@/components/WorkflowProgress.vue'
import WorkflowPipeline from '@/components/WorkflowPipeline.vue'
import GenerationResourceBrowser from '@/components/chapter-generation/GenerationResourceBrowser.vue'
import ChapterEditorPanel from '@/components/chapter-generation/ChapterEditorPanel.vue'
import { appendIndentedChapterText, indentChapterParagraphs } from '@/components/chapter-generation/paragraphIndent'
import ChapterDialoguePanel from '@/components/chapter-generation/ChapterDialoguePanel.vue'
import type { ChapterDialogueCandidate, ChapterDialogueMessage } from '@/components/chapter-generation/chapterDialogueTypes'
import ChapterAnalysisPanel from '@/components/chapter-generation/ChapterAnalysisPanel.vue'
import ChapterVersionsPanel from '@/components/chapter-generation/ChapterVersionsPanel.vue'
import ChapterTracePanel from '@/components/chapter-generation/ChapterTracePanel.vue'
import ChapterPreferencesPanel from '@/components/chapter-generation/ChapterPreferencesPanel.vue'
import WorkflowRunDetailsModal from '@/components/chapter-generation/WorkflowRunDetailsModal.vue'
import type { PipelineStep } from '@/components/WorkflowPipeline.vue'
import type { MemoryLevel } from '@/components/MemoryLayer.vue'
import AgentPluginCard from '@/components/AgentPluginCard.vue'
import type { SkillInfo } from '@/components/AgentPluginCard.vue'
import ContextSelector from '@/components/ContextSelector.vue'
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
  OrganizationItem,
  OutlineItem,
  WorldSetting,
} from '@/types/domain'

const message = useMessage()
const projectStore = useProjectStore()

// ---- 基础状态 ----
const loading = ref(false)
const workflowAction = ref<'generate' | 'resume' | 'restart' | null>(null)
const workflowStreamActive = ref(false)
const stopRequested = ref(false)
const chapterGenerationAbortController = ref<AbortController | null>(null)
const draft = ref('')
const chapterTitle = ref('')
const analysis = ref('')
const analysisStatus = ref('')
const activeTab = ref('params')
const pipelineExpanded = ref(false)

// ---- 资料数据 ----
const outlines = ref<OutlineItem[]>([])
const chapters = ref<ChapterItem[]>([])
const worlds = ref<WorldSetting[]>([])
const characters = ref<CharacterItem[]>([])
const organizations = ref<OrganizationItem[]>([])
const foreshadowings = ref<ForeshadowingItem[]>([])
const summaries = ref<ChapterSummary[]>([])
const changeProposals = ref<ChapterChangeProposal[]>([])
const proposalContentSnapshot = ref<string | null>(null)
const proposalSnapshotChapterId = ref<number | null>(null)
let proposalLoadRequestId = 0
const proposalLoading = ref(false)
const proposalBusyIds = ref<string[]>([])
const proposalEditVisible = ref(false)
const proposalEditSaving = ref(false)
const proposalEditText = ref('')
const editingProposal = ref<ChapterChangeProposal | null>(null)
const visibleChangeProposals = computed(() => proposalSnapshotChapterId.value !== chapterId.value
  ? []
  : changeProposals.value.map((item) => ({
      ...item,
      is_stale: item.is_stale === true
        || (proposalContentSnapshot.value !== null && proposalContentSnapshot.value !== draft.value),
    })))
const pendingProposalCount = computed(() => visibleChangeProposals.value.filter(item => item.status === 'pending').length)
const localEvents = ref<
  Array<{ id: string; title: string; detail: string; time: string; status: string }>
>([])
const contextPreview = ref<ContextPreview | null>(null)
const nextChapterTarget = ref<NextChapterTarget | null>(null)
const previewLoading = ref(false)
let contextPreviewRequestId = 0

// 上下文选择器状态
const selectedCharacterIds = ref<number[]>([])
const selectedOrganizationIds = ref<number[]>([])
const selectedWorldIds = ref<number[]>([])
const selectedForeshadowingIds = ref<number[]>([])
const manualContextIds = reactive<Record<string, number[]>>({
  character_ids: [], organization_ids: [], world_setting_ids: [], foreshadowing_ids: [],
})

function handleManualContextSelectionChange(category: string, id: number, selected: boolean) {
  const ids = new Set(manualContextIds[category] ?? [])
  if (selected) ids.add(id)
  else ids.delete(id)
  manualContextIds[category] = [...ids]
}

function replaceManualContextSelection(category: string, ids: number[]) {
  manualContextIds[category] = [...ids]
}

function clearManualContextSelection() {
  Object.keys(manualContextIds).forEach((category) => { manualContextIds[category] = [] })
}

function getManualContextSelectionPayload(): Record<string, number[]> {
  return Object.fromEntries(Object.entries(manualContextIds).map(([category, ids]) => [category, [...ids]]))
}

function contextSourceLabel(source: string): string {
  const labels: Record<string, string> = {
    manual: '手动选择', recommended: '智能推荐', automatic: '自动匹配', system: '系统资料',
  }
  return labels[source] ?? '系统资料'
}

// 步骤 1：由页面集中维护上下文选择状态，子组件只负责触发选择事件。
function toggleContextId(selectedIds: number[], id: number) {
  const index = selectedIds.indexOf(id)
  if (index >= 0) selectedIds.splice(index, 1)
  else selectedIds.push(id)
}

function toggleCharacter(id: number) { toggleContextId(selectedCharacterIds.value, id) }
function toggleOrganization(id: number) { toggleContextId(selectedOrganizationIds.value, id) }
function toggleWorld(id: number) { toggleContextId(selectedWorldIds.value, id) }
function toggleForeshadowing(id: number) { toggleContextId(selectedForeshadowingIds.value, id) }

/**
 * 生成前统一组装作者勾选的上下文实体。
 * 步骤 1：复制四类选择 ID，避免请求期间页面数组变更。
 * 步骤 2：用后端约定的字段名供预览、生成和续跑共用。
 */
function getContextSelectionPayload(): Record<string, number[]> {
  return {
    character_ids: [...selectedCharacterIds.value],
    organization_ids: [...selectedOrganizationIds.value],
    world_setting_ids: [...selectedWorldIds.value],
    foreshadowing_ids: [...selectedForeshadowingIds.value],
  }
}

// 自动推荐上下文
function autoRecommendContext() {
  // 步骤 1：重跑推荐后，系统推荐项与作者主动选项保持来源区分。
  clearManualContextSelection()
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
const chapterProjectId = ref<number | null>(null)
const dialogueScope = ref<'chapter' | 'selection'>('chapter')
const dialogueMessages = ref<ChapterDialogueMessage[]>([])
const dialogueSessions = ref<ChapterEditSessionSummary[]>([])
const dialogueSessionId = ref<string | null>(null)
const dialogueSessionRevision = ref(0)
const dialogueSessionLoading = ref(false)
const dialogueBusyStatus = ref('')
let dialogueAbortController: AbortController | null = null
let dialogueSessionLoadSequence = 0
let dialogueSessionLoadingKey: string | null = null
const dialogueCandidate = ref<(ChapterDialogueCandidate & {
  chapterId: number
  selectionStart: number | null
  instruction: string
}) | null>(null)
const editorSelection = ref<{ start: number; end: number; text: string } | null>(null)
const dialogueBusy = ref(false)
const dialogueApplying = ref(false)
const canApplyDialogueCandidate = computed(() => Boolean(
  dialogueCandidate.value
  && dialogueCandidate.value.chapterId === chapterId.value
  && dialogueCandidate.value.expectedContent === draft.value,
))
const draftSaveStatus = ref<'saved' | 'unsaved' | 'saving' | 'error'>('unsaved')
const draftSaveError = ref('')
const persistedDraftFingerprint = ref('')
let draftAutosaveTimer: ReturnType<typeof setTimeout> | undefined
let draftSaveInFlight: Promise<boolean> | null = null
let draftSaveQueued = false
const polishOriginal = ref('')
const consistencyResult = ref<ConsistencyCheckResult | null>(null)

const analysisSections = reactive({
  summary: '',
  character_changes: '',
  world_changes: '',
  new_foreshadowings: '',
  timeline_events: '',
})
const analysisContentSnapshot = ref<string | null>(null)
const analysisPersistedStale = ref<boolean | null>(null)
const analysisIsStale = computed(() => analysisPersistedStale.value === true
  || (analysisContentSnapshot.value !== null && analysisContentSnapshot.value !== draft.value))
const analysisFreshnessUnknown = computed(() => analysisPersistedStale.value === null
  && analysisContentSnapshot.value !== null
  && !analysisIsStale.value)

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
const selectedWorkflow = ref('quick_write')
const workflowSteps = ref<StepInfo[]>([])
const writingPlanText = ref('')
const backgroundAnalysisStatus = ref<'running' | 'completed' | 'failed' | ''>('')
const backgroundAnalysisChapterId = ref<number | null>(null)
const generationPhase = ref('')
const generationPhaseLabel = computed(() => ({
  planning: '剧情规划中',
  writing: '正文写作中',
  repairing: '字数纠偏中',
  analysis: '分析沉淀中',
  saved: '正文已保存',
  complete: '流程完成',
  analysis_failed: '分析待重试',
}[generationPhase.value] || ''))
const currentWorkflowStep = ref<string | null>(null)
const workflowProgress = ref(0)
const currentRunId = ref<string | null>(null)
const workflowRunDetail = ref<{ run: WorkflowRunRecord; steps: WorkflowStepRecord[] } | null>(null)
const showWorkflowRunDetails = ref(false)
const chapterVersionsPanel = ref<InstanceType<typeof ChapterVersionsPanel> | null>(null)
const chapterTracePanel = ref<InstanceType<typeof ChapterTracePanel> | null>(null)
const showWorkflowPanel = ref(false)  // 生成中显示步骤面板
const isInterrupted = ref(false)  // 是否为中断状态
const interruptedRunId = ref<string | null>(null)  // 中断的 run_id
type GenerationTarget = { outlineId: number | null; chapterNo: number; chapterId: number | null }
const activeGenerationTarget = ref<GenerationTarget | null>(null)
const interruptedGenerationTarget = ref<GenerationTarget | null>(null)
const canResumeInterruptedRun = computed(() => {
  const target = interruptedGenerationTarget.value
  return !target || (
    target.outlineId === form.outline_id
    && target.chapterNo === form.chapter_no
    && (target.chapterId === null || target.chapterId === chapterId.value)
  )
})
let replacePartialOnNextWriterDelta = false
let replacePartialOnNextWriterPlan = false
const workflowClock = ref(Date.now())
let workflowClockTimer: ReturnType<typeof setInterval> | undefined

const workflowUsage = computed(() => {
  // 步骤重跑会保留多条尝试记录；汇总所有记录，避免只显示最后一次而低估消耗。
  const attempts = workflowRunDetail.value?.steps ?? []
  const latestRecords = new Map<string, WorkflowStepRecord>()
  for (const record of attempts) latestRecords.set(record.step_id, record)
  let inputTokens = 0
  let outputTokens = 0
  let totalTokens = 0
  let llmCalls = 0
  let durationMs = 0
  let measuredAttempts = 0
  let pricedAttempts = 0
  let estimatedCost = 0
  const hasUsage = (usage?: WorkflowStepRecord['token_usage']) => Boolean(
    usage && [usage.input_tokens, usage.output_tokens, usage.total_tokens].some(value => typeof value === 'number'),
  )
  const addUsage = (usage?: WorkflowStepRecord['token_usage']) => {
    if (!hasUsage(usage)) return
    measuredAttempts += 1
    inputTokens += usage?.input_tokens ?? 0
    outputTokens += usage?.output_tokens ?? 0
    totalTokens += usage?.total_tokens ?? (usage?.input_tokens ?? 0) + (usage?.output_tokens ?? 0)
    if (typeof usage?.cost_cny === 'number') {
      pricedAttempts += 1
      estimatedCost += usage.cost_cny
    }
  }
  for (const attempt of attempts) {
    addUsage(attempt.token_usage)
    llmCalls += attempt.llm_calls ?? 0
    durationMs += attempt.duration_ms ?? 0
  }

  // SSE 到达与详情刷新之间可能有短暂间隔，只在最新记录尚无数值时补入实时值，避免重复累计。
  for (const liveStep of workflowSteps.value) {
    const latest = latestRecords.get(liveStep.id)
    if (!hasUsage(latest?.token_usage)) addUsage(liveStep.tokenUsage ?? undefined)
    if (!latest?.llm_calls) llmCalls += liveStep.llmCalls ?? 0
    if (latest?.duration_ms == null) {
      durationMs += liveStep.durationMs
        ?? (liveStep.startedAt ? workflowClock.value - liveStep.startedAt : 0)
    }
  }
  const pricingSnapshots = [
    ...attempts.map((attempt) => attempt.input_snapshot?.effective_settings?.model?.pricing),
    ...workflowSteps.value.map((step) => {
      const settings = step.effectiveSettings as { model?: { pricing?: { input_price_per_million?: number | null; output_price_per_million?: number | null } } } | undefined
      return settings?.model?.pricing
    }),
  ].filter((pricing): pricing is NonNullable<typeof pricing> => Boolean(pricing))
  const hasPriceSnapshot = pricingSnapshots.length > 0
  const hasAnyPrice = pricingSnapshots.some((pricing) =>
    typeof pricing.input_price_per_million === 'number'
      || typeof pricing.output_price_per_million === 'number',
  )
  const hasCompletePrice = pricingSnapshots.some((pricing) =>
    typeof pricing.input_price_per_million === 'number'
      && typeof pricing.output_price_per_million === 'number',
  )
  const isRunning = loading.value
    || workflowRunDetail.value?.run.status === 'running'
    || attempts.some(attempt => attempt.status === 'running')
  const costLabel = pricedAttempts
    ? `${formatWorkflowCurrency(estimatedCost)}${pricedAttempts < measuredAttempts ? ' *' : ''}`
    : !hasPriceSnapshot
      ? llmCalls ? '无价格快照' : '—'
      : !hasAnyPrice
        ? '未配置单价'
        : !hasCompletePrice
          ? '单价未配全'
          : isRunning
            ? '等待用量'
            : measuredAttempts === 0
              ? '未返回用量'
              : '无法估算'
  const costNote = pricedAttempts
    ? '费用已按调用时价格估算。'
    : !hasPriceSnapshot
      ? '本次运行没有价格快照。'
      : !hasAnyPrice
        ? '本次调用时没有配置输入和输出单价。'
        : !hasCompletePrice
          ? '输入和输出单价需要同时配置。'
          : isRunning
            ? '单价已配置，等待模型返回 Token 用量。'
            : '服务商未返回 Token 用量，无法估算费用。'
  return {
    inputTokens,
    outputTokens,
    totalTokens,
    llmCalls,
    durationMs,
    pricedAttempts,
    estimatedCost,
    costLabel,
    costNote,
  }
})

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
    output: s.outputSummary || s.outputContent
      ? { summary: s.outputSummary || s.outputContent?.slice(0, 320), raw: s.outputContent }
      : undefined,
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
    fast: '快节奏',
  }
  return map[selectedWriterVariant.value] || '均衡风格'
})

const selectedWriterVariant = ref('default')

const writerVariants = [
  { id: 'default',   name: '均衡风格', description: '叙事平稳，适合大多数题材', icon: '⚖️' },
  { id: 'shuangwen', name: '爽文风',   description: '节奏紧凑，打脸升级快感强', icon: '🔥' },
  { id: 'wenqing',   name: '文青风',   description: '文笔细腻，情感氛围浓厚',   icon: '🎨' },
  { id: 'fast',      name: '快节奏',   description: '情节密集，悬念迭起',       icon: '⚡' },
]

function handleVariantChange(variantId: string) {
  if (loading.value) return
  selectedWriterVariant.value = variantId
  addEvent('风格切换', `切换为 ${activeVariantName.value}`, 'info')
  message.success(`本次生成将使用${activeVariantName.value}；长期默认值可在偏好中保存`)
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
const editorPrefsSaving = ref(false)
const userPrefs = reactive({
  default_template: 'quick_write',
  default_writer_variant: 'default',
  default_temperature: 80,
  default_target_word_count: 3000,
  auto_sync_level: 'low_risk_only',
  editor_font_size: 16,
  total_generations: 0,
  total_words_generated: 0,
})
const generationControls = reactive({ temperature: userPrefs.default_temperature, targetWordCount: userPrefs.default_target_word_count })

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
      { id: 'writer', label: '规划并写正文', icon: '✨', status: 'pending' },
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
  return templates[templateName] ?? templates.quick_write
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
const selectedForeshadowings = computed(() =>
  selectedForeshadowingIds.value
    .map((id) => foreshadowings.value.find((item) => item.id === id))
    .filter((item): item is ForeshadowingItem => Boolean(item))
)

function removeSelectedForeshadowing(id: number) {
  selectedForeshadowingIds.value = selectedForeshadowingIds.value.filter((selectedId) => selectedId !== id)
}

// ---- 计算属性 ----
const project = computed(() => projectStore.currentProject)

const selectedOutline = computed(
  () => outlines.value.find((item) => item.id === form.outline_id) ?? null
)
const selectedVolumeOutline = computed(() => {
  const volumeId = selectedOutline.value?.volume_id
  if (volumeId === null || volumeId === undefined) return null
  return outlines.value.find((item) => item.id === volumeId && item.node_type === 'volume') ?? null
})
const editorVolumeOutline = computed(() =>
  selectedOutline.value?.node_type === 'volume' ? selectedOutline.value : selectedVolumeOutline.value
)
const selectedChapter = computed(
  () => chapters.value.find((item) => item.id === chapterId.value) ?? null
)
const currentGenerationOutline = computed(() => {
  if (selectedChapter.value) return findOutlineForChapter(selectedChapter.value)
  if (selectedOutline.value?.node_type === 'chapter') return selectedOutline.value
  if (selectedOutline.value?.node_type === 'volume') {
    const inVolume = outlines.value
      .filter((item) => item.node_type === 'chapter' && item.volume_id === selectedOutline.value?.id)
      .sort((left, right) => (left.chapter_no ?? left.sort_index) - (right.chapter_no ?? right.sort_index))
    return inVolume.find((item) => item.chapter_no === form.chapter_no) ?? inVolume[0] ?? null
  }
  if (nextChapterTarget.value?.available) {
    return outlines.value.find((item) => item.id === nextChapterTarget.value?.outline_id) ?? null
  }
  return null
})
const currentGenerationChapterNo = computed(() =>
  currentGenerationOutline.value?.chapter_no ?? currentGenerationOutline.value?.sort_index ?? form.chapter_no
)
const canGenerateCurrentChapter = computed(() => Boolean(currentGenerationOutline.value))
const targetWordRange = computed(() => {
  const target = Math.max(500, Math.min(10000, Number(generationControls.targetWordCount) || 3000))
  return { min: Math.ceil(target * 0.9), max: Math.floor(target * 1.1) }
})
const editorChapterNo = computed(() => {
  const titleNumber = Number(chapterTitle.value.match(/^第\s*(\d+)\s*章$/)?.[1])
  const candidates = [
    selectedChapter.value?.chapter_no,
    selectedOutline.value?.node_type === 'chapter' ? selectedOutline.value.chapter_no : undefined,
    titleNumber,
    nextChapterTarget.value?.chapter_no,
    form.chapter_no,
  ]
  return candidates.find((value): value is number =>
    typeof value === 'number' && Number.isInteger(value) && value > 0
  ) ?? 1
})
const editorChapterOutline = computed(() => {
  if (selectedOutline.value?.node_type === 'chapter') return selectedOutline.value
  const nextTarget = nextChapterTarget.value
  if (nextTarget?.available && nextTarget.chapter_no === editorChapterNo.value) {
    const targetOutline = outlines.value.find((item) => item.id === nextTarget.outline_id)
    if (targetOutline?.node_type === 'chapter') return targetOutline
    if (nextTarget.outline_title) return { title: nextTarget.outline_title }
  }
  return outlines.value.find((item) =>
    item.node_type === 'chapter'
    && item.chapter_no === editorChapterNo.value
    && (selectedOutline.value?.node_type !== 'volume' || item.volume_id === selectedOutline.value.id)
  ) ?? null
})
const wordCount = computed(() => draft.value.replace(/\s/g, '').length)

const polishSegments = computed(() => {
  const before = splitParagraphs(polishOriginal.value)
  return splitParagraphs(draft.value).map((text, index) => ({
    text,
    status: text.trim() !== (before[index] ?? '').trim() ? 'changed' as const : 'same' as const,
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

// ---- 工具函数 ----
function shortText(value: string, max = 58) {
  return value?.length > max ? `${value.slice(0, max)}...` : value || '暂无正文'
}

function formatChars(content: string): string {
  const len = content?.replace(/\s/g, '').length || 0
  if (len >= 10000) return (len / 10000).toFixed(1) + '万'
  return len.toString()
}

function formatDateTime(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

function splitParagraphs(value: string) {
  return value
    .split(/\n{2,}/)
    .map((item) => item.trim())
    .filter(Boolean)
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
  analysisStatus.value = ''
  analysisContentSnapshot.value = null
  analysisPersistedStale.value = null
}

/**
 * 统一处理生成、续跑和步骤重跑返回的分析结果。
 * 步骤 1：识别模型不可用状态，清除兜底文本解析出的伪分析字段。
 * 步骤 2：只将有效分析摘要和各变化分区放入工作台。
 */
function applyWorkflowAnalysisResult(result: Record<string, unknown>) {
  if (result.analysis_status === 'unavailable') {
    const wasAlreadyUnavailable = analysisStatus.value === 'unavailable'
    setAnalysisSections({})
    analysisContentSnapshot.value = null
    analysisPersistedStale.value = null
    analysis.value = String(result.analysis_message || '模型服务不可用，本次未保存章节分析；配置模型后可重新分析。')
    analysisStatus.value = 'unavailable'
    if (!wasAlreadyUnavailable) addEvent('分析不可用', analysis.value, 'error')
    return
  }

  analysisStatus.value = 'completed'
  analysis.value = String(result.summary || result.content || '')
  setAnalysisSections(result)
  analysisContentSnapshot.value = draft.value
  analysisPersistedStale.value = false
}

async function loadChapterChangeProposals() {
  const projectId = projectStore.currentProject?.id
  const currentChapterId = chapterId.value
  if (!projectId || !currentChapterId) {
    changeProposals.value = []
    proposalContentSnapshot.value = null
    proposalSnapshotChapterId.value = null
    return
  }
  const requestId = ++proposalLoadRequestId
  const contentSnapshot = draft.value
  proposalLoading.value = true
  try {
    const result = await getChapterChangeProposals(projectId, currentChapterId)
    if (requestId !== proposalLoadRequestId || currentChapterId !== chapterId.value) return
    changeProposals.value = result.items
    proposalContentSnapshot.value = contentSnapshot
    proposalSnapshotChapterId.value = currentChapterId
  } catch {
    if (requestId !== proposalLoadRequestId || currentChapterId !== chapterId.value) return
    // 章节刚切换或后端尚未升级时，保留页面其他功能并允许手动重试。
    changeProposals.value = []
  } finally {
    if (requestId === proposalLoadRequestId) proposalLoading.value = false
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
  await chapterTracePanel.value?.refresh()
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
    nextTarget,
  ] = await Promise.all([
    listResource<OutlineItem>(projectId, 'outlines'),
    listResource<ChapterItem>(projectId, 'chapters'),
    listResource<WorldSetting>(projectId, 'world'),
    listResource<CharacterItem>(projectId, 'characters'),
    listResource<OrganizationItem>(projectId, 'organizations'),
    listResource<ForeshadowingItem>(projectId, 'foreshadowings'),
    getChapterSummaries(projectId, 100),
    getNextChapterTarget(projectId),
  ])
  outlines.value = outlineList
  chapters.value = chapterList
  worlds.value = worldList
  characters.value = characterList
  organizations.value = organizationList
  foreshadowings.value = foreshadowingList
  summaries.value = summaryList
  nextChapterTarget.value = nextTarget
  await restoreChapterSelection(projectId, chapterList)
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

  const requestId = ++contextPreviewRequestId
  previewLoading.value = true
  try {
    const result = await getContextPreview(
      projectId,
      form.chapter_no,
      form.outline_id,
      form.instruction,
      getContextSelectionPayload(),
      getManualContextSelectionPayload(),
    )
    if (requestId !== contextPreviewRequestId) return
    contextPreview.value = result
    if (!options.silent)
      addEvent(
        '拼装上下文',
        `角色 ${contextPreview.value.characters.length}，组织 ${contextPreview.value.organizations.length}，伏笔 ${contextPreview.value.foreshadowings.length}，长期记忆 ${contextPreview.value.long_term_memories.length}`
      )
  } catch (error) {
    if (requestId !== contextPreviewRequestId) return
    if (!options.silent) {
      addEvent('上下文预览失败', errorMessage(error), 'error')
      message.error('上下文预览失败')
    }
  } finally {
    if (requestId === contextPreviewRequestId) previewLoading.value = false
  }
}

// ---- 生成相关 ----
async function requestGenerate(mode: 'generate' | 'generateAndAnalyze') {
  if (isInterrupted.value && interruptedRunId.value) {
    message.warning(canResumeInterruptedRun.value
      ? '当前章节生成尚未完成，请先继续或重跑这次任务'
      : `第 ${interruptedGenerationTarget.value?.chapterNo} 章仍有暂停的生成任务，请先返回该章继续`)
    return
  }
  if (loading.value || !await prepareCurrentGenerationTarget()) return
  if (!hasGenerationGoal()) {
    message.warning('请先选择单章细纲或填写本章目标')
    addEvent('生成拦截', '当前章节缺少可用的写作目标', 'error')
    return
  }
  await runGenerateMode(mode)
}

/** 保存当前编辑，并把本次生成绑定到作者选中的章节细纲。 */
async function prepareCurrentGenerationTarget() {
  const projectId = await ensureProject()
  if (!projectId) return false

  // 先按当前编辑区的身份保存；切换目标会另走章节选择流程。
  if (!await saveDraftBeforeNavigation('开始生成')) return false

  const outline = currentGenerationOutline.value
  if (!outline) {
    message.warning('请先从左侧选择要生成的单章细纲')
    return false
  }

  form.outline_id = outline.id
  form.chapter_no = Math.max(1, outline.chapter_no ?? outline.sort_index)
  if (!form.instruction.trim() || form.instruction === selectedChapter.value?.title) {
    form.instruction = outline.description || outline.title
  }
  form.chapter_id = chapterId.value
  markDraftPersisted()
  addEvent('生成目标', `对当前第 ${form.chapter_no} 章执行正文生成`)
  await refreshContextPreview({ silent: true })
  return true
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

function findOutlineForChapter(item: ChapterItem) {
  const chapterOutlines = outlines.value.filter((outline) => outline.node_type === 'chapter')
  const linked = chapterOutlines.find((outline) => outline.id === item.outline_id)
  if (linked) return linked

  const matches = chapterOutlines.filter((outline) => outline.chapter_no === item.chapter_no)
  return matches.length === 1 ? matches[0] : null
}

function hydrateInstructionFromSelection() {
  const currentChapter = selectedChapter.value
  if (!currentChapter) return

  const relatedOutline = findOutlineForChapter(currentChapter)
  if (relatedOutline) {
    form.outline_id = relatedOutline.id
    form.chapter_no = relatedOutline.chapter_no ?? relatedOutline.sort_index ?? currentChapter.chapter_no
    if (!form.instruction.trim() || form.instruction === currentChapter.title) {
      form.instruction = relatedOutline.description
    }
  } else if (!form.instruction.trim()) {
    form.instruction = currentChapter.title
  }
}

function applyOutlineToForm(item: OutlineItem, options: { forceInstruction?: boolean } = {}) {
  form.outline_id = item.id
  if (item.node_type === 'volume') {
    const firstChapter = outlines.value
      .filter((outline) => outline.node_type === 'chapter' && outline.volume_id === item.id)
      .sort((left, right) => (left.chapter_no ?? left.sort_index) - (right.chapter_no ?? right.sort_index))[0]
    form.chapter_no = firstChapter
      ? Math.max(1, firstChapter.chapter_no ?? firstChapter.sort_index)
      : Math.max(1, form.chapter_no || 1)
  } else {
    form.chapter_no = Math.max(1, item.chapter_no ?? item.sort_index)
  }
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

/** 选择单章细纲：恢复关联正文，或准备该章的空白写作目标。 */
async function selectChapterOutline(item: OutlineItem) {
  if (item.node_type !== 'chapter') return

  const chapterNo = Math.max(1, item.chapter_no ?? item.sort_index)
  const chapterOutlines = outlines.value.filter((outline) => outline.node_type === 'chapter')
  const linked = chapters.value
    .filter((chapter) => chapter.outline_id === item.id)
    .sort((left, right) => right.id - left.id)
  const uniqueNumber = chapterOutlines.filter((outline) => outline.chapter_no === item.chapter_no).length === 1
  const legacy = uniqueNumber
    ? chapters.value
        .filter((chapter) => chapter.outline_id === null && chapter.chapter_no === chapterNo)
        .sort((left, right) => right.id - left.id)
    : []
  const relatedChapter = linked.find((chapter) => Boolean(chapter.content?.trim()))
    ?? linked[0]
    ?? legacy.find((chapter) => Boolean(chapter.content?.trim()))
    ?? legacy[0]

  if (form.outline_id === item.id && (relatedChapter?.id ?? null) === chapterId.value) return

  if (!await prepareForChapterSwitch()) return

  if (relatedChapter) {
    await selectChapter(relatedChapter, { prepared: true })
    return
  }

  // 新章没有正文记录时只切换生成上下文，不预建空章节。
  setActiveChapterId(null)
  form.chapter_id = null
  form.outline_id = item.id
  form.chapter_no = chapterNo
  form.instruction = item.description || item.title
  chapterTitle.value = `第${chapterNo}章`
  draft.value = ''
  analysis.value = ''
  writingPlanText.value = ''
  backgroundAnalysisStatus.value = ''
  generationPhase.value = ''
  clearAnalysisSections()
  analysisStatus.value = ''
  analysisContentSnapshot.value = null
  analysisPersistedStale.value = null
  polishOriginal.value = ''
  consistencyResult.value = null
  markDraftPersisted()
  addEvent('选择章节细纲', `第 ${chapterNo} 章·${item.title || '未命名章节'} 已设为写作目标`)
  void refreshContextPreview({ silent: true })
  void refreshChapterVersions()
  if (activeTab.value === 'logs') void refreshTrace()
  nextTick(() => autoRecommendContext())
}

let chapterSwitchPreparation: Promise<boolean> | null = null

function waitUntilGenerationSettles(timeoutMs = 45000): Promise<boolean> {
  if (!loading.value) return Promise.resolve(true)
  return new Promise((resolve) => {
    let stopWatching = () => {}
    let timeoutId = 0
    const finish = (settled: boolean) => {
      window.clearTimeout(timeoutId)
      stopWatching()
      resolve(settled)
    }
    timeoutId = window.setTimeout(() => finish(false), timeoutMs)
    stopWatching = watch(loading, (isLoading) => {
      if (!isLoading) finish(true)
    })
    if (!loading.value) finish(true)
  })
}

/** 切章时暂停当前生成并保存已输出正文，避免生成结果写入另一章。 */
async function prepareForChapterSwitch(): Promise<boolean> {
  if (chapterSwitchPreparation) {
    message.info('正在安全暂停并保存当前章节，请稍候')
    return false
  }

  const preparation = (async () => {
    if (loading.value && useV3Workflow.value && activeGenerationTarget.value && !workflowStreamActive.value) {
      const deadline = Date.now() + 20000
      while (loading.value && !workflowStreamActive.value && Date.now() < deadline) {
        await new Promise((resolve) => window.setTimeout(resolve, 50))
      }
    }

    if (loading.value) {
      if (workflowStreamActive.value) {
        const deadline = Date.now() + 20000
        while (loading.value && workflowStreamActive.value && !currentRunId.value && Date.now() < deadline) {
          await new Promise((resolve) => window.setTimeout(resolve, 50))
        }
        if (loading.value && !currentRunId.value) {
          message.warning('生成流程尚未就绪，请稍候再切换章节')
          return false
        }
        if (loading.value && !stopRequested.value) await stopCurrentGeneration()
        if (!await waitUntilGenerationSettles()) {
          message.warning('生成仍在停止，请稍后再切换章节')
          return false
        }
        if (interruptedRunId.value && activeGenerationTarget.value) {
          interruptedGenerationTarget.value = {
            ...activeGenerationTarget.value,
            chapterId: chapterId.value ?? activeGenerationTarget.value.chapterId,
          }
          addEvent('切换章节', `已暂停第 ${activeGenerationTarget.value.chapterNo} 章并保留进度`)
        }
      } else if (chapterGenerationAbortController.value) {
        chapterGenerationAbortController.value.abort()
        if (!await waitUntilGenerationSettles()) {
          message.warning('生成仍在停止，请稍后再切换章节')
          return false
        }
        addEvent('切换章节', '已停止当前正文生成并保留已输出内容')
      } else {
        message.warning('当前操作完成后即可切换章节')
        return false
      }
    }

    if (!await saveDraftBeforeNavigation('切换细纲')) return false

    if (
      interruptedGenerationTarget.value
      && interruptedGenerationTarget.value.outlineId === form.outline_id
      && interruptedGenerationTarget.value.chapterNo === form.chapter_no
      && chapterId.value !== null
    ) {
      interruptedGenerationTarget.value.chapterId = chapterId.value
    }
    return true
  })()

  chapterSwitchPreparation = preparation
  try {
    return await preparation
  } finally {
    if (chapterSwitchPreparation === preparation) chapterSwitchPreparation = null
  }
}

function chapterSelectionStorageKey(projectId: number) {
  return `imagin:last-chapter:${projectId}`
}

function rememberChapterSelection(projectId: number, id: number) {
  try {
    window.localStorage.setItem(chapterSelectionStorageKey(projectId), String(id))
  } catch {
    // 浏览器禁用本地存储时，服务端章节列表仍可用于恢复最近草稿。
  }
}

function setActiveChapterId(id: number | null, projectId = projectStore.currentProject?.id ?? null) {
  chapterId.value = id
  form.chapter_id = id
  chapterProjectId.value = id === null ? null : projectId
  if (id !== null && projectId !== null) rememberChapterSelection(projectId, id)
}

function draftFingerprint(
  id = chapterId.value,
  title = chapterTitle.value,
  content = draft.value,
  chapterNo = form.chapter_no,
  outlineId = form.outline_id,
) {
  return JSON.stringify([id, title, content, chapterNo, outlineId])
}

function isDefaultChapterTitle(title: string, chapterNo: number) {
  const titleNumber = Number(title.trim().match(/^第\s*(\d+)\s*章$/)?.[1])
  return Number.isInteger(chapterNo) && titleNumber === chapterNo
}

/** 空白新细纲的“第 N 章”只是占位标题，不需要创建空草稿记录。 */
function hasDraftToPersist() {
  if (chapterId.value !== null || draft.value.trim()) return true
  const title = chapterTitle.value.trim()
  return Boolean(title) && !isDefaultChapterTitle(title, form.chapter_no)
}

/** 离开当前目标前仅保存真实草稿；空白占位章节直接记为干净状态。 */
async function saveDraftBeforeNavigation(action: string) {
  if (draftAutosaveTimer) clearTimeout(draftAutosaveTimer)
  if (draftSaveInFlight) await draftSaveInFlight
  if (!hasDraftToPersist()) {
    markDraftPersisted()
    return true
  }
  if (draftFingerprint() === persistedDraftFingerprint.value) return true
  if (await persistChapterDraft(true)) return true

  const detail = draftSaveError.value
  message.error(detail
    ? `当前章节草稿保存失败，暂不能${action}：${detail}`
    : `当前章节草稿保存失败，暂不能${action}。请检查网络或服务状态后重试。`)
  return false
}

function markDraftPersisted(storedContent = draft.value) {
  persistedDraftFingerprint.value = draftFingerprint(
    chapterId.value,
    chapterTitle.value,
    storedContent,
    form.chapter_no,
    form.outline_id,
  )
  draftSaveStatus.value = draftFingerprint() === persistedDraftFingerprint.value ? 'saved' : 'unsaved'
}

/** 页面刷新或切换项目后恢复最近编辑的草稿。 */
async function restoreChapterSelection(projectId: number, chapterList: ChapterItem[]) {
  const currentStillBelongsToProject = chapterProjectId.value === projectId
    && chapterList.some((item) => item.id === chapterId.value)
  if (currentStillBelongsToProject) return

  // 步骤 1：先清理上一项目的编辑区，防止项目切换时短暂展示错章正文。
  setActiveChapterId(null)
  chapterTitle.value = ''
  draft.value = ''
  form.outline_id = null
  form.chapter_no = 1
  form.instruction = ''
  analysis.value = ''
  clearAnalysisSections()
  polishOriginal.value = ''

  // 步骤 2：默认回到最近已有正文的章节；首次打开或尚无正文时再恢复上次选中项。
  let rememberedId: number | null = null
  try {
    const storedId = Number(window.localStorage.getItem(chapterSelectionStorageKey(projectId)))
    if (Number.isInteger(storedId) && storedId > 0) rememberedId = storedId
  } catch {
    // 本地存储不可用时继续按后端列表的最新记录恢复。
  }
  const orderedChapters = [...chapterList].sort((left, right) =>
    left.chapter_no - right.chapter_no || left.id - right.id,
  )
  const generatedChapters = orderedChapters.filter((item) => Boolean(item.content?.trim()))
  const chapter = generatedChapters[generatedChapters.length - 1]
    ?? orderedChapters.find((item) => item.id === rememberedId)
    ?? orderedChapters[0]
  if (chapter) {
    await selectChapter(chapter, { recordEvent: false })
  } else {
    persistedDraftFingerprint.value = draftFingerprint()
    draftSaveStatus.value = 'unsaved'
  }
}

async function selectChapter(item: ChapterItem, options: { recordEvent?: boolean; prepared?: boolean } = {}) {
  if (chapterProjectId.value === projectStore.currentProject?.id && chapterId.value === item.id) return
  if (!options.prepared && !await prepareForChapterSwitch()) return

  const relatedOutline = findOutlineForChapter(item)
  setActiveChapterId(item.id)
  form.outline_id = relatedOutline?.id ?? item.outline_id
  form.chapter_no = Number.isInteger(item.chapter_no) && item.chapter_no > 0 ? item.chapter_no : 1
  form.instruction = relatedOutline?.description || form.instruction || item.title
  const storedContent = item.content
  draft.value = indentChapterParagraphs(storedContent)
  chapterTitle.value = item.title
  markDraftPersisted(storedContent)
  analysis.value = ''
  writingPlanText.value = ''
  backgroundAnalysisStatus.value = ''
  generationPhase.value = ''
  backgroundAnalysisChapterId.value = null
  clearAnalysisSections()
  const savedAnalysis = summaries.value.find((summary) => summary.chapter_id === item.id)
  if (savedAnalysis) {
    analysis.value = savedAnalysis.summary || ''
    analysisStatus.value = 'completed'
    setAnalysisSections({
      summary: savedAnalysis.summary,
      character_changes: savedAnalysis.character_changes,
      world_changes: savedAnalysis.world_changes,
      new_foreshadowings: savedAnalysis.new_foreshadowings,
      timeline_events: savedAnalysis.timeline_events,
    })
    analysisContentSnapshot.value = item.content
    analysisPersistedStale.value = savedAnalysis.is_stale
  }
  polishOriginal.value = ''
  consistencyResult.value = null
  if (options.recordEvent ?? true) {
    addEvent('载入章节', relatedOutline ? `${item.title} 已载入，并恢复章纲目标` : `${item.title} 已进入正文编辑区`)
  }
  void refreshContextPreview({ silent: true })
  void refreshChapterVersions()  // 加载版本列表
  if (activeTab.value === 'logs') void refreshTrace()
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
  const generationController = new AbortController()
  chapterGenerationAbortController.value = generationController
  const previousDraft = draft.value
  const previousAnalysis = analysis.value
  const previousPolishOriginal = polishOriginal.value
  let rawGeneratedContent = ''
  try {
    await refreshContextPreview()
    if (generationController.signal.aborted) throw new Error('章节生成已中断，当前输出已保留')
    addEvent('生成启动', `第 ${form.chapter_no} 章，节奏 ${form.rhythm_level}`, 'running')
    draft.value = ''
    analysis.value = ''
    polishOriginal.value = ''
    consistencyResult.value = null
    clearAnalysisSections()
    const result = await draftChapterStream(
      {
        project_id: projectId,
        outline_id: form.outline_id,
        chapter_id: form.chapter_id,
        chapter_no: form.chapter_no,
        instruction: form.instruction,
        rhythm_level: form.rhythm_level,
        context_selection: getContextSelectionPayload(),
      },
      {
        onStart: (detail, startedChapterId) => {
          if (startedChapterId) {
            setActiveChapterId(startedChapterId, projectId)
          }
          addEvent('流式生成', detail, 'running')
        },
        onDelta: (content) => {
          rawGeneratedContent += content
          draft.value = appendIndentedChapterText(draft.value, content)
        },
        onError: (detail) => addEvent('生成中断', detail, 'error'),
      },
      generationController.signal,
    )
    if (!result) throw new Error('流式生成未返回完成事件')
    setActiveChapterId(result.chapter_id, projectId)
    // 自动生成标题
    if (!chapterTitle.value) {
      chapterTitle.value = `第${form.chapter_no}章`
    }
    markDraftPersisted(rawGeneratedContent)
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
    if (generationController.signal.aborted) {
      addEvent('生成已停止', '按切换章节请求停止；已输出内容保留在当前章节', 'info')
    } else {
      addEvent('生成失败', errorMessage(error), 'error')
      message.error(draft.value.trim() ? '生成中断，已保留当前输出' : '章节生成失败')
    }
    return false
  } finally {
    loading.value = false
    if (chapterGenerationAbortController.value === generationController) {
      chapterGenerationAbortController.value = null
    }
  }
}

async function generateAndAnalyze() {
  const generated = await generate({ showToast: false })
  if (generated) {
    const analyzed = await analyze({ showToast: false })
    message.success(analyzed ? '章节已生成并分析完成' : '章节已生成，分析未完成')
  }
}

/** 统一回填工作流完成状态，确保编辑器显示与持久化一致的最终正文。 */
function applyWorkflowCompletion(
  status: string,
  runId: string,
  sessionContext: Record<string, unknown>,
  actionLabel: string,
) {
  // 步骤 1：回填运行状态和进度，区分已完成与可继续恢复的运行。
  currentRunId.value = runId
  workflowProgress.value = status === 'completed' ? 100 : workflowProgress.value
  currentWorkflowStep.value = null
  isInterrupted.value = status !== 'completed'
  interruptedRunId.value = status === 'completed' ? null : runId
  addEvent(status === 'completed' ? `${actionLabel}完成` : `${actionLabel}未完成`, `状态：${status}`, status === 'completed' ? 'success' : 'error')

  // 步骤 2：完成后使用后端确认的最终稿，避免精修稿或恢复后的正文留在旧状态。
  if (status === 'completed') {
    generationPhase.value = 'saved'
    const finalContent = sessionContext.final_content || sessionContext.draft_content
    if (typeof finalContent === 'string' && finalContent.trim()) draft.value = indentChapterParagraphs(finalContent)
    if (typeof sessionContext.writing_plan === 'string') writingPlanText.value = sessionContext.writing_plan
  }

  // 步骤 3：从持久化结果回填分析和章节关联，覆盖刷新后没有收到步骤事件的情况。
  if (sessionContext.analysis_status) {
    applyWorkflowAnalysisResult({
      analysis_status: sessionContext.analysis_status,
      analysis_message: sessionContext.analysis_message,
      summary: sessionContext.chapter_summary,
      character_changes: sessionContext.character_changes,
      world_changes: sessionContext.world_changes,
      new_foreshadowings: sessionContext.new_foreshadowings,
      timeline_events: sessionContext.timeline_events,
    })
  }
  if (typeof sessionContext.chapter_id === 'number') {
    setActiveChapterId(sessionContext.chapter_id)
    if (activeGenerationTarget.value) activeGenerationTarget.value.chapterId = sessionContext.chapter_id
  }
  if (status === 'completed') {
    const storedContent = String(sessionContext.final_content || sessionContext.draft_content || draft.value)
    markDraftPersisted(storedContent)
    interruptedGenerationTarget.value = null
    activeGenerationTarget.value = null
  } else if (activeGenerationTarget.value) {
    interruptedGenerationTarget.value = { ...activeGenerationTarget.value }
  }
}

/** 读取工作流持久化步骤详情，回填服务端耗时和 Token 用量。 */
async function refreshWorkflowRunDetail(runId: string) {
  try {
    // 步骤 1：读取每步执行记录；步骤 2：同步服务端状态和耗时到流程图。
    const detail = await getWorkflowRunDetail(runId)
    if (!detail) return
    workflowRunDetail.value = detail
    if (detail.run.status === 'paused') {
      currentRunId.value = runId
      interruptedRunId.value = runId
      isInterrupted.value = true
      const partial = detail.session_context?.interrupted_partial_content
      if (typeof partial === 'string' && partial && !draft.value.trim()) draft.value = indentChapterParagraphs(partial)
    }
    for (const record of detail.steps) {
      const step = workflowSteps.value.find((item) => item.id === record.step_id)
      if (!step) continue
      step.status = record.status
      step.durationMs = record.duration_ms ?? undefined
      step.errorMessage = record.error_message || undefined
      step.tokenUsage = record.token_usage
      step.llmCalls = record.llm_calls
      step.contextSummary = record.input_snapshot?.context_summary
      step.effectiveSettings = record.input_snapshot?.effective_settings
      const output = record.output_snapshot ?? {}
      if (step.id === 'planner' && typeof output.content === 'string') step.outputContent = output.content
      if (step.id === 'analyzer' && typeof output.summary === 'string') step.outputSummary = output.summary
      if (step.id === 'writer') {
        const actualCount = Number(output.actual_character_count)
        const minimum = Number(output.target_word_min)
        const maximum = Number(output.target_word_max)
        if (Number.isFinite(actualCount) && Number.isFinite(minimum) && Number.isFinite(maximum)) {
          const inRange = output.word_count_valid === true
          const repairNote = String(output.length_repair_warning || output.length_repair_error || '')
          step.outputSummary = `目标范围 ${minimum}-${maximum} 字，实际 ${actualCount} 字（${inRange ? '符合' : '未符合'}）${repairNote ? `；${repairNote}` : ''}`
        }
        const plan = typeof output.writing_plan === 'string' ? output.writing_plan : output.partial_plan
        if (typeof plan === 'string' && plan) writingPlanText.value = plan
        const partialContent = output.partial_content
        if (typeof partialContent === 'string' && partialContent && !draft.value.trim()) {
          draft.value = indentChapterParagraphs(partialContent)
        }
      }
    }
  } catch (error) {
    // 步骤 3：统计详情不可用不改变章节正文或生成状态，只在事件记录中提示。
    addEvent('运行统计读取失败', errorMessage(error), 'error')
  }
}

function applyWorkflowStepStart(stepId: string) {
  const step = workflowSteps.value.find((item) => item.id === stepId)
  if (!step) return
  step.status = 'running'
  step.startedAt = Date.now()
  step.durationMs = undefined
  step.errorMessage = undefined
  step.tokenUsage = null
  step.llmCalls = 0
  if (stepId === 'planner') generationPhase.value = 'planning'
  else if (stepId === 'writer') generationPhase.value = selectedWorkflow.value === 'quick_write' && !writingPlanText.value ? 'planning' : 'writing'
  else if (stepId === 'analyzer') generationPhase.value = 'analysis'
}

function applyWorkflowStepContext(
  stepId: string,
  contextSummary: Record<string, unknown>,
  effectiveSettings: Record<string, unknown>,
) {
  const step = workflowSteps.value.find((item) => item.id === stepId)
  if (!step) return
  step.contextSummary = contextSummary
  step.effectiveSettings = effectiveSettings
  step.llmCalls = effectiveSettings.model_called === true ? 1 : 0
}

function applyWorkflowStepDone(stepId: string, result: Record<string, unknown>) {
  const step = workflowSteps.value.find((item) => item.id === stepId)
  if (!step) return
  step.status = 'completed'
  step.durationMs = step.startedAt ? Date.now() - step.startedAt : undefined
  step.startedAt = undefined
  const tokenUsage = result.token_usage
  step.tokenUsage = tokenUsage && typeof tokenUsage === 'object'
    ? tokenUsage as WorkflowStepRecord['token_usage']
    : null
  step.llmCalls = typeof result.llm_calls === 'number' ? result.llm_calls : 0

  const content = typeof result.content === 'string' ? result.content : ''
  if (stepId === 'writer' && typeof result.writing_plan === 'string') writingPlanText.value = result.writing_plan
  if (stepId === 'writer') generationPhase.value = 'writing'
  if (stepId === 'analyzer') generationPhase.value = 'complete'
  if (stepId === 'planner') step.outputContent = content
  if (stepId === 'analyzer') {
    step.outputSummary = String(result.summary || result.analysis_message || '')
  } else if (stepId === 'writer' || stepId === 'polisher') {
    const actualCount = content.replace(/\s/g, '').length
    const minimum = Number(result.target_word_min)
    const maximum = Number(result.target_word_max)
    const targetSummary = Number.isFinite(minimum) && Number.isFinite(maximum)
      ? `目标范围 ${minimum}-${maximum} 字；`
      : ''
    const lengthStatus = typeof result.word_count_valid === 'boolean'
      ? (result.word_count_valid ? '符合目标' : '未达到目标')
      : '已完成'
    const repairNote = String(result.length_repair_warning || result.length_repair_error || '')
    step.outputSummary = content
      ? `${targetSummary}实际 ${formatTokenCount(actualCount)} 字，${lengthStatus}${repairNote ? `；${repairNote}` : ''}`
      : '步骤已完成。'
    if (typeof result.length_repair_warning === 'string') addEvent('字数纠偏', result.length_repair_warning, 'error')
    if (typeof result.length_repair_error === 'string') addEvent('字数纠偏未完成', result.length_repair_error, 'error')
  } else {
    step.outputSummary = content.slice(0, 500)
  }

  const completedCount = workflowSteps.value.filter((item) => item.status === 'completed').length
  workflowProgress.value = workflowSteps.value.length > 0
    ? (completedCount / workflowSteps.value.length) * 100
    : 0
}

function openWorkflowRunDetails() {
  showWorkflowRunDetails.value = true
  if (currentRunId.value) void refreshWorkflowRunDetail(currentRunId.value)
}

function formatTokenCount(value: number) {
  return new Intl.NumberFormat('zh-CN').format(value)
}

function formatWorkflowCurrency(value: number) {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency', currency: 'CNY', minimumFractionDigits: 4, maximumFractionDigits: 6,
  }).format(value)
}

function formatWorkflowDuration(value: number) {
  const seconds = Math.floor(value / 1000)
  if (seconds < 60) return `${seconds} 秒`
  return `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒`
}

// ---- v3 工作流生成 ----
async function stopCurrentGeneration() {
  const runId = currentRunId.value
  if (!workflowStreamActive.value || !runId || stopRequested.value) return

  stopRequested.value = true
  try {
    await pauseWorkflowRun(runId)
    addEvent('请求中断', '已收到请求，正在结束当前步骤并保留进度', 'info')
    message.info('正在关闭当前模型连接并保留已完成步骤')
  } catch (error) {
    stopRequested.value = false
    message.error(errorMessage(error) || '中断请求失败')
  }
}

async function generateV3(options: { showToast?: boolean } = {}) {
  const { showToast = true } = options
  if (loading.value) return false

  const requestedTargetWordCount = generationControls.targetWordCount

  const projectId = await ensureProject()
  if (!projectId) return false

  workflowAction.value = 'generate'
  loading.value = true
  hydrateInstructionFromSelection()
  ensureActiveOutline()
  if (!hasGenerationGoal()) {
    loading.value = false
    workflowAction.value = null
    message.warning('请先选择大纲或填写本章目标')
    addEvent('生成拦截', '缺少大纲或本章目标，已取消生成', 'error')
    return false
  }
  activeGenerationTarget.value = {
    outlineId: form.outline_id,
    chapterNo: form.chapter_no,
    chapterId: chapterId.value,
  }
  interruptedGenerationTarget.value = null
  await refreshContextPreview()

  const previousDraft = draft.value
  const previousAnalysis = analysis.value
  draft.value = ''
  analysis.value = ''
  writingPlanText.value = ''
  backgroundAnalysisStatus.value = ''
  generationPhase.value = ''
  backgroundAnalysisChapterId.value = null
  polishOriginal.value = ''
  consistencyResult.value = null
  clearAnalysisSections()

  // 初始化工作流步骤
  workflowSteps.value = buildWorkflowSteps(selectedWorkflow.value)
  currentWorkflowStep.value = null
  workflowProgress.value = 0
  currentRunId.value = null
  workflowRunDetail.value = null
  interruptedRunId.value = null
  isInterrupted.value = false
  showWorkflowPanel.value = true
  activeTab.value = 'params'

  addEvent(
    'v3 工作流启动',
    `模板：${workflowTemplates.value.find(t => t.name === selectedWorkflow.value)?.label ?? selectedWorkflow.value}，第 ${form.chapter_no} 章`,
    'running'
  )

  try {
    workflowStreamActive.value = true
    stopRequested.value = false
    const result = await workflowGenerateStream(
      {
        project_id: projectId,
        outline_id: form.outline_id,
        chapter_id: form.chapter_id,
        chapter_no: form.chapter_no,
        instruction: form.instruction,
        rhythm_level: form.rhythm_level,
        context_selection: getContextSelectionPayload(),
        manual_context_selection: getManualContextSelectionPayload(),
        template_name: selectedWorkflow.value,
        generation_options: {
          writer_variant: selectedWriterVariant.value,
          temperature: generationControls.temperature / 100,
          target_word_count: generationControls.targetWordCount,
          active_skills: agentSkills.value.filter(skill => skill.active).map(skill => skill.id),
        },
      },
      {
        onStepStart: (stepId, label, runId) => {
          // 步骤 1：收到第一步事件就记下运行 ID，连接中断时用户仍能恢复。
          if (runId) currentRunId.value = runId
          currentWorkflowStep.value = stepId
          if (stepId === 'writer') draft.value = ''
          applyWorkflowStepStart(stepId)
          addEvent('步骤开始', label, 'running')
        },
        onStepContext: applyWorkflowStepContext,
        onDelta: (stepId, content) => {
          // 只有写作步骤的 delta 写入正文
          if (stepId === 'writer') {
            generationPhase.value = 'writing'
            draft.value = appendIndentedChapterText(draft.value, content)
          }
        },
        onPlanDelta: (stepId, content) => {
          if (stepId === 'writer') {
            generationPhase.value = 'planning'
            writingPlanText.value += content
          }
        },
        onContentReset: (stepId) => {
          if (stepId === 'writer') draft.value = ''
        },
        onStepNotice: (_stepId, notice) => {
          generationPhase.value = 'repairing'
          addEvent('字数纠偏', notice, 'info')
        },
        onStepDone: (stepId, result) => {
          applyWorkflowStepDone(stepId, result)
          const step = workflowSteps.value.find(s => s.id === stepId)
          addEvent('步骤完成', step?.label ?? stepId, 'success')

          // 如果是分析步骤，保存分析结果
          if (stepId === 'analyzer' && result) applyWorkflowAnalysisResult(result)

          // 如果是精修步骤，把精修结果写入草稿
          if (stepId === 'polisher' && result?.content) draft.value = indentChapterParagraphs(String(result.content))
        },
        onWorkflowDone: (status, runId, sessionContext) => {
          applyWorkflowCompletion(status, runId, sessionContext, '工作流')
        },
        onChangeProposalsReady: (savedChapterId, pendingCount) => {
          setActiveChapterId(savedChapterId, projectId)
          if (activeGenerationTarget.value) activeGenerationTarget.value.chapterId = savedChapterId
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
    if (result.status !== 'completed') throw new Error(`工作流尚未完成：${result.status}`)
    await refreshWorkflowRunDetail(result.run_id)

    // 自动生成标题
    if (!chapterTitle.value) {
      chapterTitle.value = `第${form.chapter_no}章`
    }

    addEvent('保存章节', `章节已写入草稿库`)
    await loadResources()
    await refreshChapterVersions()  // 刷新版本列表
    await loadChapterChangeProposals()
    addEvent('生成完成', 'v3 工作流已完成', 'success')
    const actualWordCount = draft.value.replace(/\s/g, '').length
    const minimumWordCount = Math.ceil(requestedTargetWordCount * 0.9)
    const maximumWordCount = Math.floor(requestedTargetWordCount * 1.1)
    const wordCountInRange = actualWordCount >= minimumWordCount && actualWordCount <= maximumWordCount
    addEvent(
      '字数核对',
      `目标 ${requestedTargetWordCount} 字，允许 ${minimumWordCount}-${maximumWordCount} 字，实际 ${actualWordCount} 字`,
      wordCountInRange ? 'success' : 'error',
    )
    if (showToast) {
      if (wordCountInRange) {
        message.success(`章节已生成，${actualWordCount} 字符合目标范围`)
      } else {
        message.warning(`正文已生成并保存，但实际 ${actualWordCount} 字，超出目标范围 ${minimumWordCount}-${maximumWordCount} 字`)
      }
    }

    const savedChapterId = result.chapter_id ?? chapterId.value
    if (savedChapterId) {
      setActiveChapterId(savedChapterId, projectId)
      if (selectedWorkflow.value === 'quick_write') {
        const savedContent = String(result.session_context.final_content ?? result.session_context.draft_content ?? draft.value)
        startPostGenerationAnalysis(projectId, savedChapterId, savedContent, result.run_id)
      } else {
        generationPhase.value = 'complete'
      }
    }

    // 生成完成后自动切到分析 Tab
    if (analysis.value) {
      activeTab.value = 'analysis'
    }
    // 生成完成后保持面板打开，方便用户查看和重跑
    // showWorkflowPanel.value = false
    return true
  } catch (error) {
    if (currentRunId.value) await refreshWorkflowRunDetail(currentRunId.value)
    if (currentRunId.value && activeGenerationTarget.value) {
      interruptedGenerationTarget.value = {
        ...activeGenerationTarget.value,
        chapterId: chapterId.value ?? activeGenerationTarget.value.chapterId,
      }
    }
    if (!draft.value.trim()) draft.value = previousDraft
    if (currentRunId.value) {
      // 步骤 3：即使规划或分析步骤中断、正文为空，也保留运行 ID 供续跑。
      isInterrupted.value = true
      interruptedRunId.value = currentRunId.value
    }
    analysis.value = previousAnalysis
    if (stopRequested.value) {
      addEvent('生成已暂停', '已保留已完成步骤和中断时的正文片段；继续时会重跑当前步骤', 'info')
      message.info('已中断并保留进度，可随时继续')
    } else {
      addEvent('生成失败', errorMessage(error), 'error')
      message.error(draft.value.trim() ? '生成中断，可点击「继续生成」或从步骤处重跑' : '章节生成失败')
    }
    // showWorkflowPanel.value = false
    return false
  } finally {
    loading.value = false
    workflowAction.value = null
    workflowStreamActive.value = false
    stopRequested.value = false
  }
}

// ---- v3 断点续传 ----
async function resumeGenerateV3() {
  if (loading.value || !interruptedRunId.value) return false
  if (!canResumeInterruptedRun.value) {
    message.warning(`请先切回第 ${interruptedGenerationTarget.value?.chapterNo} 章再继续生成`)
    return false
  }

  const projectId = await ensureProject()
  if (!projectId) return false

  const resumeTarget = interruptedGenerationTarget.value
    ? { ...interruptedGenerationTarget.value }
    : { outlineId: form.outline_id, chapterNo: form.chapter_no, chapterId: chapterId.value }
  workflowAction.value = 'resume'
  loading.value = true
  activeGenerationTarget.value = resumeTarget
  showWorkflowPanel.value = true
  workflowRunDetail.value = null

  addEvent('续传启动', `从 ${currentWorkflowStep.value ?? '中断处'} 继续生成`, 'running')

  try {
    workflowStreamActive.value = true
    stopRequested.value = false
    replacePartialOnNextWriterDelta = Boolean(draft.value.trim())
    replacePartialOnNextWriterPlan = Boolean(writingPlanText.value.trim())
    const result = await workflowResumeStream(
      {
        run_id: interruptedRunId.value,
        chapter_no: resumeTarget.chapterNo,
        outline_id: resumeTarget.outlineId ?? undefined,
      },
      {
        onStepStart: (stepId, label, runId) => {
          if (runId) currentRunId.value = runId
          currentWorkflowStep.value = stepId
          if (stepId === 'writer' && !replacePartialOnNextWriterDelta) draft.value = ''
          applyWorkflowStepStart(stepId)
          addEvent('步骤开始', label, 'running')
        },
        onStepContext: applyWorkflowStepContext,
        onDelta: (stepId, content) => {
          if (stepId === 'writer') {
            generationPhase.value = 'writing'
            if (replacePartialOnNextWriterDelta) {
              draft.value = ''
              replacePartialOnNextWriterDelta = false
            }
            draft.value = appendIndentedChapterText(draft.value, content)
          }
        },
        onPlanDelta: (stepId, content) => {
          if (stepId === 'writer') {
            generationPhase.value = 'planning'
            if (replacePartialOnNextWriterPlan) {
              writingPlanText.value = ''
              replacePartialOnNextWriterPlan = false
            }
            writingPlanText.value += content
          }
        },
        onContentReset: (stepId) => { if (stepId === 'writer') draft.value = '' },
        onStepNotice: (_stepId, notice) => {
          generationPhase.value = 'repairing'
          addEvent('字数纠偏', notice, 'info')
        },
        onStepDone: (stepId, stepResult) => {
          applyWorkflowStepDone(stepId, stepResult)
          const step = workflowSteps.value.find(s => s.id === stepId)
          addEvent('步骤完成', step?.label ?? stepId, 'success')

          if (stepId === 'analyzer' && stepResult) applyWorkflowAnalysisResult(stepResult)

          if (stepId === 'polisher' && stepResult?.content) {
            draft.value = indentChapterParagraphs(String(stepResult.content))
          }
        },
        onWorkflowDone: (status, runId, sessionContext) => {
          applyWorkflowCompletion(status, runId, sessionContext, '续传')
        },
        onChangeProposalsReady: (savedChapterId, pendingCount) => {
          setActiveChapterId(savedChapterId)
          if (activeGenerationTarget.value) activeGenerationTarget.value.chapterId = savedChapterId
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
    if (result.status !== 'completed') throw new Error(`续传尚未完成：${result.status}`)
    await refreshWorkflowRunDetail(result.run_id)

    if (!chapterTitle.value) {
      chapterTitle.value = `第${form.chapter_no}章`
    }

    addEvent('保存章节', `章节已写入草稿库`)
    await loadResources()
    await refreshChapterVersions()
    await loadChapterChangeProposals()
    addEvent('续传成功', '工作流已从中断处完成', 'success')
    message.success('续传完成')

    const resumedChapterId = result.chapter_id ?? chapterId.value
    const resumedContent = String(result.session_context.final_content ?? result.session_context.draft_content ?? draft.value)
    const resumedTemplate = workflowRunDetail.value?.run.template_name ?? selectedWorkflow.value
    if (resumedChapterId && resumedTemplate === 'quick_write') {
      setActiveChapterId(resumedChapterId, projectId)
      startPostGenerationAnalysis(projectId, resumedChapterId, resumedContent, result.run_id)
    }

    if (analysis.value) {
      activeTab.value = 'analysis'
    }
    showWorkflowPanel.value = false
    return true
  } catch (error) {
    if (currentRunId.value) await refreshWorkflowRunDetail(currentRunId.value)
    if (currentRunId.value) {
      isInterrupted.value = true
      interruptedRunId.value = currentRunId.value
    }
    addEvent('续传失败', errorMessage(error), 'error')
    if (stopRequested.value) {
      addEvent('续传已暂停', '已保留已完成步骤和当前草稿，可继续恢复', 'info')
      message.info('续传已中断并保留进度')
    } else {
      message.error(`续传失败：${errorMessage(error)}`)
    }
    showWorkflowPanel.value = false
    return false
  } finally {
    loading.value = false
    workflowAction.value = null
    workflowStreamActive.value = false
    stopRequested.value = false
    replacePartialOnNextWriterDelta = false
    replacePartialOnNextWriterPlan = false
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
  if (interruptedRunId.value && !canResumeInterruptedRun.value) {
    message.warning(`请先切回第 ${interruptedGenerationTarget.value?.chapterNo} 章再重跑步骤`)
    return
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
  const restartTarget = interruptedGenerationTarget.value
    ? { ...interruptedGenerationTarget.value }
    : { outlineId: form.outline_id, chapterNo: form.chapter_no, chapterId: chapterId.value }
  activeGenerationTarget.value = restartTarget
  workflowAction.value = 'restart'
  loading.value = true
  workflowStreamActive.value = true
  stopRequested.value = false
  showWorkflowPanel.value = true
  workflowRunDetail.value = null

  addEvent('重跑步骤', `从 ${stepName} 开始重跑`, 'running')

  try {
    const result = await workflowResumeStream(
      {
        run_id: runId,
        chapter_no: restartTarget.chapterNo,
        outline_id: restartTarget.outlineId ?? undefined,
        restart_from_step_id: stepId,
      },
      {
        onStepStart: (sid, label, resumedRunId) => {
          if (resumedRunId) currentRunId.value = resumedRunId
          currentWorkflowStep.value = sid
          if (sid === 'writer') {
            draft.value = ''
            writingPlanText.value = ''
          }
          applyWorkflowStepStart(sid)
        },
        onStepContext: applyWorkflowStepContext,
        onDelta: (sid, content) => {
          if (sid === 'writer') {
            generationPhase.value = 'writing'
            draft.value = appendIndentedChapterText(draft.value, content)
          }
        },
        onPlanDelta: (sid, content) => {
          if (sid === 'writer') {
            generationPhase.value = 'planning'
            writingPlanText.value += content
          }
        },
        onContentReset: (sid) => { if (sid === 'writer') draft.value = '' },
        onStepNotice: (_sid, notice) => {
          generationPhase.value = 'repairing'
          addEvent('字数纠偏', notice, 'info')
        },
        onStepDone: (sid, stepResult) => {
          applyWorkflowStepDone(sid, stepResult)
          const s = workflowSteps.value.find(x => x.id === sid)
          addEvent('步骤完成', s?.label ?? sid, 'success')

          if (sid === 'analyzer' && stepResult) applyWorkflowAnalysisResult(stepResult)
          if (sid === 'polisher' && stepResult?.content) {
            draft.value = indentChapterParagraphs(String(stepResult.content))
          }
        },
        onWorkflowDone: (status, newRunId, sessionContext) => {
          applyWorkflowCompletion(status, newRunId, sessionContext, '重跑')
        },
        onChangeProposalsReady: (savedChapterId, pendingCount) => {
          setActiveChapterId(savedChapterId)
          if (activeGenerationTarget.value) activeGenerationTarget.value.chapterId = savedChapterId
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
    if (result.status !== 'completed') throw new Error(`重跑尚未完成：${result.status}`)
    await refreshWorkflowRunDetail(result.run_id)
    await loadResources()
    await refreshChapterVersions()
    await loadChapterChangeProposals()
    const restartedChapterId = result.chapter_id ?? chapterId.value
    const restartedContent = String(result.session_context.final_content ?? result.session_context.draft_content ?? draft.value)
    const restartedTemplate = workflowRunDetail.value?.run.template_name ?? selectedWorkflow.value
    const restartProjectId = projectStore.currentProject?.id
    if (restartProjectId && restartedChapterId && restartedTemplate === 'quick_write') {
      setActiveChapterId(restartedChapterId, restartProjectId)
      startPostGenerationAnalysis(restartProjectId, restartedChapterId, restartedContent, result.run_id)
    }
    message.success('重跑完成')
    showWorkflowPanel.value = false
  } catch (error) {
    if (currentRunId.value) await refreshWorkflowRunDetail(currentRunId.value)
    if (currentRunId.value) {
      isInterrupted.value = true
      interruptedRunId.value = currentRunId.value
      if (activeGenerationTarget.value) interruptedGenerationTarget.value = { ...activeGenerationTarget.value }
    }
    addEvent('重跑失败', errorMessage(error), 'error')
    message.error('重跑失败')
    showWorkflowPanel.value = false
  } finally {
    loading.value = false
    workflowAction.value = null
    workflowStreamActive.value = false
    stopRequested.value = false
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
    // 初始化时优先使用项目偏好；没有可用偏好时采用质量均衡流程。
    if (workflowTemplates.value.length > 0) {
      const preferredTemplate = userPrefs.default_template === 'smart_mode' ? 'quick_write' : userPrefs.default_template
      const defaultTemplate = workflowTemplates.value.find(t => t.name === preferredTemplate)
        ?? workflowTemplates.value.find(t => t.name === 'quick_write')
        ?? workflowTemplates.value[0]
      selectedWorkflow.value = defaultTemplate.name
    }
    // 初始化工作流步骤，让流水线始终可见
    workflowSteps.value = buildWorkflowSteps(selectedWorkflow.value)
  } catch (error) {
    console.warn('加载工作流模板失败，使用内置默认值', error)
    // 使用内置默认模板
    workflowTemplates.value = [
      { name: 'quick_write', label: '质量均衡', description: '同一请求先整理可查看的剧情节拍，再写正文；正文保存后独立进行分析沉淀', icon: '✨', category: 'writing', step_count: 1 },
      { name: 'smart_mode', label: '完整流程', description: '规划、正文、分析依次独立调用模型；步骤更明确，但串行等待更久', icon: '🎯', category: 'writing', step_count: 3 },
      { name: 'deep_creation', label: '深度创作', description: '规划、写作、精修、分析依次调用模型，耗时最长', icon: '🎨', category: 'writing', step_count: 4 },
    ]
    workflowSteps.value = buildWorkflowSteps(selectedWorkflow.value)
  }
}

// 加载用户偏好
async function loadPreferences() {
  if (!projectStore.currentProject) return
  prefsLoading.value = true
  try {
    // 写作习惯属于项目；字号属于用户，跨项目复用。
    const [projectPrefs, personalPrefs] = await Promise.all([
      getUserPreferences(projectStore.currentProject.id, true),
      getUserPreferences(projectStore.currentProject.id, false),
    ])
    Object.assign(userPrefs, projectPrefs)
    generationControls.temperature = userPrefs.default_temperature
    generationControls.targetWordCount = userPrefs.default_target_word_count
    if (typeof personalPrefs.editor_font_size === 'number') {
      userPrefs.editor_font_size = personalPrefs.editor_font_size
    }
    const storedVariant = projectPrefs.default_writer_variant
    selectedWriterVariant.value = typeof storedVariant === 'string'
      && writerVariants.some(item => item.id === storedVariant)
      ? storedVariant
      : 'default'
    // 如果偏好中有默认模板，同步到选中状态
    const storedTemplate = projectPrefs.default_template as string | undefined
    const defaultTpl = storedTemplate === 'smart_mode' ? 'quick_write' : storedTemplate
    if (storedTemplate === 'smart_mode') userPrefs.default_template = 'quick_write'
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
    await updateUserPreferences(projectStore.currentProject.id, {
      default_template: userPrefs.default_template,
      default_writer_variant: userPrefs.default_writer_variant,
      default_temperature: userPrefs.default_temperature,
      default_target_word_count: userPrefs.default_target_word_count,
      auto_sync_level: userPrefs.auto_sync_level,
    }, true)
    generationControls.temperature = userPrefs.default_temperature
    generationControls.targetWordCount = userPrefs.default_target_word_count
    selectedWriterVariant.value = userPrefs.default_writer_variant
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
async function refreshChapterVersions() {
  await chapterVersionsPanel.value?.refresh()
}

function handleChapterVersionRestored(payload: { content: string; version: GenerationVersion }) {
  draft.value = indentChapterParagraphs(payload.content)
  markDraftPersisted(payload.content)
  polishOriginal.value = ''
  addEvent('恢复版本', `从 v${payload.version.version_number} 创建了新版本`, 'success')
  void loadResources()
}

async function refreshTrace() {
  await loadAgentLogs()
}

function handleTabChange(tab: string) {
  if (tab === 'versions') void refreshChapterVersions()
  if (tab === 'preferences') void loadPreferences()
  if (tab === 'logs') void refreshTrace()
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
  if (loading.value) return
  const skill = agentSkills.value.find(s => s.id === skillId)
  if (skill) skill.active = !skill.active
  addEvent('技能切换', `${skill?.name}: ${skill?.active ? '启用' : '禁用'}`, 'info')
}

// ---- 保存章节 ----
async function persistChapterDraft(silent = true): Promise<boolean> {
  if (loading.value) return false
  if (draftSaveInFlight) {
    draftSaveQueued = true
    return draftSaveInFlight
  }

  // 空白新细纲不创建空记录；已有章节清空正文时仍允许保存这个修改。
  if (!hasDraftToPersist()) return false
  const projectId = await ensureProject()
  if (!projectId) return false

  const target = {
    chapterId: chapterId.value,
    title: chapterTitle.value.trim() || `第${form.chapter_no}章`,
    content: draft.value,
    chapterNo: form.chapter_no,
    outlineId: form.outline_id,
  }
  const payload = {
    project_id: projectId,
    outline_id: target.outlineId,
    chapter_no: target.chapterNo,
    title: target.title,
    content: target.content,
    status: 'draft',
  }

  draftSaveStatus.value = 'saving'
  draftSaveError.value = ''
  const request = (async () => {
    try {
      const saved = target.chapterId
        ? await updateResource<ChapterItem>('chapters', target.chapterId, payload)
        : await createResource<ChapterItem>('chapters', payload)

      // 步骤 1：更新本地列表；步骤 2：仅在编辑目标未切换时回填当前章节 ID。
      const existingIndex = chapters.value.findIndex((item) => item.id === saved.id)
      if (existingIndex >= 0) chapters.value[existingIndex] = saved
      else chapters.value.unshift(saved)
      const sameEditor = projectStore.currentProject?.id === projectId
        && chapterId.value === target.chapterId
        && form.outline_id === target.outlineId
        && form.chapter_no === target.chapterNo
      if (sameEditor) {
        if (!target.chapterId) setActiveChapterId(saved.id, projectId)
        if (!chapterTitle.value.trim()) chapterTitle.value = target.title
        rememberChapterSelection(projectId, saved.id)
        persistedDraftFingerprint.value = draftFingerprint(
          saved.id,
          target.title,
          target.content,
          target.chapterNo,
          target.outlineId,
        )
        draftSaveStatus.value = draftFingerprint() === persistedDraftFingerprint.value ? 'saved' : 'unsaved'
      }

      if (!silent) {
        addEvent('保存章节', `章节 ID ${saved.id} 已保存`)
        message.success('章节草稿已保存')
      }
      return true
    } catch (error) {
      const sameEditor = projectStore.currentProject?.id === projectId
        && chapterId.value === target.chapterId
        && form.outline_id === target.outlineId
        && form.chapter_no === target.chapterNo
      draftSaveError.value = errorMessage(error) || '章节草稿保存失败'
      if (sameEditor) draftSaveStatus.value = 'error'
      if (!silent) message.error(errorMessage(error) || '章节草稿保存失败')
      return false
    }
  })()

  draftSaveInFlight = request
  try {
    return await request
  } finally {
    if (draftSaveInFlight === request) draftSaveInFlight = null
    if (draftSaveQueued) {
      draftSaveQueued = false
      if (draftFingerprint() !== persistedDraftFingerprint.value && !loading.value) {
        if (draftAutosaveTimer) clearTimeout(draftAutosaveTimer)
        draftAutosaveTimer = setTimeout(() => void persistChapterDraft(true), 0)
      }
    }
  }
}

async function saveEditorPreference() {
  if (!projectStore.currentProject) return
  editorPrefsSaving.value = true
  try {
    await updateUserPreferences(projectStore.currentProject.id, {
      editor_font_size: userPrefs.editor_font_size,
    }, false)
    addEvent('个人设置保存', `编辑器字号已保存为 ${userPrefs.editor_font_size}px`, 'success')
    message.success('个人字号已保存')
  } catch (error) {
    addEvent('个人设置保存失败', errorMessage(error), 'error')
    message.error('个人字号保存失败')
  } finally {
    editorPrefsSaving.value = false
  }
}

async function saveCurrentChapter() {
  if (await persistChapterDraft(false)) await loadResources()
}

function handleEditorSelection(selection: { start: number; end: number; text: string } | null) {
  editorSelection.value = selection
}

function tokenUsageLabel(usage: { input_tokens?: number; output_tokens?: number; total_tokens?: number } | null) {
  if (!usage) return '模型未返回 Token 用量'
  const total = usage.total_tokens ?? ((usage.input_tokens ?? 0) + (usage.output_tokens ?? 0))
  return `本次消耗 ${total.toLocaleString()} Tokens`
}

function chapterDialogueError(error: unknown) {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: unknown } } }).response
    if (typeof response?.data?.detail === 'string') return response.data.detail
  }
  return errorMessage(error)
}

function dialogueSessionTitle(messages: ChapterDialogueMessage[]) {
  const firstUserMessage = messages.find((item) => item.role === 'user')?.content?.trim()
  return firstUserMessage ? firstUserMessage.slice(0, 36) : '新建改稿对话'
}

function activateDialogueSession(session: ChapterEditSession) {
  dialogueSessionId.value = session.session_id
  dialogueSessionRevision.value = session.revision
  dialogueMessages.value = session.state?.messages ?? []
  dialogueCandidate.value = session.state?.candidate ?? null
  dialogueScope.value = session.state?.scope ?? 'chapter'
}

async function loadChapterDialogueSessions() {
  const projectId = projectStore.currentProject?.id
  const targetChapterId = chapterId.value
  if (!projectId || !targetChapterId) {
    // 章节切换经过空值时使旧请求失效，并确保旧请求的 finally 不会留下永久加载态。
    dialogueSessionLoadSequence += 1
    dialogueSessionLoadingKey = null
    dialogueSessionLoading.value = false
    dialogueSessions.value = []
    dialogueSessionId.value = null
    dialogueSessionRevision.value = 0
    dialogueMessages.value = []
    dialogueCandidate.value = null
    dialogueScope.value = 'chapter'
    return
  }

  const loadingKey = `${projectId}:${targetChapterId}`
  // 同一章节的 watcher 可能因初始化和数据恢复连续触发；复用当前请求，避免重复创建空会话。
  if (dialogueSessionLoading.value && dialogueSessionLoadingKey === loadingKey) return

  const sequence = ++dialogueSessionLoadSequence
  dialogueSessionLoadingKey = loadingKey

  dialogueSessionLoading.value = true
  try {
    const sessions = await listChapterEditSessions(projectId, targetChapterId)
    if (sequence !== dialogueSessionLoadSequence || chapterId.value !== targetChapterId) return
    dialogueSessions.value = sessions
    if (sessions.length === 0) {
      const created = await createChapterEditSession(projectId, targetChapterId)
      if (sequence !== dialogueSessionLoadSequence || chapterId.value !== targetChapterId) return
      dialogueSessions.value = [created]
      activateDialogueSession(created)
      return
    }

    const latestSession = await getChapterEditSession(projectId, targetChapterId, sessions[0].session_id)
    if (sequence !== dialogueSessionLoadSequence || chapterId.value !== targetChapterId) return
    activateDialogueSession(latestSession)
  } catch (error) {
    if (sequence === dialogueSessionLoadSequence) {
      dialogueSessionId.value = null
      message.error(`改稿会话读取失败：${chapterDialogueError(error)}`)
    }
  } finally {
    if (sequence === dialogueSessionLoadSequence) {
      dialogueSessionLoading.value = false
      dialogueSessionLoadingKey = null
    }
  }
}

async function saveActiveDialogueSession() {
  const projectId = projectStore.currentProject?.id
  const targetChapterId = chapterId.value
  const sessionId = dialogueSessionId.value
  if (!projectId || !targetChapterId || !sessionId || dialogueSessionLoading.value) return false
  try {
    const saved = await saveChapterEditSession(projectId, targetChapterId, sessionId, {
      revision: dialogueSessionRevision.value,
      title: dialogueSessionTitle(dialogueMessages.value),
      scope: dialogueScope.value,
      messages: dialogueMessages.value,
      candidate: dialogueCandidate.value,
    })
    if (dialogueSessionId.value !== sessionId || chapterId.value !== targetChapterId) return false
    dialogueSessionRevision.value = saved.revision
    dialogueSessions.value = dialogueSessions.value.map((item) => item.session_id === sessionId
      ? { ...item, title: saved.title, revision: saved.revision, updated_at: saved.updated_at }
      : item)
    return true
  } catch (error) {
    message.error(`改稿会话保存失败：${chapterDialogueError(error)}`)
    return false
  }
}

async function changeDialogueScope(scope: 'chapter' | 'selection') {
  dialogueScope.value = scope
  await saveActiveDialogueSession()
}

async function discardDialogueCandidate() {
  dialogueCandidate.value = null
  await saveActiveDialogueSession()
}

async function newChapterDialogueSession() {
  const projectId = projectStore.currentProject?.id
  const targetChapterId = chapterId.value
  if (!projectId || !targetChapterId || dialogueSessionLoading.value) return
  if (!await saveActiveDialogueSession()) return
  const operationKey = `${projectId}:${targetChapterId}`
  dialogueSessionLoadingKey = operationKey
  dialogueSessionLoading.value = true
  try {
    const created = await createChapterEditSession(projectId, targetChapterId)
    if (chapterId.value !== targetChapterId) return
    dialogueSessions.value = [created, ...dialogueSessions.value]
    activateDialogueSession(created)
    editorSelection.value = null
  } catch (error) {
    message.error(`新建改稿会话失败：${chapterDialogueError(error)}`)
  } finally {
    if (dialogueSessionLoadingKey === operationKey) {
      dialogueSessionLoading.value = false
      dialogueSessionLoadingKey = null
    }
  }
}

async function selectChapterDialogueSession(sessionId: string) {
  const projectId = projectStore.currentProject?.id
  const targetChapterId = chapterId.value
  if (!projectId || !targetChapterId || sessionId === dialogueSessionId.value) return
  if (!await saveActiveDialogueSession()) return
  const operationKey = `${projectId}:${targetChapterId}`
  dialogueSessionLoadingKey = operationKey
  dialogueSessionLoading.value = true
  try {
    const session = await getChapterEditSession(projectId, targetChapterId, sessionId)
    if (chapterId.value !== targetChapterId) return
    activateDialogueSession(session)
    editorSelection.value = null
  } catch (error) {
    message.error(`切换改稿会话失败：${chapterDialogueError(error)}`)
  } finally {
    if (dialogueSessionLoadingKey === operationKey) {
      dialogueSessionLoading.value = false
      dialogueSessionLoadingKey = null
    }
  }
}

async function sendChapterDialogue(instruction: string) {
  if (!projectStore.currentProject || !draft.value.trim()) {
    message.warning('请先选择一章有正文的章节')
    return
  }
  if (dialogueBusy.value || dialogueApplying.value || dialogueSessionLoading.value) return
  if (!dialogueSessionId.value) {
    message.warning('改稿会话尚未准备好，请稍后重试')
    return
  }

  const requestedProjectId = projectStore.currentProject.id
  const requestedSessionId = dialogueSessionId.value

  const pendingCandidate = dialogueCandidate.value
  if (pendingCandidate && (pendingCandidate.chapterId !== chapterId.value || pendingCandidate.expectedContent !== draft.value)) {
    message.warning('当前正文已经变化，请先舍弃过期候选，再基于新正文继续对话')
    return
  }
  if (pendingCandidate && dialogueScope.value === 'selection' && pendingCandidate.scope !== 'selection') {
    message.warning('当前候选是整章改稿，请保持“整章”继续调整，或先舍弃候选再选中片段')
    return
  }

  const requestedChapterId = chapterId.value
  const requestedContent = draft.value
  const requestedTitle = chapterTitle.value
  dialogueBusy.value = true
  dialogueBusyStatus.value = '正在整理正文、卷纲/章纲、前情摘要、相关记忆与本会话历史…'
  dialogueAbortController = new AbortController()
  const userMessage: ChapterDialogueMessage = {
    id: `user-${Date.now()}`,
    role: 'user',
    content: instruction,
  }
  dialogueMessages.value.push(userMessage)
  if (!await saveActiveDialogueSession()) {
    dialogueBusy.value = false
    dialogueBusyStatus.value = ''
    dialogueAbortController = null
    return
  }

  try {
    // 步骤 1：先把正在编辑的草稿落库，后端才能将确认后的改稿可靠地绑定到章节。
    if (!await persistChapterDraft(true) || !chapterId.value) {
      throw new Error('章节草稿保存失败，请稍后重试')
    }
    if (
      draft.value !== requestedContent
      || chapterTitle.value !== requestedTitle
      || projectStore.currentProject?.id !== requestedProjectId
      || (requestedChapterId !== null && chapterId.value !== requestedChapterId)
    ) {
      throw new Error('章节已切换或正文有变化，请重新发送本轮要求')
    }
    const targetChapterId = chapterId.value
    const expectedContent = pendingCandidate?.expectedContent ?? draft.value
    const baseContent = pendingCandidate?.proposedContent ?? draft.value
    let selectionStart: number | null = null
    let selectionEnd: number | null = null

    if (dialogueScope.value === 'selection') {
      if (pendingCandidate?.scope === 'selection') {
        selectionStart = pendingCandidate.selectionStart
        selectionEnd = selectionStart === null ? null : selectionStart + pendingCandidate.revisedSegment.length
      } else {
        const currentSelection = editorSelection.value
        if (!currentSelection || draft.value.slice(currentSelection.start, currentSelection.end) !== currentSelection.text) {
          throw new Error('请先在正文中重新选中要修改的文字')
        }
        selectionStart = currentSelection.start
        selectionEnd = currentSelection.end
      }
      if (selectionStart === null || selectionEnd === null || selectionEnd > baseContent.length) {
        throw new Error('所选片段已失效，请重新选择正文')
      }
    }

    const result = await chatChapterEditStream({
      project_id: requestedProjectId,
      chapter_id: targetChapterId,
      chapter_no: form.chapter_no,
      chapter_title: chapterTitle.value,
      outline_id: form.outline_id,
      content: baseContent,
      scope: dialogueScope.value,
      selection_start: selectionStart,
      selection_end: selectionEnd,
      instruction,
      conversation: dialogueMessages.value.slice(-9).map(({ role, content }) => ({ role, content })),
      context_selection: getContextSelectionPayload(),
    }, dialogueAbortController.signal, (event) => {
      dialogueBusyStatus.value = event.type === 'stage'
        ? (event.stage || '正在分析正文与相关设定…')
        : `正在接收模型回复${event.received_characters ? ` · ${event.received_characters} 字` : ''}…`
    })

    if (
      projectStore.currentProject?.id !== requestedProjectId
      || chapterId.value !== targetChapterId
      || dialogueSessionId.value !== requestedSessionId
    ) {
      message.info('已切换到其他章节，本次答复未混入当前对话')
      return
    }

    const assistantMessage: ChapterDialogueMessage = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: result.reply || (result.action === 'proposal' ? '已根据你的要求准备候选稿。' : '我们可以继续讨论这一章。'),
      usageLabel: tokenUsageLabel(result.usage),
    }
    dialogueMessages.value.push(assistantMessage)

    if (result.action === 'proposal') {
      const revisedSegment = result.candidate_text
      const proposedContent = result.scope === 'selection'
        ? `${baseContent.slice(0, selectionStart!)}${revisedSegment}${baseContent.slice(selectionEnd!)}`
        : revisedSegment
      const originalSegment = pendingCandidate?.scope === 'selection' && result.scope === 'selection'
        ? pendingCandidate.originalSegment
        : result.scope === 'selection'
          ? expectedContent.slice(selectionStart!, selectionEnd!)
          : expectedContent
      dialogueCandidate.value = {
        chapterId: targetChapterId,
        scope: result.scope,
        expectedContent,
        proposedContent,
        originalSegment,
        revisedSegment: result.scope === 'selection' ? revisedSegment : proposedContent,
        selectionStart: result.scope === 'selection' ? selectionStart : null,
        instruction,
      }
    }
    await saveActiveDialogueSession()
  } catch (error) {
    const requestStillActive = projectStore.currentProject?.id === requestedProjectId
      && chapterId.value === requestedChapterId
      && dialogueSessionId.value === requestedSessionId
    if (error instanceof DOMException && error.name === 'AbortError') {
      // 切章造成的取消不能写入新章节会话；原会话已先保存用户本轮要求。
      if (requestStillActive) {
        dialogueMessages.value.push({
          id: `assistant-cancelled-${Date.now()}`,
          role: 'assistant',
          content: '本轮对话已中断。你的要求和已有正文已保留，没有生成或应用候选稿。',
        })
        await saveActiveDialogueSession()
      }
      return
    }
    if (!requestStillActive) {
      message.info('章节已切换，本次答复未写入其他章节会话')
      return
    }
    const detail = chapterDialogueError(error) || '对话改稿失败'
    dialogueMessages.value.push({
      id: `assistant-error-${Date.now()}`,
      role: 'assistant',
      content: `这次没有完成：${detail}`,
    })
    await saveActiveDialogueSession()
    message.error(detail)
  } finally {
    dialogueBusy.value = false
    dialogueBusyStatus.value = ''
    dialogueAbortController = null
  }
}

function stopChapterDialogue() {
  if (!dialogueAbortController || !dialogueBusy.value) return
  dialogueBusyStatus.value = '正在关闭本次模型请求…'
  dialogueAbortController.abort()
}

async function applyChapterDialogueCandidate() {
  const candidate = dialogueCandidate.value
  const projectId = projectStore.currentProject?.id
  if (!candidate || !projectId || !chapterId.value) return
  if (!canApplyDialogueCandidate.value) {
    message.warning('正文或章节已经变化，请重新生成候选稿后再应用')
    return
  }

  dialogueApplying.value = true
  try {
    if (!await persistChapterDraft(true)) throw new Error('当前正文保存失败，不能应用候选稿')
    const result = await applyChapterEdit({
      project_id: projectId,
      chapter_id: candidate.chapterId,
      expected_content: candidate.expectedContent,
      revised_content: candidate.proposedContent,
      summary: `对话改稿：${candidate.instruction}`,
    })

    // 步骤 1：后端已同时更新正文与版本；步骤 2：同步编辑区和列表状态。
    draft.value = indentChapterParagraphs(candidate.proposedContent)
    markDraftPersisted(candidate.proposedContent)
    dialogueCandidate.value = null
    dialogueMessages.value.push({
      id: `assistant-applied-${Date.now()}`,
      role: 'assistant',
      content: `候选稿已应用，并保存为 v${result.version_number}。原有版本仍可在“版本”中恢复。`,
    })
    await saveActiveDialogueSession()
    await Promise.all([refreshChapterVersions(), loadResources()])
    message.success(`改稿已应用，保存为 v${result.version_number}`)
  } catch (error) {
    const detail = chapterDialogueError(error) || '应用改稿失败'
    message.error(detail)
    if (
      detail.includes('已发生变化')
      || (typeof error === 'object' && error !== null && 'response' in error
        && (error as { response?: { status?: number } }).response?.status === 409)
    ) dialogueCandidate.value = null
  } finally {
    dialogueApplying.value = false
  }
}

// ---- 分析章节 ----
async function analyze(options: { showToast?: boolean } = {}) {
  const { showToast = true } = options
  if (backgroundAnalysisStatus.value === 'running' && backgroundAnalysisChapterId.value === chapterId.value) {
    message.info('本章分析沉淀正在后台进行')
    return false
  }
  if (!chapterId.value || !projectStore.currentProject) {
    message.warning('请先生成或保存章节后再分析')
    return false
  }
  // 步骤 1：先落库当前正文，避免摘要和提案关联到尚未保存的编辑内容。
  if (draftFingerprint() !== persistedDraftFingerprint.value && !await persistChapterDraft(false)) {
    message.error('章节草稿未能保存，当前分析已取消')
    return false
  }
  const analyzedContent = draft.value
  addEvent('分析启动', `章节 ID ${chapterId.value} 正在沉淀摘要`, 'running')
  activeTab.value = 'analysis'
  try {
    const result = await analyzeChapter({
      project_id: projectStore.currentProject.id,
      chapter_id: chapterId.value,
      content: analyzedContent,
    })
    analysis.value = result.analysis
    analysisStatus.value = String(result.analysis_status || 'completed')
    setAnalysisSections(result)
    if (result.analysis_status !== 'unavailable') {
      analysisContentSnapshot.value = analyzedContent
      analysisPersistedStale.value = false
    }
    if (result.analysis_status === 'unavailable') {
      analysisContentSnapshot.value = null
      analysisPersistedStale.value = null
      await loadAgentLogs()
      addEvent('分析不可用', result.analysis, 'error')
      message.warning('模型暂不可用；章节正文已保留，请检查 API 配置后重试')
      return false
    }
    await loadAgentLogs()
    await Promise.all([refreshChapterVersions(), loadResources()])
    await loadChapterChangeProposals()
    addEvent('分析完成', '摘要、人物变化、伏笔线索已生成')
    if (showToast) message.success('章节分析已完成')
    return true
  } catch (error) {
    addEvent('分析失败', errorMessage(error), 'error')
    message.error(errorMessage(error) || '章节分析失败')
    return false
  }
}

/** 正文保存后单独启动分析；不等待分析结果就结束正文生成流程。 */
function startPostGenerationAnalysis(
  projectId: number,
  savedChapterId: number,
  content: string,
  runId: string,
) {
  if (!content.trim()) return
  backgroundAnalysisChapterId.value = savedChapterId
  backgroundAnalysisStatus.value = 'running'
  generationPhase.value = 'analysis'
  addEvent('后台分析启动', '正文已保存；摘要、设定变化与伏笔沉淀将在后台执行', 'running')

  void (async () => {
    try {
      const result = await analyzeChapter({
        project_id: projectId,
        chapter_id: savedChapterId,
        content,
        run_id: runId,
      })
      if (currentRunId.value === runId) await refreshWorkflowRunDetail(runId)
      const isCurrentChapter = chapterId.value === savedChapterId
      if (isCurrentChapter) {
        analysis.value = result.analysis
        analysisStatus.value = String(result.analysis_status || 'completed')
        setAnalysisSections(result)
        if (result.analysis_status !== 'unavailable') {
          analysisContentSnapshot.value = content
          analysisPersistedStale.value = draft.value === content ? false : true
        } else {
          analysisContentSnapshot.value = null
          analysisPersistedStale.value = null
        }
        await Promise.all([refreshChapterVersions(), loadChapterChangeProposals()])
      }
      await loadAgentLogs()
      const currentRun = currentRunId.value === runId
      if (currentRun) {
        backgroundAnalysisStatus.value = result.analysis_status === 'unavailable' ? 'failed' : 'completed'
        generationPhase.value = result.analysis_status === 'unavailable' ? 'analysis_failed' : 'complete'
        addEvent(
          result.analysis_status === 'unavailable' ? '后台分析不可用' : '后台分析完成',
          result.analysis_status === 'unavailable' ? result.analysis : '章节摘要和可审核变化已沉淀',
          result.analysis_status === 'unavailable' ? 'error' : 'success',
        )
      }
      if (isCurrentChapter) await loadResources()
    } catch (error) {
      if (currentRunId.value === runId) {
        backgroundAnalysisStatus.value = 'failed'
        generationPhase.value = 'analysis_failed'
        addEvent('后台分析失败', errorMessage(error), 'error')
      }
    }
  })()
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
    draft.value = indentChapterParagraphs(result.content)
    await Promise.all([refreshChapterVersions(), loadResources()])
    addEvent('精修完成', `已保存为 v${result.version_number}，变化段落已高亮`)
    message.success(`精修稿已保存为 v${result.version_number}`)
  } catch (error) {
    addEvent('精修失败', errorMessage(error), 'error')
    message.error('章节精修失败')
  }
}

// ---- 删除章节 ----
async function removeChapter(id: number) {
  await deleteResource('chapters', id)
  if (chapterId.value === id) {
    setActiveChapterId(null)
    draft.value = ''
    chapterTitle.value = ''
    persistedDraftFingerprint.value = draftFingerprint()
    draftSaveStatus.value = 'unsaved'
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

// 步骤 1：正文、标题和章节归属变化后标记未保存；步骤 2：停止输入一小段时间后写回章节草稿。
watch(
  () => [chapterId.value, chapterTitle.value, draft.value, form.chapter_no, form.outline_id, loading.value],
  () => {
    if (draftFingerprint() === persistedDraftFingerprint.value) {
      if (draftSaveStatus.value !== 'error') draftSaveStatus.value = 'saved'
      return
    }
    if (!hasDraftToPersist()) {
      markDraftPersisted()
      return
    }
    draftSaveStatus.value = 'unsaved'
    if (draftAutosaveTimer) clearTimeout(draftAutosaveTimer)
    if (loading.value) return
    draftAutosaveTimer = setTimeout(() => {
      void persistChapterDraft(true)
    }, 800)
  },
  { flush: 'post' },
)

// 离开页面时尽量提交还没到防抖时间的修改，服务端仍是正文的正式存储位置。
onMounted(() => {
  workflowClockTimer = setInterval(() => { workflowClock.value = Date.now() }, 1000)
})

onBeforeUnmount(() => {
  if (workflowClockTimer) clearInterval(workflowClockTimer)
  if (draftAutosaveTimer) clearTimeout(draftAutosaveTimer)
  if (draftFingerprint() !== persistedDraftFingerprint.value && hasDraftToPersist() && !loading.value) {
    void persistChapterDraft(true)
  }
})

// 步骤 1：章节目标或勾选资料改变后，延迟刷新后端实际上下文预览。
let contextPreviewRefreshTimer: ReturnType<typeof setTimeout> | undefined
watch(
  () => [
    form.chapter_no,
    form.outline_id,
    form.instruction,
    selectedCharacterIds.value.join(','),
    selectedOrganizationIds.value.join(','),
    selectedWorldIds.value.join(','),
    selectedForeshadowingIds.value.join(','),
  ],
  () => {
    if (contextPreviewRefreshTimer) clearTimeout(contextPreviewRefreshTimer)
    contextPreviewRefreshTimer = setTimeout(() => {
      void refreshContextPreview({ silent: true })
    }, 250)
  },
)

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

// 项目或章节切换时恢复各自独立的对话，避免刷新后丢失候选稿。
watch(
  () => `${projectStore.currentProject?.id ?? ''}:${chapterId.value ?? ''}`,
  () => {
    // 离开当前章节时停止其改稿请求，避免浪费调用并隔离迟到答复。
    if (dialogueBusy.value) dialogueAbortController?.abort()
    editorSelection.value = null
    void loadChapterDialogueSessions()
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
  justify-content: flex-start;
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

.pipeline-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 42px;
  padding: 7px 11px;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: var(--bg-card);
  color: var(--text-secondary);
  text-align: left;
}
.pipeline-summary:hover { border-color: rgba(99, 102, 241, .45); }
.pipeline-summary-main {
  min-width: 0;
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0;
  border: 0;
  color: inherit;
  background: transparent;
  text-align: left;
  cursor: pointer;
}
.pipeline-summary-title { color: var(--text-primary); font-size: 12px; font-weight: 700; white-space: nowrap; }
.pipeline-summary-step { display: inline-flex; align-items: center; gap: 5px; padding: 4px 7px; border-radius: 12px; background: rgba(255,255,255,.035); font-size: 11px; white-space: nowrap; }
.pipeline-summary-step i { width: 7px; height: 7px; border-radius: 50%; background: #64748b; }
.pipeline-summary-step.running i { background: #38bdf8; box-shadow: 0 0 7px #38bdf8; }
.pipeline-summary-step.completed i { background: #34d399; }
.pipeline-summary-step.failed i { background: #f87171; }
.pipeline-summary-usage { color: #8f83ff; font-size: 11px; white-space: nowrap; }
.pipeline-phase { padding: 3px 8px; border-radius: 999px; color: var(--n-primary-color, #a8a0ff); background: color-mix(in srgb, var(--n-primary-color, #7c72ff) 12%, transparent); font-size: 11px; white-space: nowrap; }
.pipeline-summary-toggle { margin-left: auto; color: #91a0b6; font-size: 11px; white-space: nowrap; }
.pipeline-summary-details { flex-shrink: 0; padding: 5px 9px; border: 1px solid rgba(113, 104, 245, .35); border-radius: 7px; color: #b8b0ff; background: rgba(113, 104, 245, .1); font-size: 11px; cursor: pointer; }
.pipeline-summary-details:hover { background: rgba(113, 104, 245, .2); }
.integrated-plan-panel {
  margin-top: 8px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-left: 3px solid var(--n-primary-color, #7c72ff);
  border-radius: 9px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
}
.integrated-plan-heading { display: flex; justify-content: space-between; gap: 12px; margin-bottom: 7px; }
.integrated-plan-heading strong { color: var(--text-primary); font-size: 12px; }
.integrated-plan-heading span { color: var(--text-muted); font-size: 11px; }
.integrated-plan-panel pre { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; font: inherit; font-size: 12px; line-height: 1.65; }

.workbench {
  flex: 1;
  display: grid;
  grid-template-columns: 280px 1fr 360px;
  gap: 14px;
  min-height: 600px;
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
  overflow-x: auto;
  scrollbar-width: none;
}
.side-tabs :deep(.n-tabs-nav)::-webkit-scrollbar { display: none; }

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
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(112px, 0.75fr);
  align-items: end;
  gap: 12px;
}

.chapter-target-row :deep(.n-form-item) {
  min-width: 0;
  margin-bottom: 0;
}

.chapter-target-row :deep(.n-form-item-blank),
.chapter-target-row :deep(.n-form-item-blank > *) {
  width: 100%;
  min-width: 0;
}

.rhythm-field :deep(.n-select) {
  width: 100%;
}

.generation-target-field {
  flex: 1;
  min-width: 0;
}

.generation-target-card {
  width: 100%;
  min-height: 42px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  padding: 8px 10px;
  border: 1px solid rgba(99, 102, 241, 0.35);
  border-radius: 8px;
  background: rgba(99, 102, 241, 0.08);
  box-sizing: border-box;
}

.generation-target-card strong {
  display: -webkit-box;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 600;
  line-height: 1.45;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.generation-target-card small {
  color: var(--text-muted);
  font-size: 10px;
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.generation-target-card.unavailable {
  border-color: rgba(245, 158, 11, 0.3);
  background: rgba(245, 158, 11, 0.06);
}

.foreshadow-field :deep(.n-form-item-blank) {
  display: block;
  min-width: 0;
}

.foreshadow-control {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  min-width: 0;
}

.foreshadow-select {
  width: 100%;
  min-width: 0;
}

.selected-foreshadowings {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 0;
}

.selected-foreshadowing-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  max-width: 100%;
  min-width: 0;
  padding: 4px 8px;
  border: 1px solid rgba(99, 102, 241, 0.28);
  border-radius: 7px;
  background: rgba(99, 102, 241, 0.1);
  color: #c7d2fe;
  font: inherit;
  font-size: 11px;
  line-height: 1.4;
  cursor: pointer;
}

.selected-foreshadowing-chip > span:first-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.selected-foreshadowing-chip:hover {
  border-color: rgba(129, 140, 248, 0.65);
  background: rgba(99, 102, 241, 0.18);
}

.chip-remove {
  flex: 0 0 auto;
  color: #9ca3af;
  font-size: 14px;
}

.selected-foreshadowing-chip:hover .chip-remove {
  color: #fff;
}

/* 生成按钮组 */
.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.interrupted-target-hint {
  padding: 9px 11px;
  border: 1px solid var(--border);
  border-radius: 7px;
  color: var(--text-secondary);
  background: var(--bg-card);
  font-size: 12px;
  line-height: 1.5;
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
.resolved-context-card {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 10px;
  background: rgba(59, 130, 246, 0.05);
}

.resolved-context-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.resolved-context-header .stats-title { margin-bottom: 8px; }

.resolved-context-groups {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.resolved-context-required {
  padding: 10px;
  border: 1px solid rgba(52, 211, 153, 0.22);
  border-radius: 8px;
  background: rgba(16, 185, 129, 0.05);
}

.resolved-context-section-title {
  margin-bottom: 6px;
  color: var(--text-primary);
  font-size: 11px;
  font-weight: 700;
}

.resolved-context-required-item + .resolved-context-required-item,
.resolved-context-memory + .resolved-context-memory {
  margin-top: 8px;
}

.resolved-context-required-item strong,
.resolved-context-memory strong {
  color: var(--text-primary);
  font-size: 11px;
}

.resolved-context-required-item p,
.resolved-context-memory p {
  margin: 3px 0 0;
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.system-context-group {
  align-items: flex-start;
}

.resolved-context-memory {
  flex: 1 1 100%;
  padding: 7px 8px;
  border-radius: 6px;
  background: rgba(148, 163, 184, 0.06);
}

.resolved-context-group {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.resolved-context-label {
  min-width: 48px;
  color: var(--text-secondary);
  font-size: 11px;
}

.resolved-context-empty,
.resolved-context-footnote {
  color: var(--text-secondary);
  font-size: 11px;
}

.resolved-context-footnote {
  padding-top: 6px;
  border-top: 1px solid rgba(148, 163, 184, 0.12);
}

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

/* 页面保留自己的运行轨迹空状态与提案编辑弹窗样式。 */
.proposal-edit-hint {
  margin: 0 0 10px;
  color: var(--n-text-color-2, #9ca3af);
  font-size: 12px;
  line-height: 1.5;
}

/* ===== 运行轨迹 ===== */
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
  color: var(--text-primary);
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid var(--border);
}

.workflow-progress-block .block-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.workflow-panel-actions { display: flex; align-items: center; gap: 8px; }

.progress-percent {
  font-size: 14px;
  font-weight: 600;
  color: var(--n-primary-color, #6366f1);
}

.workflow-run-metrics {
  margin-top: 16px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: rgba(9, 15, 27, 0.38);
}

.workflow-metrics-heading,
.workflow-step-usage-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.workflow-metrics-heading {
  margin-bottom: 10px;
  color: var(--n-text-color, #333);
}

.workflow-metrics-heading span,
.workflow-step-usage-row span:last-child,
.workflow-usage-note {
  color: var(--n-text-color-3, #7b8494);
  font-size: 12px;
}

.workflow-metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.workflow-metrics-grid > div {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  padding: 8px;
  border-radius: 8px;
  background: rgba(99, 102, 241, 0.12);
}

.workflow-metrics-grid strong {
  overflow: hidden;
  color: var(--n-primary-color, #6366f1);
  font-size: 15px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workflow-metrics-grid span {
  color: var(--n-text-color-3, #7b8494);
  font-size: 11px;
}

.workflow-step-usage {
  display: grid;
  gap: 6px;
  margin-top: 10px;
}

.workflow-step-usage-row {
  font-size: 12px;
  align-items: flex-start;
}

.workflow-step-main {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.workflow-step-main > span {
  color: var(--n-text-color, #333);
}

.workflow-step-main small {
  overflow-wrap: anywhere;
  color: var(--n-text-color-3, #7b8494);
  font-size: 11px;
  line-height: 1.45;
}

.workflow-usage-note {
  margin: 8px 0 0;
  line-height: 1.5;
}

.generation-controls-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.background-analysis-status {
  margin-top: 12px;
  padding: 9px 11px;
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 12px;
}
.background-analysis-status.running { border-color: rgba(56, 189, 248, .35); color: var(--n-info-color, #38bdf8); }
.background-analysis-status.completed { border-color: rgba(52, 211, 153, .35); color: var(--n-success-color, #34d399); }
.background-analysis-status.failed { border-color: rgba(248, 113, 113, .35); color: var(--n-error-color, #f87171); }

.resolved-context-updated {
  display: block;
  margin-top: 2px;
  color: var(--text-tertiary);
  font-size: 10px;
}

.generation-controls {
  padding: 12px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.055), rgba(255, 255, 255, 0.018));
}

.generation-controls-grid :deep(.n-form-item) {
  min-width: 0;
  margin-bottom: 0;
}

.generation-controls-grid :deep(.n-form-item-blank) {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 5px;
  min-width: 0;
}

.generation-controls-grid :deep(.n-slider),
.generation-controls-grid :deep(.n-input-number) {
  width: 100%;
}

.generation-controls-grid small {
  display: block;
  margin: 0;
  color: var(--n-text-color-3, #7b8494);
  font-size: 11px;
  line-height: 1.45;
}

.selected-foreshadowings {
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 8px;
  border: 1px solid rgba(99, 102, 241, 0.16);
  border-radius: 8px;
  background: rgba(15, 22, 41, 0.38);
}

.selected-foreshadowings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 10px;
}

.selected-foreshadowings-header > span:first-child {
  color: #c7d2fe;
  font-weight: 600;
}

.selected-foreshadowing-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 0;
}

/* ===== 响应式 ===== */
@media (max-width: 1400px) {
  .workbench {
    grid-template-columns: 240px 1fr 320px;
  }
}

@media (max-width: 760px) {
  .page-header {
    align-items: flex-start;
    gap: 12px;
  }

  .header-right {
    gap: 8px;
  }

  .header-stats {
    gap: 8px;
    padding: 6px 9px;
  }

  .header-stats .stat {
    min-width: 42px;
  }

  .form-row {
    grid-template-columns: minmax(0, 1fr);
    gap: 4px;
  }

  .generation-controls-grid,
  .workflow-metrics-grid {
    grid-template-columns: 1fr;
  }

}
</style>
