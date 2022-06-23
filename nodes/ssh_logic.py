from datetime import datetime, timedelta
import paramiko
import re
from time import sleep


MAX_COMMAND_WAIT = 10
AFTER_COMMAND_WAIT = 1
CHANNEL_TIMEOUT = 20


class SSHConnector():
    client = None
    channel = None
    first_cmd_flag = False
    sudo_flag = False
    screen_flag = False

    def __init__(self, host, username, password, max_command_wait=MAX_COMMAND_WAIT, \
            after_command_wait=AFTER_COMMAND_WAIT, channel_timeout=CHANNEL_TIMEOUT) -> None:
        self.username = username
        self.password = password
        self.host = host
        self.max_command_wait = max_command_wait
        self.after_command_wait = after_command_wait
        self.channel_timeout = channel_timeout
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def connect(self) -> None:
        self.client.connect(self.host, username=self.username, password=self.password)
        self.channel = self.client.get_transport().open_session()
        self.channel.get_pty()
        self.channel.settimeout(self.channel_timeout)

    def send_command(self, cmd) -> None:
        if not self.first_cmd_flag:
            self.first_cmd_flag = True
            self.connect()
            self.channel.exec_command(cmd)
            self.wait_ready(cmd)
        else:
            self.channel.send(cmd + '\n')
            self.wait_ready(cmd)

    def wait_ready(self, cmd) -> None:
        sleep(3)
        dt_start = datetime.now()
        while not self.channel.recv_ready():
            dt_now = datetime.now()
            if dt_start + timedelta(seconds=self.max_command_wait) < dt_now:
                raise TimeoutError(f'Cannot execute command {cmd}, after {self.max_command_wait} seconds')
            sleep(1)
        sleep(self.after_command_wait)

    def enter_sudo(self) -> None:
        if self.sudo_flag:
            return
        self.send_command(f'sudo su')
        self.send_command(self.password)
        self.sudo_flag = True

    def enter_screen(self, screen) -> None:
        if self.screen_flag:
            return
        self.send_command(f'screen -dr {screen}')
        self.screen_flag = True

    def exec_commands(self, cmds, screen=False, sudo=False) -> str:
        if sudo:
            self.enter_sudo()
        if screen:
            self.enter_screen(screen)

        for cmd in cmds:
            self.send_command(cmd)
        return self.parse_answer(self.channel.recv(9999).decode())

    @staticmethod
    def parse_answer(answer):
        ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
        answer_parsed = ansi_escape.sub('', answer)

        answer_lines = []
        for l in answer_parsed.split('\n'):
            answer_lines += l.split('\r')
        return list(filter(lambda x: x, answer_lines))

    def __del__(self) -> None:
        if self.channel:
            self.channel.close()
        if self.client:
            self.client.close()
