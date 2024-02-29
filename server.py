from flask import Flask, render_template, request, session, jsonify
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

UPLOAD_FOLDER = 'D:/projects/HACKATON_N4/upload/'
REPORTS_FOLDER = 'D:/projects/HACKATON_N4/resumes/'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)

app.config['SECRET_KEY'] = 'yuyfhjhdjshjdhfjdhsjhjdhjshjshsjhlllljgsdfghjk'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

CORS(app, supports_credentials=True)

Session(app)


def get_fields(text, instructions, parser):
    prompt_value = prompt.format_prompt(text=text, format_instructions=instructions)
    chain = prompt | llm | parser
    response = chain.invoke({'text': text, 'format_instructions': instructions})
    return response.dict()


def moderate(text: str):
    response = moderator.moderations.create(input=text)
    output = response.results[0].flagged
    return output


def llm_layer(text: str):
    if moderate(text) == False:
        try:
            easy_fields = get_fields(text, easy_instructions, easy_output_parser)
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
            contact_fields = get_fields(text, contact_instructions, contact_output_parser)
        except:
            contact_fields = {'contactItems': [], }
        try:
            education_fields = get_fields(text, education_instructions, education_output_parser)
        except:
            education_fields = {'educationItems': [], }
        try:
            experience_fields = get_fields(text, experience_instructions, experience_output_parser)
        except:
            experience_fields = {'experienceItems': [], }
        try:
            language_fields = get_fields(text, language_instructions, language_output_parser)
        except:
            language_fields = {'languageItems': []}

        easy_fields['resume_id'] = str(randint(10000, 100000))

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


def create_json(directory_name, file_name):
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
    path_to_json = os.path.join(REPORTS_FOLDER, directory_name, file_name.split('.')[0] + '.json')

    print(path_to_json)
    data = {'name': path_to_doc}
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
    print(directory_name, file_name)
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
        print('exxxxx=', e)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    llm = ChatOpenAI(model='gpt-3.5-turbo-0125', temperature=0, openai_api_key=chat_openai_key)
    moderator = OpenAI(api_key=chat_openai_key)
    prompt_template = """
    Ты - hr менеджер и тебе нужно извлекать данные из текста резюме кандидата
    Получи следующую информацию из текста резюме:

    {format_instructions}

    Строго соблюдай следующие инструкции:



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
    easy_fixik1 = RetryOutputParser.from_llm(parser=easy_output_parser, llm=llm)


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
    contact_fixik1 = RetryOutputParser.from_llm(parser=contact_output_parser, llm=llm)


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
    education_fixik1 = RetryOutputParser.from_llm(parser=education_output_parser, llm=llm)


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
    experience_fixik1 = RetryOutputParser.from_llm(parser=experience_output_parser, llm=llm)


    class LanguageItem(BaseModel):
        language: Optional[str] = Field(
            description="Извлеките язык владеемый кандидатом. Если такой информации нет выведите None")
        language_level: Optional[int] = Field(
            description="Определите уровень знания языка и верните цифру: 1: Начальный 2: Элементарный 3: Средний 4: Средне-продвинутый 5: Продвинутый 6: В совершенстве 7: Родной. Если данная информация не найдена или пункта нет в списке выведите None")


    class LanguageItems(BaseModel):
        languageItems: list[LanguageItem]


    language_output_parser = PydanticOutputParser(pydantic_object=LanguageItems)
    language_instructions = language_output_parser.get_format_instructions()

    # app.run(host="0.0.0.0", port=5000)
    app.run()
