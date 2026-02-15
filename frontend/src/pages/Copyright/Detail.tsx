import React, { useEffect, useRef, useState } from 'react';
import { PageContainer } from '@ant-design/pro-components';
import {
    Alert,
    Button,
    Card,
    Form,
    Input,
    Modal,
    Select,
    Space,
    Spin,
    Switch,
    message,
    Typography,
} from 'antd';
import { useParams, useNavigate, useModel } from '@umijs/max';
import GenerationProgressDisplay, { GenerationProgress } from '@/components/GenerationProgress';
import { isRateLimitError } from '@/utils/errors';
import {
    CopyrightProject,
    downloadCopyrightZip,
    getCopyrightProjectDetail,
    pollLatestCopyrightJob,
    startCopyrightGeneration,
    updateCopyrightProject,
} from '@/services/copyright';

const CopyrightDetail: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { initialState } = useModel('@@initialState');
    const aiConfigured =
        Boolean(initialState?.currentUser?.has_api_key) &&
        Boolean(initialState?.currentUser?.ai_base_url);

    const [form] = Form.useForm();
    const [project, setProject] = useState<CopyrightProject | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [progress, setProgress] = useState<GenerationProgress | null>(null);
    const [progressOpen, setProgressOpen] = useState(false);
    const [guideOpen, setGuideOpen] = useState(false);
    const pollingRef = useRef(false);
    const rateLimitShownRef = useRef(false);

    const loadProject = async () => {
        if (!id) return;
        setLoading(true);
        try {
            const data = await getCopyrightProjectDetail(Number(id));
            setProject(data);
            form.setFieldsValue({
                name: data.name,
                domain: data.domain,
                system_name: data.system_name,
                software_abbr: data.software_abbr,
                description: data.description,
                output_type: data.output_type,
                generation_mode: data.generation_mode,
                include_sourcecode: data.include_sourcecode,
                include_ui_desc: data.include_ui_desc,
                include_tech_desc: data.include_tech_desc,
                requirements_text: data.requirements_text,
                ui_description: data.ui_description,
                tech_description: data.tech_description,
            });
        } catch (error) {
            message.error('加载项目失败');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadProject();
    }, [id]);

    useEffect(() => {
        return () => {
            pollingRef.current = false;
        };
    }, []);

    const mapJobToProgress = (job: any): GenerationProgress => {
        const stageMap: Record<string, GenerationProgress['stage']> = {
            queued: 'preparing',
            running: 'generating',
            completed: 'completed',
            failed: 'error',
        };
        const stage =
            (job?.stage as GenerationProgress['stage']) ||
            stageMap[job?.status] ||
            'preparing';
        const progress =
            typeof job?.progress === 'number'
                ? job.progress
                : job?.status === 'completed'
                    ? 100
                    : 0;
        const message = job?.message || job?.error || '正在生成中...';
        return { stage, progress, message };
    };

    const pollJobStatus = async (projectId: number, since?: string) => {
        if (!pollingRef.current) {
            return;
        }
        try {
            const job = await pollLatestCopyrightJob(projectId, { wait: 25, since });
            if (!pollingRef.current) {
                return;
            }
            if (job) {
                setProgress(mapJobToProgress(job));
                if (job.status === 'completed' || job.status === 'failed') {
                    pollingRef.current = false;
                    loadProject();
                    return;
                }
                const nextSince = job.updated_at || since;
                pollJobStatus(projectId, nextSince);
            }
        } catch (error) {
            if (isRateLimitError(error)) {
                pollingRef.current = false;
                if (!rateLimitShownRef.current) {
                    rateLimitShownRef.current = true;
                    setProgress({
                        stage: 'error',
                        progress: 0,
                        message:
                            '已触发接口限流（Rate Limit）。请稍后再试或更换接口提供商，避免同时生成多个任务。',
                    });
                    setProgressOpen(true);
                    Modal.warning({
                        title: '接口限流',
                        content:
                            '当前接口触发限流，请稍后再试或更换接口提供商。建议不要同时生成多个任务。',
                    });
                }
                return;
            }
            if (pollingRef.current) {
                setTimeout(() => pollJobStatus(projectId, since), 3000);
            }
        }
    };

    const handleSave = async () => {
        if (!id) return;
        try {
            const values = await form.validateFields();
            setSaving(true);
            const updated = await updateCopyrightProject(Number(id), values);
            setProject(updated);
            message.success('保存成功');
        } catch (error) {
            message.error('保存失败');
        } finally {
            setSaving(false);
        }
    };

    const handleGenerate = async () => {
        if (!id || !project) return;
        if (!aiConfigured) {
            Modal.info({
                title: '请先配置 AI',
                content: '生成软著材料需要先配置 AI Base URL 与 API Key。',
                okText: '前往配置',
                onOk: () => navigate('/profile'),
            });
            return;
        }
        const values = await form.validateFields();
        const requirements = values.requirements_text;
        if (!requirements || !requirements.trim()) {
            message.error('请先填写需求文档');
            return;
        }
        try {
            const updated = await updateCopyrightProject(Number(id), values);
            setProject(updated);
        } catch (error) {
            message.error('保存配置失败，请重试');
            return;
        }
        setProgress({ stage: 'preparing', progress: 0, message: '正在建立连接...' });
        setProgressOpen(true);
        rateLimitShownRef.current = false;
        try {
            const job = await startCopyrightGeneration(Number(id));
            setProgress(mapJobToProgress(job));
            pollingRef.current = true;
            pollJobStatus(Number(id), job.updated_at);
            message.info('已开始后台生成，可关闭页面稍后查看进度');
        } catch (error: any) {
            message.error(error?.message || '生成失败');
        }
    };

    if (loading || !project) {
        return (
            <PageContainer title="软著项目详情">
                <Card>
                    <div style={{ textAlign: 'center', padding: '40px 0' }}>
                        <Spin size="large" />
                    </div>
                </Card>
            </PageContainer>
        );
    }

    return (
        <PageContainer
            title="软著项目详情"
            extra={
                <Space>
                    <Button onClick={() => setGuideOpen(true)}>使用说明</Button>
                    <Button onClick={() => navigate('/copyright')}>返回列表</Button>
                </Space>
            }
        >
            <Space direction="vertical" style={{ width: '100%' }} size="large">
                {!aiConfigured && (
                    <Alert
                        message="未配置 AI"
                        description="生成软著材料需要先配置 AI Base URL 与 API Key。"
                        type="warning"
                        showIcon
                        action={
                            <Button type="primary" size="small" onClick={() => navigate('/profile')}>
                                前往配置
                            </Button>
                        }
                    />
                )}

                <Card title="项目配置">
                    <Form form={form} layout="vertical">
                        <Form.Item
                            label="项目名称"
                            name="name"
                            rules={[{ required: true, message: '请输入项目名称' }]}
                        >
                            <Input />
                        </Form.Item>
                        <Form.Item label="所属领域" name="domain">
                            <Input />
                        </Form.Item>
                        <Form.Item label="软件名称" name="system_name">
                            <Input />
                        </Form.Item>
                        <Form.Item label="软件简称" name="software_abbr">
                            <Input />
                        </Form.Item>
                        <Form.Item label="系统简介" name="description">
                            <Input.TextArea rows={3} />
                        </Form.Item>
                        <Form.Item label="输出类型" name="output_type">
                            <Select options={[{ label: 'ZIP', value: 'zip' }]} />
                        </Form.Item>
                        <Form.Item label="生成模式" name="generation_mode">
                            <Select
                                options={[
                                    { label: '快速模式', value: 'fast' },
                                    { label: '完整模式', value: 'full' },
                                ]}
                            />
                        </Form.Item>
                        <Form.Item label="包含源代码" name="include_sourcecode" valuePropName="checked">
                            <Switch />
                        </Form.Item>
                        <Form.Item label="包含 UI 说明" name="include_ui_desc" valuePropName="checked">
                            <Switch />
                        </Form.Item>
                        <Form.Item label="包含技术栈说明" name="include_tech_desc" valuePropName="checked">
                            <Switch />
                        </Form.Item>
                        <Form.Item
                            label="需求文档"
                            name="requirements_text"
                            rules={[{ required: true, message: '请输入需求文档' }]}
                        >
                            <Input.TextArea rows={6} />
                        </Form.Item>
                        <Form.Item label="UI 设计说明" name="ui_description">
                            <Input.TextArea rows={4} />
                        </Form.Item>
                        <Form.Item label="技术栈说明" name="tech_description">
                            <Input.TextArea rows={4} />
                        </Form.Item>
                    </Form>
                </Card>

                <Card>
                    <Alert
                        type="info"
                        showIcon
                        message="软著材料生成时间较长"
                        description="点击“一键生成”后可关闭页面，任务会在后台继续执行。你可随时返回本页查看进度并下载 ZIP。"
                        style={{ marginBottom: 12 }}
                    />
                    <Space>
                        <Button type="primary" loading={saving} onClick={handleSave}>
                            保存配置
                        </Button>
                        {!project.latest_job && (
                            <Button type="primary" onClick={handleGenerate} disabled={!aiConfigured}>
                                一键生成
                            </Button>
                        )}
                        {project.latest_job && (
                            <Button
                                onClick={() =>
                                    Modal.confirm({
                                        title: '重新生成软著材料',
                                        content:
                                            '当前任务可能已中断或已完成。重新生成会启动新的后台任务，旧任务进度将被忽略。',
                                        okText: '重新生成',
                                        cancelText: '取消',
                                        onOk: handleGenerate,
                                    })
                                }
                            >
                                重新生成
                            </Button>
                        )}
                        <Button
                            onClick={() => downloadCopyrightZip(project.id)}
                            disabled={project.latest_job?.status !== 'completed'}
                        >
                            下载 ZIP
                        </Button>
                    </Space>
                </Card>

                <Modal
                    title="软著材料生成进度"
                    open={progressOpen}
                    footer={null}
                    onCancel={() => {
                        setProgressOpen(false);
                        pollingRef.current = false;
                    }}
                    width={640}
                >
                    <Alert
                        type="info"
                        showIcon
                        message="软著材料生成时间较长"
                        description="生成过程可能需要数分钟，可先关闭页面，稍后再查看进度。"
                        style={{ marginBottom: 16 }}
                    />
                    <GenerationProgressDisplay progress={progress} />
                    {progress?.stage === 'completed' && (
                        <div style={{ marginTop: 16 }}>
                            <Button type="primary" onClick={() => downloadCopyrightZip(project.id)}>
                                下载 ZIP
                            </Button>
                        </div>
                    )}
                </Modal>

                <Modal
                    title="软著材料模块使用说明"
                    open={guideOpen}
                    onCancel={() => setGuideOpen(false)}
                    footer={[
                        <Button key="close" type="primary" onClick={() => setGuideOpen(false)}>
                            知道了
                        </Button>,
                    ]}
                    width={720}
                >
                    <Typography.Paragraph>
                        本模块用于生成软件著作权申请材料，输出为 ZIP 压缩包。请按照以下步骤操作：
                    </Typography.Paragraph>
                    <Typography.Paragraph>
                        1. 先在“个人中心”配置 AI Base URL 与 API Key（未配置无法生成）。
                    </Typography.Paragraph>
                    <Typography.Paragraph>
                        2. 填写项目配置与需求文档（需求文档必填）。
                    </Typography.Paragraph>
                    <Typography.Paragraph>
                        3. 点击“一键生成”，等待进度完成后即可下载 ZIP。
                    </Typography.Paragraph>
                    <Typography.Paragraph>
                        4. 同一项目重复生成会覆盖更新最新 ZIP。
                    </Typography.Paragraph>
                    <Typography.Paragraph>
                        生成模式区别：快速模式侧重核心页面与关键接口，生成速度更快；完整模式覆盖完整功能模块与更多页面接口，内容更丰富但耗时更长。
                    </Typography.Paragraph>
                    <Alert
                        type="info"
                        showIcon
                        message="提示"
                        description="生成完成后请使用“下载 ZIP”获取材料；内容依赖 AI 输出，请检查材料完整性与规范性。"
                    />
                </Modal>
            </Space>
        </PageContainer>
    );
};

export default CopyrightDetail;
