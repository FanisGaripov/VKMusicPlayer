import sys
import io
#
# if getattr(sys, 'frozen', False):
#     # Если приложение 'заморожено' PyInstaller
#     sys.stdin = io.StringIO()
#     sys.stdout = sys.__stdout__
#     sys.stderr = sys.__stderr__


import os
from flask import Flask, render_template, redirect, request, session, jsonify, url_for
from vk_api import VkApi
from vk_api.audio import VkAudio, scrap_tracks
import vk_api
import time
from threading import Thread, Event, Condition
import webview
from random import randint
from vk_api.exceptions import Captcha, AuthError
from vk_api.utils import enable_debug_mode
import asyncio

#
# if sys.platform == "win32":
#     sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


app = Flask(__name__)
audios_list_for_app = []
see_login = False
see_code = False
see_captcha = False
captcha_sid = ''
captcha_url = ''
captcha_key = ''
auth_code = ''
login = ''
password = ''
app.secret_key = 'supersecretkey'
captcha_data = {
    'key': None,
    'ready': False
}
auth_data = {
    'code': None,
    'ready': False
}


def init_auth_file():
    if not os.path.exists('auth.txt'):
        with open('auth.txt', 'w') as f:
            pass

init_auth_file()
auth_event = Event()


async def handle_auth():
    global see_code, auth_data
    while see_code and auth_data['ready'] == False:
        await asyncio.sleep(0.1)
    return auth_data['code']


async def handle_captcha():
    global see_captcha, captcha_data
    while see_captcha and captcha_data['ready'] == False:
        await asyncio.sleep(0.1)
    return captcha_data['captcha']



def authorization():
    global see_code, auth_code, auth_data
    see_code = True
    print('Требуется код двухфакторной аутентификации')
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    code = asyncio.run_coroutine_threadsafe(handle_auth(), loop)
    return code, True


def captcha_handler(captcha):
    global see_captcha, captcha_sid, captcha_url, captcha_data
    see_captcha = True
    print('Требуется ввод капчи')
    if hasattr(captcha, 'redirect_uri'):
        captcha_url = captcha.redirect_uri
    else:
        # Формируем URL капчи вручную, если redirect_uri недоступен
        captcha_url = f"https://api.vk.com/captcha.php?sid={captcha.sid}&s=1"

    print(f"Капча доступна по URL: {captcha_url}")
    captcha_sid = captcha.sid
    captcha_url = f"https://vk.com/captcha.php?sid={captcha.sid}&s=1"
    '''http:\/\/api.vk.com\/captcha.php?sid=239633676097&s=1&v={int(time.time())}'''
    print(captcha_url)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    key = asyncio.run_coroutine_threadsafe(handle_captcha(), loop)
    return captcha.try_again(key)


def enable_captcha_support(session):
    """Настройка поддержки капчи"""
    session.http.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'X-VK-Captcha-Supported': '1',
        'X-VK-Android-Client': 'new'
    })


# @app.route('/', methods=['GET','POST'])
def login_to_acc(login, password):
    global vk_audio, user_id, see_login, see_code, see_captcha, vk_session
    see_login = False
    try:
        vk_session = vk_api.VkApi(
            login=login,
            password=password,
            auth_handler=authorization,
            captcha_handler=captcha_handler,
            app_id=2685278
        )
        enable_debug_mode(vk_session, print_content=True)
        enable_captcha_support(vk_session)

        print('Пытаюсь авторизоваться')
        vk_session.auth()

        # Если авторизация успешна
        vk_audio = VkAudio(vk_session)
        vk = vk_session.get_api()
        user_info = vk.users.get()[0]
        user_id = user_info['id']

        with open('auth.txt', 'w') as auth_file:
            auth_file.write(f"{login}\n{password}")

        # see_code = False
        # see_captcha = False
        # see_login = False

        return True
    except Exception as e:
        print(f"Ошибка авторизации: {e}")
        # При ошибке сбрасываем все флаги, чтобы не застрять в состоянии
        # see_code = False
        # see_captcha = False
        # see_login = True
        return False


# except Exception as e:
#     print(f"Ошибка авторизации: {e}")
#     if see_captcha:
#         return False, 'captcha'
#     elif see_code:
#         return False, 'code'
#     else:
#         return False, 'login'


with open('auth.txt', 'r') as auth_file:
    info = auth_file.readlines()
    if len(info) == 0 or len(info) < 2:
        see_login = True
    else:
        login = info[0].strip()
        password = info[1].strip()
        login_thread = Thread(target=login_to_acc, args=(login, password))
        login_thread.start()
        login_thread.join()


if not see_login and not see_captcha and not see_code:
    vk_audio = VkAudio(vk_session)
    vk = vk_session.get_api()
    user_info = vk.users.get()[0]
    user_id = user_info['id']

    with open('auth.txt', 'w') as auth_file:
        auth_file.write(f"{login}\n{password}")


def music_searching():
    global audios_list_for_app, vk_audio
    audios = vk_audio.get_iter()
    audios_list = []
    for track in audios:
        audios_list.append(track)
        audios_list_for_app = audios_list
    print('Музыка найдена')


@app.route('/')
@app.route('/<q>')
def index(q=None):
    print('ИНДЕЕЕЕЕЕЕЕЕЕЕЕЕЕЕЕЕЕЕЕЕЕЕЕЕЕЕЕЕЕКС')
    global see_code, see_captcha, see_login
    if see_login:
        return redirect('/login')
    elif see_captcha:
        return redirect('/captcha')
    elif see_code:
        return redirect('/code')
    else:
        music_info = []
        url = ''
        # q = "Hear Me Now"
        # audio = next(vk_audio.search_iter(q=q))
        # url = audio['url']
        # print(audio, url)

        for music in audios_list_for_app:
            artist = music.get('artist')
            title = music.get('title')
            duration = music.get('duration')
            time_format = time.strftime("%M:%S", time.gmtime(int(duration)))
            duration = time_format
            photo = music.get('track_covers')
            track_id = music.get('id')
            if len(photo) != 0:
                info = f'<a href="/{track_id}"><img src="{photo[0]}"> {artist}, {title}, {duration}</a>'
            else:
                info = f'<a href="/{track_id}"><img src="static/default_track.jpg"> {artist}, {title}, {duration}</a>'
            music_info.append(info)
        if q != None:
            # for track in audios_list:
            #     if q in track['title'] or q in track['artist']:
            #         artist = track.get('artist')
            #         title = track.get('title')
            #         duration = track.get('duration')
            #         photo = track.get('track_covers')
            #         url = track.get('url')
            #         print(url)
            #         break
            track = vk_audio.get_audio_by_id(user_id, q)
            artist = track.get('artist')
            title = track.get('title')
            duration = track.get('duration')
            photo = track.get('track_covers')
            url = track.get('url')
            # audio = next(vk_audio.search_iter(q=q))
            # url = audio['url']
            # print(audio, url)
            current_index = None
            for idx, audio in enumerate(audios_list_for_app):
                if str(audio.get('id')) == str(q):
                    current_index = idx
                    break

            # Получаем ID предыдущего и следующего треков
            prev_track_id = None
            next_track_id = None

            if current_index is not None:
                if current_index > 0:
                    prev_track_id = audios_list_for_app[current_index - 1].get('id')
                if current_index < len(audios_list_for_app) - 1:
                    next_track_id = audios_list_for_app[current_index + 1].get('id')

            return render_template('index.html', artist=artist, title=title, duration=duration, photo=photo, url=url, audios_list=music_info, prev_track_id=prev_track_id, next_track_id=next_track_id)
        else:
            return render_template('index.html', audios_list=music_info, url=None, artist=None, title=None, duration=None, photo=None)


# Изменение: Добавлены маршруты для обработки капчи и кода
@app.route('/captcha', methods=['GET', 'POST'])
def captcha():
    global captcha_key, see_captcha, captcha_url, captcha_event, captcha_data

    if request.method == 'POST':
        captcha_key = request.form.get('captcha_key')
        if not captcha_key:
            return render_template('captcha.html',
                                   captcha_url=captcha_url,
                                   error="Пожалуйста, введите капчу")

        # Сохраняем ключ и разблокируем handler
        captcha_data['key'] = captcha_key
        captcha_data['ready'] = True
        see_captcha = False

        return redirect('/')

    return render_template('captcha.html', captcha_url=captcha_url)


@app.route('/code', methods=['GET', 'POST'])
def auth_code():
    global auth_code, see_code, auth_data

    if request.method == 'POST':
        auth_code = request.form.get('code')

        auth_data['code'] = auth_code
        auth_data['ready'] = True
        see_code = False

        return redirect('/')

    return render_template('code.html')


# def run_login_in_thread(login, password):
#     global operation, status
#     operation, status = login_to_acc(login, password)


@app.route('/login', methods=['GET', 'POST'])
def login():
    global see_login, see_code, see_captcha
    see_login = False
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')
        see_login = False

        auth_thread2 = Thread(target=login_to_acc, args=(login, password))
        auth_thread2.daemon = True
        auth_thread2.start()
        auth_thread2.join()
        time.sleep(1)
        print('Перед выбором...')
        print(f'Код:{see_code}, Капча:{see_captcha}, Логин:{see_login}')
        if see_code:
            return redirect('/code')
        elif see_captcha:
            return redirect('/captcha')
        elif see_login:
            return redirect('/login')
        elif not see_login and not see_captcha and not see_code:
            return redirect('/')
    return render_template('login.html')


# библиотека ffmpeg для загрузки hls
def download_tracks():
    pass


# searched_tracks_list = []


# def tracks_in_searching(query):
#     global searched_tracks_list, vk_audio
#     tracks = vk_audio.search_iter(query)
#     audios_list = []
#     for track in tracks:
#         audios_list.append(track)
#         searched_tracks_list = audios_list
#         print(searched_tracks_list)


music_info = []


@app.route('/search', methods=['GET', 'POST'])
@app.route('/search/<q>', methods=['GET', 'POST'])
def search(q=None):
    if request.method == 'GET' and q is None:
        return render_template('search.html', searched_tracks_list=None)

    if request.method == 'POST':
        query = request.form.get('zapros')
        session['last_search_results'] = []
        session['last_search_query'] = query
        session.modified = True
        print(f'Запрос {query}')
        tracks = list(vk_audio.search(query, 10))  # Преобразуем в список
        music_info = []
        serializable_tracks = []

        for music in tracks:
            # Подготовка данных для сессии
            track_data = {
                'id': music.get('id'),
                'artist': music.get('artist'),
                'title': music.get('title'),
                'duration': music.get('duration'),
                'track_covers': music.get('track_covers', []),
                'url': music.get('url')
            }
            serializable_tracks.append(track_data)
            print(serializable_tracks)

            # Формирование HTML для отображения
            duration = time.strftime("%M:%S", time.gmtime(int(track_data['duration'])))
            photo = track_data['track_covers']
            track_id = track_data['id']

            if photo and len(photo) > 0:
                info = f'<a href="/search/{track_id}"><img src="{photo[0]}"> {track_data["artist"]}, {track_data["title"]}, {duration}</a>'
            else:
                info = f'<a href="/search/{track_id}"><img src="static/default_track.jpg"> {track_data["artist"]}, {track_data["title"]}, {duration}</a>'

            music_info.append(info)

        # Сохраняем в сессию
        session['last_search_results'] = serializable_tracks
        session['last_search_query'] = query
        session.modified = True

        return render_template('search.html', searched_tracks_list=music_info)

    if request.method == 'GET' and q is not None:
        try:
            tracks = session.get('last_search_results', [])
            track = None
            current_index = None

            # Ищем трек по ID с проверкой на None
            for idx, t in enumerate(tracks):
                if t.get('id') is not None and str(t['id']) == str(q):
                    track = t
                    current_index = idx
                    break

            if not track:
                return "Трек не найден", 404

            # Формируем данные для плеера
            duration_sec = track.get('duration', 0)
            time_format = time.strftime("%M:%S", time.gmtime(int(duration_sec))) if duration_sec else "0:00"
            photo = track.get('track_covers', [])
            print(photo)

            # Получаем соседние треки
            prev_track_id = tracks[current_index - 1]['id'] if current_index > 0 else None
            next_track_id = tracks[current_index + 1]['id'] if current_index < len(tracks) - 1 else None

            # Восстанавливаем список треков для отображения
            music_info = []
            for music in tracks:
                duration_info = time.strftime("%M:%S", time.gmtime(int(music.get('duration', 0))))
                photo_info = music.get('track_covers', [])
                track_id = music['id']

                if photo_info and len(photo_info) > 0:
                    info = f'<a href="/search/{track_id}"><img src="{photo_info[0]}"> {music["artist"]}, {music["title"]}, {duration_info}</a>'
                else:
                    info = f'<a href="/search/{track_id}"><img src="static/default_track.jpg"> {music["artist"]}, {music["title"]}, {duration_info}</a>'

                music_info.append(info)

            return render_template('search.html',
                                   searched_tracks_list=music_info,
                                   artist=track['artist'],
                                   title=track['title'],
                                   duration=time_format,
                                   photo=photo[0] if photo and len(photo) > 0 else 'static/default_track.jpg',
                                   url=track['url'],
                                   prev_track_id=prev_track_id,
                                   next_track_id=next_track_id)

        except Exception as e:
            print(f"Ошибка при получении аудио по ID: {e}")
            return "Ошибка получения аудио", 500

    return "Method Not Allowed", 405


@app.route('/likes', methods=['GET', 'POST'])
def likes():
    return render_template('likes.html')


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    return render_template('settings.html')


@app.route("/logout", methods=['GET'])
def logout():
    global see_login, login, password, vk_audio, user_id
    with open('auth.txt', 'w') as auth_file:
        auth_file.write('')
    see_login = True
    login = ''
    password = ''
    vk_audio = None
    user_id = None
    return redirect('/login')


@app.route('/random_track_from_playlist', methods=['GET', 'POST'])
def random_track_from_playlist():
    global audios_list_for_app
    random_number_of_track = randint(0, len(audios_list_for_app) - 1)
    track_id = audios_list_for_app[random_number_of_track].get('id')
    # artist = audios_list_for_app[random_number_of_track].get('artist')
    # title = audios_list_for_app[random_number_of_track].get('title')
    # photo = audios_list_for_app[random_number_of_track].get('photo')
    # duration = audios_list_for_app[random_number_of_track].get('duration')
    # url = audios_list_for_app[random_number_of_track].get('url')
    return redirect(f'/{track_id}')


@app.route('/player')
def only_player_page():
    return render_template('player.html', artist='Неизвестный исполнитель', title='Нет названия', duration=None, photo='static/default_track.jpg')


def start_server():
    app.run(debug=True, port=5000, host='0.0.0.0')


def open_window():
    webview.create_window(
        'VK Music Player', app,
        width=800,
        height=600,
        min_size=(400, 300))
    webview.start(debug=True)


if __name__ == '__main__':
    # Инициализация файла авторизации
    init_auth_file()

    # Загрузка данных авторизации
    with open('auth.txt', 'r') as auth_file:
        info = auth_file.readlines()
        if len(info) >= 2:
            login = info[0].strip()
            password = info[1].strip()

            # Пытаемся авторизоваться в фоновом режиме
            auth_thread = Thread(target=login_to_acc, args=(login, password))
            auth_thread.daemon = True
            auth_thread.start()
        else:
            see_login = True

    # Запуск поиска музыки (если авторизация успешна)
    if not see_login:
        music_thread = Thread(target=music_searching)
        music_thread.daemon = True
        music_thread.start()

    # Запуск основного окна
    open_window()
