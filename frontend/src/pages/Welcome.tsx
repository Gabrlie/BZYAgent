import { PageContainer } from '@ant-design/pro-components';
import {
  BookOutlined,
  CloudOutlined,
  FileDoneOutlined,
  FileProtectOutlined,
  FileTextOutlined,
  ProfileOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useModel, useNavigate } from '@umijs/max';
import { Button, Card, Col, Row, Space, Statistic, Tag, Typography, message } from 'antd';
import React, { useEffect, useState } from 'react';
import { DashboardSummary, getDashboardSummary } from '@/services/dashboard';

const Welcome: React.FC = () => {
  const navigate = useNavigate();
  const { initialState } = useModel('@@initialState');
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<DashboardSummary>({
    course_count: 0,
    document_count: 0,
    teaching_plan_count: 0,
    lesson_plan_count: 0,
    courseware_count: 0,
    copyright_project_count: 0,
    ai_configured: false,
  });

  const loadSummary = async () => {
    setLoading(true);
    try {
      const data = await getDashboardSummary();
      setSummary(data);
    } catch (error) {
      message.error('加载仪表盘数据失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSummary();
  }, []);

  const aiConfigured =
    summary.ai_configured &&
    Boolean(initialState?.currentUser?.ai_base_url) &&
    Boolean(initialState?.currentUser?.has_api_key);

  return (
    <PageContainer
      title="仪表盘"
      extra={[
        <Button key="refresh" icon={<ReloadOutlined />} onClick={loadSummary} loading={loading}>
          刷新
        </Button>,
      ]}
    >
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} md={8} lg={6}>
              <Card bordered={false}>
                <Statistic
                  title="课程数量"
                  value={summary.course_count}
                  prefix={<BookOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8} lg={6}>
              <Card bordered={false}>
                <Statistic
                  title="授课计划数量"
                  value={summary.teaching_plan_count}
                  prefix={<FileTextOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8} lg={6}>
              <Card bordered={false}>
                <Statistic
                  title="教案数量"
                  value={summary.lesson_plan_count}
                  prefix={<FileDoneOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8} lg={6}>
              <Card bordered={false}>
                <Statistic
                  title="文档总数"
                  value={summary.document_count}
                  prefix={<ProfileOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8} lg={6}>
              <Card bordered={false}>
                <Statistic
                  title="课件数量"
                  value={summary.courseware_count}
                  prefix={<ProfileOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8} lg={6}>
              <Card bordered={false}>
                <Statistic
                  title="软著项目数"
                  value={summary.copyright_project_count}
                  prefix={<FileProtectOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8} lg={6}>
              <Card bordered={false}>
                <Statistic
                  title="AI 配置状态"
                  value={aiConfigured ? '已配置' : '未配置'}
                  prefix={<CloudOutlined />}
                />
              </Card>
            </Col>
          </Row>
        </Card>

        <Card title="配置概览">
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Space direction="vertical">
                <Typography.Text strong>AI 配置情况</Typography.Text>
                <Space>
                  <Tag color={aiConfigured ? 'success' : 'warning'}>
                    {aiConfigured ? '已配置' : '未配置'}
                  </Tag>
                  <Typography.Text type="secondary">
                    {initialState?.currentUser?.ai_base_url || '未设置 Base URL'}
                  </Typography.Text>
                </Space>
                {!aiConfigured && (
                  <Button type="primary" onClick={() => navigate('/profile')}>
                    前往配置
                  </Button>
                )}
              </Space>
            </Col>
            <Col xs={24} md={12}>
              <Space direction="vertical">
                <Typography.Text strong>近期提醒</Typography.Text>
                <Typography.Text type="secondary">
                  教案与授课计划生成依赖 AI 配置，请确保接口可用。
                </Typography.Text>
                <Typography.Text type="secondary">
                  软著材料生成耗时较长，可在后台执行并稍后下载 ZIP。
                </Typography.Text>
              </Space>
            </Col>
          </Row>
        </Card>
      </Space>
    </PageContainer>
  );
};

export default Welcome;
