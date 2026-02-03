/**
 * 单份文档管理组件 - 课程标准、授课计划
 */
import { ProList } from '@ant-design/pro-components';
import { Button, message, Space, Tag } from 'antd';
import { CloudUploadOutlined, RobotOutlined, EditOutlined, DownloadOutlined } from '@ant-design/icons';
import { useIntl, useNavigate } from '@umijs/max';
import { useEffect, useState } from 'react';
import { getDocuments, downloadDocument, type CourseDocument } from '@/services/document';

interface SingleDocumentsProps {
    courseId: number;
}

const docTypes = ['standard', 'plan'];

const SingleDocuments: React.FC<SingleDocumentsProps> = ({ courseId }) => {
    const intl = useIntl();
    const navigate = useNavigate();
    const [documents, setDocuments] = useState<CourseDocument[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        loadDocuments();
    }, [courseId]);

    const loadDocuments = async () => {
        setLoading(true);
        try {
            const data = await getDocuments(courseId);
            // 过滤出单份文档
            const singleDocs = data.filter(doc => docTypes.includes(doc.doc_type));
            setDocuments(singleDocs);
        } catch (error) {
            message.error('加载文档列表失败');
        } finally {
            setLoading(false);
        }
    };

    const handleDownload = async (doc: CourseDocument) => {
        try {
            await downloadDocument(doc.id);
            message.success('下载成功');
        } catch (error) {
            message.error('下载失败');
        }
    };

    const handleGenerate = (docType: string) => {
        if (docType === 'plan') {
            // 跳转到授课计划生成页面
            navigate(`/courses/${courseId}/teaching-plan/generate`);
        } else {
            message.info('AI 生成功能开发中');
        }
    };

    const getDocName = (docType: string) => {
        return intl.formatMessage({ id: `pages.courses.documents.${docType}` });
    };

    const getDocData = (docType: string) => {
        return documents.find(doc => doc.doc_type === docType);
    };

    return (
        <ProList<{ docType: string }>
            loading={loading}
            dataSource={docTypes.map(type => ({ docType: type }))}
            metas={{
                title: {
                    render: (_, record) => getDocName(record.docType),
                },
                description: {
                    render: (_, record) => {
                        const doc = getDocData(record.docType);
                        return doc ? (
                            <Space>
                                <Tag color="success">{intl.formatMessage({ id: 'pages.courses.documents.generated' })}</Tag>
                                <span>{doc.title}</span>
                            </Space>
                        ) : (
                            <Tag>{intl.formatMessage({ id: 'pages.courses.documents.notGenerated' })}</Tag>
                        );
                    },
                },
                actions: {
                    render: (_, record) => {
                        const doc = getDocData(record.docType);
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
                                onClick={() => message.info('上传功能开发中')}
                            >
                                {intl.formatMessage({ id: 'pages.courses.documents.upload' })}
                            </Button>,
                            doc && (
                                <Button
                                    key="edit"
                                    type="link"
                                    icon={<EditOutlined />}
                                    onClick={() => message.info('编辑功能开发中')}
                                >
                                    {intl.formatMessage({ id: 'pages.courses.documents.edit' })}
                                </Button>
                            ),
                            doc && doc.file_url && (
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
    );
};

export default SingleDocuments;
