'use client';

import { useEffect, useState, useMemo } from 'react';
import { useAuth } from '@/context/AuthContext';
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

export default function UsersPage() {
  const { hasPermission } = useAuth();
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
  const [error, setError] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [usersData, rolesData] = await Promise.all([
        userService.getAll(),
        roleService.getAll(),
      ]);
      setUsers(usersData);
      setRoles(rolesData);
    } catch (error) {
      console.error('Error loading data:', error);
      showError('Error al cargar los datos');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingUser(null);
    setFormData({
      username: '',
      email: '',
      password: '',
      full_name: '',
      is_active: true,
      role_ids: [],
    });
    setError('');
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
      role_ids: user.roles.map((r) => r.id),
    });
    setError('');
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
      success(`Usuario "${user.username}" eliminado exitosamente`);
      await loadData();
    } catch (error) {
      console.error('Error deleting user:', error);
      showError('Error al eliminar el usuario');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    try {
      if (editingUser) {
        const updateData: UpdateUserDTO = {
          email: formData.email,
          full_name: formData.full_name,
          is_active: formData.is_active,
        };
        if (formData.password) {
          updateData.password = formData.password;
        }
        await userService.update(editingUser.id, updateData);

        if (formData.role_ids && formData.role_ids.length > 0) {
          await userService.assignRoles(editingUser.id, formData.role_ids);
        }
      } else {
        await userService.create(formData);
      }

      setIsModalOpen(false);
      success(editingUser ? 'Usuario actualizado exitosamente' : 'Usuario creado exitosamente');
      await loadData();
    } catch (error) {
      console.error('Error saving user:', error);
      setError(error instanceof Error ? error.message : 'Error al guardar el usuario');
    }
  };

  // Filtered users based on search and filters
  const filteredUsers = useMemo(() => {
    return users.filter((user) => {
      // Search filter
      const matchesSearch =
        searchQuery === '' ||
        user.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
        user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
        user.full_name.toLowerCase().includes(searchQuery.toLowerCase());

      // Status filter
      const matchesStatus =
        statusFilter === 'all' ||
        (statusFilter === 'active' && user.is_active) ||
        (statusFilter === 'inactive' && !user.is_active);

      return matchesSearch && matchesStatus;
    });
  }, [users, searchQuery, statusFilter]);

  // Pagination
  const {
    currentPage,
    totalPages,
    currentData: paginatedUsers,
    itemsPerPage,
    startIndex,
    endIndex,
    goToPage,
    nextPage,
    previousPage,
    goToFirstPage,
    goToLastPage,
    setItemsPerPage,
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
          <span className="font-medium">{user.username}</span>
        </div>
      ),
    },
    {
      key: 'full_name',
      label: 'Nombre Completo',
    },
    {
      key: 'email',
      label: 'Email',
    },
    {
      key: 'roles',
      label: 'Roles',
      render: (user) => (
        <div className="flex flex-wrap gap-1">
          {user.roles.map((role) => (
            <span
              key={role.id}
              className="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded"
            >
              {role.name}
            </span>
          ))}
        </div>
      ),
    },
    {
      key: 'is_active',
      label: 'Estado',
      render: (user) => (
        <span
          className={`px-2 py-1 text-xs font-medium rounded ${
            user.is_active
              ? 'bg-green-100 text-green-800'
              : 'bg-red-100 text-red-800'
          }`}
        >
          {user.is_active ? 'Activo' : 'Inactivo'}
        </span>
      ),
    },
  ];

  const actions: TableAction<User>[] = [
    {
      label: 'Editar',
      onClick: handleEdit,
      variant: 'secondary',
      permission: 'users:update',
      icon: '✏️',
    },
    {
      label: 'Eliminar',
      onClick: handleDelete,
      variant: 'danger',
      permission: 'users:delete',
      icon: '🗑️',
    },
  ];

  return (
    <DashboardLayout title="Gestión de Usuarios">
      <Card
        title="Usuarios del Sistema"
        actions={
          <ProtectedComponent permissions={['users:create']}>
            <Button onClick={handleCreate}>+ Nuevo Usuario</Button>
          </ProtectedComponent>
        }
      >
        {/* Search and Filters */}
        <div className="mb-6 flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <SearchBar
              placeholder="Buscar por usuario, email o nombre..."
              onSearch={setSearchQuery}
            />
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

        <Table
          data={paginatedUsers}
          columns={columns}
          actions={actions}
          isLoading={isLoading}
          emptyMessage="No se encontraron usuarios"
        />

        {/* Pagination */}
        {filteredUsers.length > 0 && (
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={goToPage}
            onFirstPage={goToFirstPage}
            onLastPage={goToLastPage}
            onPreviousPage={previousPage}
            onNextPage={nextPage}
            startIndex={startIndex}
            endIndex={endIndex}
            totalItems={filteredUsers.length}
            itemsPerPage={itemsPerPage}
            onItemsPerPageChange={setItemsPerPage}
          />
        )}
      </Card>

      {/* Modal Create/Edit */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingUser ? 'Editar Usuario' : 'Crear Usuario'}
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSubmit}>
              {editingUser ? 'Actualizar' : 'Crear'}
            </Button>
          </>
        }
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
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
            required
          />

          <Input
            label="Email"
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            required
          />

          <Input
            label={editingUser ? 'Nueva Contraseña (dejar vacío para mantener)' : 'Contraseña'}
            type="password"
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            required={!editingUser}
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Roles
            </label>
            <div className="space-y-2 max-h-40 overflow-y-auto border border-gray-300 rounded-lg p-3">
              {roles.map((role) => (
                <label key={role.id} className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={formData.role_ids?.includes(role.id)}
                    onChange={(e) => {
                      const newRoleIds = e.target.checked
                        ? [...(formData.role_ids || []), role.id]
                        : (formData.role_ids || []).filter((id) => id !== role.id);
                      setFormData({ ...formData, role_ids: newRoleIds });
                    }}
                    className="rounded"
                  />
                  <span className="text-sm">{role.name}</span>
                </label>
              ))}
            </div>
          </div>

          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="rounded"
            />
            <span className="text-sm font-medium text-gray-700">Usuario Activo</span>
          </label>
        </form>
      </Modal>

      {/* Confirmation Dialog */}
      <ConfirmationDialog />
    </DashboardLayout>
  );
}
