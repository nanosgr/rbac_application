import { useCallback, useEffect, useState } from 'react';
import { useToast } from '@/context/ToastContext';
import { useConfirm } from '@/lib/hooks/useConfirm';
import { orderService, userService } from '@/lib/api/services';
import { ORDER_STATUS_OPTIONS, ORDER_STATUS_FILTER_OPTIONS } from '@/lib/constants';
import DashboardLayout from '@/components/layout/DashboardLayout';
import Card from '@/components/common/Card';
import Table from '@/components/common/Table';
import Modal from '@/components/common/Modal';
import Input from '@/components/common/Input';
import Button from '@/components/common/Button';
import ProtectedComponent from '@/components/common/ProtectedComponent';
import FilterSelect from '@/components/common/FilterSelect';
import Pagination from '@/components/common/Pagination';
import ErrorAlert from '@/components/common/ErrorAlert';
import ModalFooter from '@/components/common/ModalFooter';
import { useAuth } from '@/context/AuthContext';
import { Order, CreateOrderDTO, TableColumn, TableAction, UserScope } from '@/types';
import { ShoppingCart, Pencil, Trash2, Filter } from 'lucide-react';

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400',
  paid: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400',
  shipped: 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400',
  cancelled: 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-400',
};

const emptyForm: CreateOrderDTO = { customer: '', total: 0, warehouse: '', status: 'pending' };

export default function OrdersPage() {
  const { user } = useAuth();
  const { success, error: showError } = useToast();
  const { confirm, ConfirmationDialog } = useConfirm();

  const [orders, setOrders] = useState<Order[]>([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState('all');
  const [isLoading, setIsLoading] = useState(true);
  const [myScopes, setMyScopes] = useState<UserScope[]>([]);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editing, setEditing] = useState<Order | null>(null);
  const [formData, setFormData] = useState<CreateOrderDTO>(emptyForm);
  const [formError, setFormError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const load = useCallback(async (currentPage: number, size: number) => {
    setIsLoading(true);
    try {
      const res = await orderService.getAll({
        page: currentPage,
        size,
        ...(statusFilter !== 'all' && { status: statusFilter }),
      });
      setOrders(res.items);
      setTotal(res.total);
      setPages(res.pages || 1);
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Error al cargar los pedidos');
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, showError]);

  useEffect(() => { setPage(1); }, [statusFilter, pageSize]);
  useEffect(() => { load(page, pageSize); }, [load, page, pageSize]);

  useEffect(() => {
    userService.getMyScopes().then((r) => setMyScopes(r.items)).catch(() => setMyScopes([]));
  }, []);

  const openCreate = () => {
    setEditing(null);
    setFormData(emptyForm);
    setFormError('');
    setIsModalOpen(true);
  };

  const openEdit = (order: Order) => {
    setEditing(order);
    setFormData({ customer: order.customer, total: order.total, warehouse: order.warehouse, status: order.status });
    setFormError('');
    setIsModalOpen(true);
  };

  const handleDelete = async (order: Order) => {
    const confirmed = await confirm({
      title: 'Eliminar Pedido',
      message: `¿Eliminar el pedido #${order.id} de "${order.customer}"?`,
      confirmText: 'Eliminar',
      cancelText: 'Cancelar',
      variant: 'danger',
    });
    if (!confirmed) return;
    try {
      await orderService.delete(order.id);
      success(`Pedido #${order.id} eliminado`);
      await load(page, pageSize);
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Error al eliminar el pedido');
    }
  };

  const handleSubmit = async () => {
    setFormError('');
    if (!formData.customer.trim() || !formData.warehouse.trim()) {
      setFormError('Cliente y depósito son obligatorios.');
      return;
    }
    setIsSubmitting(true);
    try {
      if (editing) {
        await orderService.update(editing.id, formData);
        success('Pedido actualizado');
      } else {
        await orderService.create(formData);
        success('Pedido creado');
      }
      setIsModalOpen(false);
      await load(page, pageSize);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Error al guardar el pedido');
    } finally {
      setIsSubmitting(false);
    }
  };

  const startIndex = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const endIndex = Math.min(page * pageSize, total);

  const columns: TableColumn<Order>[] = [
    { key: 'id', label: '#', render: (o) => <span className="font-mono text-xs text-stone-400">#{o.id}</span> },
    { key: 'customer', label: 'Cliente', render: (o) => <span className="font-medium text-stone-800 dark:text-stone-200">{o.customer}</span> },
    {
      key: 'warehouse',
      label: 'Depósito',
      render: (o) => <span className="px-2 py-1 bg-blue-100 text-blue-800 dark:bg-blue-950/40 dark:text-blue-300 text-xs rounded font-medium">{o.warehouse}</span>,
    },
    {
      key: 'total',
      label: 'Total',
      render: (o) => <span className="tabular-nums">{o.total.toLocaleString('es-AR', { style: 'currency', currency: 'ARS' })}</span>,
    },
    {
      key: 'status',
      label: 'Estado',
      render: (o) => (
        <span className={`px-2 py-1 text-xs font-medium rounded ${STATUS_STYLES[o.status] ?? 'bg-stone-100 text-stone-600'}`}>
          {ORDER_STATUS_OPTIONS.find((s) => s.value === o.status)?.label ?? o.status}
        </span>
      ),
    },
    {
      key: 'owner_id',
      label: 'Vendedor',
      render: (o) => (
        <span className="text-xs text-stone-500 dark:text-stone-400">
          {o.owner_id === user?.id ? 'Yo' : o.owner_id ? `#${o.owner_id}` : '—'}
        </span>
      ),
    },
  ];

  const actions: TableAction<Order>[] = [
    { label: 'Editar', onClick: openEdit, variant: 'secondary', permission: 'orders:update', icon: <Pencil className="w-3 h-3" /> },
    { label: 'Eliminar', onClick: handleDelete, variant: 'danger', permission: 'orders:delete', icon: <Trash2 className="w-3 h-3" /> },
  ];

  return (
    <DashboardLayout title="Pedidos">
      <div className="space-y-4">
        <div className="rounded-lg border border-blue-200 dark:border-blue-900/60 bg-blue-50/60 dark:bg-blue-950/20 px-4 py-3 flex items-start gap-2.5">
          <Filter className="w-4 h-4 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
          <div className="text-xs text-blue-800 dark:text-blue-300">
            <p>
              Esta lista ya viene <strong>filtrada por tu alcance</strong>: según los permisos de
              tus roles verás todos los pedidos, sólo los tuyos, o sólo los de tus dimensiones.
            </p>
            {myScopes.length > 0 && (
              <p className="mt-1">
                Tus alcances:{' '}
                {myScopes.map((s, i) => (
                  <span key={i} className="font-mono">
                    {s.dimension}={s.value}{i < myScopes.length - 1 ? ', ' : ''}
                  </span>
                ))}
              </p>
            )}
          </div>
        </div>

        <Card
          title={`Pedidos (${total})`}
          actions={
            <ProtectedComponent permissions={['orders:create']}>
              <Button onClick={openCreate} className="flex items-center gap-2">
                <ShoppingCart className="w-4 h-4" />
                Nuevo Pedido
              </Button>
            </ProtectedComponent>
          }
        >
          <div className="mb-5">
            <FilterSelect
              label="Estado"
              value={statusFilter}
              onChange={setStatusFilter}
              options={ORDER_STATUS_FILTER_OPTIONS}
            />
          </div>

          <Table data={orders} columns={columns} actions={actions} isLoading={isLoading} emptyMessage="No hay pedidos en tu alcance" />

          {pages > 0 && (
            <Pagination
              currentPage={page}
              totalPages={pages}
              onPageChange={setPage}
              onFirstPage={() => setPage(1)}
              onLastPage={() => setPage(pages)}
              onPreviousPage={() => setPage((p) => Math.max(1, p - 1))}
              onNextPage={() => setPage((p) => Math.min(pages, p + 1))}
              startIndex={startIndex}
              endIndex={endIndex}
              totalItems={total}
              itemsPerPage={pageSize}
              onItemsPerPageChange={setPageSize}
            />
          )}
        </Card>
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editing ? `Editar Pedido #${editing.id}` : 'Nuevo Pedido'}
        footer={
          <ModalFooter
            onCancel={() => setIsModalOpen(false)}
            onSubmit={handleSubmit}
            isSubmitting={isSubmitting}
            isEditing={!!editing}
          />
        }
      >
        <div className="space-y-4">
          <ErrorAlert message={formError} />
          <Input
            label="Cliente *"
            value={formData.customer}
            onChange={(e) => setFormData({ ...formData, customer: e.target.value })}
            required
          />
          <Input
            label="Total"
            type="number"
            value={formData.total}
            onChange={(e) => setFormData({ ...formData, total: Number(e.target.value) })}
          />
          <Input
            label="Depósito *"
            value={formData.warehouse}
            onChange={(e) => setFormData({ ...formData, warehouse: e.target.value })}
            placeholder="norte / sur / centro..."
            required
          />
          <div>
            <label className="block text-xs font-medium text-stone-600 dark:text-stone-400 mb-1.5">Estado</label>
            <select
              value={formData.status}
              onChange={(e) => setFormData({ ...formData, status: e.target.value })}
              className="w-full px-3 py-2 text-sm rounded-md border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 transition-colors"
            >
              {ORDER_STATUS_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </div>
        </div>
      </Modal>

      <ConfirmationDialog />
    </DashboardLayout>
  );
}
