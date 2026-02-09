import React from 'react';
import { Card, Progress, Steps, Alert, Space } from 'antd';
import {
    LoadingOutlined,
    CheckCircleOutlined,
    CloseCircleOutlined,
} from '@ant-design/icons';

const { Step } = Steps;

export interface GenerationProgress {
    stage:
        | 'preparing'
        | 'analyzing'
        | 'retrieving'
        | 'validating'
        | 'generating'
        | 'rendering'
        | 'saving'
        | 'completed'
        | 'error';
    progress: number;
    message: string;
    document_id?: number;
    file_url?: string;
    data?: any;
}

interface ProgressDisplayProps {
    progress: GenerationProgress | null;
}

const phaseSteps = [
    { key: 'preparing', title: '数据准备' },
    { key: 'generating', title: '内容生成' },
    { key: 'rendering', title: '格式化处理' },
    { key: 'completed', title: '生成完成' },
] as const;

const stageToPhase: Record<string, (typeof phaseSteps)[number]['key']> = {
    preparing: 'preparing',
    analyzing: 'preparing',
    retrieving: 'preparing',
    validating: 'preparing',
    generating: 'generating',
    rendering: 'rendering',
    saving: 'rendering',
    completed: 'completed',
    error: 'completed',
};

/**
 * 通用文档生成进度显示组件
 */
const GenerationProgressDisplay: React.FC<ProgressDisplayProps> = ({ progress }) => {
    if (!progress) {
        return null;
    }

    const currentPhaseKey = stageToPhase[progress.stage] || 'preparing';
    const currentStageIndex = Math.max(
        0,
        phaseSteps.findIndex((step) => step.key === currentPhaseKey)
    );
    const isError = progress.stage === 'error';
    const isCompleted = progress.stage === 'completed';

    return (
        <Card>
            <Space direction="vertical" style={{ width: '100%' }} size="large">
                {/* 进度条 */}
                <div>
                    <div style={{ marginBottom: 8 }}>
                        <strong>生成进度</strong>
                    </div>
                    <Progress
                        percent={progress.progress}
                        status={isError ? 'exception' : isCompleted ? 'success' : 'active'}
                        strokeColor={isError ? '#ff4d4f' : isCompleted ? '#52c41a' : '#1890ff'}
                    />
                </div>

                {/* 步骤指示 */}
                <Steps
                    current={currentStageIndex}
                    status={isError ? 'error' : isCompleted ? 'finish' : 'process'}
                >
                    {phaseSteps.map((step, index) => {
                        let icon = null;
                        if (isError && index === currentStageIndex) {
                            icon = <CloseCircleOutlined />;
                        } else if (isCompleted || index < currentStageIndex) {
                            icon = <CheckCircleOutlined />;
                        } else if (index === currentStageIndex) {
                            icon = <LoadingOutlined />;
                        }

                        return <Step key={step.key} title={step.title} icon={icon} />;
                    })}
                </Steps>

                {/* 当前状态消息 */}
                <Alert
                    message={progress.message}
                    type={isError ? 'error' : isCompleted ? 'success' : 'info'}
                    showIcon
                />
            </Space>
        </Card>
    );
};

export default GenerationProgressDisplay;
