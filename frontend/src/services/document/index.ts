/**
 * 文档管理 API 服务
 */
import { get, post, put, del } from '@/utils/request';

export interface CourseDocument {
    id: number;
    course_id: number;
    doc_type: string;
    title: string;
    content?: string;
    file_url?: string;
    lesson_number?: number;
    file_exists?: boolean;
    created_at: string;
    updated_at: string;
}

export interface DocumentCreateParams {
    doc_type: string;
    title: string;
    content?: string;
    file_url?: string;
    lesson_number?: number;
}

export interface DocumentUpdateParams {
    title?: string;
    content?: string;
    file_url?: string;
    lesson_number?: number;
}

export interface DocumentUploadParams {
    doc_type: string;
    title: string;
    lesson_number?: number;
    file: File;
}

// API 调用函数

/** 创建文档 */
export async function createDocument(courseId: number, params: DocumentCreateParams) {
    return post<CourseDocument>(`/api/courses/${courseId}/documents`, params);
}

/** 上传文档文件 */
export async function uploadDocument(courseId: number, params: DocumentUploadParams) {
    const formData = new FormData();
    formData.append('file', params.file);
    formData.append('doc_type', params.doc_type);
    formData.append('title', params.title);
    if (params.lesson_number !== undefined) {
        formData.append('lesson_number', params.lesson_number.toString());
    }

    return post<{ message: string; document: CourseDocument }>(
        `/api/courses/${courseId}/documents/upload`,
        formData
    );
}

/** 获取课程的所有文档 */
export async function getDocuments(courseId: number) {
    return get<CourseDocument[]>(`/api/courses/${courseId}/documents`);
}

/** 按类型获取文档 */
export async function getDocumentsByType(courseId: number, docType: string) {
    return get<CourseDocument[]>(`/api/courses/${courseId}/documents/type/${docType}`);
}

/** 获取单个文档详情 */
export async function getDocumentDetail(documentId: number) {
    return get<CourseDocument>(`/api/documents/${documentId}`);
}

/** 更新文档 */
export async function updateDocument(documentId: number, params: DocumentUpdateParams) {
    return put<CourseDocument>(`/api/documents/${documentId}`, params);
}

/** 删除文档 */
export async function deleteDocument(documentId: number) {
    return del<{ message: string }>(`/api/documents/${documentId}`);
}

/** 下载文档 */
export async function downloadDocument(documentId: number) {
    window.open(`/api/documents/${documentId}/download`, '_blank');
}

/** 获取文档下载URL */
export function getDownloadUrl(courseId: number, filename: string): string {
    return `/api/documents/files/${courseId}/${filename}`;
}
