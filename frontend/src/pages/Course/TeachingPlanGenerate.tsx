import React, { useState, useEffect } from 'react';
import { PageContainer } from '@ant-design/pro-components';
import {
    Card,
    Button,
    Form,
    Input,
    InputNumber,
    Switch,
    Select,
    message,
    Space,
    Row,
    Col,
    Divider,
    Alert,
    Spin,
    Modal,
} from 'antd';
import { useParams, history, useModel } from '@umijs/max';
import GenerationProgressDisplay, {
    GenerationProgress,
} from '@/components/GenerationProgress';
import { generateTeachingPlanStream } from '@/services/teaching-plan';
import { downloadDocument } from '@/services/document';
import { getCourseDetail } from '@/services/course';

/**
 * 授课计划生成页面
 */
const TeachingPlanGenerate: React.FC = () => {
    const { id: courseId } = useParams<{ id: string }>();
    const { initialState } = useModel('@@initialState');
    const [form] = Form.useForm();
    const [generating, setGenerating] = useState(false);
    const [progress, setProgress] = useState<GenerationProgress | null>(null);
    const [documentId, setDocumentId] = useState<number | null>(null);
    const [fileUrl, setFileUrl] = useState<string | null>(null);
    const [loadingCourse, setLoadingCourse] = useState(true);
    const [course, setCourse] = useState<any>(null);

    // 表单值状态（用于实时计算）
    const [formValues, setFormValues] = useState({
        total_weeks: 18,
        hour_per_class: 4,
        classes_per_week: 1,
        final_review: true,
        first_week_classes: 1,
        skip_slots: [] as Array<{ week: number; class: number }>,
    });
    const [existingDoc, setExistingDoc] = useState<any>(null); // 已有文档

    // 实时计算结果
    const calculateSchedule = () => {
        const maxClasses = formValues.total_weeks * formValues.classes_per_week;
        const maxHours = maxClasses * formValues.hour_per_class;

        // 根据总学时计算实际课次数
        const actualClasses = course ? Math.floor(course.total_hours / formValues.hour_per_class) : maxClasses;
        const actualClassesWithReview = formValues.final_review ? actualClasses - 1 : actualClasses;

        const classesPerWeek = Math.min(Math.max(formValues.classes_per_week || 1, 1), 7);
        const firstWeekClasses = Math.min(
            Math.max(formValues.first_week_classes || 1, 1),
            classesPerWeek,
        );

        const baseAvailableSlots = firstWeekClasses + (formValues.total_weeks - 1) * classesPerWeek;

        const skipSlots = Array.isArray(formValues.skip_slots) ? formValues.skip_slots : [];
        const skipSet = new Set(
            skipSlots
                .filter((item) => item?.week && item?.class)
                .map((item) => `${item.week}-${item.class}`),
        );

        let availableSlots = 0;
        for (let week = 1; week <= formValues.total_weeks; week += 1) {
            const weekLimit = week === 1 ? firstWeekClasses : classesPerWeek;
            for (let cls = 1; cls <= weekLimit; cls += 1) {
                if (skipSet.has(`${week}-${cls}`)) {
                    continue;
                }
                availableSlots += 1;
            }
        }

        const diff = availableSlots - actualClasses;
        const isValid = course ? diff >= 0 && diff <= 6 : true;

        return {
            maxClasses,        // 最大课次（周数 × 每周次数）
            maxHours,          // 最大学时
            actualClasses,     // 实际课次（根据总学时计算）
            actualClassesWithReview, // 考虑复习考核的实际课次
            courseHours: course?.total_hours || 0,
            baseAvailableSlots,
            availableSlots,    // 可用课次（第一周上课次数 + 不上课设置后）
            diff,
            isValid,
        };
    };

    const scheduleInfo = calculateSchedule();
    const showSkipSlots = scheduleInfo.baseAvailableSlots > scheduleInfo.actualClasses;

    useEffect(() => {
        if (!showSkipSlots && formValues.skip_slots.length > 0) {
            form.setFieldsValue({ skip_slots: [] });
            setFormValues((prev) => ({ ...prev, skip_slots: [] }));
        }
    }, [form, formValues.skip_slots.length, showSkipSlots]);

    useEffect(() => {
        loadCourseInfo();
    }, [courseId]);

    const loadCourseInfo = async () => {
        setLoadingCourse(true);
        try {
            const data = await getCourseDetail(Number(courseId));
            setCourse(data.course);

            // 检查是否已有授课计划
            const planDoc = data.documents?.find((doc: any) => doc.doc_type === 'plan');
            setExistingDoc(planDoc || null);

            // 设置默认授课教师为当前用户名
            form.setFieldsValue({
                teacher_name: initialState?.currentUser?.username || '',
            });
        } catch (error) {
            message.error('加载课程信息失败');
        } finally {
            setLoadingCourse(false);
        }
    };

    const handleGenerate = async () => {
        if (!course?.course_catalog) {
            message.error('请先在课程详情页编辑课程目录');
            return;
        }

        try {
            const values = await form.validateFields();
            setGenerating(true);
            setProgress({
                stage: 'preparing',
                progress: 0,
                message: '正在建立连接...',
            });
            setDocumentId(null);
            setFileUrl(null);

            const payload = {
                teacher_name: values.teacher_name,
                total_weeks: values.total_weeks,
                hour_per_class: values.hour_per_class,
                classes_per_week: values.classes_per_week,
                final_review: values.final_review,
                first_week_classes: values.first_week_classes,
                skip_slots: (values.skip_slots || []).filter(
                    (item: { week?: number; class?: number }) => {
                        if (!item?.week || !item?.class) {
                            return false;
                        }
                        if (item.week > values.total_weeks) {
                            return false;
                        }
                        if (item.week === 1 && item.class > values.first_week_classes) {
                            return false;
                        }
                        return item.class <= values.classes_per_week;
                    },
                ),
            };

            await generateTeachingPlanStream(
                Number(courseId),
                payload,
                (progressData: GenerationProgress) => {
                    setProgress(progressData);

                    if (progressData.stage === 'completed') {
                        message.success('授课计划生成成功！');
                        setDocumentId(progressData.document_id || null);
                        setFileUrl(progressData.file_url || null);
                        setGenerating(false);

                        // 更新 existingDoc 状态
                        setExistingDoc({
                            id: progressData.document_id,
                            doc_type: 'plan',
                        });

                        window.dispatchEvent(
                            new CustomEvent('bzyagent:documents-refresh', {
                                detail: { courseId: Number(courseId), docType: 'plan' },
                            })
                        );

                        // 显示成功提示 Modal
                        Modal.success({
                            title: '授课计划生成成功！',
                            content: '您可以下载 Word 文档或返回课程页面。',
                            okText: '知道了',
                            onOk: () => {
                                // 滚动到页面底部，显示操作按钮
                                window.scrollTo({
                                    top: document.body.scrollHeight,
                                    behavior: 'smooth'
                                });
                            }
                        });
                    }
                },
            );
        } catch (error) {
            message.error('生成失败：' + (error as Error).message);
            setGenerating(false);
        }
    };

    const handleDownload = () => {
        if (documentId) {
            downloadDocument(documentId);
            return;
        }
        if (fileUrl) {
            const token = localStorage.getItem('token');
            if (token && fileUrl.startsWith('/api/') && !fileUrl.includes('token=')) {
                const separator = fileUrl.includes('?') ? '&' : '?';
                window.open(`${fileUrl}${separator}token=${encodeURIComponent(token)}`, '_blank');
                return;
            }
            window.open(fileUrl, '_blank');
        }
    };

    if (loadingCourse) {
        return (
            <PageContainer title="生成授课计划">
                <Card>
                    <div style={{ textAlign: 'center', padding: '40px 0' }}>
                        <Spin size="large" />
                        <div style={{ marginTop: 16 }}>正在加载课程信息...</div>
                    </div>
                </Card>
            </PageContainer>
        );
    }

    const hasCatalog = course?.course_catalog && course.course_catalog.trim().length > 0;

    return (
        <PageContainer
            title="生成授课计划"
            extra={
                <Button onClick={() => history.push(`/courses/${courseId}`)}>返回课程</Button>
            }
        >
            <Space direction="vertical" style={{ width: '100%' }} size="large">
                {/* 课程目录检查 */}
                {!hasCatalog ? (
                    <Alert
                        message="缺少课程目录"
                        description={
                            <div>
                                <p>生成授课计划需要先设置课程目录。</p>
                                <Button
                                    type="primary"
                                    onClick={() => history.push(`/courses/${courseId}`)}
                                    style={{ marginTop: 8 }}
                                >
                                    返回课程页面编辑课程目录
                                </Button>
                            </div>
                        }
                        type="warning"
                        showIcon
                    />
                ) : (
                    <>
                        <Alert
                            message="已找到课程目录"
                            description={`将基于课程目录生成授课计划表`}
                            type="success"
                            showIcon
                        />

                        {/* 课程信息卡片 */}
                        <Card title="课程信息">
                            <p><strong>课程名称：</strong>{course.name}</p>
                            <p><strong>授课班级：</strong>{course.class_name}</p>
                            <p><strong>总学时：</strong>{course.total_hours} 学时</p>
                            <p><strong>理论学时：</strong>{course.total_hours - course.practice_hours} 学时</p>
                            <p><strong>实训学时：</strong>{course.practice_hours} 学时</p>
                        </Card>

                        {progress ? (
                            <GenerationProgressDisplay progress={progress} />
                        ) : (
                            <div style={{ display: 'flex', gap: 24 }}>
                                {/* 左侧表单 */}
                                <Card title="生成配置" style={{ flex: 1 }}>
                                    <Form
                                        form={form}
                                        layout="vertical"
                                        initialValues={{
                                            teacher_name: '',
                                            total_weeks: 18,
                                            hour_per_class: 4,
                                            classes_per_week: 1,
                                            final_review: true,
                                            first_week_classes: 1,
                                            skip_slots: [],
                                        }}
                                        onValuesChange={(_, allValues) => {
                                            const nextClassesPerWeek = Math.min(allValues.classes_per_week || 1, 7);
                                            const nextFirstWeekClasses = Math.min(
                                                Math.max(allValues.first_week_classes || 1, 1),
                                                nextClassesPerWeek,
                                            );
                                            if ((allValues.first_week_classes || 1) > nextClassesPerWeek) {
                                                form.setFieldsValue({ first_week_classes: nextFirstWeekClasses });
                                            }
                                            setFormValues({
                                                total_weeks: allValues.total_weeks || 18,
                                                hour_per_class: allValues.hour_per_class || 4,
                                                classes_per_week: nextClassesPerWeek,
                                                final_review: allValues.final_review ?? true,
                                                first_week_classes: nextFirstWeekClasses,
                                                skip_slots: allValues.skip_slots || [],
                                            });
                                        }}
                                    >
                                        <Form.Item
                                            label="授课教师"
                                            name="teacher_name"
                                            rules={[{ required: true, message: '请输入授课教师姓名' }]}
                                        >
                                            <Input placeholder="请输入授课教师姓名" />
                                        </Form.Item>

                                        <Row gutter={[16, 0]}>
                                            <Col xs={24} md={8}>
                                                <Form.Item
                                                    label="总周数"
                                                    name="total_weeks"
                                                    rules={[{ required: true, message: '请输入总周数' }]}
                                                    tooltip="一般为 18 周，根据实际情况调整"
                                                >
                                                    <InputNumber
                                                        min={1}
                                                        max={30}
                                                        placeholder="一般为 18 周"
                                                        style={{ width: '100%' }}
                                                    />
                                                </Form.Item>
                                            </Col>
                                            <Col xs={24} md={8}>
                                                <Form.Item
                                                    label="每周上课次数"
                                                    name="classes_per_week"
                                                    rules={[{ required: true, message: '请输入每周上课次数' }]}
                                                    tooltip="用于计算周次"
                                                >
                                                    <InputNumber
                                                        min={1}
                                                        max={7}
                                                        placeholder="一般为 1 次"
                                                        style={{ width: '100%' }}
                                                    />
                                                </Form.Item>
                                            </Col>
                                            <Col xs={24} md={8}>
                                                <Form.Item
                                                    label="单次学时"
                                                    name="hour_per_class"
                                                    rules={[{ required: true, message: '请选择单次学时' }]}
                                                    tooltip="每次课上多少学时"
                                                >
                                                    <Select
                                                        style={{ width: '100%' }}
                                                        options={[
                                                            { value: 2, label: '2 学时' },
                                                            { value: 4, label: '4 学时' },
                                                            { value: 6, label: '6 学时' },
                                                        ]}
                                                    />
                                                </Form.Item>
                                            </Col>
                                        </Row>

                                        <Row gutter={[16, 0]}>
                                            <Col xs={24} md={8}>
                                                <Form.Item
                                                    label="第一周上课次数"
                                                    name="first_week_classes"
                                                    rules={[{ required: true, message: '请输入第一周上课次数' }]}
                                                    tooltip="第一周上几次课（不考虑星期）"
                                                >
                                                    <InputNumber
                                                        min={1}
                                                        max={formValues.classes_per_week}
                                                        placeholder="第一周上课次数"
                                                        style={{ width: '100%' }}
                                                    />
                                                </Form.Item>
                                            </Col>
                                            <Col xs={24} md={8}>
                                                <Form.Item
                                                    label="最后一次课为复习考核"
                                                    name="final_review"
                                                    valuePropName="checked"
                                                    tooltip="开启后，最后一次课固定为'课程复习与考核'，AI 会少生成一次课的内容"
                                                >
                                                    <Switch />
                                                </Form.Item>
                                            </Col>
                                        </Row>

                                        {showSkipSlots && (
                                            <Form.Item label="不上课设置">
                                                <Form.List name="skip_slots">
                                                    {(fields, { add, remove }) => (
                                                        <div>
                                                            {fields.map((field) => (
                                                                <Row
                                                                    key={field.key}
                                                                    gutter={[12, 0]}
                                                                    align="middle"
                                                                    style={{ marginBottom: 8 }}
                                                                >
                                                                    <Col xs={12} sm={8} md={6}>
                                                                        <Form.Item
                                                                            {...field}
                                                                            name={[field.name, 'week']}
                                                                            rules={[{ required: true, message: '请输入周次' }]}
                                                                        >
                                                                            <InputNumber
                                                                                min={1}
                                                                                max={formValues.total_weeks}
                                                                                placeholder="周次"
                                                                                style={{ width: '100%' }}
                                                                            />
                                                                        </Form.Item>
                                                                    </Col>
                                                                    <Col xs={12} sm={8} md={6}>
                                                                        <Form.Item
                                                                            {...field}
                                                                            name={[field.name, 'class']}
                                                                            rules={[{ required: true, message: '请输入课次' }]}
                                                                        >
                                                                            <InputNumber
                                                                                min={1}
                                                                                max={formValues.classes_per_week}
                                                                                placeholder="课次"
                                                                                style={{ width: '100%' }}
                                                                            />
                                                                        </Form.Item>
                                                                    </Col>
                                                                    <Col xs={24} sm={4} md={4}>
                                                                        <Button
                                                                            type="link"
                                                                            danger
                                                                            onClick={() => remove(field.name)}
                                                                        >
                                                                            移除
                                                                        </Button>
                                                                    </Col>
                                                                </Row>
                                                            ))}
                                                            <Button
                                                                type="dashed"
                                                                onClick={() => add({ week: 1, class: 1 })}
                                                                style={{ width: '100%' }}
                                                            >
                                                                新增不上课
                                                            </Button>
                                                        </div>
                                                    )}
                                                </Form.List>
                                            </Form.Item>
                                        )}

                                        <Form.Item>
                                            <Alert
                                                type="info"
                                                showIcon
                                                message="提示"
                                                description="AI 生成内容仅供参考，请结合课程实际情况核对并适当调整。"
                                            />
                                        </Form.Item>

                                        <Form.Item>
                                            <Button
                                                type="primary"
                                                size="large"
                                                onClick={handleGenerate}
                                                loading={generating}
                                                disabled={generating || !scheduleInfo.isValid}
                                            >
                                                {generating
                                                    ? '生成中...'
                                                    : !scheduleInfo.isValid
                                                        ? '排课参数不足'
                                                        : existingDoc
                                                            ? '重新生成授课计划'
                                                            : '开始生成授课计划'}
                                            </Button>
                                        </Form.Item>
                                    </Form>
                                </Card>

                                {/* 右侧预览 */}
                                <Card title="计划预览" style={{ width: 350 }}>
                                    <Space direction="vertical" style={{ width: '100%' }} size="large">
                                        <div>
                                            <div style={{ color: '#666', marginBottom: 8 }}>最大可排课次</div>
                                            <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1890ff' }}>
                                                {scheduleInfo.maxClasses} 次课
                                            </div>
                                            <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                                                ({formValues.total_weeks} 周 × {formValues.classes_per_week} 次/周)
                                            </div>
                                        </div>

                                        <div>
                                            <div style={{ color: '#666', marginBottom: 8 }}>可用课次</div>
                                            <div style={{ fontSize: 20, fontWeight: 'bold', color: '#722ed1' }}>
                                                {scheduleInfo.availableSlots} 次课
                                            </div>
                                            <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                                                (第一周上课次数与不上课设置后)
                                            </div>
                                        </div>

                                        <div>
                                            <div style={{ color: '#666', marginBottom: 8 }}>实际需要课次</div>
                                            <div style={{ fontSize: 20, fontWeight: 'bold', color: '#52c41a' }}>
                                                {scheduleInfo.actualClasses} 次课
                                            </div>
                                            <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                                                ({scheduleInfo.courseHours} 学时 ÷ {formValues.hour_per_class} 学时/次)
                                            </div>
                                        </div>

                                        <div>
                                            <div style={{ color: '#666', marginBottom: 8 }}>单次学时</div>
                                            <div style={{ fontSize: 20, fontWeight: 'bold' }}>
                                                {formValues.hour_per_class} 学时/次
                                            </div>
                                        </div>

                                        <Divider style={{ margin: '8px 0' }} />

                                        {!scheduleInfo.isValid ? (
                                            <Alert
                                                message="排课参数不足"
                                                description={
                                                    <div>
                                                        课程需要 <strong>{scheduleInfo.actualClasses}</strong> 次课，
                                                        当前可用课次为 <strong>{scheduleInfo.availableSlots}</strong> 次。
                                                        <br />
                                                        差额为 <strong>{Math.abs(scheduleInfo.diff)}</strong> 次，
                                                        差额不能超过 6。
                                                        <br />
                                                        请调整第一周上课次数、每周上课次数或不上课设置。
                                                    </div>
                                                }
                                                type="error"
                                                showIcon
                                            />
                                        ) : (
                                            <Alert
                                                message="配置匹配"
                                                description={
                                                    <div>
                                                        AI 将生成 <strong>{scheduleInfo.actualClassesWithReview}</strong> 次课的内容
                                                        {formValues.final_review && '，最后一次课为复习考核'}
                                                    </div>
                                                }
                                                type="success"
                                                showIcon
                                            />
                                        )}

                                        {formValues.final_review && scheduleInfo.isValid && (
                                            <Alert
                                                message={
                                                    <div>
                                                        AI 将生成 <strong>{scheduleInfo.actualClassesWithReview}</strong> 次课的内容，
                                                        最后一次课自动设为"课程复习与考核"
                                                    </div>
                                                }
                                                type="info"
                                                showIcon
                                            />
                                        )}
                                    </Space>
                                </Card>
                            </div>
                        )}
                    </>
                )}

                {/* 操作按钮 */}
                {documentId && fileUrl && (
                    <Card>
                        <Space>
                            <Button type="primary" onClick={handleDownload}>
                                下载 Word 文档
                            </Button>
                            <Button onClick={() => history.push(`/courses/${courseId}`)}>
                                返回课程页面
                            </Button>
                        </Space>
                    </Card>
                )}
            </Space>
        </PageContainer>
    );
};

export default TeachingPlanGenerate;
