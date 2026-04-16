from flask import Flask, render_template, request, jsonify, session, redirect
import json
import random
import os
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

@app.route('/')
def index():
    # Генерируем уникальный ID для сессии
    if 'user_id' not in session:
        session['user_id'] = datetime.now().strftime('%Y%m%d_%H%M%S_') + str(random.randint(1000, 9999))
    
    session['score'] = 0
    session['current_index'] = 0
    session['questions'] = random.sample(questions, min(5, len(questions)))
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
    # Проверяем, есть ли данные
    if 'questions' not in session or len(session.get('questions', [])) == 0:
        return redirect('/')
    
    total = len(session['questions'])
    score = session.get('score', 0)
    
    # Вычисляем процент
    if total > 0:
        percent = (score / total) * 100
    else:
        percent = 0
    
    # Добавим отладку
    print(f"DEBUG: score={score}, total={total}, percent={percent}")
    print(f"DEBUG: answers={session.get('answers', [])}")
    
    return render_template('result.html', 
                         score=score, 
                         total=total, 
                         percent=percent,
                         answers=session.get('answers', []))

@app.route('/admin/results')
def admin_results():
    """Админ-страница для просмотра всех результатов"""
    results = []
    if os.path.exists(RESULTS_DIR):
        for filename in os.listdir(RESULTS_DIR):
            if filename.endswith('.json'):
                with open(f"{RESULTS_DIR}/{filename}", 'r', encoding='utf-8') as f:
                    results.append(json.load(f))
    
    # Сортируем по баллам
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return render_template('admin.html', results=results)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)