import { PageContainer, ProCard, ProForm, ProFormText, ProFormSelect } from '@ant-design/pro-components';
import { App, Button, Row, Col, Descriptions } from 'antd';
import React, { useState, useEffect } from 'react';
import { changePassword, changeUsername, updateUserSettings, getAvailableModels } from '@/services/auth';
import { useModel } from '@umijs/max';
import { ReloadOutlined } from '@ant-design/icons';
import { formatBackendTime } from '@/utils/time';

const Profile: React.FC = () => {
    const { message } = App.useApp();
    const { initialState, setInitialState } = useModel('@@initialState');
    const { currentUser } = initialState || {};
    const [loadingModels, setLoadingModels] = useState(false);
    const [models, setModels] = useState<Array<{ id: string; name: string }>>([]);
    const [aiFormRef] = ProForm.useForm();
    const [usernameFormRef] = ProForm.useForm();

    // 当 currentUser 变化时，更新表单值
    useEffect(() => {
        console.log('🔍 Current User:', currentUser);

        if (currentUser) {
            console.log('📝 设置用户名表单:', currentUser.username);
            console.log('📝 设置 AI 配置:', {
                ai_base_url: currentUser.ai_base_url,
                ai_model_name: currentUser.ai_model_name,
                has_api_key: currentUser.has_api_key,
            });

            // 更新用户名表单
            usernameFormRef?.setFieldsValue({
                new_username: currentUser.username || '',
            });

            // 更新 AI 配置表单
            aiFormRef?.setFieldsValue({
                ai_base_url: currentUser.ai_base_url || '',
                ai_model_name: currentUser.ai_model_name || '',
            });

            console.log('✅ 表单值已设置');
        } else {
            console.log('⚠️ currentUser 为空');
        }
    }, [currentUser, aiFormRef, usernameFormRef]);

    // 修改用户名
    const handleUsernameChange = async (values: any) => {
        try {
            const result = await changeUsername(values.new_username);
            message.success('用户名修改成功');

            // 更新 Token
            localStorage.setItem('token', result.access_token);

            // 刷新用户信息
            const userInfo = await initialState?.fetchUserInfo?.();
            if (userInfo) {
                setInitialState((s: any) => ({
                    ...s,
                    currentUser: userInfo,
                }));
            }

            return true;
        } catch (error: any) {
            message.error(error.message || '用户名修改失败');
            return false;
        }
    };

    // 修改密码
    const handlePasswordChange = async (values: any) => {
        try {
            await changePassword(values.old_password, values.new_password);
            message.success('密码修改成功');
            return true;
        } catch (error: any) {
            message.error(error.message || '密码修改失败');
            return false;
        }
    };

    // 获取模型列表
    const fetchModels = async () => {
        const apiKey = aiFormRef?.getFieldValue('ai_api_key');
        const baseUrl = aiFormRef?.getFieldValue('ai_base_url');

        // 如果用户没有输入新的 API Key，但已经配置过，则使用已保存的
        if (!apiKey && !currentUser?.has_api_key) {
            message.warning('请先配置 API Key');
            return;
        }

        if (!baseUrl) {
            message.warning('请先填写 Base URL');
            return;
        }

        setLoadingModels(true);
        try {
            const data = await getAvailableModels({
                ai_api_key: apiKey || undefined,  // 如果为空，后端会使用已保存的
                ai_base_url: baseUrl,
            });

            if (data.error) {
                message.warning(`获取模型列表失败，显示默认列表`);
            }

            setModels(data.models);
            message.success(`成功获取 ${data.models.length} 个模型`);
        } catch (error: any) {
            message.error('获取模型列表失败');
            // 设置默认模型列表
            setModels([
                { id: 'gpt-3.5-turbo', name: 'gpt-3.5-turbo' },
                { id: 'gpt-4', name: 'gpt-4' },
                { id: 'gpt-4-turbo', name: 'gpt-4-turbo' },
            ]);
        } finally {
            setLoadingModels(false);
        }
    };

    // 保存 AI 配置
    const handleSettingsSave = async (values: any) => {
        try {
            await updateUserSettings({
                ai_api_key: values.ai_api_key,
                ai_base_url: values.ai_base_url,
                ai_model_name: values.ai_model_name,
            });
            message.success('设置保存成功');

            // 更新用户信息
            const userInfo = await initialState?.fetchUserInfo?.();
            if (userInfo) {
                setInitialState((s: any) => ({
                    ...s,
                    currentUser: userInfo,
                }));
            }

            return true;
        } catch (error: any) {
            message.error(error.message || '保存失败');
            return false;
        }
    };

    return (
        <PageContainer>
            {/* 第一排：用户信息 | 修改密码 */}
            <Row gutter={16} style={{ marginBottom: 24 }} align="middle">
                <Col xs={24} lg={12}>
                    <ProCard
                        title="用户信息"
                        style={{ minHeight: 450 }}
                    >
                        <Descriptions column={1} style={{ marginBottom: 16 }}>
                            <Descriptions.Item label="用户ID">{currentUser?.id}</Descriptions.Item>
                            <Descriptions.Item label="当前用户名">{currentUser?.username}</Descriptions.Item>
                            <Descriptions.Item label="注册时间">
                                {formatBackendTime(currentUser?.created_at)}
                            </Descriptions.Item>
                        </Descriptions>

                        <ProForm
                            form={usernameFormRef}
                            onFinish={handleUsernameChange}
                            submitter={{
                                searchConfig: {
                                    submitText: '修改用户名',
                                },
                                resetButtonProps: {
                                    style: { display: 'none' },
                                },
                            }}
                        >
                            <ProFormText
                                name="new_username"
                                label="新用户名"
                                placeholder="请输入新用户名"
                                rules={[
                                    { required: true, message: '请输入新用户名' },
                                    { min: 3, message: '用户名至少3位' },
                                ]}
                                width="md"
                            />
                        </ProForm>
                    </ProCard>
                </Col>

                <Col xs={24} lg={12}>
                    <ProCard
                        title="修改密码"
                        style={{ minHeight: 450 }}
                    >
                        <ProForm
                            onFinish={handlePasswordChange}
                            submitter={{
                                searchConfig: {
                                    submitText: '提交修改',
                                },
                                resetButtonProps: {
                                    style: { display: 'none' },
                                },
                            }}
                        >
                            <ProFormText.Password
                                name="old_password"
                                label="旧密码"
                                placeholder="请输入旧密码"
                                rules={[{ required: true, message: '请输入旧密码' }]}
                                width="md"
                            />
                            <ProFormText.Password
                                name="new_password"
                                label="新密码"
                                placeholder="请输入新密码"
                                rules={[
                                    { required: true, message: '请输入新密码' },
                                    { min: 6, message: '密码至少6位' },
                                ]}
                                width="md"
                            />
                            <ProFormText.Password
                                name="confirm_password"
                                label="确认新密码"
                                placeholder="请再次输入新密码"
                                dependencies={['new_password']}
                                rules={[
                                    { required: true, message: '请确认新密码' },
                                    ({ getFieldValue }) => ({
                                        validator(_, value) {
                                            if (!value || getFieldValue('new_password') === value) {
                                                return Promise.resolve();
                                            }
                                            return Promise.reject(new Error('两次密码输入不一致'));
                                        },
                                    }),
                                ]}
                                width="md"
                            />
                        </ProForm>
                    </ProCard>
                </Col>
            </Row>

            {/* 第二排：AI 配置 */}
            <Row gutter={16}>
                <Col span={24}>
                    <ProCard title="AI 配置">
                        <ProForm
                            form={aiFormRef}
                            onFinish={handleSettingsSave}
                            submitter={{
                                searchConfig: {
                                    submitText: '保存配置',
                                },
                                resetButtonProps: {
                                    style: { display: 'none' },
                                },
                            }}
                        >
                            <Row gutter={16}>
                                <Col xs={24} lg={12}>
                                    <ProFormText.Password
                                        name="ai_api_key"
                                        label="AI API Key"
                                        placeholder={currentUser?.has_api_key ? '已配置（重新输入可修改）' : 'sk-...'}
                                        tooltip="OpenAI / Azure / 自定义端点的 API Key"
                                    />
                                </Col>
                                <Col xs={24} lg={12}>
                                    <ProFormText
                                        name="ai_base_url"
                                        label="Base URL"
                                        placeholder="https://api.openai.com/v1"
                                        tooltip="API 基础地址，必须以 /v1 结尾"
                                        rules={[
                                            {
                                                validator: (_, value) => {
                                                    if (!value) {
                                                        return Promise.resolve();
                                                    }

                                                    // 检查是否以 http:// 或 https:// 开头
                                                    if (!value.startsWith('http://') && !value.startsWith('https://')) {
                                                        return Promise.reject(new Error('URL 必须以 http:// 或 https:// 开头'));
                                                    }

                                                    // 检查是否有双重协议
                                                    if (value.includes('://http://') || value.includes('://https://')) {
                                                        return Promise.reject(new Error('URL 格式错误，请移除重复的协议'));
                                                    }

                                                    // 检查是否以 /v1 结尾
                                                    if (!value.endsWith('/v1')) {
                                                        return Promise.reject(new Error('Base URL 必须以 /v1 结尾'));
                                                    }

                                                    // 尝试解析 URL
                                                    try {
                                                        new URL(value);
                                                    } catch (e) {
                                                        return Promise.reject(new Error('URL 格式无效'));
                                                    }

                                                    return Promise.resolve();
                                                },
                                            },
                                        ]}
                                    />
                                </Col>
                            </Row>

                            <Row gutter={16}>
                                <Col xs={24} lg={12}>
                                    <ProFormSelect
                                        name="ai_model_name"
                                        label="模型名称"
                                        placeholder="请选择模型"
                                        tooltip="先填写 API Key 和 Base URL，然后点击刷新"
                                        options={models.map((m) => ({ label: m.name, value: m.id }))}
                                        fieldProps={{
                                            showSearch: true,
                                            allowClear: true,
                                            notFoundContent: '暂无模型，请点击刷新按钮获取',
                                        }}
                                        addonAfter={
                                            <Button
                                                icon={<ReloadOutlined />}
                                                loading={loadingModels}
                                                onClick={fetchModels}
                                                type="link"
                                            >
                                                刷新模型列表
                                            </Button>
                                        }
                                    />
                                </Col>
                                <Col xs={24} lg={12}>
                                    <div style={{ paddingTop: 30, color: '#666' }}>
                                        {currentUser?.has_api_key ? (
                                            <span>✅ API Key 已配置</span>
                                        ) : (
                                            <span>⚠️ 请先配置 API Key</span>
                                        )}
                                    </div>
                                </Col>
                            </Row>
                        </ProForm>
                    </ProCard>
                </Col>
            </Row>
        </PageContainer>
    );
};

export default Profile;
