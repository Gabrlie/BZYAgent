export const formatBackendTime = (value?: string, locale: string = 'zh-CN'): string => {
    if (!value) {
        return '-';
    }
    let text = value.trim();
    if (!text) {
        return '-';
    }
    if (!text.includes('T') && text.includes(' ')) {
        text = text.replace(' ', 'T');
    }
    const hasTimezone = /Z$|[+-]\d{2}:?\d{2}$/.test(text);
    const normalized = hasTimezone ? text : `${text}Z`;
    const date = new Date(normalized);
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    return date.toLocaleString(locale);
};
