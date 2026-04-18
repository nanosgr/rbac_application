'use client';

import { useEffect, useState, useMemo } from 'react';
import { useToast } from '@/context/ToastContext';
import { useConfirm } from '@/lib/hooks/useConfirm';
import { usePagination } from '@/lib/hooks/usePagination';
import { permissionService } from '@/lib/api/services';
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
import { Permission, CreatePermissionDTO, UpdatePermissionDTO, TableColumn, TableAction } from '@/types';

export default function PermissionsPage() {
  const { success, error: showError } = useToast();
  const { confirm, ConfirmationDialog } = useConfirm();
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingPermission, setEditingPermission] = useState<Permission | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [formData, setFormData] = useState<CreatePermissionDTO>({
    name: '',
    description: '',
    resource: '',
    action: '',
    is_active: true,
  });
  const [error, setError] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const data = await permissionService.getAll();
      setPermissions(data);
    } catch (error) {
      console.error('Error loading permissions:', error);
      showError('Error al cargar los permisos');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingPermission(null);
    setFormData({
      name: '',
      description: '',
      resource: '',
      action: '',
      is_active: true,
    });
    setError('');
    setIsModalOpen(true);
  };

  const handleEdit = (permission: Permission) => {
    setEditingPermission(permission);
    setFormData({
      name: permission.name,
      description: permission.description,
      resource: permission.resource,
      action: permission.action,
      is_active: permission.is_active,
    });
    setError('');
    setIsModalOpen(true);
  };

  const handleDelete = async (permission: Permission) => {
    const confirmed = await confirm({
      title: 'Eliminar Permiso',
      message: `¿Está seguro de eliminar el permiso "${permission.name}"? Esta acción no se puede deshacer.`,
      confirmText: 'Eliminar',
      cancelText: 'Cancelar',
      variant: 'danger',
    });

    if (!confirmed) return;

    try {
      await permissionService.delete(permission.id);
      success(`Permiso "${permission.name}" eliminado exitosamente`);
      await loadData();
    } catch (error) {
      console.error('Error deleting permission:', error);
      showError('Error al eliminar el permiso');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    try {
      if (editingPermission) {
        const updateData: UpdatePermissionDTO = {
          name: formData.name,
          description: formData.description,
          is_active: formData.is_active,
        };
        await permissionService.update(editingPermission.id, updateData);
      } else {
        await permissionService.create(formData);
      }

      setIsModalOpen(false);
      success(editingPermission ? 'Permiso actualizado exitosamente' : 'Permiso creado exitosamente');
      await loadData();
    } catch (error) {
      console.error('Error saving permission:', error);
      setError(error instanceof Error ? error.message : 'Error al guardar el permiso');
    }
  };

  // Filtered permissions based on search and filters
  const filteredPermissions = useMemo(() => {
    return permissions.filter((perm) => {
      const matchesSearch =
        searchQuery === '' ||
        perm.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        perm.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        perm.resource.toLowerCase().includes(searchQuery.toLowerCase()) ||
        perm.action.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesStatus =
        statusFilter === 'all' ||
        (statusFilter === 'active' && perm.is_active) ||
        (statusFilter === 'inactive' && !perm.is_active);

      return matchesSearch && matchesStatus;
    });
  }, [permissions, searchQuery, statusFilter]);

  // Pagination
  const {
    currentPage,
    totalPages,
    currentData: paginatedPermissions,
    itemsPerPage,
    startIndex,
    endIndex,
    goToPage,
    nextPage,
    previousPage,
    goToFirstPage,
    goToLastPage,
    setItemsPerPage,
  } = usePagination({ data: filteredPermissions, itemsPerPage: 10 });

  const columns: TableColumn<Permission>[] = [
    {
      key: 'name',
      label: 'Nombre',
      render: (perm) => (
        <div className="flex items-center space-x-2">
          <span className="text-2xl">🔑</span>
          <span className="font-medium">{perm.name}</span>
        </div>
      ),
    },
    {
      key: 'description',
      label: 'Descripción',
    },
    {
      key: 'resource',
      label: 'Recurso',
      render: (perm) => (
        <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded font-medium">
          {perm.resource}
        </span>
      ),
    },
    {
      key: 'action',
      label: 'Acción',
      render: (perm) => (
        <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded font-medium">
          {perm.action}
        </span>
      ),
    },
    {
      key: 'is_active',
      label: 'Estado',
      render: (perm) => (
        <span
          className={`px-2 py-1 text-xs font-medium rounded ${
            perm.is_active
              ? 'bg-green-100 text-green-800'
              : 'bg-red-100 text-red-800'
          }`}
        >
          {perm.is_active ? 'Activo' : 'Inactivo'}
        </span>
      ),
    },
  ];

  const actions: TableAction<Permission>[] = [
    {
      label: 'Editar',
      onClick: handleEdit,
      variant: 'secondary',
      permission: 'permissions:update',
      icon: '✏️',
    },
    {
      label: 'Eliminar',
      onClick: handleDelete,
      variant: 'danger',
      permission: 'permissions:delete',
      icon: '🗑️',
    },
  ];

  // Group filtered permissions by resource for better visualization
  const groupedPermissions = filteredPermissions.reduce((acc, perm) => {
    if (!acc[perm.resource]) {
      acc[perm.resource] = [];
    }
    acc[perm.resource].push(perm);
    return acc;
  }, {} as Record<string, Permission[]>);

  return (
    <DashboardLayout title="Gestión de Permisos">
      <div className="space-y-6">
        <Card
          title="Permisos del Sistema"
          actions={
            <ProtectedComponent permissions={['permissions:create']}>
              <Button onClick={handleCreate}>+ Nuevo Permiso</Button>
            </ProtectedComponent>
          }
        >
          {/* Search and Filters */}
          <div className="mb-6 flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <SearchBar
                placeholder="Buscar por nombre, recurso o acción..."
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
            data={paginatedPermissions}
            columns={columns}
            actions={actions}
            isLoading={isLoading}
            emptyMessage="No se encontraron permisos"
          />

          {/* Pagination */}
          {filteredPermissions.length > 0 && (
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
              totalItems={filteredPermissions.length}
              itemsPerPage={itemsPerPage}
              onItemsPerPageChange={setItemsPerPage}
            />
          )}
        </Card>

        {/* Permissions by Resource */}
        <Card title="Permisos por Recurso">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(groupedPermissions).map(([resource, perms]) => (
              <div
                key={resource}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <h3 className="font-semibold text-gray-800 mb-3 capitalize text-lg">
                  {resource}
                </h3>
                <div className="space-y-2">
                  {perms.map((perm) => (
                    <div
                      key={perm.id}
                      className="flex items-center justify-between text-sm"
                    >
                      <span className="text-gray-700">{perm.action}</span>
                      <span
                        className={`px-2 py-0.5 text-xs rounded ${
                          perm.is_active
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {perm.is_active ? '✓' : '✗'}
                      </span>
                    </div>
                  ))}
                </div>
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <p className="text-xs text-gray-500">
                    {perms.length} permiso{perms.length !== 1 ? 's' : ''}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Modal Create/Edit */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingPermission ? 'Editar Permiso' : 'Crear Permiso'}
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSubmit}>
              {editingPermission ? 'Actualizar' : 'Crear'}
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
            placeholder="ej: users:read"
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
              placeholder="Descripción del permiso"
              required
            />
          </div>

          <Input
            label="Recurso"
            value={formData.resource}
            onChange={(e) => setFormData({ ...formData, resource: e.target.value })}
            placeholder="ej: users, roles, permissions"
            required
            disabled={!!editingPermission}
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Acción
            </label>
            <select
              value={formData.action}
              onChange={(e) => setFormData({ ...formData, action: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
              disabled={!!editingPermission}
            >
              <option value="">Seleccionar acción...</option>
              <option value="create">create</option>
              <option value="read">read</option>
              <option value="update">update</option>
              <option value="delete">delete</option>
              <option value="export">export</option>
            </select>
          </div>

          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="rounded"
            />
            <span className="text-sm font-medium text-gray-700">Permiso Activo</span>
          </label>
        </form>
      </Modal>

      {/* Confirmation Dialog */}
      <ConfirmationDialog />
    </DashboardLayout>
  );
}
