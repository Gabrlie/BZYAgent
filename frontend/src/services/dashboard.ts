import { get } from '@/utils/request';

export interface DashboardSummary {
  course_count: number;
  document_count: number;
  teaching_plan_count: number;
  lesson_plan_count: number;
  courseware_count: number;
  copyright_project_count: number;
  ai_configured: boolean;
}

export async function getDashboardSummary() {
  return get<DashboardSummary>('/api/dashboard/summary');
}
