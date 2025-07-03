import sys
from flask import Flask, render_template
from vk_api import VkApi
from vk_api.audio import VkAudio, scrap_tracks
import vk_api # Не разобрался с импортами, думаю этот импорт лишний
import time
from threading import Thread # разделение на потоки: в 1 потоке подгрузка песен, во 2 потоке открытие окна и запуск сервера (pywebview + flask)
import webview # pywebview


app = Flask(__name__)
audios_list_for_app = [] # переменная, хранящая нынешний список песен(т.е используется, когда еще не все песни подгружены - парсинг всех песен +- 2 минуты)
login = "" # Ввести свой номер телефона(в формате +79999999999) или электронную почту, привязанные к аккаунту
password = "" # Пароль от аккаунта ВК


# функция для авторизации(работает, если на аккаунте стоит двухфакторная аутентификация) - будет переделываться
def authorization():
    code = input('Введи код для входа: ')
    return code, True

vk_session = vk_api.VkApi(login, password, auth_handler=authorization)

vk_session.auth()
vk_audio = VkAudio(vk_session)
vk = vk_session.get_api()
user_info = vk.users.get()[0]
user_id = user_info['id']


# функция поиска и парсинга песен с аккаунта
def music_searching():
    global audios_list_for_app
    audios = vk_audio.get_iter()
    audios_list = []
    for track in audios:
        audios_list.append(track)
        audios_list_for_app = audios_list # пока песни парсятся и добавляются в список мы обновляем нашу начальную переменную, которую я объявил глобальной, и можем досрочно использовать подгруженные песни
    print('Музыка найдена')


@app.route('/')
@app.route('/<q>')
def index(q=None):
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
        track = vk_audio.get_audio_by_id(user_id, q) # получение всех данных о треке
        artist = track.get('artist') # из всех данных выдает исполнителя
        title = track.get('title') # название
        duration = track.get('duration') # длительность в секундах
        photo = track.get('track_covers') # обложку трека или плейлиста
        url = track.get('url') # ссылка для воспроизведения
        # audio = next(vk_audio.search_iter(q=q))
        # url = audio['url']
        # print(audio, url)
        current_index = None
        for idx, audio in enumerate(audios_list_for_app):
            if str(audio.get('id')) == str(q):
                current_index = idx
                break

        # получаем айдишники предыдущего и следующего треков
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


# скорее всего ненужная функция запуска сервера, т.к pywebview поддерживает запуск сервера flask из под себя
def start_server():
    app.run(debug=True, port=5000, host='0.0.0.0')


# запуск окна pywebview
def open_window():
    webview.create_window(
        'VK Music Player', app,
        width=800,
        height=600,
        min_size=(400, 300))
    webview.start(debug=True)
    # app - это сам сервер, который указывается в качестве аргумента для его запуска


if __name__ == '__main__':
    music_thread = Thread(target=music_searching) # поток с поиском музыки
    music_thread.start()
    # server_thread = Thread(target=start_server)
    # server_thread.start()
    open_window() # запуск окна + старт сервера


    sys.exit()
