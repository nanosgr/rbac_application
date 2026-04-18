'use client';

import { useEffect, useState, useMemo } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { useConfirm } from '@/lib/hooks/useConfirm';
import { usePagination } from '@/lib/hooks/usePagination';
import { roleService, permissionService } from '@/lib/api/services';
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
import { Role, Permission, CreateRoleDTO, UpdateRoleDTO, TableColumn, TableAction } from '@/types';

export default function RolesPage() {
  const { success, error: showError } = useToast();
  const { confirm, ConfirmationDialog } = useConfirm();
  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [formData, setFormData] = useState<CreateRoleDTO>({
    name: '',
    description: '',
    is_active: true,
    permission_ids: [],
  });
  const [error, setError] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [rolesData, permissionsData] = await Promise.all([
        roleService.getAll(),
        permissionService.getAll(),
      ]);
      setRoles(rolesData);
      setPermissions(permissionsData);
    } catch (error) {
      console.error('Error loading data:', error);
      showError('Error al cargar los datos');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingRole(null);
    setFormData({
      name: '',
      description: '',
      is_active: true,
      permission_ids: [],
    });
    setError('');
    setIsModalOpen(true);
  };

  const handleEdit = (role: Role) => {
    setEditingRole(role);
    setFormData({
      name: role.name,
      description: role.description,
      is_active: role.is_active,
      permission_ids: role.permissions.map((p) => p.id),
    });
    setError('');
    setIsModalOpen(true);
  };

  const handleDelete = async (role: Role) => {
    const confirmed = await confirm({
      title: 'Eliminar Rol',
      message: `¿Está seguro de eliminar el rol "${role.name}"? Esta acción no se puede deshacer.`,
      confirmText: 'Eliminar',
      cancelText: 'Cancelar',
      variant: 'danger',
    });

    if (!confirmed) return;

    try {
      await roleService.delete(role.id);
      success(`Rol "${role.name}" eliminado exitosamente`);
      await loadData();
    } catch (error) {
      console.error('Error deleting role:', error);
      showError('Error al eliminar el rol');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    try {
      if (editingRole) {
        const updateData: UpdateRoleDTO = {
          name: formData.name,
          description: formData.description,
          is_active: formData.is_active,
        };
        await roleService.update(editingRole.id, updateData);

        if (formData.permission_ids && formData.permission_ids.length > 0) {
          await roleService.assignPermissions(editingRole.id, formData.permission_ids);
        }
      } else {
        await roleService.create(formData);
      }

      setIsModalOpen(false);
      success(editingRole ? 'Rol actualizado exitosamente' : 'Rol creado exitosamente');
      await loadData();
    } catch (error) {
      console.error('Error saving role:', error);
      setError(error instanceof Error ? error.message : 'Error al guardar el rol');
    }
  };

  // Filtered roles based on search and filters
  const filteredRoles = useMemo(() => {
    return roles.filter((role) => {
      const matchesSearch =
        searchQuery === '' ||
        role.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        role.description.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesStatus =
        statusFilter === 'all' ||
        (statusFilter === 'active' && role.is_active) ||
        (statusFilter === 'inactive' && !role.is_active);

      return matchesSearch && matchesStatus;
    });
  }, [roles, searchQuery, statusFilter]);

  // Pagination
  const {
    currentPage,
    totalPages,
    currentData: paginatedRoles,
    itemsPerPage,
    startIndex,
    endIndex,
    goToPage,
    nextPage,
    previousPage,
    goToFirstPage,
    goToLastPage,
    setItemsPerPage,
  } = usePagination({ data: filteredRoles, itemsPerPage: 10 });

  // Group permissions by resource
  const groupedPermissions = permissions.reduce((acc, perm) => {
    if (!acc[perm.resource]) {
      acc[perm.resource] = [];
    }
    acc[perm.resource].push(perm);
    return acc;
  }, {} as Record<string, Permission[]>);

  const columns: TableColumn<Role>[] = [
    {
      key: 'name',
      label: 'Nombre',
      render: (role) => (
        <div className="flex items-center space-x-2">
          <span className="text-2xl">🎭</span>
          <span className="font-medium">{role.name}</span>
        </div>
      ),
    },
    {
      key: 'description',
      label: 'Descripción',
    },
    {
      key: 'permissions',
      label: 'Permisos',
      render: (role) => (
        <span className="text-gray-600">{role.permissions.length} permisos</span>
      ),
    },
    {
      key: 'is_active',
      label: 'Estado',
      render: (role) => (
        <span
          className={`px-2 py-1 text-xs font-medium rounded ${
            role.is_active
              ? 'bg-green-100 text-green-800'
              : 'bg-red-100 text-red-800'
          }`}
        >
          {role.is_active ? 'Activo' : 'Inactivo'}
        </span>
      ),
    },
  ];

  const actions: TableAction<Role>[] = [
    {
      label: 'Editar',
      onClick: handleEdit,
      variant: 'secondary',
      permission: 'roles:update',
      icon: '✏️',
    },
    {
      label: 'Eliminar',
      onClick: handleDelete,
      variant: 'danger',
      permission: 'roles:delete',
      icon: '🗑️',
    },
  ];

  return (
    <DashboardLayout title="Gestión de Roles">
      <Card
        title="Roles del Sistema"
        actions={
          <ProtectedComponent permissions={['roles:create']}>
            <Button onClick={handleCreate}>+ Nuevo Rol</Button>
          </ProtectedComponent>
        }
      >
        {/* Search and Filters */}
        <div className="mb-6 flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <SearchBar
              placeholder="Buscar por nombre o descripción..."
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
          data={paginatedRoles}
          columns={columns}
          actions={actions}
          isLoading={isLoading}
          emptyMessage="No se encontraron roles"
        />

        {/* Pagination */}
        {filteredRoles.length > 0 && (
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
            totalItems={filteredRoles.length}
            itemsPerPage={itemsPerPage}
            onItemsPerPageChange={setItemsPerPage}
          />
        )}
      </Card>

      {/* Modal Create/Edit */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingRole ? 'Editar Rol' : 'Crear Rol'}
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSubmit}>
              {editingRole ? 'Actualizar' : 'Crear'}
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
            label="Nombre"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Descripción
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={3}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Permisos ({formData.permission_ids?.length || 0} seleccionados)
            </label>
            <div className="border border-gray-300 rounded-lg p-4 max-h-96 overflow-y-auto">
              {Object.entries(groupedPermissions).map(([resource, perms]) => (
                <div key={resource} className="mb-4 last:mb-0">
                  <h4 className="font-semibold text-gray-800 mb-2 capitalize">
                    {resource}
                  </h4>
                  <div className="grid grid-cols-2 gap-2 ml-4">
                    {perms.map((perm) => (
                      <label key={perm.id} className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          checked={formData.permission_ids?.includes(perm.id)}
                          onChange={(e) => {
                            const newPermIds = e.target.checked
                              ? [...(formData.permission_ids || []), perm.id]
                              : (formData.permission_ids || []).filter((id) => id !== perm.id);
                            setFormData({ ...formData, permission_ids: newPermIds });
                          }}
                          className="rounded"
                        />
                        <span className="text-sm">{perm.action}</span>
                      </label>
                    ))}
                  </div>
                </div>
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
            <span className="text-sm font-medium text-gray-700">Rol Activo</span>
          </label>
        </form>
      </Modal>

      {/* Confirmation Dialog */}
      <ConfirmationDialog />
    </DashboardLayout>
  );
}
