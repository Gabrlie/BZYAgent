import React, { useState, useEffect } from 'react';
import { PageContainer } from '@ant-design/pro-components';
import { Card, Button, Form, InputNumber, message, Space, Alert, Spin, Modal } from 'antd';
import { useParams, history, useSearchParams } from '@umijs/max';
import GenerationProgressDisplay, {
    GenerationProgress,
} from '@/components/GenerationProgress';
import { generateLessonPlanStream } from '@/services/lesson-plan';
import { getDocumentsByType, downloadDocument } from '@/services/document';

/**
 * 教案生成页面
 */
const LessonPlanGenerate: React.FC = () => {
    const { id: courseId } = useParams<{ id: string }>();
    const [searchParams] = useSearchParams();
    const [form] = Form.useForm();
    const [generating, setGenerating] = useState(false);
    const [progress, setProgress] = useState<GenerationProgress | null>(null);
    const [documentId, setDocumentId] = useState<number | null>(null);
    const [loadingPlan, setLoadingPlan] = useState(true);
    const [teachingPlan, setTeachingPlan] = useState<any>(null);

    useEffect(() => {
        checkTeachingPlan();
    }, [courseId]);

    useEffect(() => {
        const sequenceParam = searchParams.get('sequence');
        if (sequenceParam) {
            const sequenceValue = Number(sequenceParam);
            if (!Number.isNaN(sequenceValue)) {
                form.setFieldsValue({ sequence: sequenceValue });
            }
        }
    }, [form, searchParams]);

    const checkTeachingPlan = async () => {
        setLoadingPlan(true);
        try {
            // 获取授课计划文档
            const documents = await getDocumentsByType(Number(courseId), 'plan');

            if (documents && documents.length > 0) {
                // 取第一个授课计划
                setTeachingPlan(documents[0]);
            } else {
                setTeachingPlan(null);
            }
        } catch (error) {
            message.error('检查授课计划失败');
        } finally {
            setLoadingPlan(false);
        }
    };

    const confirmOverwrite = async (sequence: number): Promise<boolean> => {
        try {
            const docs = await getDocumentsByType(Number(courseId), 'lesson');
            const existing = docs.find((doc) => doc.lesson_number === sequence);
            if (!existing) {
                return true;
            }

            return await new Promise((resolve) => {
                const missingFile = existing.file_exists === false;
                Modal.confirm({
                    title: `第 ${sequence} 次课教案已存在`,
                    content: missingFile
                        ? '该教案文件不存在，将重新生成并覆盖记录，是否继续？'
                        : '是否覆盖该教案？',
                    okText: '覆盖',
                    cancelText: '取消',
                    onOk: () => resolve(true),
                    onCancel: () => resolve(false),
                });
            });
        } catch (error) {
            message.error('检查已有教案失败');
            return false;
        }
    };

    const handleGenerate = async () => {
        if (!teachingPlan) {
            message.error('请先创建授课计划');
            return;
        }

        try {
            const values = await form.validateFields();
            const canProceed = await confirmOverwrite(values.sequence);
            if (!canProceed) {
                return;
            }
            setGenerating(true);
            setProgress({
                stage: 'preparing',
                progress: 0,
                message: '正在建立连接...',
            });
            setDocumentId(null);

            await generateLessonPlanStream(
                Number(courseId),
                values.sequence,
                (progressData: GenerationProgress) => {
                    setProgress(progressData);

                    if (progressData.stage === 'completed') {
                        message.success('教案生成成功！');
                        setDocumentId(progressData.document_id || null);
                        setGenerating(false);
                        window.dispatchEvent(
                            new CustomEvent('bzyagent:documents-refresh', {
                                detail: { courseId: Number(courseId), docType: 'lesson' },
                            })
                        );
                    }
                },
            );
        } catch (error) {
            message.error('生成失败：' + (error as Error).message);
            setGenerating(false);
        }
    };

    const handleViewDocument = () => {
        if (documentId) {
            // 跳转到预览页面（后续实现）
            history.push(`/course/${courseId}/lesson-plan/${documentId}`);
        }
    };

    if (loadingPlan) {
        return (
            <PageContainer title="生成教案">
                <Card>
                    <div style={{ textAlign: 'center', padding: '40px 0' }}>
                        <Spin size="large" />
                        <div style={{ marginTop: 16 }}>正在检查授课计划...</div>
                    </div>
                </Card>
            </PageContainer>
        );
    }

    return (
        <PageContainer
            title="生成教案"
            extra={
                <Button onClick={() => history.push(`/courses/${courseId}`)}>返回课程</Button>
            }
        >
            <Space direction="vertical" style={{ width: '100%' }} size="large">
                {/* 授课计划状态检查 */}
                {!teachingPlan ? (
                    <Alert
                        message="缺少授课计划"
                        description={
                            <div>
                                <p>生成教案需要先创建授课计划文档。</p>
                                <Button
                                    type="primary"
                                    onClick={() => history.push(`/courses/${courseId}`)}
                                    style={{ marginTop: 8 }}
                                >
                                    返回课程页面创建授课计划
                                </Button>
                            </div>
                        }
                        type="warning"
                        showIcon
                    />
                ) : (
                    <Alert
                        message="已找到授课计划"
                        description={`将使用"${teachingPlan.title}"生成教案`}
                        type="success"
                        showIcon
                    />
                )}

                {/* 输入表单 */}
                {/* 输入表单 / 进度显示 */}
                {teachingPlan && !progress && (
                    <Card title="基础信息">
                        <Form
                            form={form}
                            layout="vertical"
                            initialValues={{
                                sequence: 1,
                            }}
                        >
                            <Form.Item
                                label="授课顺序"
                                name="sequence"
                                rules={[{ required: true, message: '请输入授课顺序' }]}
                                tooltip="请输入第几次课，例如：第1次课输入1，第2次课输入2"
                            >
                                <InputNumber
                                    min={1}
                                    max={100}
                                    placeholder="请输入授课顺序（如：1、2、3）"
                                    style={{ width: 200 }}
                                />
                            </Form.Item>

                            <Form.Item>
                                <Button
                                    type="primary"
                                    size="large"
                                    onClick={handleGenerate}
                                    loading={generating}
                                    disabled={generating}
                                >
                                    {generating ? '生成中...' : '开始生成教案'}
                                </Button>
                            </Form.Item>
                        </Form>
                    </Card>
                )}
                {progress && <GenerationProgressDisplay progress={progress} />}

                {/* 操作按钮 */}
                {documentId && (
                    <Card>
                        <Space>
                            <Button type="primary" onClick={handleViewDocument}>
                                查看/编辑教案
                            </Button>
                            <Button onClick={() => downloadDocument(documentId)}>
                                下载 Word 文档
                            </Button>
                        </Space>
                    </Card>
                )}
            </Space>
        </PageContainer>
    );
};

export default LessonPlanGenerate;
