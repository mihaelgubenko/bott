"""
Веб-интерфейс для управления данными HR-Психоаналитического бота
Позволяет просматривать, экспортировать и импортировать данные через браузер
"""

import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash
from werkzeug.utils import secure_filename
from data_sync import get_sync_manager
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Конфигурация
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'json', 'csv'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Создаем папку для загрузок
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Инициализируем менеджер синхронизации
sync_manager = get_sync_manager()

def allowed_file(filename):
    """Проверка разрешенных расширений файлов"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_stats():
    """Получение статистики базы данных"""
    conn = sqlite3.connect('psychoanalyst.db')
    cursor = conn.cursor()
    
    # Подсчет анализов
    cursor.execute('SELECT COUNT(*) FROM clients')
    total_analyses = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM clients WHERE analysis_type = "express"')
    express_analyses = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM clients WHERE analysis_type = "full"')
    full_analyses = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM clients WHERE payment_status = "paid"')
    paid_analyses = cursor.fetchone()[0]
    
    # Подсчет A/B тестов
    cursor.execute('SELECT COUNT(*) FROM ab_test_results')
    total_ab_tests = cursor.fetchone()[0]
    
    # Последние анализы
    cursor.execute('''
        SELECT telegram_id, name, analysis_type, payment_status, created_at 
        FROM clients 
        ORDER BY created_at DESC 
        LIMIT 10
    ''')
    recent_analyses = cursor.fetchall()
    
    conn.close()
    
    return {
        'total_analyses': total_analyses,
        'express_analyses': express_analyses,
        'full_analyses': full_analyses,
        'paid_analyses': paid_analyses,
        'total_ab_tests': total_ab_tests,
        'recent_analyses': recent_analyses
    }

@app.route('/')
def index():
    """Главная страница"""
    stats = get_db_stats()
    return render_template('index.html', stats=stats)

@app.route('/analyses')
def analyses():
    """Страница со списком анализов"""
    conn = sqlite3.connect('psychoanalyst.db')
    cursor = conn.cursor()
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    
    # Получаем анализы с пагинацией
    cursor.execute('''
        SELECT id, telegram_id, name, analysis_type, payment_status, created_at 
        FROM clients 
        ORDER BY created_at DESC 
        LIMIT ? OFFSET ?
    ''', (per_page, offset))
    
    analyses = cursor.fetchall()
    
    # Подсчет общего количества
    cursor.execute('SELECT COUNT(*) FROM clients')
    total = cursor.fetchone()[0]
    
    conn.close()
    
    return render_template('analyses.html', 
                         analyses=analyses, 
                         page=page, 
                         per_page=per_page, 
                         total=total)

@app.route('/analysis/<int:analysis_id>')
def view_analysis(analysis_id):
    """Просмотр конкретного анализа"""
    conn = sqlite3.connect('psychoanalyst.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM clients WHERE id = ?', (analysis_id,))
    analysis = cursor.fetchone()
    
    conn.close()
    
    if not analysis:
        flash('Анализ не найден', 'error')
        return redirect(url_for('analyses'))
    
    # Парсим JSON данные анализа
    analysis_data = json.loads(analysis[4]) if analysis[4] else {}
    
    return render_template('analysis_detail.html', 
                         analysis=analysis, 
                         analysis_data=analysis_data)

@app.route('/export')
def export_page():
    """Страница экспорта данных"""
    export_info = sync_manager.get_export_info()
    return render_template('export.html', export_info=export_info)

@app.route('/export/download/<format_type>')
def download_export(format_type):
    """Скачивание экспорта"""
    try:
        filepath = sync_manager.export_all_data(format_type)
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        flash(f'Ошибка при экспорте: {e}', 'error')
        return redirect(url_for('export_page'))

@app.route('/import', methods=['GET', 'POST'])
def import_page():
    """Страница импорта данных"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Файл не выбран', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('Файл не выбран', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                merge_mode = request.form.get('merge_mode') == 'on'
                result = sync_manager.import_data(filepath, merge_mode=merge_mode)
                
                flash(f'Импорт завершен! Импортировано: {result["analyses"]} анализов, {result["ab_results"]} A/B результатов', 'success')
                
                # Удаляем временный файл
                os.remove(filepath)
                
            except Exception as e:
                flash(f'Ошибка при импорте: {e}', 'error')
                if os.path.exists(filepath):
                    os.remove(filepath)
        
        return redirect(url_for('import_page'))
    
    return render_template('import.html')

@app.route('/stats')
def stats_page():
    """Страница статистики"""
    stats = get_db_stats()
    
    # Дополнительная статистика
    conn = sqlite3.connect('psychoanalyst.db')
    cursor = conn.cursor()
    
    # Статистика по дням
    cursor.execute('''
        SELECT DATE(created_at) as date, COUNT(*) as count 
        FROM clients 
        WHERE created_at >= date('now', '-30 days')
        GROUP BY DATE(created_at) 
        ORDER BY date DESC
    ''')
    daily_stats = cursor.fetchall()
    
    # Статистика A/B тестов
    cursor.execute('''
        SELECT prompt_variant_id, COUNT(*) as count 
        FROM ab_test_results 
        GROUP BY prompt_variant_id
    ''')
    ab_stats = cursor.fetchall()
    
    conn.close()
    
    return render_template('stats.html', 
                         stats=stats, 
                         daily_stats=daily_stats, 
                         ab_stats=ab_stats)

@app.route('/api/analyses')
def api_analyses():
    """API для получения списка анализов"""
    conn = sqlite3.connect('psychoanalyst.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, telegram_id, name, analysis_type, payment_status, created_at 
        FROM clients 
        ORDER BY created_at DESC
    ''')
    
    analyses = cursor.fetchall()
    conn.close()
    
    return jsonify([{
        'id': a[0],
        'telegram_id': a[1],
        'name': a[2],
        'analysis_type': a[3],
        'payment_status': a[4],
        'created_at': a[5]
    } for a in analyses])

@app.route('/api/analysis/<int:analysis_id>')
def api_analysis(analysis_id):
    """API для получения конкретного анализа"""
    conn = sqlite3.connect('psychoanalyst.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM clients WHERE id = ?', (analysis_id,))
    analysis = cursor.fetchone()
    
    conn.close()
    
    if not analysis:
        return jsonify({'error': 'Analysis not found'}), 404
    
    return jsonify({
        'id': analysis[0],
        'telegram_id': analysis[1],
        'name': analysis[2],
        'analysis_type': analysis[3],
        'analysis_data': json.loads(analysis[4]) if analysis[4] else {},
        'payment_status': analysis[5],
        'created_at': analysis[6]
    })

if __name__ == '__main__':
    # Создаем папку для шаблонов
    os.makedirs('templates', exist_ok=True)
    
    # Запускаем веб-сервер
    app.run(host='0.0.0.0', port=5000, debug=True)