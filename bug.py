import socket
from docopt import docopt
import subprocess
import sys
import threading

doc = """
Usage:
    bug
    bug connect <host> [options]
    bug server [options]

Options:
    --port=<PORT>  [default: 4613]
"""
opt = docopt(doc)
opt['--port'] = int(opt['--port'])

END_MSG_IDF = '<END>'


def cmd_beep():
    code = 'echo •'
    return cmd_exec(code, shell=True)


def cmd_exec(command, shell=True):
    return subprocess.run(["start", "cmd", "/c", command], shell=shell, stdout=subprocess.PIPE).stdout.decode()


def receive_msg(socket, end_msg_identifier=END_MSG_IDF):
    msg = ''
    while end_msg_identifier not in msg:
        msg += socket.recv(1024).decode()
    return msg[0:-len(end_msg_identifier)]


def send_msg(socket, msg):
    socket.send((msg + END_MSG_IDF).encode())


def client_loop(sock):
    while True:
        msg = input('$ ')
        send_msg(sock, msg)
        answer = receive_msg(sock)
        if answer == 'server terminated' or answer == 'disconnected':
            sock.close()
            break
        print(answer)


def server_loop(client_sock):
    while True:
        msg = receive_msg(client_sock)
        print(f'{msg} <- command received from {client_sock.getpeername()}')
        answer = ''
        if msg == 'terminate':
            send_msg(client_sock, 'server terminated')
            client_sock.close()
            print('terminating programm')
            sys.exit(0)
        elif msg == 'logout':
            send_msg(client_sock, 'disconnected')
            print(f'{client_sock.getpeername()} disconnected')
            client_sock.close()
            break
        elif msg == 'beep':
            cmd_beep()
        else:
            answer = cmd_exec(msg)
        send_msg(client_sock, answer)


def run():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if opt['connect']:
        target_addr = (opt['<host>'], opt['--port'])
        print(f'connecting to {target_addr}')
        sock.connect(target_addr)
        print('connected')
        client_loop(sock)
    elif opt['server']:
        server_addr = (socket.gethostbyname(socket.gethostname()), opt['--port'])
        print(f'creating Server on {server_addr}')
        sock.bind(server_addr)
        sock.listen(10)
        threads = []
        while True:
            print(f'server listening')
            client_sock = sock.accept()[0]
            print(f'connection accepted from {client_sock.getpeername()}')
            thread = threading.Thread(target=server_loop, args=[client_sock])
            threads.append(thread)
            thread.start()
            print(f'{len(threads)} active connections')


if __name__ == '__main__':
    run()