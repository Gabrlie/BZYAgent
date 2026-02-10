import React, { useEffect, useMemo, useState } from 'react';
import { PageContainer } from '@ant-design/pro-components';
import {
    Button,
    Card,
    Col,
    Divider,
    Form,
    Input,
    InputNumber,
    message,
    Row,
    Space,
    Spin,
    Tag,
    Typography,
} from 'antd';
import { useParams, history } from '@umijs/max';
import { getDocumentDetail, renderDocument, updateDocument } from '@/services/document';

const { Title, Text } = Typography;

const LessonPlanEdit: React.FC = () => {
    const { id: courseId, documentId } = useParams<{ id: string; documentId: string }>();
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [document, setDocument] = useState<any>(null);
    const [previewData, setPreviewData] = useState<any>(null);
    const [contentError, setContentError] = useState<string | null>(null);

    const watchedValues = Form.useWatch([], form);

    useEffect(() => {
        if (watchedValues) {
            setPreviewData(watchedValues);
        }
    }, [watchedValues]);

    useEffect(() => {
        loadDocument();
    }, [documentId]);

    const normalizeLessonValues = (raw: any) => {
        const base = raw && typeof raw === 'object' ? raw : {};
        return {
            project_name: base.project_name || '',
            week: base.week ?? undefined,
            sequence: base.sequence ?? undefined,
            hours: base.hours ?? undefined,
            total_hours: base.total_hours ?? undefined,
            knowledge_goals: base.knowledge_goals || '',
            ability_goals: base.ability_goals || '',
            quality_goals: base.quality_goals || '',
            teaching_content: base.teaching_content || '',
            teaching_focus: base.teaching_focus || '',
            teaching_difficulty: base.teaching_difficulty || '',
            review_content: base.review_content || '',
            review_time: base.review_time ?? undefined,
            new_lessons: Array.isArray(base.new_lessons) ? base.new_lessons : [],
            assessment_content: base.assessment_content || '',
            summary_content: base.summary_content || '',
            homework_content: base.homework_content || '',
        };
    };

    const normalizePlanValues = (raw: any) => {
        const base = raw && typeof raw === 'object' ? raw : {};
        return {
            academic_year: base.academic_year || '',
            course_name: base.course_name || '',
            target_classes: base.target_classes || '',
            teacher_name: base.teacher_name || '',
            total_hours: base.total_hours ?? undefined,
            theory_hours: base.theory_hours ?? undefined,
            practice_hours: base.practice_hours ?? undefined,
            schedule: Array.isArray(base.schedule) ? base.schedule : [],
        };
    };

    const loadDocument = async () => {
        if (!documentId) {
            return;
        }
        setLoading(true);
        try {
            const data = await getDocumentDetail(Number(documentId));
            setDocument(data);
            setContentError(null);

            if (!data.content) {
                setContentError('文档内容为空，暂不能在线编辑');
                setPreviewData(null);
                return;
            }

            let parsed = {};
            try {
                parsed = JSON.parse(data.content);
            } catch (error) {
                setContentError('文档内容格式错误，暂不能在线编辑');
                setPreviewData(null);
                return;
            }

            const initialValues =
                data.doc_type === 'plan' ? normalizePlanValues(parsed) : normalizeLessonValues(parsed);
            form.setFieldsValue(initialValues);
            setPreviewData(initialValues);
        } catch (error) {
            message.error('加载文档内容失败');
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        if (!documentId || contentError) {
            return;
        }
        try {
            const values = await form.validateFields();
            setSaving(true);
            const payload =
                document?.doc_type === 'plan'
                    ? {
                          ...values,
                          schedule: (values.schedule || []).filter(
                              (item: any) =>
                                  item &&
                                  (item.order !== undefined ||
                                      item.week !== undefined ||
                                      item.title ||
                                      item.tasks ||
                                      item.hour !== undefined),
                          ),
                      }
                    : {
                          ...values,
                          new_lessons: (values.new_lessons || []).filter(
                              (item: any) => item && (item.content || item.time),
                          ),
                      };
            await updateDocument(Number(documentId), {
                content: JSON.stringify(payload),
            });
            await renderDocument(Number(documentId));
            message.success('保存并渲染成功');
            const docType = document?.doc_type === 'plan' ? 'plan' : 'lesson';
            window.dispatchEvent(
                new CustomEvent('bzyagent:documents-refresh', {
                    detail: { courseId: Number(courseId), docType },
                }),
            );
        } catch (error) {
            message.error('保存失败');
        } finally {
            setSaving(false);
        }
    };

    const preview = useMemo(() => {
        const data = previewData || {};
        return {
            ...data,
            new_lessons: Array.isArray(data.new_lessons) ? data.new_lessons : [],
            schedule: Array.isArray(data.schedule) ? data.schedule : [],
        };
    }, [previewData]);

    if (loading) {
        return (
            <PageContainer title="编辑教案">
                <Card>
                    <div style={{ textAlign: 'center', padding: '40px 0' }}>
                        <Spin size="large" />
                        <div style={{ marginTop: 16 }}>正在加载文档内容...</div>
                    </div>
                </Card>
            </PageContainer>
        );
    }

    if (!document) {
        return (
            <PageContainer title="编辑教案">
                <Card>未找到教案内容</Card>
            </PageContainer>
        );
    }

    if (contentError) {
        return (
            <PageContainer title={document?.doc_type === 'plan' ? '编辑授课计划' : '编辑教案'}>
                <Card>
                    <Space direction="vertical">
                        <Text type="danger">{contentError}</Text>
                        <Button onClick={() => history.push(`/courses/${courseId}`)}>返回课程</Button>
                    </Space>
                </Card>
            </PageContainer>
        );
    }

    const isPlan = document.doc_type === 'plan';

    return (
        <PageContainer
            title={isPlan ? '编辑授课计划' : '编辑教案'}
            extra={
                <Space>
                    <Button onClick={() => history.push(`/courses/${courseId}`)}>返回课程</Button>
                    <Button type="primary" onClick={handleSave} loading={saving}>
                        保存并渲染
                    </Button>
                </Space>
            }
        >
            <Row gutter={[16, 16]}>
                <Col xs={24} lg={14}>
                    <Card title="文档预览" bordered>
                        {isPlan ? (
                            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                                <div>
                                    <Title level={4} style={{ marginBottom: 8 }}>
                                        {preview.course_name || '未填写课程名称'}
                                    </Title>
                                    <Space wrap>
                                        <Tag>学年: {preview.academic_year || '-'}</Tag>
                                        <Tag>授课班级: {preview.target_classes || '-'}</Tag>
                                        <Tag>授课教师: {preview.teacher_name || '-'}</Tag>
                                        <Tag>总学时: {preview.total_hours ?? '-'}</Tag>
                                        <Tag>理论学时: {preview.theory_hours ?? '-'}</Tag>
                                        <Tag>实训学时: {preview.practice_hours ?? '-'}</Tag>
                                    </Space>
                                </div>

                                <Divider />

                                <div>
                                    <Title level={5}>授课计划安排</Title>
                                    <ol>
                                        {preview.schedule
                                            .slice()
                                            .sort((a: any, b: any) => (a?.order || 0) - (b?.order || 0))
                                            .map((item: any, index: number) => (
                                                <li key={`${index}-${item?.order || index}`}>
                                                    <div>
                                                        <Text strong>
                                                            第{item?.order ?? '-'}次 / 第{item?.week ?? '-'}周
                                                        </Text>
                                                    </div>
                                                    <div style={{ whiteSpace: 'pre-wrap' }}>
                                                        {item?.title || '未填写标题'}
                                                    </div>
                                                    <div style={{ whiteSpace: 'pre-wrap' }}>
                                                        {item?.tasks || '未填写任务'}
                                                    </div>
                                                    <Text type="secondary">学时: {item?.hour ?? '-'}</Text>
                                                </li>
                                            ))}
                                    </ol>
                                </div>
                            </Space>
                        ) : (
                            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                                <div>
                                    <Title level={4} style={{ marginBottom: 8 }}>
                                        {preview.project_name || '未填写项目名称'}
                                    </Title>
                                    <Space wrap>
                                        <Tag>周次: {preview.week ?? '-'}</Tag>
                                        <Tag>授课顺序: {preview.sequence ?? '-'}</Tag>
                                        <Tag>本次学时: {preview.hours ?? '-'}</Tag>
                                        <Tag>累计学时: {preview.total_hours ?? '-'}</Tag>
                                        <Tag>复习时间: {preview.review_time ?? '-'} 分钟</Tag>
                                    </Space>
                                </div>

                                <Divider />

                                <div>
                                    <Title level={5}>教学目标 - 知识</Title>
                                    <div style={{ whiteSpace: 'pre-wrap' }}>{preview.knowledge_goals}</div>
                                </div>
                                <div>
                                    <Title level={5}>教学目标 - 能力</Title>
                                    <div style={{ whiteSpace: 'pre-wrap' }}>{preview.ability_goals}</div>
                                </div>
                                <div>
                                    <Title level={5}>教学目标 - 素质</Title>
                                    <div style={{ whiteSpace: 'pre-wrap' }}>{preview.quality_goals}</div>
                                </div>

                                <Divider />

                                <div>
                                    <Title level={5}>教学内容</Title>
                                    <div style={{ whiteSpace: 'pre-wrap' }}>{preview.teaching_content}</div>
                                </div>
                                <div>
                                    <Title level={5}>教学重点</Title>
                                    <div style={{ whiteSpace: 'pre-wrap' }}>{preview.teaching_focus}</div>
                                </div>
                                <div>
                                    <Title level={5}>教学难点</Title>
                                    <div style={{ whiteSpace: 'pre-wrap' }}>{preview.teaching_difficulty}</div>
                                </div>

                                <Divider />

                                <div>
                                    <Title level={5}>复习及新课导入</Title>
                                    <div style={{ whiteSpace: 'pre-wrap' }}>{preview.review_content}</div>
                                </div>

                                <Divider />

                                <div>
                                    <Title level={5}>新课教学内容</Title>
                                    <ol>
                                        {preview.new_lessons.map((item: any, index: number) => (
                                            <li key={`${index}-${item?.content || ''}`}>
                                                <div style={{ whiteSpace: 'pre-wrap' }}>
                                                    {item?.content || '未填写内容'}
                                                </div>
                                                <Text type="secondary">{item?.time ?? '-'} 分钟</Text>
                                            </li>
                                        ))}
                                    </ol>
                                </div>

                                <Divider />

                                <div>
                                    <Title level={5}>考核评价</Title>
                                    <div style={{ whiteSpace: 'pre-wrap' }}>{preview.assessment_content}</div>
                                </div>
                                <div>
                                    <Title level={5}>课堂小结</Title>
                                    <div style={{ whiteSpace: 'pre-wrap' }}>{preview.summary_content}</div>
                                </div>
                                <div>
                                    <Title level={5}>作业布置</Title>
                                    <div style={{ whiteSpace: 'pre-wrap' }}>{preview.homework_content}</div>
                                </div>
                            </Space>
                        )}
                    </Card>
                </Col>

                <Col xs={24} lg={10}>
                    <Card title="字段表单" bordered>
                        {isPlan ? (
                            <Form
                                form={form}
                                layout="vertical"
                                onValuesChange={(_, allValues) => setPreviewData(allValues)}
                            >
                                <Title level={5}>基础信息</Title>
                                <Form.Item label="学年" name="academic_year">
                                    <Input />
                                </Form.Item>
                                <Form.Item label="课程名称" name="course_name">
                                    <Input />
                                </Form.Item>
                                <Form.Item label="授课班级" name="target_classes">
                                    <Input />
                                </Form.Item>
                                <Form.Item label="授课教师" name="teacher_name">
                                    <Input />
                                </Form.Item>
                                <Row gutter={12}>
                                    <Col span={8}>
                                        <Form.Item label="总学时" name="total_hours">
                                            <InputNumber min={0} style={{ width: '100%' }} />
                                        </Form.Item>
                                    </Col>
                                    <Col span={8}>
                                        <Form.Item label="理论学时" name="theory_hours">
                                            <InputNumber min={0} style={{ width: '100%' }} />
                                        </Form.Item>
                                    </Col>
                                    <Col span={8}>
                                        <Form.Item label="实训学时" name="practice_hours">
                                            <InputNumber min={0} style={{ width: '100%' }} />
                                        </Form.Item>
                                    </Col>
                                </Row>

                                <Divider />

                                <Title level={5}>授课计划安排</Title>
                                <Form.List name="schedule">
                                    {(fields, { add, remove }) => (
                                        <Space direction="vertical" style={{ width: '100%' }} size="middle">
                                            {fields.map((field) => (
                                                <Card
                                                    key={field.key}
                                                    size="small"
                                                    title={`课次 ${field.name + 1}`}
                                                    extra={<Button onClick={() => remove(field.name)}>删除</Button>}
                                                >
                                                    <Row gutter={12}>
                                                        <Col span={8}>
                                                            <Form.Item
                                                                {...field}
                                                                label="周次"
                                                                name={[field.name, 'week']}
                                                            >
                                                                <InputNumber min={1} style={{ width: '100%' }} />
                                                            </Form.Item>
                                                        </Col>
                                                        <Col span={8}>
                                                            <Form.Item
                                                                {...field}
                                                                label="授课顺序"
                                                                name={[field.name, 'order']}
                                                            >
                                                                <InputNumber min={1} style={{ width: '100%' }} />
                                                            </Form.Item>
                                                        </Col>
                                                        <Col span={8}>
                                                            <Form.Item
                                                                {...field}
                                                                label="学时"
                                                                name={[field.name, 'hour']}
                                                            >
                                                                <InputNumber min={1} style={{ width: '100%' }} />
                                                            </Form.Item>
                                                        </Col>
                                                    </Row>
                                                    <Form.Item
                                                        {...field}
                                                        label="标题"
                                                        name={[field.name, 'title']}
                                                    >
                                                        <Input />
                                                    </Form.Item>
                                                    <Form.Item
                                                        {...field}
                                                        label="任务内容"
                                                        name={[field.name, 'tasks']}
                                                    >
                                                        <Input.TextArea rows={3} />
                                                    </Form.Item>
                                                </Card>
                                            ))}
                                            <Button onClick={() => add()} type="dashed" block>
                                                添加课次
                                            </Button>
                                        </Space>
                                    )}
                                </Form.List>
                            </Form>
                        ) : (
                            <Form
                                form={form}
                                layout="vertical"
                                onValuesChange={(_, allValues) => setPreviewData(allValues)}
                            >
                                <Title level={5}>基础信息</Title>
                                <Row gutter={12}>
                                    <Col span={24}>
                                        <Form.Item
                                            label="项目名称"
                                            name="project_name"
                                            rules={[{ required: true, message: '请输入项目名称' }]}
                                        >
                                            <Input placeholder="请输入项目名称" />
                                        </Form.Item>
                                    </Col>
                                    <Col span={12}>
                                        <Form.Item label="周次" name="week">
                                            <InputNumber min={1} style={{ width: '100%' }} />
                                        </Form.Item>
                                    </Col>
                                    <Col span={12}>
                                        <Form.Item label="授课顺序" name="sequence">
                                            <InputNumber min={1} style={{ width: '100%' }} />
                                        </Form.Item>
                                    </Col>
                                    <Col span={12}>
                                        <Form.Item label="本次学时" name="hours">
                                            <InputNumber min={1} style={{ width: '100%' }} />
                                        </Form.Item>
                                    </Col>
                                    <Col span={12}>
                                        <Form.Item label="累计学时" name="total_hours">
                                            <InputNumber min={0} style={{ width: '100%' }} />
                                        </Form.Item>
                                    </Col>
                                    <Col span={12}>
                                        <Form.Item label="复习时间(分钟)" name="review_time">
                                            <InputNumber min={0} style={{ width: '100%' }} />
                                        </Form.Item>
                                    </Col>
                                </Row>

                                <Divider />

                                <Title level={5}>教学目标</Title>
                                <Form.Item label="知识目标" name="knowledge_goals">
                                    <Input.TextArea rows={4} placeholder="每行一条目标" />
                                </Form.Item>
                                <Form.Item label="能力目标" name="ability_goals">
                                    <Input.TextArea rows={4} placeholder="每行一条目标" />
                                </Form.Item>
                                <Form.Item label="素质目标" name="quality_goals">
                                    <Input.TextArea rows={4} placeholder="每行一条目标" />
                                </Form.Item>

                                <Divider />

                                <Title level={5}>教学内容与重难点</Title>
                                <Form.Item label="教学内容" name="teaching_content">
                                    <Input.TextArea rows={4} />
                                </Form.Item>
                                <Form.Item label="教学重点" name="teaching_focus">
                                    <Input.TextArea rows={3} />
                                </Form.Item>
                                <Form.Item label="教学难点" name="teaching_difficulty">
                                    <Input.TextArea rows={3} />
                                </Form.Item>

                                <Divider />

                                <Title level={5}>复习及新课导入</Title>
                                <Form.Item label="复习内容" name="review_content">
                                    <Input.TextArea rows={4} />
                                </Form.Item>

                                <Divider />

                                <Title level={5}>新课教学列表</Title>
                                <Form.List name="new_lessons">
                                    {(fields, { add, remove }) => (
                                        <Space direction="vertical" style={{ width: '100%' }} size="middle">
                                            {fields.map((field) => (
                                                <Card
                                                    key={field.key}
                                                    size="small"
                                                    title={`任务 ${field.name + 1}`}
                                                    extra={<Button onClick={() => remove(field.name)}>删除</Button>}
                                                >
                                                    <Form.Item
                                                        {...field}
                                                        label="任务内容"
                                                        name={[field.name, 'content']}
                                                        rules={[{ required: true, message: '请输入任务内容' }]}
                                                    >
                                                        <Input.TextArea rows={3} />
                                                    </Form.Item>
                                                    <Form.Item
                                                        {...field}
                                                        label="时间(分钟)"
                                                        name={[field.name, 'time']}
                                                        rules={[{ required: true, message: '请输入时间' }]}
                                                    >
                                                        <InputNumber min={1} style={{ width: '100%' }} />
                                                    </Form.Item>
                                                </Card>
                                            ))}
                                            <Button onClick={() => add()} type="dashed" block>
                                                添加任务
                                            </Button>
                                        </Space>
                                    )}
                                </Form.List>

                                <Divider />

                                <Title level={5}>总结与作业</Title>
                                <Form.Item label="考核评价" name="assessment_content">
                                    <Input.TextArea rows={3} />
                                </Form.Item>
                                <Form.Item label="课堂小结" name="summary_content">
                                    <Input.TextArea rows={4} />
                                </Form.Item>
                                <Form.Item label="作业布置" name="homework_content">
                                    <Input.TextArea rows={3} />
                                </Form.Item>
                            </Form>
                        )}
                    </Card>
                </Col>
            </Row>
        </PageContainer>
    );
};

export default LessonPlanEdit;
