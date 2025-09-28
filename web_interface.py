#!/usr/bin/env python3
"""
Веб-интерфейс для тестирования психологического бота
"""

from flask import Flask, render_template, request, jsonify
from final_psychology_bot import FinalPsychologyBot
import json

app = Flask(__name__)
bot = FinalPsychologyBot()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_message = request.json.get('message', '')
        if not user_message:
            return jsonify({'error': 'Сообщение не может быть пустым'}), 400
        
        # Обрабатываем сообщение ботом
        response = bot.process_message(user_message)
        
        return jsonify({
            'response': response,
            'status': 'success'
        })
    
    except Exception as e:
        return jsonify({
            'error': f'Ошибка обработки сообщения: {str(e)}',
            'status': 'error'
        }), 500

@app.route('/reset', methods=['POST'])
def reset():
    """Сброс контекста диалога"""
    try:
        # Создаем новый экземпляр бота для сброса контекста
        global bot
        bot = FinalPsychologyBot()
        return jsonify({'status': 'success', 'message': 'Контекст сброшен'})
    except Exception as e:
        return jsonify({'error': f'Ошибка сброса: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)