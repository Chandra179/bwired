/**
 * Skeleton loader component for search result items
 * Shows animated placeholder while content loads
 */
function SkeletonItem() {
  return (
    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-4 animate-pulse">
      {/* Title skeleton */}
      <div class="h-6 bg-gray-200 rounded w-3/4 mb-3"></div>
      
      {/* Content skeleton - 3 lines */}
      <div class="space-y-2 mb-4">
        <div class="h-4 bg-gray-200 rounded w-full"></div>
        <div class="h-4 bg-gray-200 rounded w-full"></div>
        <div class="h-4 bg-gray-200 rounded w-5/6"></div>
      </div>
      
      {/* Footer skeleton - engine badge */}
      <div class="flex items-center justify-between">
        <div class="h-5 bg-gray-200 rounded w-24"></div>
        <div class="h-4 bg-gray-200 rounded w-16"></div>
      </div>
    </div>
  );
}

export default SkeletonItem;
