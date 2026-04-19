import { apiClient } from './client';
import {
  User,
  Role,
  Permission,
  PaginatedResponse,
  CreateUserDTO,
  UpdateUserDTO,
  UpdateProfileDTO,
  ChangePasswordDTO,
  CreateRoleDTO,
  UpdateRoleDTO,
  CreatePermissionDTO,
  UpdatePermissionDTO,
  GetUsersParams,
  GetRolesParams,
  GetPermissionsParams,
} from '@/types';

function buildQuery(params: Record<string, string | number | boolean | undefined>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '' && value !== null) {
      query.set(key, String(value));
    }
  }
  const str = query.toString();
  return str ? `?${str}` : '';
}

// User Service
export const userService = {
  getAll: (params: GetUsersParams = {}) =>
    apiClient.get<PaginatedResponse<User>>(`/users/${buildQuery(params as Record<string, string | number | boolean | undefined>)}`),

  getById: (id: number) =>
    apiClient.get<User>(`/users/${id}`),

  getMe: () =>
    apiClient.get<User>('/users/me'),

  create: (data: CreateUserDTO) =>
    apiClient.post<User>('/users/', data),

  update: (id: number, data: UpdateUserDTO) =>
    apiClient.put<User>(`/users/${id}`, data),

  updateMe: (data: UpdateProfileDTO) =>
    apiClient.put<User>('/users/me', data),

  changePassword: (data: ChangePasswordDTO) =>
    apiClient.put<{ message: string }>('/users/me/password', data),

  delete: (id: number) =>
    apiClient.delete<void>(`/users/${id}`),

  assignRoles: (id: number, roleIds: number[]) =>
    apiClient.post<User>(`/users/${id}/roles`, { user_id: id, role_ids: roleIds }),
};

// Role Service
export const roleService = {
  getAll: (params: GetRolesParams = {}) =>
    apiClient.get<PaginatedResponse<Role>>(`/roles/${buildQuery(params as Record<string, string | number | boolean | undefined>)}`),

  getById: (id: number) =>
    apiClient.get<Role>(`/roles/${id}`),

  create: (data: CreateRoleDTO) =>
    apiClient.post<Role>('/roles/', data),

  update: (id: number, data: UpdateRoleDTO) =>
    apiClient.put<Role>(`/roles/${id}`, data),

  delete: (id: number) =>
    apiClient.delete<void>(`/roles/${id}`),

  assignPermissions: (id: number, permissionIds: number[]) =>
    apiClient.post<Role>(`/roles/${id}/permissions`, { role_id: id, permission_ids: permissionIds }),
};

// Permission Service
export const permissionService = {
  getAll: (params: GetPermissionsParams = {}) =>
    apiClient.get<PaginatedResponse<Permission>>(`/permissions/${buildQuery(params as Record<string, string | number | boolean | undefined>)}`),

  getById: (id: number) =>
    apiClient.get<Permission>(`/permissions/${id}`),

  create: (data: CreatePermissionDTO) =>
    apiClient.post<Permission>('/permissions/', data),

  update: (id: number, data: UpdatePermissionDTO) =>
    apiClient.put<Permission>(`/permissions/${id}`, data),

  delete: (id: number) =>
    apiClient.delete<void>(`/permissions/${id}`),

  getAvailableResources: () =>
    apiClient.get<{ resources: string[] }>('/permissions/resources/available'),

  getAvailableActions: () =>
    apiClient.get<{ actions: string[] }>('/permissions/actions/available'),
};
