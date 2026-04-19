'use client';

import { useEffect, useState, useMemo, useCallback } from 'react';
import { useToast } from '@/context/ToastContext';
import { useConfirm } from '@/lib/hooks/useConfirm';
import { usePagination } from '@/lib/hooks/usePagination';
import { userService, roleService } from '@/lib/api/services';
import DashboardLayout from '@/components/layout/DashboardLayout';
import Card from '@/components/common/Card';
import Table from '@/components/common/Table';
import Modal from '@/components/common/Modal';
import Input from '@/components/common/Input';
import Button from '@/components/common/Button';
import ProtectedComponent from '@/components/common/ProtectedComponent';
import SearchBar from '@/components/common/SearchBar';
import FilterSelect from '@/components/common/FilterSelect';
import Pagination from '@/components/common/Pagination';
import { User, Role, CreateUserDTO, UpdateUserDTO, TableColumn, TableAction } from '@/types';
import { UserPlus, Pencil, Trash2 } from 'lucide-react';

export default function UsersPage() {
  const { success, error: showError } = useToast();
  const { confirm, ConfirmationDialog } = useConfirm();
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [formData, setFormData] = useState<CreateUserDTO>({
    username: '',
    email: '',
    password: '',
    full_name: '',
    is_active: true,
    role_ids: [],
  });
  const [formError, setFormError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [usersRes, rolesRes] = await Promise.all([
        userService.getAll({ size: 500 }),
        roleService.getAll({ size: 100 }),
      ]);
      setUsers(usersRes.items);
      setRoles(rolesRes.items);
    } catch {
      showError('Error al cargar los datos');
    } finally {
      setIsLoading(false);
    }
  }, [showError]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreate = () => {
    setEditingUser(null);
    setFormData({ username: '', email: '', password: '', full_name: '', is_active: true, role_ids: [] });
    setFormError('');
    setIsModalOpen(true);
  };

  const handleEdit = (user: User) => {
    setEditingUser(user);
    setFormData({
      username: user.username,
      email: user.email,
      password: '',
      full_name: user.full_name,
      is_active: user.is_active,
      role_ids: (user.roles ?? []).map((r) => r.id),
    });
    setFormError('');
    setIsModalOpen(true);
  };

  const handleDelete = async (user: User) => {
    const confirmed = await confirm({
      title: 'Eliminar Usuario',
      message: `¿Está seguro de eliminar al usuario "${user.username}"? Esta acción no se puede deshacer.`,
      confirmText: 'Eliminar',
      cancelText: 'Cancelar',
      variant: 'danger',
    });
    if (!confirmed) return;
    try {
      await userService.delete(user.id);
      success(`Usuario "${user.username}" eliminado`);
      await loadData();
    } catch {
      showError('Error al eliminar el usuario');
    }
  };

  const handleSubmit = async () => {
    setFormError('');
    setIsSubmitting(true);
    try {
      if (editingUser) {
        const updateData: UpdateUserDTO = {
          email: formData.email,
          full_name: formData.full_name,
          is_active: formData.is_active,
        };
        if (formData.password) updateData.password = formData.password;
        await userService.update(editingUser.id, updateData);
        await userService.assignRoles(editingUser.id, formData.role_ids ?? []);
        success('Usuario actualizado');
      } else {
        const { role_ids, ...createPayload } = formData;
        const newUser = await userService.create(createPayload);
        if (role_ids && role_ids.length > 0) {
          await userService.assignRoles(newUser.id, role_ids);
        }
        success('Usuario creado');
      }
      setIsModalOpen(false);
      await loadData();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Error al guardar el usuario');
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredUsers = useMemo(() => {
    return users.filter((user) => {
      const matchesSearch =
        searchQuery === '' ||
        user.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
        user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
        user.full_name.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus =
        statusFilter === 'all' ||
        (statusFilter === 'active' && user.is_active) ||
        (statusFilter === 'inactive' && !user.is_active);
      return matchesSearch && matchesStatus;
    });
  }, [users, searchQuery, statusFilter]);

  const {
    currentPage, totalPages, currentData: paginatedUsers,
    itemsPerPage, startIndex, endIndex,
    goToPage, nextPage, previousPage, goToFirstPage, goToLastPage, setItemsPerPage,
  } = usePagination({ data: filteredUsers, itemsPerPage: 10 });

  const columns: TableColumn<User>[] = [
    {
      key: 'username',
      label: 'Usuario',
      render: (user) => (
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white font-semibold text-sm">
            {user.username[0].toUpperCase()}
          </div>
          <div>
            <p className="font-medium text-gray-900">{user.username}</p>
            <p className="text-xs text-gray-500">{user.email}</p>
          </div>
        </div>
      ),
    },
    { key: 'full_name', label: 'Nombre Completo' },
    {
      key: 'roles',
      label: 'Roles',
      render: (user) => (
        <div className="flex flex-wrap gap-1">
          {(user.roles ?? []).length === 0 ? (
            <span className="text-gray-400 text-xs">Sin roles</span>
          ) : (
            (user.roles ?? []).map((role) => (
              <span key={role.id} className="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded">
                {role.name}
              </span>
            ))
          )}
        </div>
      ),
    },
    {
      key: 'is_active',
      label: 'Estado',
      render: (user) => (
        <span className={`px-2 py-1 text-xs font-medium rounded ${user.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
          {user.is_active ? 'Activo' : 'Inactivo'}
        </span>
      ),
    },
  ];

  const actions: TableAction<User>[] = [
    { label: 'Editar', onClick: handleEdit, variant: 'secondary', permission: 'users:update', icon: <Pencil className="w-3 h-3" /> },
    { label: 'Eliminar', onClick: handleDelete, variant: 'danger', permission: 'users:delete', icon: <Trash2 className="w-3 h-3" /> },
  ];

  return (
    <DashboardLayout title="Gestión de Usuarios">
      <Card
        title="Usuarios del Sistema"
        actions={
          <ProtectedComponent permissions={['users:create']}>
            <Button onClick={handleCreate} className="flex items-center gap-2">
              <UserPlus className="w-4 h-4" />
              Nuevo Usuario
            </Button>
          </ProtectedComponent>
        }
      >
        <div className="mb-6 flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <SearchBar placeholder="Buscar por usuario, email o nombre..." onSearch={setSearchQuery} />
          </div>
          <FilterSelect
            label="Estado"
            value={statusFilter}
            onChange={setStatusFilter}
            options={[
              { value: 'all', label: 'Todos' },
              { value: 'active', label: 'Activos' },
              { value: 'inactive', label: 'Inactivos' },
            ]}
          />
        </div>

        <Table data={paginatedUsers} columns={columns} actions={actions} isLoading={isLoading} emptyMessage="No se encontraron usuarios" />

        {filteredUsers.length > 0 && (
          <Pagination
            currentPage={currentPage} totalPages={totalPages}
            onPageChange={goToPage} onFirstPage={goToFirstPage} onLastPage={goToLastPage}
            onPreviousPage={previousPage} onNextPage={nextPage}
            startIndex={startIndex} endIndex={endIndex}
            totalItems={filteredUsers.length} itemsPerPage={itemsPerPage}
            onItemsPerPageChange={setItemsPerPage}
          />
        )}
      </Card>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingUser ? 'Editar Usuario' : 'Crear Usuario'}
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
            <Button onClick={handleSubmit} disabled={isSubmitting}>
              {isSubmitting ? 'Guardando...' : editingUser ? 'Actualizar' : 'Crear'}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {formError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">{formError}</div>
          )}
          <Input
            label="Usuario"
            value={formData.username}
            onChange={(e) => setFormData({ ...formData, username: e.target.value })}
            required
            disabled={!!editingUser}
          />
          <Input
            label="Nombre Completo"
            value={formData.full_name}
            onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
          />
          <Input
            label="Email"
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            required
          />
          <Input
            label={editingUser ? 'Nueva Contraseña (dejar vacío para mantener)' : 'Contraseña *'}
            type="password"
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            required={!editingUser}
          />
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Roles</label>
            <div className="space-y-2 max-h-40 overflow-y-auto border border-gray-300 rounded-lg p-3">
              {roles.map((role) => (
                <label key={role.id} className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.role_ids?.includes(role.id)}
                    onChange={(e) => {
                      const newIds = e.target.checked
                        ? [...(formData.role_ids ?? []), role.id]
                        : (formData.role_ids ?? []).filter((id) => id !== role.id);
                      setFormData({ ...formData, role_ids: newIds });
                    }}
                    className="rounded"
                  />
                  <span className="text-sm">{role.name}</span>
                </label>
              ))}
            </div>
          </div>
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="rounded"
            />
            <span className="text-sm font-medium text-gray-700">Usuario Activo</span>
          </label>
        </div>
      </Modal>

      <ConfirmationDialog />
    </DashboardLayout>
  );
}
