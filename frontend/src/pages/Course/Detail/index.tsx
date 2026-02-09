import { PageContainer, ProCard, ProDescriptions } from '@ant-design/pro-components';
import { Button, Image, message, Modal, Tabs, Input, Space, Dropdown, Checkbox, Popover } from 'antd';
import { EditOutlined, DeleteOutlined, ReloadOutlined, SettingOutlined, ColumnHeightOutlined } from '@ant-design/icons';
import { useNavigate, useParams, useIntl } from '@umijs/max';
import { useEffect, useMemo, useState } from 'react';
import { getCourseDetail, deleteCourse, updateCourse, type Course } from '@/services/course';
import SingleDocuments from './components/SingleDocuments';
import MultiDocuments from './components/MultiDocuments';

const { TextArea } = Input;

const CourseDetail: React.FC = () => {
    const navigate = useNavigate();
    const params = useParams<{ id: string }>();
    const intl = useIntl();
    const [course, setCourse] = useState<Course>();
    const [loading, setLoading] = useState(false);
    const [catalogModalOpen, setCatalogModalOpen] = useState(false);
    const [editingCatalog, setEditingCatalog] = useState('');
    const [activeTab, setActiveTab] = useState('single');
    const [tableSize, setTableSize] = useState<'large' | 'middle' | 'small'>('middle');
    const [refreshTick, setRefreshTick] = useState({ lesson: 0, courseware: 0 });
    const [visibleColumns, setVisibleColumns] = useState({
        lesson: {
            lesson_number: true,
            title: true,
            created_at: true,
            actions: true,
        },
        courseware: {
            lesson_number: true,
            title: true,
            created_at: true,
            actions: true,
        },
    });

    useEffect(() => {
        loadCourseDetail();
    }, [params.id]);

    const loadCourseDetail = async () => {
        setLoading(true);
        try {
            const data = await getCourseDetail(Number(params.id));
            // API返回 { course: {...}, documents: [...] }，取出course对象
            setCourse(data.course);
        } catch (error) {
            message.error('加载课程详情失败');
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = () => {
        Modal.confirm({
            title: '确认删除',
            content: `确定要删除课程"${course?.name}"吗？此操作不可恢复。`,
            okText: '确定',
            cancelText: '取消',
            okType: 'danger',
            onOk: async () => {
                try {
                    await deleteCourse(Number(params.id));
                    message.success('删除成功');
                    navigate('/courses');
                } catch (error) {
                    message.error('删除失败');
                }
            },
        });
    };

    const handleEditCatalog = () => {
        setEditingCatalog(course?.course_catalog || '');
        setCatalogModalOpen(true);
    };

    const handleSaveCatalog = async () => {
        try {
            await updateCourse(Number(params.id), {
                course_catalog: editingCatalog,
            });
            message.success('课程目录更新成功');
            setCatalogModalOpen(false);
            // 重新加载数据
            loadCourseDetail();
        } catch (error) {
            message.error('更新失败');
        }
    };

    const densityMenu = useMemo(
        () => ({
            items: [
                { key: 'large', label: '宽松' },
                { key: 'middle', label: '默认' },
                { key: 'small', label: '紧凑' },
            ],
            onClick: ({ key }: { key: 'large' | 'middle' | 'small' }) => {
                setTableSize(key);
            },
        }),
        [],
    );

    const columnOptions = useMemo(
        () => [
            { label: intl.formatMessage({ id: 'pages.courses.documents.lessonNumber' }), value: 'lesson_number' },
            { label: intl.formatMessage({ id: 'pages.courses.documents.title' }), value: 'title' },
            { label: intl.formatMessage({ id: 'pages.courses.documents.createdAt' }), value: 'created_at' },
            { label: intl.formatMessage({ id: 'pages.courses.documents.actions' }), value: 'actions' },
        ],
        [intl],
    );

    const tabExtra = useMemo(() => {
        if (activeTab !== 'lesson' && activeTab !== 'courseware') {
            return null;
        }

        const isLesson = activeTab === 'lesson';
        const currentVisible = visibleColumns[activeTab as 'lesson' | 'courseware'];
        const checkedValues = columnOptions
            .filter((option) => currentVisible[option.value])
            .map((option) => option.value);

        return (
            <Space>
                <Button
                    type="primary"
                    onClick={() =>
                        isLesson
                            ? navigate(`/courses/${params.id}/lesson-plan/generate`)
                            : message.info('新建功能开发中')
                    }
                >
                    {isLesson ? '新建教案' : '新建课件'}
                </Button>
                {(isLesson || activeTab === 'courseware') && (
                    <Button
                        onClick={() =>
                            window.dispatchEvent(
                                new CustomEvent('bzyagent:documents-upload', {
                                    detail: {
                                        courseId: Number(params.id),
                                        docType: isLesson ? 'lesson' : 'courseware',
                                    },
                                }),
                            )
                        }
                    >
                        {isLesson ? '上传教案' : '上传课件'}
                    </Button>
                )}
                <Button
                    icon={<ReloadOutlined />}
                    onClick={() =>
                        setRefreshTick((prev) => ({
                            ...prev,
                            [activeTab]: prev[activeTab as 'lesson' | 'courseware'] + 1,
                        }))
                    }
                />
                <Dropdown menu={densityMenu} placement="bottomRight">
                    <Button icon={<ColumnHeightOutlined />} />
                </Dropdown>
                <Popover
                    placement="bottomRight"
                    trigger="click"
                    content={
                        <Checkbox.Group
                            value={checkedValues}
                            options={columnOptions}
                            onChange={(values) => {
                                setVisibleColumns((prev) => ({
                                    ...prev,
                                    [activeTab]: columnOptions.reduce<Record<string, boolean>>(
                                        (acc, option) => {
                                            acc[option.value] = values.includes(option.value);
                                            return acc;
                                        },
                                        {},
                                    ),
                                }));
                            }}
                        />
                    }
                >
                    <Button icon={<SettingOutlined />} />
                </Popover>
            </Space>
        );
    }, [activeTab, columnOptions, densityMenu, message, navigate, params.id, visibleColumns]);

    if (!course) {
        return <PageContainer loading={loading} />;
    }

    const theoryHours = course.total_hours - course.practice_hours;

    return (
        <PageContainer
            header={{
                title: course.name,
                subTitle: course.semester,
                onBack: () => navigate('/courses'),
                extra: [
                    <Button
                        key="edit"
                        icon={<EditOutlined />}
                        onClick={() => navigate(`/courses/${params.id}/edit`)}
                    >
                        {intl.formatMessage({ id: 'pages.courses.detail.editCourse' })}
                    </Button>,
                    <Button
                        key="delete"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={handleDelete}
                    >
                        {intl.formatMessage({ id: 'pages.courses.detail.deleteCourse' })}
                    </Button>,
                ],
            }}
            breadcrumb={false}
            loading={loading}
        >
            {/* 课程信息卡片 */}
            <ProCard style={{ marginBottom: 24 }}>
                <div style={{ display: 'flex', gap: 24 }}>
                    {/* 左侧：教材图片 */}
                    <div style={{ flex: '0 0 200px' }}>
                        <Image
                            src={course.textbook_image}
                            alt={course.textbook_name}
                            style={{ width: 200, height: 280, objectFit: 'cover' }}
                        />
                    </div>

                    {/* 右侧：课程详细信息 */}
                    <div style={{ flex: 1 }}>
                        <ProDescriptions
                            column={2}
                            dataSource={course}
                            columns={[
                                {
                                    title: intl.formatMessage({ id: 'pages.courses.list.semester' }),
                                    dataIndex: 'semester',
                                },
                                {
                                    title: intl.formatMessage({ id: 'pages.courses.list.class' }),
                                    dataIndex: 'class_name',
                                },
                                {
                                    title: intl.formatMessage({ id: 'pages.courses.detail.totalHours' }),
                                    render: () => `${course.total_hours} 学时`,
                                },
                                {
                                    title: intl.formatMessage({ id: 'pages.courses.detail.practiceHours' }),
                                    render: () => `${course.practice_hours} 学时`,
                                },
                                {
                                    title: intl.formatMessage({ id: 'pages.courses.detail.theoryHours' }),
                                    render: () => `${theoryHours} 学时`,
                                },
                                {
                                    title: intl.formatMessage({ id: 'pages.courses.detail.courseType' }),
                                    render: () => `${course.course_type}类课程`,
                                },
                                {
                                    title: intl.formatMessage({ id: 'pages.courses.detail.isbn' }),
                                    dataIndex: 'textbook_isbn',
                                    span: 2,
                                },
                                {
                                    title: intl.formatMessage({ id: 'pages.courses.create.textbookName.label' }),
                                    dataIndex: 'textbook_name',
                                    span: 2,
                                },
                                {
                                    title: intl.formatMessage({ id: 'pages.courses.detail.publisher' }),
                                    dataIndex: 'textbook_publisher',
                                    span: 2,
                                    render: (text) => text || '-',
                                },
                                {
                                    title: intl.formatMessage({ id: 'pages.courses.detail.link' }),
                                    dataIndex: 'textbook_link',
                                    span: 2,
                                    render: (text) => text ? (
                                        <a href={text} target="_blank" rel="noopener noreferrer">{text}</a>
                                    ) : '-',
                                },
                            ]}
                        />
                    </div>
                </div>
            </ProCard>

            {/* 文档管理区 */}
            <ProCard title={intl.formatMessage({ id: 'pages.courses.detail.documents' })}>
                <Tabs
                    defaultActiveKey="single"
                    onChange={setActiveTab}
                    tabBarExtraContent={tabExtra ? { right: tabExtra } : undefined}
                    items={[
                        {
                            key: 'single',
                            label: '单份文档',
                            children: <SingleDocuments courseId={Number(params.id)} />,
                        },
                        {
                            key: 'catalog',
                            label: '课程目录',
                            children: (
                                <div>
                                    <div style={{ marginBottom: 16 }}>
                                        <Button
                                            type="primary"
                                            icon={<EditOutlined />}
                                            onClick={handleEditCatalog}
                                        >
                                            编辑课程目录
                                        </Button>
                                    </div>
                                    <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
                                        {course?.course_catalog || '暂无课程目录'}
                                    </div>
                                </div>
                            ),
                        },
                        {
                            key: 'lesson',
                            label: intl.formatMessage({ id: 'pages.courses.documents.lesson' }),
                            children: (
                                <MultiDocuments
                                    courseId={Number(params.id)}
                                    docType="lesson"
                                    refreshKey={refreshTick.lesson}
                                    size={tableSize}
                                    visibleColumns={visibleColumns.lesson}
                                />
                            ),
                        },
                        {
                            key: 'courseware',
                            label: intl.formatMessage({ id: 'pages.courses.documents.courseware' }),
                            children: (
                                <MultiDocuments
                                    courseId={Number(params.id)}
                                    docType="courseware"
                                    refreshKey={refreshTick.courseware}
                                    size={tableSize}
                                    visibleColumns={visibleColumns.courseware}
                                />
                            ),
                        },
                    ]}
                />
            </ProCard>

            {/* 课程目录编辑Modal */}
            <Modal
                title="编辑课程目录"
                open={catalogModalOpen}
                onOk={handleSaveCatalog}
                onCancel={() => setCatalogModalOpen(false)}
                width={800}
                okText="保存"
                cancelText="取消"
            >
                <TextArea
                    value={editingCatalog}
                    onChange={(e) => setEditingCatalog(e.target.value)}
                    rows={20}
                    placeholder="请输入课程目录"
                />
            </Modal>
        </PageContainer>
    );
};

export default CourseDetail;
