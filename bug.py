import socket
from docopt import docopt
import subprocess
import sys
import threading
import os

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
PWD_DEFAULT = 'C:\\'


def cmd_beep():
    code = 'echo •'
    return cmd_exec(code, shell=True)


def strip_split(string, split_on=' '):
    words = []
    word = []
    for i, c in enumerate(string):
        if c != split_on:
            word.append(c)
        if c == split_on or len(string) - 1 == i:
            if len(word) > 0:
                words.append(''.join(word))
            word = []
    return words


def cmd_exec(command, working_dir, shell=True):
    cmd = strip_split(command)
    db = ['cd', 'C:\\', '&&', 'dir']
    val = subprocess.run(cmd, stdin=subprocess.PIPE, shell=shell, stdout=subprocess.PIPE, cwd=working_dir, close_fds=True)
    return val.stdout.decode()


def receive_msg(socket, end_msg_identifier=END_MSG_IDF):
    msg = ''
    while end_msg_identifier not in msg:
        msg += socket.recv(1024).decode()
    return msg[0:-len(end_msg_identifier)]


def send_msg(socket, msg):
    socket.send((msg + END_MSG_IDF).encode())


def client_loop(sock):
    pwd = PWD_DEFAULT
    while True:
        msg = input(f'{pwd} $ ')
        send_msg(sock, msg)
        answer = receive_msg(sock)
        if answer == 'server terminated' or answer == 'disconnected':
            sock.close()
            break
        if '<UPDATE_PWD>' in answer:
            answer = answer[len('<UPDATE_PWD>'):]
            pwd = answer
            continue
        print(answer)


def server_loop(client_sock):
    command_info = {
        'terminate': 'terminate the server',
        'logout': 'disconnect from server',
        'beep': 'make a beep sound',
        'coninfo': 'display connection info',
        'bughelp': 'display this help',
        'cd': 'change directory remotely',
    }
    pwd = PWD_DEFAULT
    while True:
        try:
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
            elif msg == 'coninfo':
                answer = f'{client_sock.getpeername()} {os.environ.get("COMPUTERNAME", "Computername not found")}'
            elif msg == 'bughelp':
                answer = 'Special Commands:\n' + \
                         ''.join([f'  {commands}: {help}\n' for commands, help in zip(command_info.keys(), command_info.values())])
            elif strip_split(msg)[0] == 'cd':
                path_change_cmd = strip_split(msg)[1:][0]
                new_pwd = ''
                if path_change_cmd[0] == '/':
                    new_pwd = path_change_cmd[1:]
                elif path_change_cmd[:2] == '..':
                    new_pwd = pwd.replace('\\', '/').split('/')[:-1]
                    new_pwd = '\\'.join(new_pwd)
                else:
                    new_pwd = pwd + path_change_cmd.replace('/', '\\')
                if os.path.isdir(new_pwd):
                    pwd = new_pwd
                    print(f'pwd changed to: {pwd}')
                    answer = f'<UPDATE_PWD>{pwd}'
                else:
                    print(f'cd failed, {new_pwd} is not a valid directory')
                    answer = f'{new_pwd} is not a valid directory'
            else:
                answer = cmd_exec(f'{msg}', pwd)
            send_msg(client_sock, answer)
        except Exception as e:
            err_msg = f'Exception occoured: {str(e)}'
            print(err_msg)
            send_msg(client_sock, err_msg)


def run():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if opt['connect']:
        target_addr = (opt['<host>'], opt['--port'])
        print(f'connecting to {target_addr}')
        sock.connect(target_addr)
        print(f'connection establiched')
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