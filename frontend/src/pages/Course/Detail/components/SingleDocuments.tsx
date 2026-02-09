/**
 * 单份文档管理组件 - 课程标准、授课计划
 */
import { ProList } from '@ant-design/pro-components';
import { Button, message, Space, Tag, Modal, Upload } from 'antd';
import type { UploadFile } from 'antd/es/upload/interface';
import {
    CloudUploadOutlined,
    RobotOutlined,
    EditOutlined,
    DownloadOutlined,
} from '@ant-design/icons';
import { useIntl, useNavigate } from '@umijs/max';
import { useEffect, useState } from 'react';
import {
    getDocuments,
    downloadDocument,
    uploadDocument,
    type CourseDocument,
} from '@/services/document';

interface SingleDocumentsProps {
    courseId: number;
}

const docTypes = ['standard', 'plan'] as const;

type DocType = (typeof docTypes)[number];

const SingleDocuments: React.FC<SingleDocumentsProps> = ({ courseId }) => {
    const intl = useIntl();
    const navigate = useNavigate();
    const [documents, setDocuments] = useState<CourseDocument[]>([]);
    const [loading, setLoading] = useState(false);
    const [uploadOpen, setUploadOpen] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [uploadFileList, setUploadFileList] = useState<UploadFile[]>([]);
    const [uploadDocType, setUploadDocType] = useState<DocType>('plan');

    useEffect(() => {
        loadDocuments();
    }, [courseId]);

    useEffect(() => {
        const handleRefresh = (event: Event) => {
            const detail = (event as CustomEvent<{ courseId?: number; docType?: string }>).detail;
            if (detail?.courseId && detail.courseId !== courseId) {
                return;
            }
            loadDocuments();
        };

        window.addEventListener('bzyagent:documents-refresh', handleRefresh as EventListener);
        return () => {
            window.removeEventListener('bzyagent:documents-refresh', handleRefresh as EventListener);
        };
    }, [courseId]);

    const loadDocuments = async () => {
        setLoading(true);
        try {
            const data = await getDocuments(courseId);
            // 过滤出单份文档
            const singleDocs = data.filter(doc => docTypes.includes(doc.doc_type as DocType));
            setDocuments(singleDocs);
        } catch (error) {
            message.error('加载文档列表失败');
        } finally {
            setLoading(false);
        }
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

    const handleGenerate = (docType: DocType) => {
        if (docType === 'plan') {
            // 跳转到授课计划生成页面
            navigate(`/courses/${courseId}/teaching-plan/generate`);
        } else {
            message.info('AI 生成功能开发中');
        }
    };

    const getDocName = (docType: DocType) => {
        return intl.formatMessage({ id: `pages.courses.documents.${docType}` });
    };

    const getDocData = (docType: DocType) => {
        return documents.find(doc => doc.doc_type === docType);
    };

    const openUpload = (docType: DocType) => {
        setUploadDocType(docType);
        setUploadFileList([]);
        setUploadOpen(true);
    };

    const handleUpload = async () => {
        const file = uploadFileList[0]?.originFileObj as File | undefined;
        if (!file) {
            message.error('请选择要上传的文件');
            return;
        }

        const existingDoc = getDocData(uploadDocType);
        const doUpload = async () => {
            setUploading(true);
            try {
                const title = existingDoc?.title || getDocName(uploadDocType);
                await uploadDocument(courseId, {
                    doc_type: uploadDocType,
                    title,
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
            Modal.confirm({
                title: `${getDocName(uploadDocType)}已存在`,
                content: '是否覆盖该文档？',
                okText: '覆盖',
                cancelText: '取消',
                onOk: doUpload,
            });
            return;
        }

        await doUpload();
    };

    return (
        <>
            <ProList<{ docType: DocType }>
                loading={loading}
                dataSource={docTypes.map(type => ({ docType: type }))}
                metas={{
                    title: {
                        render: (_, record) => getDocName(record.docType),
                    },
                    description: {
                        render: (_, record) => {
                            const doc = getDocData(record.docType);
                            if (!doc) {
                                return <Tag>{intl.formatMessage({ id: 'pages.courses.documents.notGenerated' })}</Tag>;
                            }
                            if (doc.file_exists === false) {
                                return (
                                    <Space>
                                        <Tag color="warning">文件不存在</Tag>
                                        <span>{doc.title}</span>
                                    </Space>
                                );
                            }
                            return (
                                <Space>
                                    <Tag color="success">
                                        {intl.formatMessage({ id: 'pages.courses.documents.generated' })}
                                    </Tag>
                                    <span>{doc.title}</span>
                                </Space>
                            );
                        },
                    },
                    actions: {
                        render: (_, record) => {
                            const doc = getDocData(record.docType);
                            const isMissingFile = doc?.file_exists === false;
                            const canDownload = doc && doc.file_url && !isMissingFile;
                            return [
                                <Button
                                    key="ai"
                                    type="link"
                                    icon={<RobotOutlined />}
                                    onClick={() => handleGenerate(record.docType)}
                                >
                                    {intl.formatMessage({ id: 'pages.courses.documents.generate' })}
                                </Button>,
                                <Button
                                    key="upload"
                                    type="link"
                                    icon={<CloudUploadOutlined />}
                                    onClick={() => openUpload(record.docType)}
                                >
                                    {intl.formatMessage({ id: 'pages.courses.documents.upload' })}
                                </Button>,
                                doc && !isMissingFile && (
                                    <Button
                                        key="edit"
                                        type="link"
                                        icon={<EditOutlined />}
                                        onClick={() => message.info('编辑功能开发中')}
                                    >
                                        {intl.formatMessage({ id: 'pages.courses.documents.edit' })}
                                    </Button>
                                ),
                                canDownload && (
                                    <Button
                                        key="download"
                                        type="link"
                                        icon={<DownloadOutlined />}
                                        onClick={() => handleDownload(doc)}
                                    >
                                        {intl.formatMessage({ id: 'pages.courses.documents.download' })}
                                    </Button>
                                ),
                            ].filter(Boolean);
                        },
                    },
                }}
            />

            <Modal
                title={`上传${getDocName(uploadDocType)}`}
                open={uploadOpen}
                onOk={handleUpload}
                confirmLoading={uploading}
                onCancel={() => setUploadOpen(false)}
                okText="上传"
                cancelText="取消"
                destroyOnClose
            >
                <Upload
                    fileList={uploadFileList}
                    beforeUpload={() => false}
                    maxCount={1}
                    accept=".docx,.pdf,.pptx,.md"
                    onChange={({ fileList }) => setUploadFileList(fileList.slice(-1))}
                >
                    <Button icon={<CloudUploadOutlined />}>选择文件</Button>
                </Upload>
            </Modal>
        </>
    );
};

export default SingleDocuments;
