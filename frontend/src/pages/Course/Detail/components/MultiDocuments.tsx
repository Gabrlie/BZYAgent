/**
 * 多份文档管理组件 - 教案、课件
 */
import { ProTable } from '@ant-design/pro-components';
import { Button, message, Modal, Tag, Upload, Form, InputNumber, Alert, Space } from 'antd';
import type { UploadFile } from 'antd/es/upload/interface';
import {
    EditOutlined,
    DeleteOutlined,
    DownloadOutlined,
    CloudUploadOutlined,
    ReloadOutlined,
} from '@ant-design/icons';
import { useIntl, useNavigate } from '@umijs/max';
import { useEffect, useMemo, useState } from 'react';
import {
    getDocumentsByType,
    deleteDocument,
    downloadDocument,
    uploadDocument,
    type CourseDocument,
} from '@/services/document';

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
    const navigate = useNavigate();
    const [documents, setDocuments] = useState<CourseDocument[]>([]);
    const [loading, setLoading] = useState(false);
    const [uploadOpen, setUploadOpen] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [uploadFileList, setUploadFileList] = useState<UploadFile[]>([]);
    const [uploadForm] = Form.useForm();

    useEffect(() => {
        loadDocuments();
    }, [courseId, docType, refreshKey]);

    useEffect(() => {
        const handleRefresh = (event: Event) => {
            const detail = (event as CustomEvent<{ courseId?: number; docType?: string }>).detail;
            if (!detail) {
                return;
            }
            if (detail.courseId && detail.courseId !== courseId) {
                return;
            }
            if (detail.docType && detail.docType !== docType) {
                return;
            }
            loadDocuments();
        };

        window.addEventListener('bzyagent:documents-refresh', handleRefresh as EventListener);
        return () => {
            window.removeEventListener('bzyagent:documents-refresh', handleRefresh as EventListener);
        };
    }, [courseId, docType]);

    useEffect(() => {
        const handleUpload = (event: Event) => {
            const detail = (event as CustomEvent<{ courseId?: number; docType?: string; lessonNumber?: number }>).detail;
            if (!detail) {
                return;
            }
            if (detail.courseId && detail.courseId !== courseId) {
                return;
            }
            if (detail.docType && detail.docType !== docType) {
                return;
            }
            openUpload(detail.lessonNumber);
        };

        window.addEventListener('bzyagent:documents-upload', handleUpload as EventListener);
        return () => {
            window.removeEventListener('bzyagent:documents-upload', handleUpload as EventListener);
        };
    }, [courseId, docType]);

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
                key: 'status',
                title: '状态',
                dataIndex: 'file_exists',
                width: 120,
                render: (_: unknown, record: CourseDocument) => {
                    if (!record.file_url) {
                        return <Tag>未生成</Tag>;
                    }
                    if (record.file_exists === false) {
                        return <Tag color="warning">文件不存在</Tag>;
                    }
                    if (!record.content) {
                        return (
                            <Space>
                                <Tag color="processing">已上传</Tag>
                                <span>上传文档无法使用AI生成与编辑功能</span>
                            </Space>
                        );
                    }
                    return <Tag color="success">已生成</Tag>;
                },
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
                width: 220,
                render: (_: any, record: CourseDocument) => {
                    const isMissingFile = record.file_exists === false;
                    const isUploaded = Boolean(record.file_url && !record.content);
                    const canDownload = record.file_url && !isMissingFile;

                    if (isMissingFile) {
                        return [
                            docType === 'lesson' && (
                                <Button
                                    key="regenerate"
                                    type="link"
                                    size="small"
                                    icon={<ReloadOutlined />}
                                    onClick={() =>
                                        navigate(
                                            `/courses/${courseId}/lesson-plan/generate?sequence=${record.lesson_number ?? ''}`,
                                        )
                                    }
                                >
                                    重新生成
                                </Button>
                            ),
                            <Button
                                key="upload"
                                type="link"
                                size="small"
                                icon={<CloudUploadOutlined />}
                                onClick={() => openUpload(record.lesson_number)}
                            >
                                上传
                            </Button>,
                        ].filter(Boolean);
                    }

                    return [
                        <Button
                            key="edit"
                            type="link"
                            size="small"
                            icon={<EditOutlined />}
                            onClick={() => {
                                if (docType === 'lesson') {
                                    navigate(`/courses/${courseId}/lesson-plan/${record.id}`);
                                    return;
                                }
                                message.info('编辑功能开发中');
                            }}
                            disabled={isUploaded}
                        >
                            {intl.formatMessage({ id: 'pages.courses.documents.edit' })}
                        </Button>,
                        canDownload && (
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
                    ].filter(Boolean);
                },
            },
        ];

        if (!visibleColumns) {
            return baseColumns;
        }

        return baseColumns.filter((col) => visibleColumns[col.key as string] !== false);
    }, [courseId, docType, intl, navigate, visibleColumns]);

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

    const openUpload = (lessonNumber?: number) => {
        setUploadOpen(true);
        uploadForm.resetFields();
        setUploadFileList([]);
        if (lessonNumber !== undefined) {
            uploadForm.setFieldsValue({ lesson_number: lessonNumber });
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
        if (doc.file_exists === false) {
            message.warning('文件不存在，请重新生成或上传');
            return;
        }
        try {
            await downloadDocument(doc.id);
            message.success('下载成功');
        } catch (error) {
            message.error('下载失败');
        }
    };

    const handleUpload = async () => {
        try {
            const values = await uploadForm.validateFields();
            const file = uploadFileList[0]?.originFileObj as File | undefined;
            if (!file) {
                message.error('请选择要上传的文件');
                return;
            }

            const lessonNumber = values.lesson_number as number | undefined;
            const existingDoc = documents.find((doc) => doc.lesson_number === lessonNumber);

            const doUpload = async () => {
                setUploading(true);
                try {
                await uploadDocument(courseId, {
                    doc_type: docType,
                    title: docType === 'lesson' ? '教案' : '课件',
                    lesson_number: lessonNumber,
                    file,
                });
                    message.success('上传成功');
                    setUploadOpen(false);
                    loadDocuments();
                } catch (error) {
                    message.error('上传失败');
                } finally {
                    setUploading(false);
                }
            };

            if (existingDoc) {
                const docLabel = docType === 'lesson' ? '教案' : '课件';
                Modal.confirm({
                    title: `第 ${lessonNumber} 次课${docLabel}已存在`,
                    content: `是否覆盖该${docLabel}？`,
                    okText: '覆盖',
                    cancelText: '取消',
                    onOk: doUpload,
                });
                return;
            }

            await doUpload();
        } catch (error) {
            // 表单校验失败或其他错误
        }
    };

    return (
        <>
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

            <Modal
                title={docType === 'lesson' ? '上传教案' : '上传课件'}
                open={uploadOpen}
                onOk={handleUpload}
                confirmLoading={uploading}
                onCancel={() => setUploadOpen(false)}
                okText="上传"
                cancelText="取消"
                destroyOnClose
            >
                <Form form={uploadForm} layout="vertical">
                    <Alert
                        message="上传文档仅用于下载与查看，无法使用AI生成与编辑功能"
                        type="warning"
                        showIcon
                        style={{ marginBottom: 12 }}
                    />
                    <Form.Item
                        label="授课顺序"
                        name="lesson_number"
                        rules={[{ required: true, message: '请输入授课顺序' }]}
                        tooltip="请输入第几次课，例如：第1次课输入1"
                    >
                        <InputNumber min={1} max={100} style={{ width: '100%' }} />
                    </Form.Item>

                    <Form.Item label="选择文件" required>
                        <Upload
                            fileList={uploadFileList}
                            beforeUpload={() => false}
                            maxCount={1}
                            accept=".doc,.docx"
                            onChange={({ fileList }) => setUploadFileList(fileList.slice(-1))}
                        >
                            <Button icon={<CloudUploadOutlined />}>选择文件</Button>
                        </Upload>
                    </Form.Item>
                </Form>
            </Modal>
        </>
    );
};

export default MultiDocuments;
