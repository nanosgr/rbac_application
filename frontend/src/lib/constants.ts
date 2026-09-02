export const STATUS_FILTER_OPTIONS = [
  { value: 'all', label: 'Todos' },
  { value: 'active', label: 'Activos' },
  { value: 'inactive', label: 'Inactivos' },
] as const;

// Alcance de datos de una regla rol -> permiso
export const SCOPE_OPTIONS = [
  { value: 'all', label: 'Todos los registros' },
  { value: 'own', label: 'Solo los propios' },
  { value: 'attribute', label: 'Por atributo (dimensión)' },
] as const;

export const SCOPE_LABELS: Record<string, string> = {
  all: 'Todos',
  own: 'Propios',
  attribute: 'Por atributo',
};

export const EFFECT_OPTIONS = [
  { value: 'allow', label: 'Permitir (allow)' },
  { value: 'deny', label: 'Denegar (deny)' },
] as const;

// Estados del modelo de ejemplo Order
export const ORDER_STATUS_OPTIONS = [
  { value: 'pending', label: 'Pendiente' },
  { value: 'paid', label: 'Pagado' },
  { value: 'shipped', label: 'Enviado' },
  { value: 'cancelled', label: 'Cancelado' },
] as const;

export const ORDER_STATUS_FILTER_OPTIONS = [
  { value: 'all', label: 'Todos los estados' },
  ...ORDER_STATUS_OPTIONS,
] as const;
