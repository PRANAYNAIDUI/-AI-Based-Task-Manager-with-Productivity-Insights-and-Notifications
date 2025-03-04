// src/App.js
import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import TaskList from './components/TaskList';
import TaskForm from './components/TaskForm';
import Insights from './components/Insights';
import Settings from './components/Settings';
import Navbar from './components/Navbar';
import Login from './components/Login';
import './App.css';

// For demo purposes - in a real app, this would come from authentication
const DEFAULT_USER_ID = 'user-1';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userId, setUserId] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [insights, setInsights] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  // Simulated login for demo
  const handleLogin = (email, password) => {
    // In a real app, this would make an API call to authenticate
    setUserId(DEFAULT_USER_ID);
    setIsLoggedIn(true);
    localStorage.setItem('userId', DEFAULT_USER_ID);
  };

  // Load user ID from local storage on app start
  useEffect(() => {
    const storedUserId = localStorage.getItem('userId');
    if (storedUserId) {
      setUserId(storedUserId);
      setIsLoggedIn(true);
    }
    setIsLoading(false);
  }, []);

  // Fetch tasks when user ID changes
  useEffect(() => {
    if (userId) {
      fetchTasks();
      fetchInsights();
    }
  }, [userId]);

  const fetchTasks = async () => {
    try {
      const response = await fetch(`http://localhost:5000/api/tasks?user_id=${userId}`);
      if (response.ok) {
        const data = await response.json();
        setTasks(data);
      }
    } catch (error) {
      console.error('Error fetching tasks:', error);
    }
  };

  const fetchInsights = async () => {
    try {
      const response = await fetch(`http://localhost:5000/api/insights?user_id=${userId}`);
      if (response.ok) {
        const data = await response.json();
        setInsights(data);
      }
    } catch (error) {
      console.error('Error fetching insights:', error);
    }
  };

  const addTask = async (taskData) => {
    try {
      const response = await fetch('http://localhost:5000/api/tasks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...taskData,
          user_id: userId,
        }),
      });

      if (response.ok) {
        fetchTasks();
        fetchInsights();
        return true;
      }
      return false;
    } catch (error) {
      console.error('Error adding task:', error);
      return false;
    }
  };

  const updateTask = async (taskId, taskData) => {
    try {
      const response = await fetch(`http://localhost:5000/api/tasks/${taskId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...taskData,
          user_id: userId,
        }),
      });

      if (response.ok) {
        fetchTasks();
        fetchInsights();
        return true;
      }
      return false;
    } catch (error) {
      console.error('Error updating task:', error);
      return false;
    }
  };

  const deleteTask = async (taskId) => {
    try {
      const response = await fetch(`http://localhost:5000/api/tasks/${taskId}?user_id=${userId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        fetchTasks();
        fetchInsights();
        return true;
      }
      return false;
    } catch (error) {
      console.error('Error deleting task:', error);
      return false;
    }
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setUserId(null);
    localStorage.removeItem('userId');
  };

  if (isLoading) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <Router>
      <div className="app">
        {isLoggedIn ? (
          <>
            <Navbar onLogout={handleLogout} />
            <div className="container">
              <Routes>
                <Route
                  path="/"
                  element={<Dashboard tasks={tasks} insights={insights} onUpdateTask={updateTask} />}
                />
                <Route
                  path="/tasks"
                  element={
                    <TaskList
                      tasks={tasks}
                      onDelete={deleteTask}
                      onUpdate={updateTask}
                    />
                  }
                />
                <Route
                  path="/add-task"
                  element={<TaskForm onSubmit={addTask} />}
                />
                <Route
                  path="/edit-task/:taskId"
                  element={<TaskForm tasks={tasks} onSubmit={updateTask} isEditing={true} />}
                />
                <Route
                  path="/insights"
                  element={<Insights insights={insights} tasks={tasks} />}
                />
                <Route
                  path="/settings"
                  element={<Settings userId={userId} />}
                />
                <Route
                  path="*"
                  element={<Navigate to="/" replace />}
                />
              </Routes>
            </div>
          </>
        ) : (
          <Login onLogin={handleLogin} />
        )}
      </div>
    </Router>
  );
}

export default App;

// src/App.css
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background-color: #f5f7fa;
  color: #333;
}

.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  flex-grow: 1;
}

.card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  padding: 20px;
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 15px;
}

label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
}

input, select, textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
}

button {
  padding: 10px 15px;
  background-color: #4a6cf7;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
}

button:hover {
  background-color: #3a5cf7;
}

button.secondary {
  background-color: #6c757d;
}

button.secondary:hover {
  background-color: #5a6268;
}

button.danger {
  background-color: #dc3545;
}

button.danger:hover {
  background-color: #c82333;
}

.loading {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  font-size: 20px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.task-priority-1 {
  border-left: 4px solid #dc3545;
}

.task-priority-2 {
  border-left: 4px solid #fd7e14;
}

.task-priority-3 {
  border-left: 4px solid #ffc107;
}

.task-priority-4 {
  border-left: 4px solid #20c997;
}

.task-priority-5 {
  border-left: 4px solid #6c757d;
}

.task-completed {
  opacity: 0.7;
  text-decoration: line-through;
}

// src/components/Navbar.js
import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import './Navbar.css';

function Navbar({ onLogout }) {
  const location = useLocation();

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <span className="brand-text">AI Task Manager</span>
      </div>
      <ul className="navbar-nav">
        <li className={location.pathname === '/' ? 'active' : ''}>
          <Link to="/">Dashboard</Link>
        </li>
        <li className={location.pathname === '/tasks' ? 'active' : ''}>
          <Link to="/tasks">Tasks</Link>
        </li>
        <li className={location.pathname === '/add-task' ? 'active' : ''}>
          <Link to="/add-task">Add Task</Link>
        </li>
        <li className={location.pathname === '/insights' ? 'active' : ''}>
          <Link to="/insights">Insights</Link>
        </li>
        <li className={location.pathname === '/settings' ? 'active' : ''}>
          <Link to="/settings">Settings</Link>
        </li>
      </ul>
      <div className="navbar-actions">
        <button onClick={onLogout} className="btn-logout">
          Logout
        </button>
      </div>
    </nav>
  );
}

export default Navbar;

// src/components/Navbar.css
.navbar {
  display: flex;
  align-items: center;
  background-color: #4a6cf7;
  color: white;
  padding: 0 20px;
  height: 70px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.navbar-brand {
  font-size: 24px;
  font-weight: bold;
  margin-right: 40px;
}

.navbar-nav {
  display: flex;
  list-style: none;
  margin: 0;
  padding: 0;
  flex-grow: 1;
}

.navbar-nav li {
  margin-right: 20px;
  position: relative;
}

.navbar-nav li a {
  color: white;
  text-decoration: none;
  font-size: 16px;
  padding: 10px 0;
  display: block;
  position: relative;
}

.navbar-nav li a:after {
  content: '';
  position: absolute;
  width: 0;
  height: 2px;
  background: white;
  left: 0;
  bottom: 0;
  transition: width 0.3s;
}

.navbar-nav li a:hover:after {
  width: 100%;
}

.navbar-nav li.active a:after {
  width: 100%;
}

.navbar-actions {
  margin-left: auto;
}

.btn-logout {
  background-color: transparent;
  border: 1px solid white;
  color: white;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.btn-logout:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

// src/components/Login.js
import React, { useState } from 'react';
import './Login.css';

function Login({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    onLogin(email, password);
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h1>AI Task Manager</h1>
        <p className="subtitle">Productivity powered by artificial intelligence</p>
        
        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
              required
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
            />
          </div>
          
          <button type="submit" className="btn-login">
            Login
          </button>
        </form>
        
        <div className="login-footer">
          <p>For demo purposes, any email and password will work</p>
        </div>
      </div>
    </div>
  );
}

export default Login;

// src/components/Login.css
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f5f7fa;
}

.login-card {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  padding: 40px;
  width: 100%;
  max-width: 400px;
  text-align: center;
}

.login-card h1 {
  margin-bottom: 10px;
  color: #4a6cf7;
}

.subtitle {
  color: #6c757d;
  margin-bottom: 30px;
}

.login-form {
  text-align: left;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
}

.form-group input {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
  transition: border-color 0.3s;
}

.form-group input:focus {
  border-color: #4a6cf7;
  outline: none;
}

.btn-login {
  width: 100%;
  padding: 12px;
  background-color: #4a6cf7;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s;
  margin-top: 10px;
}

.btn-login:hover {
  background-color: #3a5cf7;
}

.login-footer {
  margin-top: 30px;
  color: #6c757d;
  font-size: 14px;
}

// src/components/Dashboard.js
import React from 'react';
import { Link } from 'react-router-dom';
import TaskSummary from './TaskSummary';
import InsightWidget from './InsightWidget';
import './Dashboard.css';

function Dashboard({ tasks, insights, onUpdateTask }) {
  // Calculate task statistics
  const totalTasks = tasks.length;
  const completedTasks = tasks.filter(task => task.status === 'completed').length;
  const pendingTasks = totalTasks - completedTasks;
  
  // Calculate tasks due today
  const today = new Date().toISOString().split('T')[0];
  const tasksDueToday = tasks.filter(task => 
    task.status !== 'completed' && 
    task.due_date && 
    task.due_date.startsWith(today)
  );
  
  // Get high priority tasks
  const highPriorityTasks = tasks.filter(task => 
    task.status !== 'completed' && 
    (task.priority === 1 || task.priority === 2)
  );

  return (
    <div className="dashboard">
      <h1>Dashboard</h1>
      
      <div className="stats-container">
        <div className="stat-card">
          <h3>Total Tasks</h3>
          <div className="stat-value">{totalTasks}</div>
        </div>
        <div className="stat-card">
          <h3>Completed</h3>
          <div className="stat-value">{completedTasks}</div>
        </div>
        <div className="stat-card">
          <h3>Pending</h3>
          <div className="stat-value">{pendingTasks}</div>
        </div>
        <div className="stat-card">
          <h3>Completion Rate</h3>
          <div className="stat-value">
            {totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0}%
          </div>
        </div>
      </div>
      
      <div className="dashboard-grid">
        <div className="dashboard-column">
          <div className="card">
            <div className="card-header">
              <h2>Due Today ({tasksDueToday.length})</h2>
              <Link to="/tasks" className="view-all">View All</Link>
            </div>
            {tasksDueToday.length > 0 ? (
              <div className="task-list">
                {tasksDueToday.map(task => (
                  <TaskSummary 
                    key={task.id} 
                    task={task} 
                    onUpdate={onUpdateTask} 
                  />
                ))}
              </div>
            ) : (
              <p className="empty-state">No tasks due today!</p>
            )}
          </div>
          
          <div className="card">
            <div className="card-header">
              <h2>High Priority ({highPriorityTasks.length})</h2>
              <Link to="/tasks" className="view-all">View All</Link>
            </div>
            {highPriorityTasks.length > 0 ? (
              <div className="task-list">
                {highPriorityTasks.slice(0, 5).map(task => (
                  <TaskSummary 
                    key={task.id} 
                    task={task} 
                    onUpdate={onUpdateTask} 
                  />
                ))}
              </div>
            ) : (
              <p className="empty-state">No high priority tasks!</p>
            )}
          </div>
        </div>
        
        <div className="dashboard-column">
          <div className="card">
            <div className="card-header">
              <h2>AI Insights</h2>
              <Link to="/insights" className="view-all">View All</Link>
            </div>
            {insights.length > 0 ? (
              <div className="insights-list">
                {insights.slice(0, 3).map(insight => (
                  <InsightWidget key={insight.id} insight={insight} />
                ))}
              </div>
            ) : (
              <p className="empty-state">Complete more tasks to generate insights!</p>
            )}
          </div>
          
          <div className="card">
            <div className="card-header">
              <h2>Quick Actions</h2>
            </div>
            <div className="quick-actions">
              <Link to="/add-task" className="quick-action-btn">
                Add New Task
              </Link>
              <Link to="/insights" className="quick-action-btn secondary">
                View Productivity Insights
              </Link>
              <Link to="/settings" className="quick-action-btn secondary">
                Notification Settings
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;

// src/components/Dashboard.css
.dashboard h1 {
  margin-bottom: 24px;
}

.stats-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  padding: 20px;
  text-align: center;
}

.stat-card h3 {
  color: #6c757d;
  font-size: 16px;
  margin-bottom: 10px;
}

.stat-value {
  font-size: 36px;
  font-weight: bold;
  color: #4a6cf7;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 768px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}

.dashboard-column {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-header h2 {
  margin: 0;
  font-size: 20px;
}

.view-all {
  color: #4a6cf7;
  text-decoration: none;
  font-size: 14px;
}

.task-list, .insights-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.empty-state {
  color: #6c757d;
  text-align: center;
  padding: 20px 0;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.quick-action-btn {
  padding: 12px 16px;
  background-color: #4a6cf7;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  text-align: center;
  text-decoration: none;
  font-size: 16px;
  transition: background-color 0.3s;
}

.quick-action-btn:hover {
  background-color: #3a5cf7;
}

.quick-action-btn.secondary {
  background-color: #6c757d;
}

.quick-action-btn.secondary:hover {
  background-color: #5a6268;
}

// src/components/TaskSummary.js
import React from 'react';
import { Link } from 'react-router-dom';
import './TaskSummary.css';

function TaskSummary({ task, onUpdate }) {
  const handleStatusChange = () => {
    onUpdate(task.id, {
      ...task,
      status: task.status === 'completed' ? 'pending' : 'completed',
      completed_at: task.status === 'completed' ? null : new Date().toISOString()
    });
  };

  const getPriorityLabel = (priority) => {
    switch(priority) {
      case 1: return 'Highest';
      case 2: return 'High';
      case 3: return 'Medium';
      case 4: return 'Low';
      case 5: return 'Lowest';
      default: return 'Medium';
    }
  };

  const formatDueDate = (dueDate) => {
    if (!dueDate) return 'No due date';
    
    const date = new Date(dueDate);
    const today = new Date();
    const tomorrow = new Date();
    tomorrow.setDate(today.getDate() + 1);
    
    if (date.toDateString() === today.toDateString()) {
      return 'Today';
    } else if (date.toDateString() === tomorrow.toDateString()) {
      return 'Tomorrow';
    } else {
      return date.toLocaleDateString();
    }
  };

  const isPastDue = () => {
    if (!task.due_date || task.status === 'completed') return false;
    const dueDate = new Date(task.due_date);
    const now = new Date();
    return dueDate < now;
  };

  return (
    <div className={`task-summary ${task.status === 'completed' ? 'completed' : ''} priority-${task.priority || 3}`}>
      <div className="task-checkbox">
        <input
          type="checkbox"
          checked={task.status === 'completed'}
          onChange={handleStatusChange}
        />
      </div>
      <div className="task-content">
        <div className="task-title">{task.title}</div>
        <div className="task-details">
          <span className="task-category">{task.category || 'Uncategorized'}</span>
          <span className="task-priority">{getPriorityLabel(task.priority)}</span>
          <span className={`task-due-date ${isPastDue() ? 'overdue' : ''}`}>
            {isPastDue() ? 'Overdue' : formatDueDate(task.due_date)}
          </span>
        </div>
      </div>
      <div className="task-actions">
        <Link to={`/edit-task/${task.id}`} className="task-edit-link">Edit</Link>
      </div>
    </div>
  );
}

export default TaskSummary;

// src/components/TaskSummary.css
.task-summary {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background-color: #f8f9fa;
  border-radius: 6px;
  border-left: 4px solid #6c757d;
  transition: background-color 0.2s;
}

.task-summary:hover {
  background-color: #f1f3f5;
}

.task-summary.completed {
  opacity: 0.7;
}

.task-summary.completed .task-title {
  text-decoration: line-through;
}

.task-summary.priority-1 {
  border-left-color: #dc3545;
}

.task-summary.priority-2 {
  border-left-color: #fd7e14;
}

.task-summary.priority-3 {
  border-left-color: #ffc107;
}

.task-summary.priority-4 {
  border-left-color: #20c997;
}

.task-summary.priority-5 {
  border-left-color: #6c757d;
}

.task-checkbox {
  margin-right: 16px;
}

.task-checkbox input {
  width: 20px;
  height: 20px;
}

.task-content {
  flex-grow: 1;
}

.task-title {
  font-weight: 500;
  margin-bottom: 4px;
}

.task-details {
  display: flex;
  gap: 12px;
  font-size: 13px;
  color: #6c757d;
}

.task-category {
  background-color: #e9ecef;
  border-radius: 12px;
  padding: 2px 8px;
}

.task-priority {
  background-color: #e9ecef;
  border-radius: 12px;
  padding: 2px 8px;
}

.task-due-date {
  background-color: #e9ecef;
  border-radius: 12px;
  padding: 2px 8px;
}

.task-due-date.overdue {
  background-color: #f8d7da;
  color: #dc3545;
}

.task-actions {
  display: flex;
  gap: 8px;
}

.task-edit-link {
  color: #4a6cf7;
  text-decoration: none;
  font-size: 14px;
}

.task-edit-link:hover {
  text-decoration: underline;
}

// src/components/InsightWidget.js
import React from 'react';
import './InsightWidget.css';

function InsightWidget({ insight }) {
  const getInsightIcon = (type) => {
    switch(type) {
      case 'productive_time':
        return '⏰';
      case 'completion_rate':
        return '📊';
      case 'category_performance':
        return '🏆';
      case 'task_recommendations':
        return '🧠';
      default:
        return '💡';
    }
  };

  const getInsightTitle = (type) => {
    switch(type) {
      case 'productive_time':
        return 'Productive Hours';
      case 'completion_rate':
        return 'Task Completion';
      case 'category_performance':
        return 'Category Performance';
      case 'task_recommendations':
        return 'Recommended Tasks';
      default:
        return 'Insight';
    }
  };

  return (
    <div className="insight-widget">
      <div className="insight-icon">
        {getInsightIcon(insight.insight_type)}
      </div>
      <div className="insight-content">
        <div className="insight-title">
          {getInsightTitle(insight.insight_type)}
        </div>
        <div className="insight-message">
          {insight.insight_data.message}
        </div>
      </div>
    </div>
  );
}

export default InsightWidget;

// src/components/InsightWidget.css
.insight-widget {
  display: flex;
  padding: 16px;
  background-color: #f8f9fa;
  border-radius: 8px;
  transition: transform 0.2s;
}

.insight-widget:hover {
  transform: translateY(-2px);
}

.insight-icon {
  font-size: 24px;
  margin-right: 16px;
  display: flex;
  align-items: center;
}

.insight-content {
  flex-grow: 1;
}

.insight-title {
  font-weight: 600;
  margin-bottom: 4px;
}

.insight-message {
  color: #495057;
  font