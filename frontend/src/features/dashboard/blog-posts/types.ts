export interface DashboardBlogPost {
  id: string;
  title: string;
  excerpt: string;
  date: string;
  views: number;
  comments: number;
  category: string;
  featured: boolean;
}

export interface BlogPostFilters {
  search: string;
  statusFilter: string;
  categoryFilter: string;
}
