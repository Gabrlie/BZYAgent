/**
 * 多份文档管理组件 - 教案、课件
 */
import { ProTable } from '@ant-design/pro-components';
import { Button, message, Modal } from 'antd';
import { EditOutlined, DeleteOutlined, DownloadOutlined } from '@ant-design/icons';
import { useIntl } from '@umijs/max';
import { useEffect, useMemo, useState } from 'react';
import { getDocumentsByType, deleteDocument, downloadDocument, type CourseDocument } from '@/services/document';

interface MultiDocumentsProps {
    courseId: number;
    docType: 'lesson' | 'courseware';
    refreshKey?: number;
    size?: 'large' | 'middle' | 'small';
    visibleColumns?: Record<string, boolean>;
}

const MultiDocuments: React.FC<MultiDocumentsProps> = ({
    courseId,
    docType,
    refreshKey,
    size = 'middle',
    visibleColumns,
}) => {
    const intl = useIntl();
    const [documents, setDocuments] = useState<CourseDocument[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        loadDocuments();
    }, [courseId, docType, refreshKey]);

    const columns = useMemo(() => {
        const baseColumns = [
            {
                key: 'lesson_number',
                title: intl.formatMessage({ id: 'pages.courses.documents.lessonNumber' }),
                dataIndex: 'lesson_number',
                width: 100,
                sorter: (a: CourseDocument, b: CourseDocument) =>
                    (a.lesson_number || 0) - (b.lesson_number || 0),
            },
            {
                key: 'title',
                title: intl.formatMessage({ id: 'pages.courses.documents.title' }),
                dataIndex: 'title',
                ellipsis: true,
            },
            {
                key: 'created_at',
                title: intl.formatMessage({ id: 'pages.courses.documents.createdAt' }),
                dataIndex: 'created_at',
                valueType: 'dateTime' as const,
                width: 180,
            },
            {
                key: 'actions',
                title: intl.formatMessage({ id: 'pages.courses.documents.actions' }),
                valueType: 'option' as const,
                width: 200,
                render: (_: any, record: CourseDocument) => [
                    <Button
                        key="edit"
                        type="link"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => message.info('编辑功能开发中')}
                    >
                        {intl.formatMessage({ id: 'pages.courses.documents.edit' })}
                    </Button>,
                    record.file_url && (
                        <Button
                            key="download"
                            type="link"
                            size="small"
                            icon={<DownloadOutlined />}
                            onClick={() => handleDownload(record)}
                        >
                            {intl.formatMessage({ id: 'pages.courses.documents.download' })}
                        </Button>
                    ),
                    <Button
                        key="delete"
                        type="link"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={() => handleDelete(record)}
                    >
                        {intl.formatMessage({ id: 'pages.courses.documents.delete' })}
                    </Button>,
                ].filter(Boolean),
            },
        ];

        if (!visibleColumns) {
            return baseColumns;
        }

        return baseColumns.filter((col) => visibleColumns[col.key as string] !== false);
    }, [intl, visibleColumns]);

    const loadDocuments = async () => {
        setLoading(true);
        try {
            const data = await getDocumentsByType(courseId, docType);
            setDocuments(data);
        } catch (error) {
            message.error('加载文档列表失败');
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = (doc: CourseDocument) => {
        Modal.confirm({
            title: intl.formatMessage({ id: 'pages.courses.documents.deleteConfirm' }),
            content: doc.title,
            okText: '确定',
            cancelText: '取消',
            okType: 'danger',
            onOk: async () => {
                try {
                    await deleteDocument(doc.id);
                    message.success('删除成功');
                    loadDocuments();
                } catch (error) {
                    message.error('删除失败');
                }
            },
        });
    };

    const handleDownload = async (doc: CourseDocument) => {
        try {
            await downloadDocument(doc.id);
            message.success('下载成功');
        } catch (error) {
            message.error('下载失败');
        }
    };

    return (
        <ProTable<CourseDocument>
            columns={columns}
            dataSource={documents}
            loading={loading}
            search={false}
            options={false}
            pagination={{
                defaultPageSize: 10,
                showSizeChanger: true,
            }}
            toolBarRender={false}
            size={size}
            rowKey="id"
        />
    );
};

export default MultiDocuments;
