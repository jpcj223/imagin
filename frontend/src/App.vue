<template>
  <n-config-provider :theme="darkTheme" :locale="zhCN" :date-locale="dateZhCN">
    <n-dialog-provider>
      <n-message-provider>
        <MainLayout/>
      </n-message-provider>
    </n-dialog-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import {darkTheme, dateZhCN, zhCN} from 'naive-ui'
import MainLayout from '@/layouts/MainLayout.vue'
</script>
