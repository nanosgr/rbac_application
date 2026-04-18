import { apiClient } from './client';
import {
  User,
  Role,
  Permission,
  CreateUserDTO,
  UpdateUserDTO,
  CreateRoleDTO,
  UpdateRoleDTO,
  CreatePermissionDTO,
  UpdatePermissionDTO,
} from '@/types';

// User Service
export const userService = {
  getAll: () => apiClient.get<User[]>('/users/'),
  getById: (id: number) => apiClient.get<User>(`/users/${id}`),
  getMe: () => apiClient.get<User>('/users/me'),
  create: (data: CreateUserDTO) => apiClient.post<User>('/users/', data),
  update: (id: number, data: UpdateUserDTO) => apiClient.put<User>(`/users/${id}`, data),
  delete: (id: number) => apiClient.delete<void>(`/users/${id}`),
  assignRoles: (id: number, roleIds: number[]) =>
    apiClient.post<User>(`/users/${id}/roles`, { user_id: id, role_ids: roleIds }),
};

// Role Service
export const roleService = {
  getAll: () => apiClient.get<Role[]>('/roles/'),
  getById: (id: number) => apiClient.get<Role>(`/roles/${id}`),
  create: (data: CreateRoleDTO) => apiClient.post<Role>('/roles/', data),
  update: (id: number, data: UpdateRoleDTO) => apiClient.put<Role>(`/roles/${id}`, data),
  delete: (id: number) => apiClient.delete<void>(`/roles/${id}`),
  assignPermissions: (id: number, permissionIds: number[]) =>
    apiClient.post<Role>(`/roles/${id}/permissions`, { role_id: id, permission_ids: permissionIds }),
};

// Permission Service
export const permissionService = {
  getAll: () => apiClient.get<Permission[]>('/permissions/'),
  getById: (id: number) => apiClient.get<Permission>(`/permissions/${id}`),
  create: (data: CreatePermissionDTO) => apiClient.post<Permission>('/permissions/', data),
  update: (id: number, data: UpdatePermissionDTO) =>
    apiClient.put<Permission>(`/permissions/${id}`, data),
  delete: (id: number) => apiClient.delete<void>(`/permissions/${id}`),
};
