import { PageContainer, ProCard } from '@ant-design/pro-components';
import { Button, Descriptions, App, Space } from 'antd';
import { useState } from 'react';
import { useModel } from '@umijs/max';

const TestAI: React.FC = () => {
    const { message } = App.useApp();
    const { initialState } = useModel('@@initialState');
    const { currentUser } = initialState || {};
    const [testing, setTesting] = useState(false);
    const [result, setResult] = useState<string>('');

    const testAIConfig = async () => {
        setTesting(true);
        setResult('正在测试...');

        try {
            const response = await fetch('http://localhost:8000/api/chat/send', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`,
                },
                body: JSON.stringify({ content: '你好' }),
            });

            if (!response.ok) {
                const error = await response.json();
                setResult(`❌ 错误: ${error.detail}`);
                return;
            }

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();
            let fullResponse = '';

            while (true) {
                const { done, value } = await reader!.read();
                if (done) break;
                const chunk = decoder.decode(value);
                fullResponse += chunk;
            }

            setResult(`✅ 成功!\n\n收到响应:\n${fullResponse}`);
        } catch (error: any) {
            setResult(`❌ 请求失败: ${error.message}`);
        } finally {
            setTesting(false);
        }
    };

    return (
        <PageContainer>
            <ProCard title="AI 配置诊断">
                <Descriptions column={1} bordered>
                    <Descriptions.Item label="用户名">{currentUser?.username}</Descriptions.Item>
                    <Descriptions.Item label="Base URL">{currentUser?.ai_base_url || '未配置'}</Descriptions.Item>
                    <Descriptions.Item label="模型名称">{currentUser?.ai_model_name || '未配置'}</Descriptions.Item>
                    <Descriptions.Item label="API Key 状态">
                        {currentUser?.has_api_key ? '✅ 已配置' : '❌ 未配置'}
                    </Descriptions.Item>
                </Descriptions>

                <Space direction="vertical" style={{ width: '100%', marginTop: 24 }}>
                    <Button
                        type="primary"
                        onClick={testAIConfig}
                        loading={testing}
                        disabled={!currentUser?.has_api_key}
                    >
                        测试 AI 连接
                    </Button>

                    {result && (
                        <pre style={{
                            padding: 16,
                            backgroundColor: '#f5f5f5',
                            borderRadius: 6,
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word'
                        }}>
                            {result}
                        </pre>
                    )}
                </Space>

                <div style={{ marginTop: 24, padding: 16, backgroundColor: '#e6f7ff', borderRadius: 6 }}>
                    <h4>📌 常见问题：</h4>
                    <ul>
                        <li>Base URL 必须以 <code>/v1</code> 结尾</li>
                        <li>不要在 Base URL 中包含双重协议（如 <code>https://https://</code>）</li>
                        <li>OpenAI 官方: <code>https://api.openai.com/v1</code></li>
                        <li>确保 API Key 有效且有配额</li>
                    </ul>
                </div>
            </ProCard>
        </PageContainer>
    );
};

export default TestAI;
