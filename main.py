import datetime
import json
import logging
import mimetypes
import pathlib
import urllib.parse  # використовується для маршрутизації
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket
from threading import Thread


BASE_DIR = pathlib.Path()
BUFFER = 1024
SERVER_IP = '127.0.0.1'
SERVER_PORT = 5000


def send_data_to_socket(body):
    """Відправляє дані на socket_server"""

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.sendto(body, (SERVER_IP, SERVER_PORT))
    client_socket.close()


class HTTPHandler(BaseHTTPRequestHandler):
    """Оброблення запитів від клієнта"""

    def do_POST(self):
        """Обробляє дані, введені в форму"""

        self.send_html('message.html')  # тут вказано те, що буде відправлятися на сервер (відобразиться на сайті) після натискання кнопки "Send"

        body = self.rfile.read(int(self.headers['Content-Length']))  # перехопимо дані, введені користувачем по кількості байтів, які вказані в headers
        send_data_to_socket(body)
        # self.send_response(302)
        # self.send_header('Content-Type', 'text/html')  # заголовок для відправлення браузеру
        # self.end_headers()  # закінчення обміну інформацією



    def do_GET(self):
        """Формує те, що повинно бути відправлено"""

        route = urllib.parse.urlparse(self.path)  # повертає об'єкти, в параметрах яких є шляхи до потрібних файлів
        match route.path:  # match element значить «зіставте елемент із наступними шаблонами»
            case "/":                        # значення взяті з файла index.html
                self.send_html('index.html')
            case "/message.html":
                self.send_html('message.html')
            case _:  # якщо нічого не знайдено з переліченого вище
                file = BASE_DIR/route.path[1:]
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html('error.html', 404)


    def send_html(self, filename, status_code=200):
        """Відправляє html на сервер"""

        self.send_response(status_code)  # повертання статусу "200 - все ок!; 404 - помилка!"
        self.send_header('Content-Type', 'text/html')  # заголовок для відправлення браузеру
        self.end_headers()  # закінчення обміну інформацією
        with open(filename, 'rb') as f:
            self.wfile.write(f.read())


    def send_static(self, filename):
        """Відправляє статичні ресурси (style.css, logo.png) на сервер"""

        self.send_response(200)  # повертання статусу "200 - все ок!; 404 - помилка!"
        mime_type, *rest = mimetypes.guess_type(filename)  # сам роспізнає mimetypes файлів
        if mime_type:
            self.send_header('Content-Type', mime_type)
        else:
            self.send_header('Content-Type', 'text/plain')  # тип - простий текст
        self.end_headers()  # закінчення обміну інформацією
        with open(filename, 'rb') as f:
            self.wfile.write(f.read())


# Створимо ф-ю, яка буде запускати сервер
def run(server=HTTPServer, handler=HTTPHandler):  # server - сервер, який працює; handler - обробляє запити
    """Запускає HTML-server"""

    address = ('0.0.0.0', 3000)  # 1й аргумент - це номер хосту (якщо б ми працювали локально, то він був би не вказаний,
    # але нам треба зберігати дані поза docker-контейнером, тому треба вказати "0.0.0.0");
    # 2й аргумент - це номер порту (повинен бути >=3000 та <10000 )
    http_server = server(address, handler)  # створюємо сервер
    # Запустимо новостворений сервер
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()  # у випадку натискання cntr+C сервер буде закрито


def save_data(data):
    """Зберігає дані"""

    # body прийде у вигляді байт-рядка і його треба перетворити на такий, що легко читається:
    body = urllib.parse.unquote_plus(data.decode())  # рядок міститиме '&' і '='
    try:
        # Розсплітимо і перетворимо в словник body по амперсанту '&' і знаку '='
        payload = {key: value for key, value in [el.split('=') for el in body.split('&')]}
        # Збережемо отримані від користувача дані в файлі data.json
        # Для додавання пари ключ-значення спочатку відкриваємо файл на читання, потім перезаписуємо файл з новим словником
        with open(BASE_DIR.joinpath('storage/data.json'), 'r', encoding='utf-8') as fd:  # для Windows обовязково вказувати encoding='utf-8' інакше розкодування буде невірним
            dict_data = json.load(fd)
        dict_data[str(datetime.datetime.now())] = payload
        with open(BASE_DIR.joinpath('storage/data.json'), 'w', encoding='utf-8') as fd:  # для Windows обовязково вказувати encoding='utf-8' інакше розкодування буде невірним
            json.dump(dict_data, fd, ensure_ascii=False)  # якщо вказати ensure_ascii=False, то json.dump не буде замінювати кирилицю на unicod (буде відображати без змін)

    except ValueError as err:
        logging.error(f"Field parse data {body} with error {err}")
    except OSError as err:
        logging.error(f"Field write data {body} with error {err}")



def run_socket_server(ip, port):
    """Запускає socket_server"""

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # тут інші параметри йдуть за замовчуванням, але можна призначити (див. конспект)
    # призначимо кортеж для сервера
    server = ip, port

    # "Прибіндимо" до сокет-сервера хост і порт
    server_socket.bind(server)  # подвійні дужки, бо передається кортеж
    # Запустимо цикл отримання даних по 1024 байт з сервера
    try:
        while True:
            data, address = server_socket.recvfrom(BUFFER)
            save_data(data)
    except KeyboardInterrupt:
        logging.info('Socked server stopped')
    finally:
        server_socket.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(threadName)s %(message)s")
    # За допомогою механізму volumes, зберіггатимемо дані з storage/data.json не всередині docker-контейнера
    STORAGE_DIR = pathlib.Path().joinpath('storage')
    FILE_STORAGE = STORAGE_DIR / 'data.json'
    if not FILE_STORAGE.exists():
        with open(FILE_STORAGE, 'w', encoding='utf-8') as fd:
            json.dump({}, fd, ensure_ascii=False)

    # Створюємо потік для thread_server
    thread_server = Thread(target=run)
    # Запускаємо потік thread_server
    thread_server.start()

    # Створюємо потік для socket_server. В аргументи додаємо IP нашого компа і порт 5000
    thread_socket = Thread(target=run_socket_server(SERVER_IP, SERVER_PORT))
    # Запускаємо потік socket_server
    thread_socket.start()




