import { useEffect, useState } from 'react';
import { getCurrentUser, logout } from '../services/auth';
import type { User } from '../types/auth';
import './HomePage.css';

interface HomePageProps {
    onLogout: () => void;
}

const HomePage = ({ onLogout }: HomePageProps) => {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        loadUserInfo();
    }, []);

    const loadUserInfo = async () => {
        try {
            const userData = await getCurrentUser();
            setUser(userData);
        } catch (err: any) {
            setError('获取用户信息失败');
        } finally {
            setLoading(false);
        }
    };

    const handleLogout = () => {
        logout();
        onLogout();
    };

    if (loading) {
        return (
            <div className="home-container">
                <div className="loading">加载中...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="home-container">
                <div className="home-content">
                    <div className="error">{error}</div>
                </div>
            </div>
        );
    }

    return (
        <div className="home-container">
            <div className="home-header">
                <h1 className="home-title">BZYAgent</h1>
                <button className="logout-button" onClick={handleLogout}>
                    登出
                </button>
            </div>

            <div className="home-content">
                <div className="user-card">
                    <h2 className="user-card-title">用户信息</h2>
                    {user && (
                        <div className="user-info">
                            <div className="info-row">
                                <span className="info-label">用户 ID:</span>
                                <span className="info-value">{user.id}</span>
                            </div>
                            <div className="info-row">
                                <span className="info-label">用户名:</span>
                                <span className="info-value">{user.username}</span>
                            </div>
                            <div className="info-row">
                                <span className="info-label">创建时间:</span>
                                <span className="info-value">
                                    {new Date(user.created_at).toLocaleString('zh-CN')}
                                </span>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default HomePage;
