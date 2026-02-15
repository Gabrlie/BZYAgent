import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
import { Helmet, useModel } from '@umijs/max';
import { Alert, App, Divider, Space, Typography } from 'antd';
import { createStyles } from 'antd-style';
import React, { useState } from 'react';
import { flushSync } from 'react-dom';
import { Footer } from '@/components';
import { login as userLogin } from '@/services/auth';
import Settings from '../../../../config/defaultSettings';

const useStyles = createStyles(() => {
  return {
    container: {
      display: 'flex',
      flexDirection: 'column',
      minHeight: '100vh',
      overflow: 'hidden',
      position: 'relative',
      isolation: 'isolate',
      background:
        'radial-gradient(1200px 800px at 10% 10%, #f7f3ea 0%, #f3f7f5 45%, #dfe9f3 100%)',
      fontFamily: '"Space Grotesk", "Segoe UI", system-ui, sans-serif',
      '&::before': {
        content: '""',
        position: 'absolute',
        inset: '-20%',
        background:
          'radial-gradient(520px 420px at 15% 30%, rgba(14,116,144,0.18), transparent 60%), radial-gradient(420px 420px at 85% 20%, rgba(234,179,8,0.18), transparent 60%), radial-gradient(520px 520px at 70% 80%, rgba(59,130,246,0.16), transparent 60%)',
        filter: 'blur(6px)',
        zIndex: -2,
      },
      '&::after': {
        content: '""',
        position: 'absolute',
        inset: 0,
        background:
          'linear-gradient(120deg, rgba(255,255,255,0.5), rgba(255,255,255,0.2))',
        zIndex: -1,
      },
    },
    layout: {
      flex: 1,
      display: 'grid',
      gridTemplateColumns: '1.1fr 0.9fr',
      gap: 40,
      alignItems: 'center',
      padding: '48px 6vw',
      '@media (max-width: 992px)': {
        gridTemplateColumns: '1fr',
        gap: 24,
        padding: '32px 6vw 24px',
      },
    },
    brandPanel: {
      color: '#0f172a',
      display: 'flex',
      flexDirection: 'column',
      gap: 20,
    },
    badge: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 8,
      padding: '8px 14px',
      borderRadius: 999,
      background: 'rgba(14,116,144,0.12)',
      color: '#0e7490',
      fontWeight: 600,
      letterSpacing: '0.08em',
      textTransform: 'uppercase',
      fontSize: 12,
    },
    headline: {
      fontFamily: '"Newsreader", "Times New Roman", serif',
      fontSize: 44,
      lineHeight: 1.1,
      fontWeight: 600,
      margin: 0,
    },
    subhead: {
      fontSize: 18,
      color: '#475569',
      maxWidth: 520,
      margin: 0,
    },
    featureList: {
      display: 'grid',
      gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
      gap: 14,
      '@media (max-width: 640px)': {
        gridTemplateColumns: '1fr',
      },
    },
    featureCard: {
      padding: 16,
      borderRadius: 16,
      background: 'rgba(255,255,255,0.7)',
      border: '1px solid rgba(148,163,184,0.3)',
      boxShadow: '0 12px 30px rgba(15, 23, 42, 0.08)',
    },
    formWrap: {
      display: 'flex',
      justifyContent: 'center',
    },
    formCard: {
      width: '100%',
      maxWidth: 420,
      padding: 28,
      borderRadius: 24,
      background: 'rgba(255,255,255,0.92)',
      border: '1px solid rgba(148,163,184,0.35)',
      boxShadow:
        '0 24px 60px rgba(15, 23, 42, 0.18), 0 4px 10px rgba(15, 23, 42, 0.06)',
      backdropFilter: 'blur(10px)',
      overflow: 'hidden',
      '& :global(.ant-pro-form-login-container)': {
        padding: 0,
        margin: 0,
        background: 'transparent',
        boxShadow: 'none',
      },
      '& :global(.ant-pro-form-login-top)': {
        display: 'none',
      },
      '& :global(.ant-pro-form-login-main)': {
        width: '100%',
        minWidth: 'unset',
        maxWidth: '100%',
      },
      '& :global(.ant-pro-form-login-main-other)': {
        display: 'none',
      },
    },
    formTitle: {
      margin: 0,
      fontSize: 24,
      fontWeight: 600,
      color: '#0f172a',
    },
    formSubtitle: {
      margin: '8px 0 0',
      color: '#64748b',
    },
    hint: {
      fontSize: 12,
      color: '#64748b',
    },
  };
});

const LoginMessage: React.FC<{
  content: string;
}> = ({ content }) => {
  return (
    <Alert
      style={{
        marginBottom: 24,
      }}
      message={content}
      type="error"
      showIcon
    />
  );
};

const Login: React.FC = () => {
  const [error, setError] = useState<string>('');
  const { initialState, setInitialState } = useModel('@@initialState');
  const { styles } = useStyles();
  const { message } = App.useApp();

  const fetchUserInfo = async () => {
    const userInfo = await initialState?.fetchUserInfo?.();
    if (userInfo) {
      flushSync(() => {
        setInitialState((s) => ({
          ...s,
          currentUser: userInfo,
        }));
      });
    }
  };

  const handleSubmit = async (values: { username: string; password: string }) => {
    try {
      setError('');
      await userLogin(values.username, values.password);

      message.success('登录成功！');

      await fetchUserInfo();

      const urlParams = new URL(window.location.href).searchParams;
      const redirectParam = urlParams.get('redirect');
      let targetPath = '/';
      if (redirectParam) {
        try {
          const redirectUrl = new URL(redirectParam, window.location.origin);
          // 只允许回到当前站点，避免端口/域名丢失或安全问题
          if (redirectUrl.origin === window.location.origin) {
            targetPath = `${redirectUrl.pathname}${redirectUrl.search}${redirectUrl.hash}`;
          }
        } catch (error) {
          // ignore invalid redirect
        }
      }
      window.location.href = targetPath;
    } catch (err: any) {
      console.error('登录失败:', err);
      const errorMessage = err?.response?.data?.detail || '登录失败，请检查用户名和密码';
      setError(errorMessage);
      message.error(errorMessage);
    }
  };

  return (
    <div className={styles.container}>
      <Helmet>
        <title>登录 - {Settings.title}</title>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,600&family=Space+Grotesk:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </Helmet>
      <div className={styles.layout}>
        <div className={styles.brandPanel}>
          <span className={styles.badge}>EduAgent Prime</span>
          <h1 className={styles.headline}>Agent 驱动的课程智作平台</h1>
          <p className={styles.subhead}>
            课程、教案、授课计划一体化管理，智能体协作生成标准化文档，让备课回归高价值教学思考。
          </p>
          <div className={styles.featureList}>
            <div className={styles.featureCard}>
              <Typography.Text strong>课程资产沉淀</Typography.Text>
              <div className={styles.hint}>统一维护教材、目录、文档与进度。</div>
            </div>
            <div className={styles.featureCard}>
              <Typography.Text strong>教案快速生成</Typography.Text>
              <div className={styles.hint}>SSE 进度回显，结果可直接导出。</div>
            </div>
            <div className={styles.featureCard}>
              <Typography.Text strong>授课计划协同</Typography.Text>
              <div className={styles.hint}>自动排课 + 模板渲染，减少重复劳动。</div>
            </div>
            <div className={styles.featureCard}>
              <Typography.Text strong>安全认证</Typography.Text>
              <div className={styles.hint}>JWT 统一鉴权，权限明确可控。</div>
            </div>
          </div>
        </div>

        <div className={styles.formWrap}>
          <div className={styles.formCard}>
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Typography.Title level={3} className={styles.formTitle}>
                EduAgent Prime
              </Typography.Title>
              <Typography.Text className={styles.formSubtitle}>
                教学智能体中枢
              </Typography.Text>
            </Space>
            <Divider style={{ margin: '16px 0 8px' }} />
            <LoginForm
              contentStyle={{
                minWidth: 280,
                maxWidth: '100%',
              }}
              onFinish={async (values) => {
                await handleSubmit(values as { username: string; password: string });
              }}
              submitter={{
                searchConfig: {
                  submitText: '进入工作台',
                },
                submitButtonProps: {
                  size: 'large',
                  style: {
                    width: '100%',
                    height: 46,
                    borderRadius: 12,
                    background: '#0e7490',
                    border: 'none',
                    boxShadow: '0 12px 20px rgba(14,116,144,0.25)',
                  },
                },
              }}
            >
              {error && <LoginMessage content={error} />}

              <ProFormText
                name="username"
                fieldProps={{
                  size: 'large',
                  prefix: <UserOutlined />,
                }}
                placeholder="用户名: admin"
                rules={[
                  {
                    required: true,
                    message: '请输入用户名!',
                  },
                ]}
              />
              <ProFormText.Password
                name="password"
                fieldProps={{
                  size: 'large',
                  prefix: <LockOutlined />,
                }}
                placeholder="密码: admin123"
                rules={[
                  {
                    required: true,
                    message: '请输入密码！',
                  },
                ]}
              />
              <Typography.Text className={styles.hint}>
                试用账号：admin / admin123
              </Typography.Text>
            </LoginForm>
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
};

export default Login;
