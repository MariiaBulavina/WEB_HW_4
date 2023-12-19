from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import logging
import mimetypes
import pathlib
import socket
from threading import Thread
import urllib.parse

BASE_DIR = pathlib.Path()
SERVER_IP = '127.0.0.1' 
SOCKET_PORT = 5000
HTTP_PORT = 3000

class HTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        route = urllib.parse.urlparse(self.path)

        match route.path:
            case "/":
                self.send_html('index.html')
            case "/message.html":
                self.send_html('message.html')
            case _:
                file = BASE_DIR / route.path[1:]
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html('error.html', 404)

    def do_POST(self):

        body = self.rfile.read(int(self.headers['Content-Length']))
        send_data_to_socket(body)
        
        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

    def send_html(self, filename, status_code=200):

        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()

        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_static(self, filename):
        
        self.send_response(200)
        m_type = mimetypes.guess_type(filename)

        if m_type:
            self.send_header('Content-Type', m_type[0])
        else:
            self.send_header('Content-Type', 'text/plain')

        self.end_headers()

        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

  
def run(server=HTTPServer, handler=HTTPRequestHandler):
    
    address = ('0.0.0.0', HTTP_PORT)
    http_server = server(address, handler)

    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()


def run_socket_server(ip, port):

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = (ip, port)
    server_socket.bind(server)
    try:
        while True:
            data = server_socket.recv(1024)
            save_data(data)
    except KeyboardInterrupt:
        logging.info('Socket server stopped')
    finally:
        server_socket.close()


def make_dict(data):

    with open('storage/data.json', 'r', encoding='utf-8') as f:

        try:
            data_dct = json.load(f)
        except ValueError:
            data_dct = {}
    
        data_dct[str(datetime.now())] = data

    return data_dct


def save_data(data):

    body = urllib.parse.unquote_plus(data.decode())

    try:
        r_data = [el.split('=') for el in body.split('&')]
        data = {k: v for k, v in r_data}
        data_dct = make_dict(data)

        with open('storage/data.json', 'w', encoding='utf-8') as f:
            json.dump(data_dct, f, ensure_ascii=False)

    except ValueError as err:
        logging.error(f'Failed parse data{data} with error {err}')
    except OSError as err:
        logging.error(f'Failed write data{data} with error {err}')


def send_data_to_socket(body):

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.sendto(body, (SERVER_IP, SOCKET_PORT))
    client_socket.close()


if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO, format="%(threadName)s %(message)s")
    
    STORAGE_DIR = pathlib.Path().joinpath('storage')
    FILE_STORAGE = STORAGE_DIR / 'data.json'

    if not FILE_STORAGE.exists():

        with open(FILE_STORAGE, 'w', encoding='utf-8') as fd:
            json.dump({}, fd, ensure_ascii=False)


    thread_server = Thread(target=run)
    thread_server.start()

    thread_socket = Thread(target=run_socket_server, args=(SERVER_IP, SOCKET_PORT))
    thread_socket.start()