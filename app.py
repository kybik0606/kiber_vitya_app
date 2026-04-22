from flask import Flask, render_template, request, jsonify, session, redirect
import json
import random
import os
import csv
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey123'

# Загружаем вопросы
with open('questions.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    questions = data['questions']

# Папка для сохранения результатов
RESULTS_DIR = 'results'
if not os.path.exists(RESULTS_DIR):
    os.makedirs(RESULTS_DIR)

def save_results_to_files(session_data):
    """Сохраняет результаты теста в JSON и CSV файлы"""
    
    user_id = session_data.get('user_id', 'unknown')
    timestamp = datetime.now()
    score = session_data.get('score', 0)
    total = len(session_data.get('questions', []))
    percent = (score / total * 100) if total > 0 else 0
    
    # Сохраняем JSON (используем user_id как имя файла)
    json_filename = f"{user_id}.json"
    json_data = {
        'user_id': user_id,
        'timestamp': timestamp.isoformat(),
        'score': score,
        'total': total,
        'percent': percent,
        'answers': session_data.get('answers', [])
    }
    
    json_filepath = os.path.join(RESULTS_DIR, json_filename)
    with open(json_filepath, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    # Сохраняем CSV
    csv_filename = os.path.join(RESULTS_DIR, 'all_results.csv')
    file_exists = os.path.isfile(csv_filename)
    
    with open(csv_filename, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['user_id', 'timestamp', 'score', 'total', 'percent'])
        writer.writerow([user_id, timestamp.isoformat(), score, total, round(percent, 1)])
    
    return True

@app.route('/')
def index():
    if 'user_id' not in session:
        session['user_id'] = datetime.now().strftime('%Y%m%d_%H%M%S_') + str(random.randint(1000, 9999))
    
    session['score'] = 0
    session['current_index'] = 0
    session['questions'] = random.sample(questions, min(15, len(questions)))
    session['answers'] = []
    session['start_time'] = datetime.now().isoformat()
    session.modified = True
    
    return render_template('index.html', total=len(session['questions']))

@app.route('/question')
def get_question():
    idx = session.get('current_index', 0)
    
    if idx >= len(session['questions']):
        return jsonify({'finished': True})
    
    q = session['questions'][idx]
    return jsonify({
        'finished': False,
        'id': idx + 1,
        'total': len(session['questions']),
        'text': q['text'],
        'score': session['score']
    })

@app.route('/answer', methods=['POST'])
def answer():
    data = request.json
    answer_user = data.get('answer')
    
    idx = session.get('current_index', 0)
    
    if idx >= len(session['questions']):
        return jsonify({'error': 'Game over'})
    
    q = session['questions'][idx]
    is_correct = (answer_user == 'phishing' and q['is_phishing']) or \
                 (answer_user == 'legit' and not q['is_phishing'])
    
    if is_correct:
        session['score'] += 1

    session['answers'].append({
        'text': q['text'],  
        'user_answer': answer_user,
        'correct': is_correct,
        'explanation': q['explanation'],
        'is_phishing': q['is_phishing']  
    })
    
    session['current_index'] = idx + 1
    session.modified = True
    
    next_qid = session['current_index'] + 1
    is_finished = session['current_index'] >= len(session['questions'])
    
    return jsonify({
        'correct': is_correct,
        'explanation': q['explanation'],
        'score': session['score'],
        'next_qid': next_qid,
        'finished': is_finished
    })

@app.route('/result')
def result():
    if 'questions' not in session or len(session.get('questions', [])) == 0:
        return redirect('/')
    
    total = len(session['questions'])
    score = session.get('score', 0)
    
    if total > 0:
        percent = (score / total) * 100
    else:
        percent = 0
    
    # Сохраняем результаты
    save_results_to_files(session)
    
    return render_template('result.html', 
                         score=score, 
                         total=total, 
                         percent=percent,
                         answers=session.get('answers', []))

@app.route('/admin/results')
def admin_results():
    results = []
    if os.path.exists(RESULTS_DIR):
        for filename in os.listdir(RESULTS_DIR):
            if filename.endswith('.json') and not filename.startswith('all_'):
                try:
                    with open(f"{RESULTS_DIR}/{filename}", 'r', encoding='utf-8') as f:
                        results.append(json.load(f))
                except:
                    pass
    
    results.sort(key=lambda x: x.get('score', 0), reverse=True)
    return render_template('admin.html', results=results)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)