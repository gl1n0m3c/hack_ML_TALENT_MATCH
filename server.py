from flask import Flask, render_template, request, jsonify, render_template
import os
from werkzeug.utils import secure_filename
from flask_cors import CORS
from flask import send_file
import json
from openpyxl import Workbook
from flask import send_file
import datetime
import pandas as pd
import json
import sys
from langchain.output_parsers import PydanticOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field, validator, ValidationError
from typing import Optional
from langchain_openai import ChatOpenAI
from config import chat_openai_key
from langchain import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from openai import OpenAI
from langchain.output_parsers import RetryOutputParser
from random import randint
import subprocess

# обработка pdf
import pdftotext
#import openai
import re
import logging
import json

import tiktoken
from docx import Document


UPLOAD_FOLDER = '/root/hakathon/app/upload'#'D:/projects/HACKATON_N4/upload/'
REPORTS_FOLDER ='/root/hakathon/app/resumes' #'D:/projects/HACKATON_N4/resumes/'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


#app = Flask(__name__,  static_folder='D:/projects/HACKATON_N4/imgquality-app/build/static',template_folder='D:/projects/HACKATON_N4/imgquality-app/build/')
app = Flask(__name__,  static_folder='/root/hakathon/app/build/static/',template_folder='/root/hakathon/app/build/')

app.config['SECRET_KEY'] = 'yuyfhjhdjshjdhfjdhsjhjdhjshjshsjhlllljgsdfghjk'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

CORS(app, supports_credentials=True)


def upcase_first_letter(s):
    if s:
        return s[0].upper() + (s[1:]).lower()
def get_methodical_text(methodical_filename):
    doc = Document(methodical_filename)
    s = '\n'.join([p.text for p in doc.paragraphs])
    return s


def get_fields(text, instructions, parser, example_text):
    chain = prompt | llm | parser
    response = chain.invoke({'text': text, 'format_instructions': instructions, 'example_text':example_text})
    return response.dict()


def moderate(text: str):
    response = moderator.moderations.create(input=text)
    output = response.results[0].flagged
    return output


def llm_layer(text: str):
    if moderate(text) == False:
        try:
            easy_fields = get_fields(text, easy_instructions, easy_output_parser, easy_example)
        except:
            easy_fields = {'first_name': None,
                           'last_name': None,
                           'middle_name': None,
                           'birth_date': None,
                           'birth_date_year_only': False,
                           'country': None,
                           'city': None,
                           'about': None,
                           'key_skills': None,
                           'salary_expectations_amount': None,
                           'salary_expectations_currency': None,
                           'gender': 1,
                           'photo_path': None,
                           'resume_name': None,
                           'source_link': None, }
        try:
            contact_fields = get_fields(text, contact_instructions, contact_output_parser, contact_example)
        except:
            contact_fields = {'contactItems': [], }
        try:
            education_fields = get_fields(text, education_instructions, education_output_parser, education_example)
        except:
            education_fields = {'educationItems': [], }
        try:
            experience_fields = get_fields(text, experience_instructions, experience_output_parser, experience_example)
        except:
            experience_fields = {'experienceItems': [], }
        try:
            language_fields = get_fields(text, language_instructions, language_output_parser, language_example)
        except:
            language_fields = {'languageItems': []}

        easy_fields['resume_id'] = str(randint(10000, 100000))

        easy_fields['first_name'] = upcase_first_letter(easy_fields['first_name'])
        easy_fields['last_name'] = upcase_first_letter(easy_fields['last_name'])
        easy_fields['middle_name'] = upcase_first_letter(easy_fields['middle_name'])

        for i in contact_fields['contactItems']:
            i['resume_contact_item_id'] = str(randint(10000, 100000))

        for i in education_fields['educationItems']:
            i['resume_education_item_id'] = str(randint(10000, 100000))

        for ind, i in enumerate(experience_fields['experienceItems']):
            i['resume_experience_item_id'] = str(randint(10000, 100000))
            i['order'] = ind

        for i in language_fields['languageItems']:
            i['resume_language_item_id'] = str(randint(10000, 100000))

        return {'resume': easy_fields | contact_fields | education_fields | experience_fields | language_fields}
    else:
        empty = {'resume':
                     {'resume_id': None,
                      'first_name': None,
                      'last_name': None,
                      'middle_name': None,
                      'birth_date': None,
                      'birth_date_year_only': False,
                      'country': None,
                      'city': None,
                      'about': None,
                      'key_skills': None,
                      'salary_expectations_amount': None,
                      'salary_expectations_currency': None,
                      'gender': 1,
                      'photo_path': None,
                      'resume_name': None,
                      'source_link': None,
                      'contactItems': [],
                      'educationItems': [],
                      'experienceItems': [],
                      'languageItems': []}}
        return empty

def num_tokens_from_string(string: str, model: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(string))
    return num_tokens

def pdf2string(pdf_path) -> str:
    """
    Extract the content of a pdf file to string.
    :param pdf_path: Path to the PDF file.
    :return: PDF content string.
    """
    with open(pdf_path, "rb") as f:
        pdf = pdftotext.PDF(f)
    pdf_str = "\n\n".join(pdf)
    pdf_str = re.sub('\s[,.]', ',', pdf_str)
    pdf_str = re.sub('[\n]+', '\n', pdf_str)
    pdf_str = re.sub('[\s]+', ' ', pdf_str)
    pdf_str = re.sub('http[s]?(://)?', '', pdf_str)
    return pdf_str

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


    path_to_doc = os.path.join(UPLOAD_FOLDER, directory_name, file_name) # тут наш файл загруженный.
    src_txt = ''
    if '.doc'  in file_name or 'docx' in file_name:
        print('IS DOC')
        src_txt = get_methodical_text(path_to_doc)
    if '.pdf' in file_name:
        print('IS PDF')
        # Выполнение команды ocrmypdf с помощью subprocess
        try:
            subprocess.run(["ocrmypdf", file_name, file_name], check=True)
            print("Конвертация PDF в текстовый файл выполнена успешно.")
        except subprocess.CalledProcessError as e:
            print(f"Произошла ошибка при конвертации PDF в текстовый файл: {e}")
        src_txt = pdf2string(path_to_doc)
    print(src_txt)
    my_json = llm_layer(src_txt)

    print(my_json)
    path_to_json= os.path.join(REPORTS_FOLDER, directory_name, file_name.split('.')[0]+'.json')

   # print(path_to_json)
    #data = {'name':path_to_doc}
   # print(data)
    # Запись данных в JSON-файл
    with open(path_to_json, 'w') as f:
        json.dump(my_json, f)
    
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
    print('YES UPLOAD?')
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


# Маршрут для обслуживания статических файлов из папки build/static
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('/root/hakathon/app/build/static/', filename)



#  Маршрут для обслуживания статических файлов из папки build
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "":
        return 
    else:
        return render_template('index.html')
    
if __name__ == '__main__':
    llm = ChatOpenAI(model='gpt-3.5-turbo-0125', temperature=0, openai_api_key=chat_openai_key)
    moderator = OpenAI(api_key=chat_openai_key)
    prompt_template = """
    Ты - hr менеджер и тебе нужно извлекать данные из текста резюме кандидата
    Получи следующую информацию из текста резюме:

    {format_instructions}

    Ты должен следовать следующему примеру:
    
    {example_text}
    
    По нему ты можешь понять какие типы данных подразумеваются для тех или иных полей.
    ПОЖАЛУЙСТА, обратите внимание на следующие условия:
    - Все значения должны соответствовать условиям, указанным в запросе, включая форматирование и дополнительные указания по каждой колонке.
    - Постарайся извлечь информацию в лучшем виде, избегай ошибок и учти что в исходном тексте могут быть такие ошибки как:
        лишние пробелы
        информация разбросана
    - Если информация не указана, нельзя придумывать или добавлять что то от себя.
    - Не изменяй фактическую информацию
    - Предоставляй информацию строго в формате указанном в инструкции!
    text: {text}
    """
    prompt = PromptTemplate.from_template(template=prompt_template)


    class CVFields(BaseModel):
        first_name: Optional[str] = Field(
            description="Извлеките имя кандидата на вакансию. Если эта информация не найдена, выведи None.")
        last_name: Optional[str] = Field(
            description="Извлеките фамилию кандидата на вакансию. Если эта информация не найдена, выведи None.")
        middle_name: Optional[str] = Field(
            description="Извлеките отчество кандидата на вакансию. Если эта информация не найдена, выведи None.")
        birth_date: Optional[str] = Field(
            description="Извлеките дату рождения в формате YYYY-MM-DD. Если эта информация не найдена, выведи None.")
        birth_date_year_only: Optional[bool] = Field(default=False,
                                                     description="Если в наличии только год рождения выведи true, если предоставлена полная дата рождения выведи false . Если эта информация не найдена, выведи false.")
        country: Optional[str] = Field(
            description="Извлеките страну проживания кандидата. Если эта информация не найдена, выведи None.")
        city: Optional[str] = Field(
            description="Извлеките город проживания кандидата. Если эта информация не найдена, выведи None.")
        about: Optional[str] = Field(
            description="Извлеките описание кандидата,(не обязательно навыки, для них есть другое поле) возможно цели, профиль. Если эта информация не найдена, выведи None.")
        key_skills: Optional[str] = Field(
            description="Извлеките все ключевые навыки кандидата. Технические навыки, мягкие навыки и т.д. Если эта информация не найдена, выведи None.")
        salary_expectations_amount: Optional[str] = Field(
            description="Извлеките информацию о зарплатных ожиданиях из текста, учитывая формат: числовое значение без пробелов, без указания валюты(только число). Если эта информация не найдена, выведи None.")
        salary_expectations_currency: Optional[str] = Field(
            description="Извлеките валюту зарплатных ожиданий из текста(только знак валюты $ ₽ или другой). Если эта информация не найдена, выведи None.")
        gender: Optional[int] = Field(
            description="Извлеките пол кандидата.Возможно из имени, возможно это будет отдельно написано(1 - мужской, 2 - женский) Выведи только 1 или 2. Если эта информация не найдена, выведи 1.")
        photo_path: Optional[str] = Field(
            description="Извлеките ссылку на фотографию если есть. Если эта информация не найдена, выведи None.")
        resume_name: Optional[str] = Field(
            description="Извлеките название резюме если есть. Если эта информация не найдена, выведи None.")
        source_link: Optional[str] = Field(
            description="Извлеките ссылку на источник резюме если есть. Если эта информация не найдена, выведи None.")


    easy_output_parser = PydanticOutputParser(pydantic_object=CVFields)
    easy_instructions = easy_output_parser.get_format_instructions()
    easy_example = """{'first_name': 'Иван',
                'last_name': 'Иванов',
                'middle_name': ,
                'birth_date': 1997-12-27,
                'birth_date_year_only': false,
                'country': 'Россия',
                'city': 'Москва',
                'about': 'Я - опытный разработчик, люблю ездить на велосипеде и читать.',
                'key_skills': 'Python, Django, CSS, HTML, ML, DS, SQL, Analytics',
                'salary_expectations_amount': '50000',
                'salary_expectations_currency': '₽',
                'gender': 1,
                'photo_path': 'https://risunok-8.jpg',
                'resume_name': Резюме кандидата Иванова Ивана,
                'source_link': 'https://linkedln.com/blablabla',}
    """

    class ContactItem(BaseModel):
        value: Optional[str] = Field(
            description="Извлеките текст контакта кандидата(только его значение). Если такой информации нет выведите None")
        comment: Optional[str] = Field(
            description="Извлеките комментарий к контакту кандидата. Если такой информации нет выведите None")
        contact_type: Optional[int] = Field(
            description="Определите тип контакта и верните цифру: 1: Телефон 2: Email 3: Skype 4: Telegram 5: Github. Если данная информация не найдена или пункта нет в списке выведите None")


    class ContactItems(BaseModel):
        contactItems: list[ContactItem] = []


    contact_output_parser = PydanticOutputParser(pydantic_object=ContactItems)
    contact_instructions = contact_output_parser.get_format_instructions()
    contact_example = """{'contactItems': [
                {
                    'value': 'aiaa3t@gmail.com',
                    'comment': 'Обращаться только по понедельникам', 
                    'contact_type': 2, 
                    'resume_contact_item_id': '43251'}]
                }
    ],}
    """

    class EducationItem(BaseModel):
        year: Optional[str] = Field(
            description="Извлеките ТОЛЬКО год окончания образования кандидата. Год начала обучения писать не надо.Месяц писать нельзя. Если такой информации нет выведите None")
        organization: Optional[str] = Field(
            description="Извлеките название учебного заведения. Если такой информации нет выведите None")
        faculty: Optional[str] = Field(description="Извлеките факультет. Если такой информации нет выведите None")
        specialty: Optional[str] = Field(description="Извлеките специальность. Если такой информации нет выведите None")
        result: Optional[str] = Field(
            description="Извлеките результат обучения. Если такой информации нет выведите None")
        education_type: Optional[int] = Field(
            description="Определите вид образования и верните цифру: 1: Начальное 2: Повышение квалификации 3: Сертификаты 4: Основное. Если данная информация не найдена или пункта нет в списке выведите None")
        education_level: Optional[int] = Field(
            description="Определите уровень образования и верните цифру: 1: Среднее 2: Среднее специальное 3: Неоконченное высшее 4: Высшее 5: Бакалавр 6: Магистр 7: Кандидат наук 8: Доктор наук. Если данная информация не найдена или пункта нет в списке выведите None")


    class EducationItems(BaseModel):
        educationItems: list[EducationItem]


    education_output_parser = PydanticOutputParser(pydantic_object=EducationItems)
    education_instructions = education_output_parser.get_format_instructions()
    education_example = """{
                'educationItems': [
                    {
                        'year': '2018', 
                        'organization': 'Казанский авиационный исследовательский университет имени Туполева', 
                        'faculty': 'Applied Computer Science', 
                        'specialty': 'Оператор информационных систем',
                        'result': 'Я извлек много полезных навыков из обучения в этом университете, например программирование и другое',
                        'education_type': 4, 
                        'education_level': 5,
                    }
                    ]}
                            Как видно на данном примере, нужно в первом поле указывать только год без лишних знаков, только год - YYYY. В остальных полях тоже следуй инструкции
    """

    class ExperienceItem(BaseModel):
        starts: Optional[str] = Field(
            description="Извлеките ТОЛЬКО год начала работы на данной работе. Месяц писать нельзя. Только год. Если такой информации нет выведите None")
        ends: Optional[str] = Field(
            description="Извлеките ТОЛЬКО год конца работы на данной работе.Месяц писать нельзя. Только год(если настоящее время - пиши 2024) Если такой информации нет выведите None")
        employer: Optional[str] = Field(
            description="Извлеките название организации на данной работе. Если такой информации нет выведите None")
        city: Optional[str] = Field(
            description="Извлеките город работы на данной работе. Если такой информации нет выведите None")
        url: Optional[str] = Field(
            description="Извлеките ссылку на сайт работадателя на данной работе. Если такой информации нет выведите None")
        position: Optional[str] = Field(
            description="Извлеките должность данного кандидата на данной работе. Если такой информации нет выведите None")
        description: Optional[str] = Field(
            description="Извлеките предоставленное описание работы на данной работе. Если такой информации нет выведите None")


    class ExperienceItems(BaseModel):
        experienceItems: list[ExperienceItem]


    experience_output_parser = PydanticOutputParser(pydantic_object=ExperienceItems)
    experience_instructions = experience_output_parser.get_format_instructions()
    experience_example = """
    {'experienceItems': [{'starts': '2023', 'ends': '2023', 'employer': 'Archetype AI', 'city': 'Belgrade', 'url': null, 'position': 'Full stack Nest, React developer', 'description': 'Prototyped and implemented a scalable real-time low-latency (under 1 second) camera streaming service for following image processing with AI tools; Prototyped an internal streamer\u2019s visualizer for real-time stream playing; On a very tight schedule unblocked a release of a major product by implementing a scalable real-time low-latency (under 1 second) camera streaming service providing video feed to AI tools for processing at Archetype AI.'}, 
    {'starts': '2022', 'ends': '2023', 'employer': 'Spotnana (Vendor at Akvelon Inc)', 'city': null, 'url': null, 'position': 'Frontend React/React Native developer', 'description': 'Reduced app loading time from 400 to 200 milliseconds, improved design consistency and user experience and accessibility by transitioning an old frontend UI design system to a new MUI 5-based one with lazy components; Implemented features that gained Spotnana partnerships with Amazon, Walmart, and Meta; Added extensive telemetry that significantly improved team's effectiveness by providing insights into user experience; Reduced CI/CD running time from 50 minutes to 30 by optimizing unit tests and sharing best practices with the team; Increased code test coverage from 80% to 85%; Improved developer experience and code quality by configuring eslint rules; Reduced total bundle size for 100kb by removing redux state manager, switching moment to days; Tightly interacted with a product manager and designer resulting in the implementation of consistent user-friendly UI; Led a team of 3 developers.'}, 
    {'starts': '2020', 'ends': '2021', 'employer': 'Rentals-Platform (Vendor at Akvelon Inc)', 'city': null, 'url': null, 'position': 'Full stack Node, React, Vue developer', 'description': 'Architected, built and supported Dealer and Shopping frontends and backends throughout the app's lifecycle; Automated the tax rates calculation by integration with Avalara tax calculation service; Automated the customer support service actions by implementing admin tools for complex booking refund and update scenarios; Assisted in the migration of 100 new customers to the rentals platform by migrating databases and continuously syncing databases from third-party services; Led a team of 3 developers.'}, 
    {'starts': '2019', 'ends': '2020', 'employer': 'Maana (Vendor at Akvelon Inc)', 'city': null, 'url': null, 'position': 'Frontend React developer', 'description': 'Implemented a real-time data analyzing tool and notification system using Material-UI; Helped gain a new partnership by implementing MS Azure SSO which was a keystone requirement of the new client.'}, 
    {'starts': '2018', 'ends': '2019', 'employer': 'National energy company (Vendor at Optisoft)', 'city': null, 'url': null, 'position': 'Full-stack NET Developer/React developer', 'description': 'Architected and built REST API and database structure; Automated entire business operational workflow: booking vehicles, maintaining vehicles, and budget calculation.'}]}
    Учитывай тип данных в каждом поле и следуй инструкции к ним.
    """

    class LanguageItem(BaseModel):
        language: Optional[str] = Field(
            description="Извлеките язык владеемый кандидатом.Это может быть только лингвистический язык, например английский или русский. Языки программирования указывать нельзя Если такой информации нет выведите None")
        language_level: Optional[int] = Field(
            description="Определите уровень знания языка и верните цифру: 1: Начальный 2: Элементарный 3: Средний 4: Средне-продвинутый 5: Продвинутый 6: В совершенстве 7: Родной. Если данная информация не найдена или пункта нет в списке выведите None")


    class LanguageItems(BaseModel):
        languageItems: list[LanguageItem]


    language_output_parser = PydanticOutputParser(pydantic_object=LanguageItems)
    language_instructions = language_output_parser.get_format_instructions()
    language_example = """{
                "languageItems": [
                    {
                        "language": "English", 
                        "language_level": 5, 
                    }, 
                    {
                        "language": "Russian", 
                        "language_level": 5, 
                    },
                    ]}
                Учитывай тип данных в каждом поле и следуй инструкции к ним.
    """

    # app.run(host="0.0.0.0", port=5000)
    app.run(host="0.0.0.0", port=5001)
    #app.run()

