/**
 * 核心库 API：菜单、字典、用户、系统配置
 */
import { apiClient } from './client'

// ==================== 菜单 ====================

export interface MenuItem {
  id: number
  parent_id: number
  name: string
  path: string
  icon: string
  component: string
  sort_order: number
  menu_type: 'menu' | 'dir' | 'button'
  permission: string
  is_visible: number
  created_at: string
  updated_at: string
  children?: MenuItem[]
}

/** 获取菜单树 */
export function fetchMenuTree(): Promise<MenuItem[]> {
  return apiClient.get('/core/menus').then((res) => res.data)
}

/** 新增菜单 */
export function createMenu(payload: Partial<MenuItem>): Promise<MenuItem> {
  return apiClient.post('/core/menus', payload).then((res) => res.data)
}

/** 更新菜单 */
export function updateMenu(id: number, payload: Partial<MenuItem>): Promise<MenuItem> {
  return apiClient.put(`/core/menus/${id}`, payload).then((res) => res.data)
}

/** 删除菜单 */
export function deleteMenu(id: number): Promise<{ success: boolean }> {
  return apiClient.delete(`/core/menus/${id}`).then((res) => res.data)
}

// ==================== 字典 ====================

export interface Dictionary {
  id: number
  dict_code: string
  dict_name: string
  description: string
  sort_order: number
  status: string
  created_at: string
  updated_at: string
}

export interface DictItem {
  id: number
  dict_id: number
  item_label: string
  item_value: string
  sort_order: number
  status: string
  remark: string
  created_at: string
}

/** 获取字典列表 */
export function fetchDictionaries(): Promise<Dictionary[]> {
  return apiClient.get('/core/dictionaries').then((res) => res.data)
}

/** 获取某个字典的所有项 */
export function fetchDictItems(dictCode: string): Promise<DictItem[]> {
  return apiClient.get(`/core/dictionaries/${dictCode}/items`).then((res) => res.data)
}

/** 新增字典 */
export function createDictionary(payload: Partial<Dictionary>): Promise<Dictionary> {
  return apiClient.post('/core/dictionaries', payload).then((res) => res.data)
}

/** 更新字典 */
export function updateDictionary(id: number, payload: Partial<Dictionary>): Promise<Dictionary> {
  return apiClient.put(`/core/dictionaries/${id}`, payload).then((res) => res.data)
}

/** 删除字典 */
export function deleteDictionary(id: number): Promise<{ success: boolean }> {
  return apiClient.delete(`/core/dictionaries/${id}`).then((res) => res.data)
}

/** 新增字典项 */
export function createDictItem(dictId: number, payload: Partial<DictItem>): Promise<DictItem> {
  return apiClient.post(`/core/dictionaries/${dictId}/items`, payload).then((res) => res.data)
}

/** 更新字典项 */
export function updateDictItem(itemId: number, payload: Partial<DictItem>): Promise<DictItem> {
  return apiClient.put(`/core/dictionaries/dict-items/${itemId}`, payload).then((res) => res.data)
}

/** 删除字典项 */
export function deleteDictItem(itemId: number): Promise<{ success: boolean }> {
  return apiClient.delete(`/core/dictionaries/dict-items/${itemId}`).then((res) => res.data)
}

// ==================== 用户 ====================

export interface SysUser {
  id: number
  username: string
  nickname: string
  email: string
  avatar: string
  role: string
  status: string
  created_at: string
  updated_at: string
}

/** 获取用户列表 */
export function fetchUsers(): Promise<SysUser[]> {
  return apiClient.get('/core/users').then((res) => res.data)
}

/** 新增用户 */
export function createUser(payload: {
  username: string
  password: string
  nickname?: string
  email?: string
  role?: string
  status?: string
}): Promise<SysUser> {
  return apiClient.post('/core/users', payload).then((res) => res.data)
}

/** 更新用户 */
export function updateUser(id: number, payload: Partial<SysUser> & { password?: string }): Promise<SysUser> {
  return apiClient.put(`/core/users/${id}`, payload).then((res) => res.data)
}

/** 删除用户 */
export function deleteUser(id: number): Promise<{ success: boolean }> {
  return apiClient.delete(`/core/users/${id}`).then((res) => res.data)
}

// ==================== 系统配置 ====================

export interface SysConfig {
  id: number
  config_key: string
  config_value: string
  config_name: string
  description: string
  created_at: string
  updated_at: string
}

/** 获取所有系统配置 */
export function fetchConfigs(): Promise<SysConfig[]> {
  return apiClient.get('/core/configs').then((res) => res.data)
}

/** 获取单个配置 */
export function fetchConfig(key: string): Promise<SysConfig> {
  return apiClient.get(`/core/configs/${key}`).then((res) => res.data)
}

/** 更新配置 */
export function updateConfig(key: string, payload: Partial<SysConfig>): Promise<SysConfig> {
  return apiClient.put(`/core/configs/${key}`, payload).then((res) => res.data)
}
