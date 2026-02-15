/**
 * 软著材料 API 服务
 */
import { get, post, put } from '@/utils/request';
import { request } from '@umijs/max';

export interface CopyrightJob {
    id: number;
    project_id: number;
    status: 'queued' | 'running' | 'completed' | 'failed';
    stage?: string;
    message?: string;
    progress?: number;
    error?: string;
    output_zip_path?: string;
    created_at: string;
    updated_at: string;
}

export interface CopyrightProject {
    id: number;
    user_id: number;
    name: string;
    domain?: string;
    system_name?: string;
    software_abbr?: string;
    description?: string;
    output_type: string;
    generation_mode: 'fast' | 'full';
    include_sourcecode: boolean;
    include_ui_desc: boolean;
    include_tech_desc: boolean;
    requirements_text?: string;
    ui_description?: string;
    tech_description?: string;
    created_at: string;
    updated_at: string;
    latest_job?: CopyrightJob;
}

export interface CopyrightProjectCreateParams {
    name: string;
    domain?: string;
    system_name?: string;
    software_abbr?: string;
    description?: string;
    output_type?: string;
    generation_mode?: 'fast' | 'full';
    include_sourcecode?: boolean;
    include_ui_desc?: boolean;
    include_tech_desc?: boolean;
    requirements_text?: string;
    ui_description?: string;
    tech_description?: string;
}

export interface CopyrightProjectUpdateParams {
    name?: string;
    domain?: string;
    system_name?: string;
    software_abbr?: string;
    description?: string;
    output_type?: string;
    generation_mode?: 'fast' | 'full';
    include_sourcecode?: boolean;
    include_ui_desc?: boolean;
    include_tech_desc?: boolean;
    requirements_text?: string;
    ui_description?: string;
    tech_description?: string;
}

export async function getCopyrightProjects() {
    return get<{ projects: CopyrightProject[] }>('/api/copyright/projects');
}

export async function getCopyrightProjectDetail(projectId: number) {
    return get<CopyrightProject>(`/api/copyright/projects/${projectId}`);
}

export async function createCopyrightProject(params: CopyrightProjectCreateParams) {
    return post<CopyrightProject>('/api/copyright/projects', params);
}

export async function updateCopyrightProject(projectId: number, params: CopyrightProjectUpdateParams) {
    return put<CopyrightProject>(`/api/copyright/projects/${projectId}`, params);
}

export async function updateCopyrightRequirements(
    projectId: number,
    params: Partial<CopyrightProjectUpdateParams>,
) {
    return post<CopyrightProject>(`/api/copyright/projects/${projectId}/requirements`, params);
}

export async function getLatestCopyrightJob(projectId: number) {
    return get<CopyrightJob>(`/api/copyright/projects/${projectId}/jobs/latest`);
}

export async function startCopyrightGeneration(projectId: number) {
    return post<CopyrightJob>(`/api/copyright/projects/${projectId}/generate`, {});
}

export async function pollLatestCopyrightJob(
    projectId: number,
    options?: { wait?: number; since?: string },
) {
    return get<CopyrightJob>(`/api/copyright/projects/${projectId}/jobs/latest`, {
        wait: options?.wait,
        since: options?.since,
    }, { showError: false });
}

export function downloadCopyrightZip(projectId: number) {
    const token = localStorage.getItem('token');
    const url = token
        ? `/api/copyright/projects/${projectId}/download?token=${encodeURIComponent(token)}`
        : `/api/copyright/projects/${projectId}/download`;
    window.open(url, '_blank');
}

export async function downloadCopyrightZipViaRequest(projectId: number) {
    return request(`/api/copyright/projects/${projectId}/download`, { method: 'GET' });
}
