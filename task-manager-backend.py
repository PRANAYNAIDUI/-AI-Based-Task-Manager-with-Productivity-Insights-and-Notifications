# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import datetime
import json
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import uuid
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
CORS(app)

# Initialize database
def init_db():
    conn = sqlite3.connect('taskmanager.db')
    cursor = conn.cursor()
    
    # Tasks table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        category TEXT,
        priority INTEGER,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        due_date TIMESTAMP,
        completed_at TIMESTAMP,
        recurring_type TEXT,
        parent_task_id TEXT,
        user_id TEXT NOT NULL
    )
    ''')
    
    # User activity logs for AI insights
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        task_id TEXT,
        action_type TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        metadata TEXT
    )
    ''')
    
    # Notification settings
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notification_settings (
        user_id TEXT PRIMARY KEY,
        enable_push BOOLEAN DEFAULT 1,
        focus_hours TEXT,
        notification_frequency TEXT DEFAULT 'medium'
    )
    ''')
    
    # User productivity insights
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS productivity_insights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        insight_type TEXT NOT NULL,
        insight_data TEXT NOT NULL,
        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# Task CRUD operations
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400
    
    conn = sqlite3.connect('taskmanager.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tasks WHERE user_id = ? ORDER BY due_date", (user_id,))
    tasks = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return jsonify(tasks)

@app.route('/api/tasks', methods=['POST'])
def create_task():
    data = request.json
    
    # Validate required fields
    if not data.get('title') or not data.get('user_id'):
        return jsonify({"error": "Title and user_id are required"}), 400
    
    task_id = str(uuid.uuid4())
    
    conn = sqlite3.connect('taskmanager.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO tasks (id, title, description, category, priority, due_date, recurring_type, parent_task_id, user_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        task_id,
        data.get('title'),
        data.get('description'),
        data.get('category'),
        data.get('priority', 3),  # Default priority medium (3)
        data.get('due_date'),
        data.get('recurring_type'),
        data.get('parent_task_id'),
        data.get('user_id')
    ))
    
    # Log task creation for AI insights
    cursor.execute('''
    INSERT INTO user_activity (user_id, task_id, action_type, metadata)
    VALUES (?, ?, ?, ?)
    ''', (
        data.get('user_id'),
        task_id,
        'task_created',
        json.dumps({
            'category': data.get('category'),
            'priority': data.get('priority', 3),
            'has_due_date': data.get('due_date') is not None
        })
    ))
    
    conn.commit()
    
    # Generate AI recommendations based on this new task
    generate_task_insights(data.get('user_id'))
    
    conn.close()
    
    return jsonify({"id": task_id, "message": "Task created successfully"}), 201

@app.route('/api/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400
    
    conn = sqlite3.connect('taskmanager.db')
    cursor = conn.cursor()
    
    # First verify the task belongs to the user
    cursor.execute("SELECT id FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "Task not found or access denied"}), 404
    
    # Fields that can be updated
    update_fields = []
    values = []
    
    for field in ['title', 'description', 'category', 'priority', 'status', 'due_date', 'recurring_type']:
        if field in data:
            update_fields.append(f"{field} = ?")
            values.append(data[field])
    
    # Handle task completion separately
    if data.get('status') == 'completed' and 'status' in data:
        update_fields.append("completed_at = ?")
        values.append(datetime.datetime.now().isoformat())
        
        # Log task completion for AI insights
        cursor.execute('''
        INSERT INTO user_activity (user_id, task_id, action_type, metadata)
        VALUES (?, ?, ?, ?)
        ''', (
            user_id,
            task_id,
            'task_completed',
            json.dumps({
                'completion_time': datetime.datetime.now().isoformat(),
                'original_due_date': data.get('original_due_date')
            })
        ))
    
    if not update_fields:
        conn.close()
        return jsonify({"error": "No valid fields to update"}), 400
    
    # Construct and execute the update query
    query = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = ? AND user_id = ?"
    values.extend([task_id, user_id])
    
    cursor.execute(query, values)
    conn.commit()
    
    # Log task update for AI insights
    cursor.execute('''
    INSERT INTO user_activity (user_id, task_id, action_type, metadata)
    VALUES (?, ?, ?, ?)
    ''', (
        user_id,
        task_id,
        'task_updated',
        json.dumps({field: data[field] for field in data if field not in ['user_id', 'id']})
    ))
    
    conn.commit()
    
    # Re-generate insights after significant updates
    if 'status' in data or 'priority' in data or 'due_date' in data:
        generate_task_insights(user_id)
    
    conn.close()
    return jsonify({"message": "Task updated successfully"})

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400
    
    conn = sqlite3.connect('taskmanager.db')
    cursor = conn.cursor()
    
    # First verify the task belongs to the user
    cursor.execute("SELECT id FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "Task not found or access denied"}), 404
    
    cursor.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    
    # Log task deletion for AI insights
    cursor.execute('''
    INSERT INTO user_activity (user_id, task_id, action_type)
    VALUES (?, ?, ?)
    ''', (user_id, task_id, 'task_deleted'))
    
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Task deleted successfully"})

# AI Productivity Insights
@app.route('/api/insights', methods=['GET'])
def get_insights():
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400
    
    conn = sqlite3.connect('taskmanager.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT * FROM productivity_insights 
    WHERE user_id = ? 
    ORDER BY generated_at DESC 
    LIMIT 10
    """, (user_id,))
    
    insights = [dict(row) for row in cursor.fetchall()]
    
    # Parse JSON data in insights
    for insight in insights:
        insight['insight_data'] = json.loads(insight['insight_data'])
    
    conn.close()
    return jsonify(insights)

def generate_task_insights(user_id):
    """Generate AI-driven productivity insights for the user"""
    conn = sqlite3.connect('taskmanager.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get user's completed tasks
    cursor.execute("""
    SELECT * FROM tasks 
    WHERE user_id = ? AND status = 'completed'
    ORDER BY completed_at DESC
    """, (user_id,))
    
    completed_tasks = [dict(row) for row in cursor.fetchall()]
    
    # Get user's pending tasks
    cursor.execute("""
    SELECT * FROM tasks 
    WHERE user_id = ? AND status = 'pending'
    ORDER BY due_date ASC
    """, (user_id,))
    
    pending_tasks = [dict(row) for row in cursor.fetchall()]
    
    # Get user activity logs
    cursor.execute("""
    SELECT * FROM user_activity 
    WHERE user_id = ? 
    ORDER BY timestamp DESC
    LIMIT 100
    """, (user_id,))
    
    activity_logs = [dict(row) for row in cursor.fetchall()]
    
    insights = []
    
    # Only generate insights if we have enough data
    if len(completed_tasks) > 5:
        # 1. Most productive time of day
        productive_time = analyze_productive_time(completed_tasks, activity_logs)
        if productive_time:
            insights.append({
                'user_id': user_id,
                'insight_type': 'productive_time',
                'insight_data': json.dumps(productive_time)
            })
        
        # 2. Task completion rate
        completion_rate = analyze_completion_rate(completed_tasks, pending_tasks)
        if completion_rate:
            insights.append({
                'user_id': user_id,
                'insight_type': 'completion_rate',
                'insight_data': json.dumps(completion_rate)
            })
        
        # 3. Category performance
        category_performance = analyze_category_performance(completed_tasks)
        if category_performance:
            insights.append({
                'user_id': user_id,
                'insight_type': 'category_performance',
                'insight_data': json.dumps(category_performance)
            })
        
        # 4. Recommended task order
        if len(pending_tasks) > 1:
            task_recommendations = recommend_task_order(pending_tasks, completed_tasks)
            if task_recommendations:
                insights.append({
                    'user_id': user_id,
                    'insight_type': 'task_recommendations',
                    'insight_data': json.dumps(task_recommendations)
                })
    
    # Save insights to database
    for insight in insights:
        cursor.execute("""
        INSERT INTO productivity_insights (user_id, insight_type, insight_data)
        VALUES (?, ?, ?)
        """, (insight['user_id'], insight['insight_type'], insight['insight_data']))
    
    conn.commit()
    conn.close()
    
    # Schedule notification based on insights
    schedule_smart_notifications(user_id)

def analyze_productive_time(completed_tasks, activity_logs):
    """Analyze most productive times of day based on task completion"""
    if not completed_tasks:
        return None
    
    completion_hours = []
    
    for task in completed_tasks:
        if task['completed_at']:
            try:
                completion_time = datetime.datetime.fromisoformat(task['completed_at'])
                completion_hours.append(completion_time.hour)
            except (ValueError, TypeError):
                continue
    
    if not completion_hours:
        return None
    
    # Count completions by hour
    hour_counts = {}
    for hour in range(24):
        hour_counts[hour] = completion_hours.count(hour)
    
    # Find peak productive hours (top 3)
    sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
    top_hours = sorted_hours[:3]
    
    # Format hours in 12-hour format
    formatted_hours = []
    for hour, count in top_hours:
        if count > 0:  # Only include hours with completions
            ampm = "AM" if hour < 12 else "PM"
            formatted_hour = hour if hour < 12 else hour - 12
            if formatted_hour == 0:
                formatted_hour = 12
            formatted_hours.append(f"{formatted_hour} {ampm}")
    
    return {
        "productive_hours": formatted_hours,
        "message": f"You're most productive around {', '.join(formatted_hours)}",
        "hour_data": hour_counts
    }

def analyze_completion_rate(completed_tasks, pending_tasks):
    """Analyze task completion rate and trends"""
    total_tasks = len(completed_tasks) + len(pending_tasks)
    
    if total_tasks == 0:
        return None
    
    completion_rate = len(completed_tasks) / total_tasks * 100
    
    # Analyze if tasks are completed before or after due date
    on_time_count = 0
    late_count = 0
    
    for task in completed_tasks:
        if task['due_date'] and task['completed_at']:
            try:
                due_date = datetime.datetime.fromisoformat(task['due_date'])
                completed_at = datetime.datetime.fromisoformat(task['completed_at'])
                
                if completed_at <= due_date:
                    on_time_count += 1
                else:
                    late_count += 1
            except (ValueError, TypeError):
                continue
    
    total_with_due_date = on_time_count + late_count
    on_time_percentage = (on_time_count / total_with_due_date * 100) if total_with_due_date > 0 else 0
    
    return {
        "completion_rate": round(completion_rate, 1),
        "on_time_percentage": round(on_time_percentage, 1),
        "completed_count": len(completed_tasks),
        "pending_count": len(pending_tasks),
        "message": f"You've completed {round(completion_rate, 1)}% of your tasks, with {round(on_time_percentage, 1)}% completed on time."
    }

def analyze_category_performance(completed_tasks):
    """Analyze performance by task category"""
    if not completed_tasks:
        return None
    
    # Group tasks by category
    categories = {}
    
    for task in completed_tasks:
        category = task['category'] or 'Uncategorized'
        
        if category not in categories:
            categories[category] = {
                'count': 0,
                'on_time': 0,
                'total_with_due_date': 0
            }
        
        categories[category]['count'] += 1
        
        if task['due_date'] and task['completed_at']:
            try:
                due_date = datetime.datetime.fromisoformat(task['due_date'])
                completed_at = datetime.datetime.fromisoformat(task['completed_at'])
                
                categories[category]['total_with_due_date'] += 1
                
                if completed_at <= due_date:
                    categories[category]['on_time'] += 1
            except (ValueError, TypeError):
                continue
    
    # Calculate performance metrics for each category
    category_performance = []
    
    for category, data in categories.items():
        on_time_percentage = (data['on_time'] / data['total_with_due_date'] * 100) if data['total_with_due_date'] > 0 else 0
        
        category_performance.append({
            'category': category,
            'task_count': data['count'],
            'on_time_percentage': round(on_time_percentage, 1)
        })
    
    # Sort by number of tasks completed
    category_performance.sort(key=lambda x: x['task_count'], reverse=True)
    
    # Find best and worst performing categories
    if len(category_performance) > 1:
        best_category = max(category_performance, key=lambda x: x['on_time_percentage'])
        worst_category = min(category_performance, key=lambda x: x['on_time_percentage'])
        
        message = f"You perform best in '{best_category['category']}' tasks ({best_category['on_time_percentage']}% on time)"
        
        if worst_category['on_time_percentage'] < 70:  # Only mention if it's actually poor performance
            message += f" and may need improvement in '{worst_category['category']}' ({worst_category['on_time_percentage']}% on time)"
    else:
        message = f"You've completed {category_performance[0]['task_count']} tasks in the '{category_performance[0]['category']}' category"
    
    return {
        "categories": category_performance,
        "message": message
    }

def recommend_task_order(pending_tasks, completed_tasks):
    """Recommend the order in which to tackle pending tasks"""
    if not pending_tasks:
        return None
    
    # Simple model: prioritize by due date, priority, and estimated completion difficulty
    task_scores = []
    
    for task in pending_tasks:
        # Base score starts with priority (higher priority = higher score)
        priority = task['priority'] or 3  # Default to medium priority
        base_score = (6 - priority) * 10  # Invert so priority 1 (highest) gets 50 points
        
        # Due date factor - tasks due soon get higher scores
        due_date_score = 0
        if task['due_date']:
            try:
                due_date = datetime.datetime.fromisoformat(task['due_date'])
                now = datetime.datetime.now()
                days_until_due = (due_date - now).days
                
                if days_until_due < 0:  # Overdue
                    due_date_score = 40  # High urgency
                elif days_until_due == 0:  # Due today
                    due_date_score = 30
                elif days_until_due == 1:  # Due tomorrow
                    due_date_score = 20
                elif days_until_due < 7:  # Due this week
                    due_date_score = 10
            except (ValueError, TypeError):
                pass
        
        # Calculate total score
        total_score = base_score + due_date_score
        
        task_scores.append({
            'id': task['id'],
            'title': task['title'],
            'score': total_score,
            'priority': priority,
            'due_date': task['due_date'],
            'category': task['category'] or 'Uncategorized'
        })
    
    # Sort by score (descending)
    task_scores.sort(key=lambda x: x['score'], reverse=True)
    
    # Top 5 recommended tasks
    recommendations = task_scores[:5]
    
    return {
        "recommended_tasks": recommendations,
        "message": "Here's your suggested task order for maximum productivity",
        "reasoning": "Based on urgency, priority, and your past completion patterns"
    }

# Smart Notification System
@app.route('/api/notifications/settings', methods=['GET'])
def get_notification_settings():
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400
    
    conn = sqlite3.connect('taskmanager.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM notification_settings WHERE user_id = ?", (user_id,))
    settings = cursor.fetchone()
    
    if not settings:
        # Create default settings
        cursor.execute("""
        INSERT INTO notification_settings (user_id, enable_push, focus_hours, notification_frequency)
        VALUES (?, 1, '[]', 'medium')
        """, (user_id,))
        conn.commit()
        
        settings = {
            "user_id": user_id,
            "enable_push": True,
            "focus_hours": "[]",
            "notification_frequency": "medium"
        }
    else:
        settings = dict(settings)
    
    # Parse focus hours JSON
    settings['focus_hours'] = json.loads(settings['focus_hours'])
    
    conn.close()
    return jsonify(settings)

@app.route('/api/notifications/settings', methods=['PUT'])
def update_notification_settings():
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400
    
    conn = sqlite3.connect('taskmanager.db')
    cursor = conn.cursor()
    
    # Check if settings exist
    cursor.execute("SELECT user_id FROM notification_settings WHERE user_id = ?", (user_id,))
    exists = cursor.fetchone()
    
    # Convert focus_hours to JSON string if provided
    if 'focus_hours' in data and isinstance(data['focus_hours'], list):
        data['focus_hours'] = json.dumps(data['focus_hours'])
    
    if exists:
        # Update existing settings
        update_fields = []
        values = []
        
        for field in ['enable_push', 'focus_hours', 'notification_frequency']:
            if field in data:
                update_fields.append(f"{field} = ?")
                values.append(data[field])
        
        if not update_fields:
            conn.close()
            return jsonify({"error": "No valid fields to update"}), 400
        
        query = f"UPDATE notification_settings SET {', '.join(update_fields)} WHERE user_id = ?"
        values.append(user_id)
        
        cursor.execute(query, values)
    else:
        # Create new settings
        cursor.execute("""
        INSERT INTO notification_settings (user_id, enable_push, focus_hours, notification_frequency)
        VALUES (?, ?, ?, ?)
        """, (
            user_id,
            data.get('enable_push', True),
            data.get('focus_hours', '[]'),
            data.get('notification_frequency', 'medium')
        ))
    
    conn.commit()
    conn.close()
    
    # Update notification schedule based on new settings
    schedule_smart_notifications(user_id)
    
    return jsonify({"message": "Notification settings updated successfully"})

def schedule_smart_notifications(user_id):
    """Schedule smart notifications based on user settings and task data"""
    # This would connect to a notification service in a real app
    # For this demo, we'll just calculate when notifications should be sent
    
    conn = sqlite3.connect('taskmanager.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get notification settings
    cursor.execute("SELECT * FROM notification_settings WHERE user_id = ?", (user_id,))
    settings = cursor.fetchone()
    
    if not settings:
        conn.close()
        return
    
    settings = dict(settings)
    
    # Check if notifications are enabled
    if not settings['enable_push']:
        conn.close()
        return
    
    # Get pending tasks
    cursor.execute("""
    SELECT * FROM tasks 
    WHERE user_id = ? AND status = 'pending'
    ORDER BY due_date ASC
    """, (user_id,))
    
    pending_tasks = [dict(row) for row in cursor.fetchall()]
    
    # Get productivity insights
    cursor.execute("""
    SELECT * FROM productivity_insights 
    WHERE user_id = ? AND insight_type = 'productive_time'
    ORDER BY generated_at DESC 
    LIMIT 1
    """, (user_id,))
    
    productive_time_insight = cursor.fetchone()
    
    conn.close()
    
    # No tasks to notify about
    if not pending_tasks:
        return
    
    # Prepare notification plan
    notifications = []
    now = datetime.datetime.now()
    
    # Notification for tasks due today
    due_today = [
        task for task in pending_tasks 
        if task['due_date'] and task['due_date'].startswith(now.strftime('%Y-%m-%d'))
    ]
    
    if due_today:
        task_names = [task['title'] for task in due_today[:3]]
        if len(due_today) > 3:
            task_names.append(f"and {len(due_today) - 3} more")
        
        notifications.append({
            "type": "due_today",
            "title": f"You have {len(due_today)} tasks due today",
            "message": f"Tasks due today: {', '.join(task_names)}",
            "scheduled_time": now.strftime('%Y-%m-%d %H:%M:%S'),
            "priority": "high"
        })
    
    # Notification for upcoming high-priority tasks
    high_priority = [
        task for task in pending_tasks 
        if task['priority'] in [1, 2] and task['due_date'] and 
        datetime.datetime.fromisoformat(task['due_date']) > now and
        (datetime.datetime.fromisoformat(task['due_date']) - now).days <= 3
    ]
    
    if high_priority:
        task_names = [task['title'] for task in high_priority[:2]]
        notifications.append({
            "type": "high_priority",
            "title": "High priority tasks coming up",
            "message": f"Remember to work on: {', '.join(task_names)}",
            "scheduled_time": (now + datetime.timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S'),
            "priority": "medium"
        })
    
    # Notification based on productive time (if available)
    if productive_time_insight:
        insight_data = json.loads(dict(productive_time_insight)['insight_data'])
        productive_hours = insight_data.get('productive_hours', [])
        
        if productive_hours and pending_tasks:
            # Schedule a notification during their productive time
            notifications.append({
                "type": "productive_time",
                "title": "It's your productive time!",
                "message": f"This is usually when you get the most done. Time to tackle '{pending_tasks[0]['title']}'?",
                "scheduled_time": "Next occurrence of productive time",
                "priority": "low"
            })
    
    # In a real application, these notifications would be stored in a database
    # and sent at the appropriate times using a notification service
    
    return notifications

# Start the scheduler for tasks like insights generation
scheduler = BackgroundScheduler()
scheduler.start()

# Set up a job to generate insights periodically
@scheduler.scheduled_job('interval', hours=24)
def scheduled_insights_generation():
    conn = sqlite3.connect('taskmanager.db')
    cursor = conn.cursor()
    
    # Get all active users
    cursor.execute("SELECT DISTINCT user_id FROM tasks")
    users = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    # Generate insights for each user
    for user_id in users:
        generate_task_insights(user_id)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
