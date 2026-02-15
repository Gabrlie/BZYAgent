import React, { useEffect, useRef, useState } from 'react';
import { PageContainer } from '@ant-design/pro-components';
import {
    Button,
    Card,
    Table,
    Tag,
    Space,
    Modal,
    Form,
    Input,
    Select,
    Alert,
    message,
    Typography,
} from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { useNavigate, useModel } from '@umijs/max';
import GenerationProgressDisplay, { GenerationProgress } from '@/components/GenerationProgress';
import { formatBackendTime } from '@/utils/time';
import { isRateLimitError } from '@/utils/errors';
import {
    CopyrightProject,
    createCopyrightProject,
    downloadCopyrightZip,
    getCopyrightProjects,
    pollLatestCopyrightJob,
    startCopyrightGeneration,
} from '@/services/copyright';

const statusColorMap: Record<string, string> = {
    queued: 'default',
    running: 'processing',
    completed: 'success',
    failed: 'error',
};
const statusTextMap: Record<string, string> = {
    queued: '排队中',
    running: '生成中',
    completed: '已完成',
    failed: '失败',
};

const CopyrightList: React.FC = () => {
    const navigate = useNavigate();
    const { initialState } = useModel('@@initialState');
    const aiConfigured =
        Boolean(initialState?.currentUser?.has_api_key) &&
        Boolean(initialState?.currentUser?.ai_base_url);

    const [projects, setProjects] = useState<CopyrightProject[]>([]);
    const [loading, setLoading] = useState(false);
    const [createOpen, setCreateOpen] = useState(false);
    const [creating, setCreating] = useState(false);
    const [progress, setProgress] = useState<GenerationProgress | null>(null);
    const [progressOpen, setProgressOpen] = useState(false);
    const [currentProjectId, setCurrentProjectId] = useState<number | null>(null);
    const [form] = Form.useForm();
    const [guideOpen, setGuideOpen] = useState(false);
    const pollingRef = useRef(false);
    const rateLimitShownRef = useRef(false);

    const loadProjects = async () => {
        setLoading(true);
        try {
            const data = await getCopyrightProjects();
            setProjects(data.projects || []);
        } catch (error) {
            message.error('加载项目列表失败');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadProjects();
    }, []);

    useEffect(() => {
        return () => {
            pollingRef.current = false;
        };
    }, []);

    useEffect(() => {
        try {
            const seen = localStorage.getItem('bzyagent:copyright:guide:seen');
            if (!seen) {
                setGuideOpen(true);
                localStorage.setItem('bzyagent:copyright:guide:seen', '1');
            }
        } catch (error) {
            setGuideOpen(true);
        }
    }, []);

    const handleCreate = async () => {
        try {
            const values = await form.validateFields();
            setCreating(true);
            const project = await createCopyrightProject({
                name: values.name,
                system_name: values.system_name,
                software_abbr: values.software_abbr,
                domain: values.domain,
                description: values.description,
                generation_mode: values.generation_mode,
                output_type: 'zip',
            });
            setCreateOpen(false);
            form.resetFields();
            navigate(`/copyright/${project.id}`);
        } catch (error) {
            message.error('创建失败，请检查输入');
        } finally {
            setCreating(false);
        }
    };

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

    const stopPolling = () => {
        pollingRef.current = false;
    };

    const openProgressModal = (record: CopyrightProject) => {
        const job = record.latest_job;
        if (!job) {
            message.info('暂无生成记录');
            return;
        }
        rateLimitShownRef.current = false;
        setCurrentProjectId(record.id);
        setProgress(mapJobToProgress(job));
        setProgressOpen(true);
        if (job.status !== 'completed' && job.status !== 'failed') {
            pollingRef.current = true;
            pollJobStatus(record.id, job.updated_at);
        }
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
                    loadProjects();
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

    const handleGenerate = async (project: CopyrightProject) => {
        if (!aiConfigured) {
            Modal.info({
                title: '请先配置 AI',
                content: '生成软著材料需要先配置 AI Base URL 与 API Key。',
                okText: '前往配置',
                onOk: () => navigate('/profile'),
            });
            return;
        }
        rateLimitShownRef.current = false;
        try {
            const job = await startCopyrightGeneration(project.id);
            setCurrentProjectId(project.id);
            setProgress(mapJobToProgress(job));
            setProgressOpen(true);
            pollingRef.current = true;
            pollJobStatus(project.id, job.updated_at);
            message.info('已开始后台生成，可关闭页面稍后查看进度');
        } catch (error: any) {
            message.error(error?.message || '生成失败');
        }
    };

    const confirmRegenerate = (project: CopyrightProject) => {
        Modal.confirm({
            title: '重新生成软著材料',
            content: '当前任务可能已中断。重新生成会启动新的后台任务，旧任务进度将被忽略。',
            okText: '重新生成',
            cancelText: '取消',
            onOk: () => handleGenerate(project),
        });
    };

    const columns = [
        {
            title: '项目名称',
            dataIndex: 'name',
            key: 'name',
        },
        {
            title: '软件名称',
            dataIndex: 'system_name',
            key: 'system_name',
            render: (value: string) => value || '-',
        },
        {
            title: '生成模式',
            dataIndex: 'generation_mode',
            key: 'generation_mode',
            render: (value: string) => (value === 'full' ? '完整模式' : '快速模式'),
        },
        {
            title: '状态',
            key: 'status',
            render: (_: any, record: CopyrightProject) => {
                const status = record.latest_job?.status;
                if (!status) {
                    return <Tag>未生成</Tag>;
                }
                return (
                    <Tag
                        color={statusColorMap[status] || 'default'}
                        style={{ cursor: 'pointer' }}
                        onClick={() => openProgressModal(record)}
                    >
                        {statusTextMap[status] || status}
                    </Tag>
                );
            },
        },
        {
            title: '更新时间',
            dataIndex: 'updated_at',
            key: 'updated_at',
            render: (value: string) => formatBackendTime(value),
        },
        {
            title: '操作',
            key: 'actions',
            render: (_: any, record: CopyrightProject) => (
                <Space>
                    <Button type="link" onClick={() => navigate(`/copyright/${record.id}`)}>
                        编辑
                    </Button>
                    {!record.latest_job && (
                        <Button
                            type="link"
                            onClick={() => handleGenerate(record)}
                            disabled={!record.requirements_text}
                        >
                            一键生成
                        </Button>
                    )}
                    {record.latest_job && (
                        <Button type="link" onClick={() => confirmRegenerate(record)}>
                            重新生成
                        </Button>
                    )}
                    <Button
                        type="link"
                        onClick={() => downloadCopyrightZip(record.id)}
                        disabled={record.latest_job?.status !== 'completed'}
                    >
                        下载 ZIP
                    </Button>
                </Space>
            ),
        },
    ];

    return (
        <PageContainer
            header={{
                title: '软著材料',
                extra: [
                    <Button key="reload" icon={<ReloadOutlined />} onClick={loadProjects}>
                        刷新
                    </Button>,
                    <Button key="guide" onClick={() => setGuideOpen(true)}>
                        使用说明
                    </Button>,
                    <Button
                        key="create"
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => setCreateOpen(true)}
                    >
                        新建项目
                    </Button>,
                ],
            }}
        >
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
                    style={{ marginBottom: 16 }}
                />
            )}
            <Alert
                type="info"
                showIcon
                message="软著材料生成时间较长"
                description="点击“一键生成”后可关闭页面，任务会在后台继续执行。你可随时返回查看进度并下载 ZIP。"
                style={{ marginBottom: 16 }}
            />

            <Card>
                <Table
                    rowKey="id"
                    columns={columns}
                    dataSource={projects}
                    loading={loading}
                    pagination={false}
                />
            </Card>

            <Modal
                title="新建软著项目"
                open={createOpen}
                onCancel={() => setCreateOpen(false)}
                onOk={handleCreate}
                confirmLoading={creating}
                okText="创建"
            >
                <Form form={form} layout="vertical">
                    <Form.Item
                        label="项目名称"
                        name="name"
                        rules={[{ required: true, message: '请输入项目名称' }]}
                    >
                        <Input placeholder="用于列表展示的项目名称" />
                    </Form.Item>
                    <Form.Item
                        label="软件名称"
                        name="system_name"
                        rules={[{ required: true, message: '请输入软件名称' }]}
                    >
                        <Input placeholder="用于软著材料的系统名称" />
                    </Form.Item>
                    <Form.Item label="软件简称" name="software_abbr">
                        <Input placeholder="可选" />
                    </Form.Item>
                    <Form.Item label="所属领域" name="domain">
                        <Input placeholder="如：教育、医疗、制造等" />
                    </Form.Item>
                    <Form.Item label="系统简介" name="description">
                        <Input.TextArea rows={3} placeholder="简要描述系统用途" />
                    </Form.Item>
                    <Form.Item
                        label="生成模式"
                        name="generation_mode"
                        initialValue="fast"
                        rules={[{ required: true, message: '请选择生成模式' }]}
                    >
                        <Select
                            options={[
                                { label: '快速模式', value: 'fast' },
                                { label: '完整模式', value: 'full' },
                            ]}
                        />
                    </Form.Item>
                </Form>
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
                    2. 点击“新建项目”，填写软件名称、生成模式等基础信息。
                </Typography.Paragraph>
                <Typography.Paragraph>
                    3. 进入项目详情，补充需求文档（必填），可选填写 UI 设计说明与技术栈说明。
                </Typography.Paragraph>
                <Typography.Paragraph>
                    4. 点击“一键生成”，等待进度完成后即可下载 ZIP。
                </Typography.Paragraph>
                <Typography.Paragraph>
                    5. 同一项目重复生成会覆盖更新最新 ZIP。
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

            <Modal
                title="软著材料生成进度"
                open={progressOpen}
                footer={null}
                onCancel={() => {
                    setProgressOpen(false);
                    stopPolling();
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
                {currentProjectId && progress?.stage === 'completed' && (
                    <div style={{ marginTop: 16 }}>
                        <Button type="primary" onClick={() => downloadCopyrightZip(currentProjectId)}>
                            下载 ZIP
                        </Button>
                    </div>
                )}
            </Modal>
        </PageContainer>
    );
};

export default CopyrightList;
