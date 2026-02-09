import { request } from '@umijs/max';

const resolveSseBaseUrl = () => {
    if (typeof window === 'undefined') {
        return '';
    }
    const { protocol, hostname, port } = window.location;
    const backendPort = '8000';
    if ((hostname === 'localhost' || hostname === '127.0.0.1') && port !== backendPort) {
        return `${protocol}//${hostname}:${backendPort}`;
    }
    return '';
};

/**
 * 生成授课计划（流式，带进度）
 */
export async function generateTeachingPlanStream(
    courseId: number,
    params: {
        teacher_name: string;
        total_weeks: number;
        hour_per_class: number;
        classes_per_week: number;
        final_review: boolean;
        first_week_classes: number;
        skip_slots: Array<{ week: number; class: number }>;
    },
    onProgress: (data: any) => void,
): Promise<void> {
    const queryParams = new URLSearchParams({
        teacher_name: params.teacher_name,
        total_weeks: String(params.total_weeks),
        hour_per_class: String(params.hour_per_class),
        classes_per_week: String(params.classes_per_week),
        final_review: String(params.final_review),
        first_week_classes: String(params.first_week_classes),
    });
    if (params.skip_slots && params.skip_slots.length > 0) {
        queryParams.append('skip_slots', JSON.stringify(params.skip_slots));
    }

    // 添加 token 到 URL（EventSource 不支持自定义 headers）
    const token = localStorage.getItem('token');
    if (token) {
        queryParams.append('token', token);
    }

    const baseUrl = resolveSseBaseUrl();
    const url = `${baseUrl}/api/courses/${courseId}/generate-teaching-plan/stream?${queryParams}`;

    const eventSource = new EventSource(url, {
        withCredentials: true,
    });

    return new Promise((resolve, reject) => {
        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                onProgress(data);

                if (data.stage === 'completed' || data.stage === 'error') {
                    eventSource.close();
                    if (data.stage === 'error') {
                        reject(new Error(data.message));
                    } else {
                        resolve();
                    }
                }
            } catch (error) {
                console.error('解析 SSE 数据失败:', error);
                eventSource.close();
                reject(error);
            }
        };

        eventSource.onerror = (error) => {
            console.error('SSE 连接错误:', error);
            eventSource.close();
            reject(error);
        };
    });
}

/**
 * 获取课程的授课计划列表
 */
export async function getTeachingPlans(courseId: number) {
    return request(`/api/courses/${courseId}/teaching-plans`, {
        method: 'GET',
    });
}
