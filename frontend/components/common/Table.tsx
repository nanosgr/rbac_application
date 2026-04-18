import { TableColumn, TableAction } from '@/types';
import Button from './Button';
import ProtectedComponent from './ProtectedComponent';
import TableSkeleton from './TableSkeleton';

interface TableProps<T> {
  data: T[];
  columns: TableColumn<T>[];
  actions?: TableAction<T>[];
  isLoading?: boolean;
  emptyMessage?: string;
}

export default function Table<T extends { id: number | string }>({
  data,
  columns,
  actions = [],
  isLoading = false,
  emptyMessage = 'No hay datos para mostrar',
}: TableProps<T>) {
  if (isLoading) {
    return <TableSkeleton rows={5} columns={columns.length + (actions.length > 0 ? 1 : 0)} />;
  }

  if (data.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((column, index) => (
              <th
                key={index}
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                {column.label}
              </th>
            ))}
            {actions.length > 0 && (
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Acciones
              </th>
            )}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {data.map((item) => (
            <tr key={item.id} className="hover:bg-gray-50">
              {columns.map((column, colIndex) => (
                <td key={colIndex} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {column.render
                    ? column.render(item)
                    : String((item as any)[column.key] ?? '')}
                </td>
              ))}
              {actions.length > 0 && (
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <div className="flex items-center justify-end space-x-2">
                    {actions.map((action, actionIndex) => (
                      <ProtectedComponent
                        key={actionIndex}
                        permissions={action.permission ? [action.permission] : []}
                      >
                        <Button
                          size="sm"
                          variant={action.variant || 'secondary'}
                          onClick={() => action.onClick(item)}
                        >
                          {action.icon && <span className="mr-1">{action.icon}</span>}
                          {action.label}
                        </Button>
                      </ProtectedComponent>
                    ))}
                  </div>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
