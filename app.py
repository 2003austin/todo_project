from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
# SQLite file in current dir
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'todo.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Model
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='ToDo')  # ToDo, On-going, Done
    due_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description or "",
            "status": self.status,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "created_at": self.created_at.isoformat()
        }

# Create DB if not exist
with app.app_context():
    db.create_all()

# Serve UI
@app.route('/')
def index():
    return render_template('index.html')

# API endpoints
@app.route('/todos', methods=['GET'])
def get_todos():
    # 支援關鍵字搜尋 ?q=keyword
    q = request.args.get('q', '').strip()
    if q:
        todos = Todo.query.filter(
            (Todo.title.contains(q)) | (Todo.description.contains(q))
        ).order_by(Todo.due_date.is_(None), Todo.due_date).all()
    else:
        todos = Todo.query.order_by(Todo.due_date.is_(None), Todo.due_date).all()
    return jsonify([t.to_dict() for t in todos]), 200

@app.route('/todos', methods=['POST'])
def create_todo():
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    description = data.get('description')
    status = data.get('status') or 'ToDo'
    due_date = data.get('due_date')
    try:
        due = datetime.fromisoformat(due_date).date() if due_date else None
    except Exception:
        return jsonify({"error": "invalid due_date format, use YYYY-MM-DD"}), 400

    todo = Todo(title=title, description=description, status=status, due_date=due)
    db.session.add(todo)
    db.session.commit()
    return jsonify(todo.to_dict()), 201

@app.route('/todos/<int:id>', methods=['PUT'])
def update_todo(id):
    todo = Todo.query.get_or_404(id)
    data = request.get_json() or {}
    title = data.get('title')
    if title is not None:
        todo.title = title.strip()
    if 'description' in data:
        todo.description = data.get('description')
    if 'status' in data:
        todo.status = data.get('status')
    if 'due_date' in data:
        due_date = data.get('due_date')
        try:
            todo.due_date = datetime.fromisoformat(due_date).date() if due_date else None
        except Exception:
            return jsonify({"error":"invalid due_date format, use YYYY-MM-DD"}), 400
    db.session.commit()
    return jsonify(todo.to_dict()), 200

@app.route('/todos/<int:id>', methods=['DELETE'])
def delete_todo(id):
    todo = Todo.query.get_or_404(id)
    db.session.delete(todo)
    db.session.commit()
    return jsonify({"message": "deleted"}), 200

# Extra endpoint for simple stats (completed / incomplete)
@app.route('/stats', methods=['GET'])
def stats():
    total = Todo.query.count()
    done = Todo.query.filter_by(status='Done').count()
    todo = Todo.query.filter_by(status='ToDo').count()
    ongoing = Todo.query.filter_by(status='On-going').count()
    return jsonify({
        "total": total,
        "done": done,
        "todo": todo,
        "ongoing": ongoing
    }), 200

if __name__ == "__main__":
    # 可直接用 python app.py 啟動
    app.run(debug=True, host='127.0.0.1', port=5000)
