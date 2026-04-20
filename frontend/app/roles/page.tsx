'use client';

import { useEffect, useState, useCallback } from 'react';
import { useToast } from '@/context/ToastContext';
import { useConfirm } from '@/lib/hooks/useConfirm';
import { usePagination } from '@/lib/hooks/usePagination';
import { useFilteredData } from '@/lib/hooks/useFilteredData';
import { roleService, permissionService } from '@/lib/api/services';
import { STATUS_FILTER_OPTIONS } from '@/lib/constants';
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
import ErrorAlert from '@/components/common/ErrorAlert';
import ModalFooter from '@/components/common/ModalFooter';
import { Role, Permission, CreateRoleDTO, UpdateRoleDTO, TableColumn, TableAction } from '@/types';
import { ShieldPlus, Pencil, Trash2 } from 'lucide-react';

const ROLE_SEARCH_FIELDS = ['name', 'description'];

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
  const [formError, setFormError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [rolesRes, permsRes] = await Promise.all([
        roleService.getAll({ size: 500 }),
        permissionService.getAll({ size: 500, is_active: true }),
      ]);
      setRoles(rolesRes.items);
      setPermissions(permsRes.items);
    } catch {
      showError('Error al cargar los datos');
    } finally {
      setIsLoading(false);
    }
  }, [showError]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreate = () => {
    setEditingRole(null);
    setFormData({ name: '', description: '', is_active: true, permission_ids: [] });
    setFormError('');
    setIsModalOpen(true);
  };

  const handleEdit = (role: Role) => {
    setEditingRole(role);
    setFormData({
      name: role.name,
      description: role.description,
      is_active: role.is_active,
      permission_ids: (role.permissions ?? []).map((p) => p.id),
    });
    setFormError('');
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
      success(`Rol "${role.name}" eliminado`);
      await loadData();
    } catch {
      showError('Error al eliminar el rol');
    }
  };

  const handleSubmit = async () => {
    setFormError('');
    setIsSubmitting(true);
    try {
      if (editingRole) {
        const updateData: UpdateRoleDTO = { name: formData.name, description: formData.description, is_active: formData.is_active };
        await roleService.update(editingRole.id, updateData);
        await roleService.assignPermissions(editingRole.id, formData.permission_ids ?? []);
        success('Rol actualizado');
      } else {
        const { permission_ids, ...createPayload } = formData;
        const newRole = await roleService.create(createPayload);
        if (permission_ids && permission_ids.length > 0) {
          await roleService.assignPermissions(newRole.id, permission_ids);
        }
        success('Rol creado');
      }
      setIsModalOpen(false);
      await loadData();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Error al guardar el rol');
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredRoles = useFilteredData({
    data: roles,
    searchQuery,
    searchFields: ROLE_SEARCH_FIELDS,
    statusFilter,
  });

  const {
    currentPage, totalPages, currentData: paginatedRoles,
    itemsPerPage, startIndex, endIndex,
    goToPage, nextPage, previousPage, goToFirstPage, goToLastPage, setItemsPerPage,
  } = usePagination({ data: filteredRoles, itemsPerPage: 10 });

  const groupedPermissions = permissions.reduce((acc, perm) => {
    if (!acc[perm.resource]) acc[perm.resource] = [];
    acc[perm.resource].push(perm);
    return acc;
  }, {} as Record<string, Permission[]>);

  const columns: TableColumn<Role>[] = [
    {
      key: 'name',
      label: 'Nombre',
      render: (role) => <span className="font-medium text-stone-800 dark:text-stone-200">{role.name}</span>,
    },
    { key: 'description', label: 'Descripción' },
    {
      key: 'permissions',
      label: 'Permisos',
      render: (role) => (
        <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded-full">
          {(role.permissions ?? []).length} permisos
        </span>
      ),
    },
    {
      key: 'is_active',
      label: 'Estado',
      render: (role) => (
        <span className={`px-2 py-1 text-xs font-medium rounded ${role.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
          {role.is_active ? 'Activo' : 'Inactivo'}
        </span>
      ),
    },
  ];

  const actions: TableAction<Role>[] = [
    { label: 'Editar', onClick: handleEdit, variant: 'secondary', permission: 'roles:update', icon: <Pencil className="w-3 h-3" /> },
    { label: 'Eliminar', onClick: handleDelete, variant: 'danger', permission: 'roles:delete', icon: <Trash2 className="w-3 h-3" /> },
  ];

  return (
    <DashboardLayout title="Gestión de Roles">
      <Card
        title="Roles del Sistema"
        actions={
          <ProtectedComponent permissions={['roles:create']}>
            <Button onClick={handleCreate} className="flex items-center gap-2">
              <ShieldPlus className="w-4 h-4" />
              Nuevo Rol
            </Button>
          </ProtectedComponent>
        }
      >
        <div className="mb-6 flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <SearchBar placeholder="Buscar por nombre o descripción..." onSearch={setSearchQuery} />
          </div>
          <FilterSelect label="Estado" value={statusFilter} onChange={setStatusFilter} options={STATUS_FILTER_OPTIONS} />
        </div>

        <Table data={paginatedRoles} columns={columns} actions={actions} isLoading={isLoading} emptyMessage="No se encontraron roles" />

        {filteredRoles.length > 0 && (
          <Pagination
            currentPage={currentPage} totalPages={totalPages}
            onPageChange={goToPage} onFirstPage={goToFirstPage} onLastPage={goToLastPage}
            onPreviousPage={previousPage} onNextPage={nextPage}
            startIndex={startIndex} endIndex={endIndex}
            totalItems={filteredRoles.length} itemsPerPage={itemsPerPage}
            onItemsPerPageChange={setItemsPerPage}
          />
        )}
      </Card>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingRole ? 'Editar Rol' : 'Crear Rol'}
        size="lg"
        footer={
          <ModalFooter
            onCancel={() => setIsModalOpen(false)}
            onSubmit={handleSubmit}
            isSubmitting={isSubmitting}
            isEditing={!!editingRole}
          />
        }
      >
        <div className="space-y-4">
          <ErrorAlert message={formError} />
          <Input
            label="Nombre *"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
          />
          <div>
            <label className="block text-xs font-medium text-stone-600 dark:text-stone-400 mb-1.5">Descripción</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 text-sm rounded-md border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100 placeholder:text-stone-400 dark:placeholder:text-stone-600 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 transition-colors"
              rows={3}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-stone-600 dark:text-stone-400 mb-1.5">
              Permisos ({formData.permission_ids?.length ?? 0} seleccionados)
            </label>
            <div className="border border-stone-200 dark:border-stone-700 rounded-md p-3 max-h-72 overflow-y-auto bg-white dark:bg-stone-900">
              {Object.entries(groupedPermissions).map(([resource, perms]) => (
                <div key={resource} className="mb-4 last:mb-0">
                  <h4 className="font-semibold text-stone-500 dark:text-stone-400 mb-2 uppercase text-xs tracking-wide">{resource}</h4>
                  <div className="grid grid-cols-2 gap-2 ml-2">
                    {perms.map((perm) => (
                      <label key={perm.id} className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={formData.permission_ids?.includes(perm.id)}
                          onChange={(e) => {
                            const newIds = e.target.checked
                              ? [...(formData.permission_ids ?? []), perm.id]
                              : (formData.permission_ids ?? []).filter((id) => id !== perm.id);
                            setFormData({ ...formData, permission_ids: newIds });
                          }}
                          className="rounded accent-blue-600"
                        />
                        <span className="text-sm text-stone-700 dark:text-stone-300">{perm.action}</span>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="rounded accent-blue-600"
            />
            <span className="text-sm font-medium text-stone-700 dark:text-stone-300">Rol Activo</span>
          </label>
        </div>
      </Modal>

      <ConfirmationDialog />
    </DashboardLayout>
  );
}
