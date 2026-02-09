/**
 * 课程管理 API 服务
 */
import { get, post, put, del } from '@/utils/request';

// 课程接口定义
export interface Course {
    id: number;
    user_id: number;
    name: string;
    semester: string;
    class_name: string;
    total_hours: number;
    practice_hours: number;
    course_type: string; // A/B/C
    textbook_isbn: string;
    textbook_name: string;
    textbook_image: string;
    textbook_publisher?: string;
    textbook_link?: string;
    course_catalog?: string;
    parent_course_id?: number;
    is_template: boolean;
    created_at: string;
    updated_at: string;
}

export interface CourseDocument {
    id: number;
    course_id: number;
    doc_type: string; // standard/plan/info/lesson/courseware
    title: string;
    content?: string;
    file_url?: string;
    lesson_number?: number;
    file_exists?: boolean;
    created_at: string;
    updated_at: string;
}

export interface CourseWithDocuments {
    course: Course;
    documents: CourseDocument[];
}

export interface CourseCreateParams {
    name: string;
    semester?: string; // 如果不提供，后端自动计算
    class_name: string;
    total_hours: number;
    practice_hours: number;
    course_type: string;
    textbook_isbn: string;
    textbook_name: string;
    textbook_image: string;
    textbook_publisher?: string;
    textbook_link?: string;
    course_catalog?: string;
}

export interface CourseUpdateParams {
    name?: string;
    semester?: string;
    class_name?: string;
    total_hours?: number;
    practice_hours?: number;
    course_type?: string;
    textbook_isbn?: string;
    textbook_name?: string;
    textbook_image?: string;
    textbook_publisher?: string;
    textbook_link?: string;
    course_catalog?: string;
}

// API 调用函数

/** 获取课程列表 */
export async function getCourses() {
    return get<Course[]>('/api/courses');
}

/** 获取课程详情（含文档） */
export async function getCourseDetail(courseId: number) {
    return get<CourseWithDocuments>(`/api/courses/${courseId}`);
}

/** 创建课程 */
export async function createCourse(params: CourseCreateParams) {
    return post<Course>('/api/courses', params);
}

/** 更新课程 */
export async function updateCourse(courseId: number, params: CourseUpdateParams) {
    return put<Course>(`/api/courses/${courseId}`, params);
}

/** 删除课程 */
export async function deleteCourse(courseId: number) {
    return del<{ message: string }>(`/api/courses/${courseId}`);
}
