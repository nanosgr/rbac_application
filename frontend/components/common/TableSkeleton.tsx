import Skeleton from './Skeleton';

interface TableSkeletonProps {
  rows?: number;
  columns?: number;
}

export default function TableSkeleton({ rows = 5, columns = 4 }: TableSkeletonProps) {
  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center space-x-4 p-4 bg-gray-50 rounded-lg">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} width="flex-1" height="h-4" />
        ))}
      </div>

      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div
          key={rowIndex}
          className="flex items-center space-x-4 p-4 bg-white border border-gray-200 rounded-lg"
        >
          {Array.from({ length: columns }).map((_, colIndex) => (
            <div key={colIndex} className="flex-1">
              {colIndex === 0 ? (
                <div className="flex items-center space-x-3">
                  <Skeleton width="w-10" height="h-10" rounded="full" />
                  <Skeleton width="w-24" height="h-4" />
                </div>
              ) : (
                <Skeleton height="h-4" />
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
