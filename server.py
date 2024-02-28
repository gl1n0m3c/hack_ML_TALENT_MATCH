from flask import Flask, render_template, request,session, jsonify
import os
from werkzeug.utils import secure_filename
import shutil
from flask_cors import CORS
from flask_session import Session
from openpyxl import Workbook
from flask import send_file
import datetime
import pandas as pd
import json
import sys

UPLOAD_FOLDER = 'D:/projects/HACKATON_N4/upload/'
REPORTS_FOLDER = 'D:/projects/HACKATON_N4/resumes/'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


app = Flask(__name__)

app.config['SECRET_KEY'] = 'yuyfhjhdjshjdhfjdhsjhjdhjshjshsjhlllljgsdfghjk'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

CORS(app, supports_credentials=True)

Session(app)


def create_json(directory_name,file_name):
    """
    Создает JSON-файл с данными data и возвращает содержимое файла.
    
    Параметры:
    - data: словарь, данные для записи в JSON-файл
    - filename: строка, имя файла для сохранения JSON
    """
    # Директорию создаем если не было
    # Путь к папке, где будет создан JSON-файл
    directory_path = os.path.join(REPORTS_FOLDER, directory_name)
    
    # Проверяем существование папки
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)  # Если папки нет, создаем ее


    path_to_doc = os.path.join(UPLOAD_FOLDER, directory_name, file_name)
    path_to_json= os.path.join(REPORTS_FOLDER, directory_name, file_name.split('.')[0]+'.json')

    print(path_to_json)
    data = {'name':path_to_doc}
    print(data)
    # Запись данных в JSON-файл
    with open(path_to_json, 'w') as f:
        json.dump(data, f)
    
    # Возвращение содержимого файла
    return path_to_json


def create_directory(directory):
    # Создаем директорию, если она не существует
    if not os.path.exists(directory):
        os.makedirs(directory)



@app.route('/getJson', methods=['GET'])
def get_image():
    # Получаем параметры "Имя директории" и "Имя файла" из запроса
    directory_name = request.args.get('directoryName')
    file_name = request.args.get('fileName')
    print(directory_name,file_name)
    # Проверяем, что переданы оба параметра
    if directory_name and file_name:
        # Собираем полный путь к изображению
        path_json = create_json(directory_name, file_name)


        # Проверяем, существует ли файл
        if os.path.exists(path_json):
            # Отправляем изображение в ответе

            return send_file(path_json, as_attachment=True)

    # Возвращаем ошибку, если файл не найден
    return 'Resume not found', 404

@app.route('/upload', methods=['POST'])
def upload():
    try:
        print('Received request with content type:', request.content_type)

        if 'files' not in request.files:
            return jsonify({'error': 'No files part in the request'}), 400

        uploaded_files = request.files.getlist('files')
      #  print('ALL FILES = ',uploaded_files)
        if not uploaded_files:
            return jsonify({'error': 'No files uploaded'}), 400

        for file in uploaded_files:
            # Получаем полный путь к файлу
            filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
           # print('FILENAME====',filename)
            # Создаем директорию, если необходимо
            directory = os.path.dirname(filename)
            create_directory(directory)

            # Сохраняем файл
            file.save(filename)
        return jsonify({'message': 'Files uploaded successfully'})
    except Exception as e:
        print('exxxxx=',e)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
   # app.run(host="0.0.0.0", port=5000)
    app.run()

