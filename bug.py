import socket
from docopt import docopt
import subprocess
import sys
import threading
import os
import traceback
import random
import atexit
import platform

doc = """
Usage:
    bug
    bug connect <host> [options]
    bug server [options]

Options:
    -p --port=<PORT>            [default: 4613]
    -P --password=<PASSWORD>    [default: 'NOPW']
    -l --local                  Create a local server
    -h --help                   Display this
"""
opt = docopt(doc)
opt['--port'] = int(opt['--port'])
if opt['<host>'] == 'here':
    opt['<host>'] = socket.gethostbyname(socket.gethostname())

def read_in_required_args():
    if opt['connect'] == False and opt['server'] == False:
        u_input = ''
        while u_input != 'server' and u_input != 'connect':
            u_input = input('Server or Client? server/connect\n')
        opt[u_input] = True
        if u_input == 'connect':
            ip = ''
            validate_ip = lambda ip: len(ip.split('.')) == 4 and len(ip) >= 7 and len(ip) <= 15
            while not validate_ip(ip):
                ip = input('ip: ')
                opt['<host>'] = ip
                if not validate_ip(ip):
                    print('invalid ip')
        port = input('port: ')
        if port != '':
            opt['--port'] = int(port)
        else:
            print(f'use default of {opt["--port"]}')
        password = input('password: ')
        if password != '':
            opt['--password'] = password
        else:
            print(f'use default of {opt["--password"]}')


read_in_required_args()

END_MSG_IDF = '<END>'
if platform.system() == 'Windows': 
    PWD_DEFAULT = 'C:\\' 
else:
    PWD_DEFAULT = '/'
PASS_CODE = f'<{opt["--password"]}a96o5uoae56u4aoe6u546aoe54u9ao4eu65a4oe8u4aoe541u98ao4eu51ao98eu46>'


def get_prime_generator(start_num=0):
    if start_num <= 1:
        yield 1
    if start_num <= 2:
        yield 2
    i = max(start_num, 3)
    j = 2
    while True:
        if j >= i:
            yield i
            j = 2
            i += 1
        if i % j == 0:
            j = 2
            i += 1
        j += 1


def get_random_prime(min_oof=5, max_oof=7):
    if min_oof + 1 > max_oof:
        raise Exception(f'The lower magnitude factor ({min_oof}) need to be at least one less that the maximum magnitude factor ({max_oof}).')
    return next(get_prime_generator(random.randint(10**(min_oof), 10**(max_oof))))


class RSACrypter:
    def __init__(self):
        self.message = 10
        self.e = 45
        self.d = 7
        self.n = 47


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


def cmd_exec(command, working_dir=None, shell=True):
    cmd = strip_split(command)
    val = subprocess.run(" ".join(cmd), stdin=subprocess.PIPE, shell=shell, stdout=subprocess.PIPE, cwd=working_dir, close_fds=True)
    try:
        return val.stdout.decode('unicode_escape', errors='strict')
    except Exception as e:
        err_msg = f'!!! encoding error Occoured. Ignoring.\n' \
                  f'!!! {str(e)}\n' \
                  f'^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n'
        return err_msg + val.stdout.decode('unicode_escape', errors='ignore')

def receive_msg(socket, end_msg_identifier=END_MSG_IDF):
    msg = ''
    while end_msg_identifier not in msg:
        msg += socket.recv(1024).decode('utf-8')
    return msg[0:-len(end_msg_identifier)]


def send_msg(socket, msg):
    socket.send((msg + END_MSG_IDF).encode('utf-8').strip())


def client_loop(sock):
    pwd = PWD_DEFAULT
    while True:
        command_msg = input(f'{pwd} $ ')
        send_msg(sock, command_msg)
        answer = receive_msg(sock)
        if answer == '<SHUTDOWN>':
            print('Server was shutdown')
            sock.close()
            sys.exit(0)
        elif answer == 'disconnected' and command_msg == 'exit':
            sys.exit(0)
        elif answer == 'disconnected':
            break
        elif '<UPDATE_PWD>' in answer:
            answer = answer[len('<UPDATE_PWD>'):]
            pwd = answer
            continue
        print(answer)


def server_loop(client_sock):
    command_info = {
        'shutdown': 'shutdown the server',
        'reconnect': 'reconnect to server',
        'beep': 'make a beep sound',
        'coninfo': 'display connection info',
        'bughelp': 'display this help',
        'cd': 'change directory remotely',
        'exit': 'terminate client',
        'cmd': '''run following string as command, even if special command.
       e.g. cmd shutdown runs the command shutdown remotely
       instead of shutting down the server'''
    }
    pwd = PWD_DEFAULT
    while True:
        try:
            msg = receive_msg(client_sock)
            print(f'{msg} <- command received from {client_sock.getpeername()}')
            answer = ''
            if msg == 'shutdown':
                send_msg(client_sock, '<SHUTDOWN>')
                client_sock.close()
                print('terminating server')
                os._exit(0)
            elif msg == 'reconnect' or msg == 'exit':
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
                if platform.system() == 'Windows': 
                    slash = "\\"
                else:
                    slash = "/"
                path_change_cmd = strip_split(msg)[1:][0]
                new_pwd = ''
                if path_change_cmd[0] == '/':
                    new_pwd = path_change_cmd[1:]
                elif path_change_cmd[1] == ':':
                    new_pwd = path_change_cmd
                elif path_change_cmd[:2] == '..':
                    new_pwd = pwd.replace(slash, '/').split('/')[:-2]
                    new_pwd = slash.join(new_pwd)
                else:
                    new_pwd = pwd + path_change_cmd.replace('/', slash)
                if os.path.isdir(new_pwd):
                    pwd = (new_pwd + slash).replace(slash+slash, slash)
                    print(f'pwd changed to: {pwd}')
                    answer = f'<UPDATE_PWD>{pwd}'
                else:
                    answer = f'cd failed, {new_pwd} is not a valid directory'
                    print(answer)
            else:
                if answer[:3] == 'cmd':
                    answer = answer[3:].strip()
                print(answer)
                answer = cmd_exec(f'{msg}', pwd)
            send_msg(client_sock, answer)
        except Exception as e:
            err_msg = f'Exception occoured: {str(e)}'
            print_exception(e)
            send_msg(client_sock, err_msg)


def print_exception(e):
    traceback.print_exception(type(e), e, e.__traceback__)

def run():
    def get_socket():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock
    if opt['connect']:
        while True:
            sock = get_socket()
            target_addr = (opt['<host>'], opt['--port'])
            print(f'connecting to {target_addr}')
            sock.connect(target_addr)
            print(f'connection establiched')
            print('send authentication')
            send_msg(sock, PASS_CODE)
            if receive_msg(sock) == '<OK>':
                print('authentication successfull')
                client_loop(sock)
            else:
                print('authentication faild, terminating client')
                sys.exit(1)
    elif opt['server']:
        sock = get_socket()
        server_addr = (socket.gethostbyname(socket.gethostname()), opt['--port'])
        print(f'creating Server on {server_addr}')
        sock.bind(server_addr)
        sock.listen(10)
        threads = []
        while True:
            print(f'server listening')
            client_sock = sock.accept()[0]
            atexit.register(lambda: send_msg(client_sock, '<SHUTDOWN>'))
            print(f'connection accepted from {client_sock.getpeername()}')
            print('authenticating')
            if receive_msg(client_sock) == PASS_CODE:
                print(f'valid authentication received from {client_sock.getpeername()}')
                send_msg(client_sock, '<OK>')
                thread = threading.Thread(target=server_loop, args=[client_sock])
                threads.append(thread)
                thread.start()
                for t in threads:
                    if not t.is_alive():
                        threads.remove(t)
                print(f'{len(threads)} active connection{"s" if len(threads) > 1 else ""}')
            else:
                print(f'invalid authentication received form {client_sock.getpeername()}, ignoring connection attempt')
                send_msg(client_sock, '<NOT_OK>')


if __name__ == '__main__':
    while True:
        try:
            run()
        except Exception as e:
            traceback.print_exception(type(e), e, e.__traceback__)
            u_input = input('do you want to restart? y/n')
            if u_input == 'n':
                sys.exit(0)
