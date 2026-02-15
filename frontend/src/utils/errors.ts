export const getErrorText = (error: any): string => {
    if (!error) {
        return '';
    }
    const parts: string[] = [];
    if (error?.response?.data) {
        const { detail, message } = error.response.data;
        if (detail) {
            parts.push(String(detail));
        }
        if (message) {
            parts.push(String(message));
        }
    }
    if (error?.message) {
        parts.push(String(error.message));
    }
    return parts.join(' ').trim();
};

export const isRateLimitError = (error: any): boolean => {
    const text = getErrorText(error).toLowerCase();
    if (!text) {
        return false;
    }
    return (
        text.includes('rate limit') ||
        text.includes('too many requests') ||
        text.includes('429') ||
        text.includes('限流')
    );
};
