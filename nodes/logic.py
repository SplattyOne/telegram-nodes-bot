import json
import re
import traceback
from abc import abstractmethod
from datetime import datetime

import requests
from django.conf import settings
from django.utils import timezone

from nodes.models import CheckHistory, Node
from nodes.ssh_logic import SSHConnector
from tgbot.handlers.broadcast_message.utils import _send_message

MAX_ERROR_LEN = 50
ADMIN_USERNAME = 'tomatto'


def remove_multiple_spaces(line):
    new_line = ''

    for i, letter in enumerate(line):
        if i != 0 and letter == ' ' and line[i-1] == ' ':
            continue
        new_line += letter
    return new_line


class BaseNodeCheckerAPI():
    node_type = None
    node_api = None

    def __init__(self, ip, port):
        node_api_template = NODE_TYPES[self.node_type].get('api')
        self.node_api = node_api_template.format(ip, port)

    @staticmethod
    def external_api_check(url):
        try:
            return requests.get(url, timeout=15).json()
        except Exception:
            return {}

    def health_check(self):
        try:
            return self.parse_answer(requests.get(self.node_api, timeout=15))
        except Exception as e:
            return (False, f'Wrong request answer {str(e)[:MAX_ERROR_LEN]}')

    def parse_answer(self, answer):
        if not isinstance(answer, requests.Response):
            return (False, 'Wrong request answer type')
        if answer.status_code > 300:
            return (False, f'Wrong request answer code {answer.status_code}')
        try:
            return self.parse_unique_answer(answer.text)
        except Exception as e:
            return (False, f'Wrong request answer parsing {str(e)[:MAX_ERROR_LEN]}')

    @abstractmethod
    def parse_unique_answer(self, answer: list[str]):
        pass


class BaseNodeCheckerSSH():
    node_type: str = None
    sudo: bool = False
    screen: bool = False
    cmds: list = None

    def __init__(self, ip: str, username: str, password: str, screen: bool, sudo: bool, **kwargs) -> None:
        self.ssh = SSHConnector(ip, username, password, **kwargs)
        self.screen = screen
        self.sudo = sudo
        self.username = username

    @staticmethod
    def external_api_check(url: str) -> dict:
        try:
            return requests.get(url, timeout=15).json()
        except Exception:
            return {}

    def health_check(self):
        try:
            return self.parse_answer(self.ssh.exec_commands(self.cmds, self.screen, self.sudo))
        except Exception as e:
            return (False, f'Wrong ssh answer {str(e)[:MAX_ERROR_LEN]}')

    def parse_answer(self, answer):
        try:
            return self.parse_unique_answer(answer)
        except Exception:
            return (False, f'Wrong ssh answer parsing {traceback.format_exc()}')

    @abstractmethod
    def parse_unique_answer(self, answer: list[str]):
        pass


class AptosNodeChecker(BaseNodeCheckerAPI):

    def __init__(self, ip, port):
        self.node_type = NODE_TYPE_APTOS
        super().__init__(ip, port)

    def parse_unique_answer(self, answer: list[str]):
        # aptos_ledger_version = self.external_api_check('https://fullnode.devnet.aptoslabs.com/').get('ledger_version')

        # sync_lines = list(filter(lambda x: 'aptos_state_sync_version' in x, answer.split('\n')))
        # if not len(sync_lines):
        #     return (False, f'Wrong aptos_state_sync_version reply')

        # applied_block_find = list(filter(lambda x: 'applied_transaction_outputs' in x, sync_lines))
        # if not len(applied_block_find):
        #     return (False, f'Wrong aptos_state_sync_version applied reply')
        # applied_block = applied_block_find[0].split(' ')[-1]

        # synced_block_find = list(filter(lambda x: 'synced' in x, sync_lines))
        # if not len(synced_block_find):
        #     return (False, f'Wrong aptos_state_sync_version synced reply')
        # synced_block = synced_block_find[0].split(' ')[-1]

        # if aptos_ledger_version and abs(int(aptos_ledger_version) - int(synced_block)) > 10:
        #     return (False, f'Something wrong in sync process, ledger {aptos_ledger_version}, synced {synced_block}')

        # if aptos_ledger_version and abs(int(aptos_ledger_version) - int(applied_block)) > 10:
        #     return (False, f'Something wrong in sync process, ledger {aptos_ledger_version}, applied {applied_block}')
        answer = json.loads(answer)

        ledger_version = answer.get('ledger_version')
        if not ledger_version:
            return (False, 'Wrong aptos ledger_version reply')

        ledger_timestamp = answer.get('ledger_timestamp')
        if not ledger_timestamp:
            return (False, 'Wrong aptos ledger_timestamp reply')
        ledger_timestamp_dt = datetime.fromtimestamp(
            int(ledger_timestamp) // 1000 // 1000)

        return (True, f'Node is OK, ledger {ledger_version}, dt {ledger_timestamp_dt}', 0)


class MinimaNodeChecker(BaseNodeCheckerAPI):

    def __init__(self, ip, port):
        self.node_type = NODE_TYPE_MINIMA
        super().__init__(ip, port)

    def parse_unique_answer(self, answer: list[str]):
        answer = json.loads(answer)
        if answer.get('status') is not True:
            return (False, f'Node status is note True {answer.get("status")}')
        response_rewards = answer['response']['details']['rewards']
        rewards = response_rewards.get('dailyRewards', 0)
        rewards += response_rewards.get('previousRewards', 0)
        rewards += response_rewards.get('communityRewards', 0)
        rewards += response_rewards.get('inviterRewards', 0)
        return (True, f'Node is OK, rewards: {rewards}', rewards)


class MassaNodeChecker(BaseNodeCheckerSSH):

    def __init__(self, ip: str, username: str, password: str, screen: bool, sudo: bool):
        # self.cmds = ['. <(wget -qO- https://raw.githubusercontent.com/SecorD0/Massa/main/insert_variables.sh)',
        # 'massa_node_info']
        self.cmds = [
            "cd $HOME/massa/massa-client/ && ./massa-client -p $(cat $HOME/massapasswd) wallet_info"]
        super().__init__(ip, username, password, screen, sudo)

    def parse_unique_answer(self, answer: list[str]):
        # active_nodes_in_find = list(filter(lambda x: 'Входящих подключений:' in x, answer[::-1]))
        # active_nodes_out_find = list(filter(lambda x: 'Исходящих подключений:' in x, answer[::-1]))
        # if not len(active_nodes_in_find) or not len(active_nodes_out_find):
        #     return (False, f'Wrong active nodes reply')
        # active_nodes_in = active_nodes_in_find[0].strip().split(' ')[-1]
        # active_nodes_out = active_nodes_out_find[0].strip().split(' ')[-1]
        rolls_find = list(filter(lambda x: 'Rolls:' in x, answer[::-1]))
        if len(rolls_find) == 0:
            return (False, 'Wrong rolls reply')
        parse_rolls = rolls_find[0].strip().split(', ')
        if len(parse_rolls) < 3:
            return (False, 'Wrong rolls string count reply')

        active_rolls = parse_rolls[0].split('=')[-1]
        candidate_rolls = parse_rolls[2].split('=')[-1]

        balance_find = list(filter(lambda x: 'Balance:' in x, answer[::-1]))
        if not len(balance_find):
            return (False, 'Wrong balance reply')
        balance = balance_find[0].strip().split(', ')[-1].split('=')[-1]

        if int(active_rolls) < 1:
            return (False, f'Wrong active rolls count {active_rolls}')
        if int(candidate_rolls) < 1:
            return (False, f'Wrong candidate rolls count {candidate_rolls}')
        # if int(active_nodes_in) + int(active_nodes_out) < 1:
        #     return (False, f'Wrong active nodes count {active_nodes_in}(in) | {active_nodes_out}(out)')
        return (True,
                f'Node is OK, rolls active: {active_rolls}, rolls candidate: {candidate_rolls}, balance: {balance}',
                balance)


class StarknetNodeChecker(BaseNodeCheckerSSH):

    def __init__(self, ip: str, username: str, password: str, screen: bool, sudo: bool):
        self.cmds = ["systemctl status starknetd | grep Active"]
        super().__init__(ip, username, password, screen, True)

    def parse_unique_answer(self, answer: list[str]):

        active_find = list(filter(lambda x: 'Active:' in x, answer[::-1]))
        if len(active_find) == 0:
            return (False, 'Wrong active reply')
        if 'active (running)' not in active_find[0].strip():
            return (False, 'Wrong active node status')

        return (True, 'Node is OK, active (running)', 0)


class AleoNodeChecker(BaseNodeCheckerSSH):

    def __init__(self, ip: str, username: str, password: str, screen: bool, sudo: bool):
        self.cmds = ["systemctl status 1to-miner | grep Active"]
        super().__init__(ip, username, password, screen, True)

    def parse_unique_answer(self, answer: list[str]):

        active_find = list(filter(lambda x: 'Active:' in x, answer[::-1]))
        if not len(active_find):
            return (False, 'Wrong active reply')
        if 'active (running)' not in active_find[0].strip():
            return (False, 'Wrong active node status')

        aleo_current_wallet = None
        if self.username == ADMIN_USERNAME:
            try:
                aleo_current_wallet_check = self.external_api_check(
                    'https://api.aleo1.to/v1/wallets/aleo1wswn9mlf280tmyu653uddrcrh7jdtxfwheunqnjkxc4t0yu6nu9qsw4pe7/')
            except Exception:
                pass
            if isinstance(aleo_current_wallet_check, dict):
                aleo_current_wallet = round(
                    aleo_current_wallet_check.get('balance', {}).get('total', 0), 2)

        return (True, f'Node is OK, active (running), balance {aleo_current_wallet}', aleo_current_wallet)


class ShardeumNodeChecker(BaseNodeCheckerSSH):

    def __init__(self, ip: str, username: str, password: str, screen: bool, sudo: bool):
        self.cmds = ["/root/.shardeum/shell.sh", "operator-cli status"]
        super().__init__(ip, username, password, screen, True)

    def parse_unique_answer(self, answer: list[str]):

        state_find = list(filter(lambda x: 'state:' in x, answer))
        if not len(state_find):
            return (False, 'Wrong state reply')
        if 'standby' not in state_find[0].strip() and 'active' not in state_find[0].strip():
            if self.username == ADMIN_USERNAME:
                # Try to restart node
                self.cmds = [
                    "/root/.shardeum/shell.sh",
                    "export APP_IP=\"95.165.31.167\"", "operator-cli start"
                ]
                self.health_check()
            return (False, f'Wrong state node status {state_find[0].strip()}')

        stake_find = list(filter(lambda x: 'lockedStake:' in x, answer))
        if not len(stake_find):
            return (False, 'Wrong stake reply')
        stake = float(stake_find[0].strip().split(': ')[-1][1:-1])

        rewards_find = list(filter(lambda x: 'currentRewards:' in x, answer))
        if not len(rewards_find):
            return (False, 'Wrong rewards reply')
        rewards = float(rewards_find[0].strip().split(': ')[-1][1:-1])

        return (True, f'Node is OK, state standby, stake {stake}, rewards {rewards}', rewards)


class DefundNodeChecker(BaseNodeCheckerSSH):

    def __init__(self, ip: str, username: str, password: str, screen: bool, sudo: bool):
        self.cmds = [
            ". $HOME/.bashrc && . $HOME/.profile && defundd status 2>&1 | jq .\"SyncInfo\""]
        super().__init__(ip, username, password, screen, sudo)

    def parse_unique_answer(self, answer: list[str]):
        defund_current_height = None
        try:
            defund_current_height = self.external_api_check(
                'https://defund.api.explorers.guru/api/v1/blocks?limit=1')
        except Exception:
            pass
        if isinstance(defund_current_height, dict) and len(defund_current_height.get('data', [])):
            defund_current_height = defund_current_height.get('data')[
                0].get('height', 0)

        defund_current_wallet = None
        if self.username == ADMIN_USERNAME:
            try:
                defund_current_wallet_check = self.external_api_check(
                    'https://defund.api.explorers.guru/api/v1/accounts/defund1pkglxk0nr3xxxslcwgtf8d6a9du9u7l59a7552/balance')
            except Exception:
                pass
            if isinstance(defund_current_wallet_check, dict) and len(defund_current_wallet_check.get('tokens', [])):
                defund_current_wallet = round(
                    defund_current_wallet_check.get('tokens')[0].get('amount', 0), 2)

        latest_block_height_find = list(
            filter(lambda x: 'latest_block_height' in x, answer[::-1]))
        if not len(latest_block_height_find):
            return (False, 'Wrong latest_block_height_find reply')
        latest_block_height = latest_block_height_find[0].strip().split(
            ' ')[-1][1:-2]

        catching_up_find = list(
            filter(lambda x: 'catching_up' in x, answer[::-1]))
        if not len(catching_up_find):
            return (False, 'Wrong catching_up reply')
        catching_up = catching_up_find[0].strip().split(' ')[-1]
        if catching_up != 'false':
            return (False, f'Wrong catching_up status {catching_up}, current_block {defund_current_height} latest_block_height {latest_block_height}')
        print(defund_current_height, latest_block_height)
        if defund_current_height and abs(int(defund_current_height) - int(latest_block_height)) > 30000:
            return (False, f'Something wrong in sync process, current_block {defund_current_height}, latest_block_height {latest_block_height}')

        return (True, f'Node is OK, current_block {defund_current_height} latest_block_height {latest_block_height}, amount: {defund_current_wallet}', defund_current_wallet)


class NibiruNodeChecker(BaseNodeCheckerSSH):

    def __init__(self, ip: str, username: str, password: str, screen: bool, sudo: bool):
        self.cmds = [
            ". $HOME/.bashrc && . $HOME/.profile && nibid status 2>&1 | jq .\"SyncInfo\""]
        super().__init__(ip, username, password, screen, sudo)

    def parse_unique_answer(self, answer: list[str]):
        nibiru_current_height = None
        try:
            nibiru_current_height = self.external_api_check('https://nibiru.api.explorers.guru/api/v1/blocks?limit=1')
        except Exception:
            pass
        if isinstance(nibiru_current_height, dict) and len(nibiru_current_height.get('data', [])):
            nibiru_current_height = nibiru_current_height.get('data')[0].get('height', 0)

        nibiru_current_wallet = None
        # if self.username == ADMIN_USERNAME:
        #     try:
        #         nibiru_current_wallet = self.external_api_check(
        #             'https://nibiru.api.explorers.guru/api/v1/accounts/nibi1ttup4wkg4smsvr4aj8huzsywlp7szdwpwr2g0l/balance'
        #         )
        #     except Exception:
        #         pass
        #     if isinstance(nibiru_current_wallet, dict) and len(nibiru_current_wallet.get('tokens', [])):
        #         nibiru_current_wallet = round(nibiru_current_wallet.get('tokens')[0].get('amount', 0), 2)

        latest_block_height_find = list(
            filter(lambda x: 'latest_block_height' in x, answer[::-1]))
        if not len(latest_block_height_find):
            return (False, 'Wrong latest_block_height_find reply')
        latest_block_height = latest_block_height_find[0].strip().split(' ')[-1][1:-2]

        catching_up_find = list(filter(lambda x: 'catching_up' in x, answer[::-1]))
        if not len(catching_up_find):
            return (False, 'Wrong catching_up reply')
        catching_up = catching_up_find[0].strip().split(' ')[-1]
        if catching_up != 'false':
            return (False, f'Wrong catching_up status {catching_up}, current_block {nibiru_current_height} latest_block_height {latest_block_height}')
        print(nibiru_current_height, latest_block_height)
        if nibiru_current_height and abs(int(nibiru_current_height) - int(latest_block_height)) > 30000:
            return (False, f'Something wrong in sync process, current_block {nibiru_current_height}, latest_block_height {latest_block_height}')

        return (True, f'Node is OK, current_block {nibiru_current_height} latest_block_height {latest_block_height}, amount: {nibiru_current_wallet}', nibiru_current_wallet)


class LavaNodeChecker(BaseNodeCheckerSSH):

    def __init__(self, ip: str, username: str, password: str, screen: bool, sudo: bool):
        self.cmds = [". $HOME/.bashrc && . $HOME/.profile && lavad status 2>&1 | jq .\"SyncInfo\""]
        super().__init__(ip, username, password, screen, sudo)

    def parse_unique_answer(self, answer: list[str]):
        lava_current_height = None
        try:
            lava_current_height = self.external_api_check('https://lava.api.explorers.guru/api/v1/blocks?limit=1')
        except Exception:
            pass
        if isinstance(lava_current_height, dict) and len(lava_current_height.get('data', [])):
            lava_current_height = lava_current_height.get('data')[
                0].get('height', 0)

        lava_current_wallet = None
        # if self.username == ADMIN_USERNAME:
        #     try:
        #         lava_current_wallet = self.external_api_check('https://lava.api.explorers.guru/api/v1/accounts/lava@1vpffj5dgvvw9ae7s0ruf3jc84ff6hwgef704tt/balance')
        #     except Exception:
        #         pass
        #     if isinstance(lava_current_wallet, dict) and len(lava_current_wallet.get('tokens', [])):
        #         lava_current_wallet = round(lava_current_wallet.get('tokens')[0].get('amount', 0), 2)

        latest_block_height_find = list(filter(lambda x: 'latest_block_height' in x, answer[::-1]))
        if not len(latest_block_height_find):
            return (False, 'Wrong latest_block_height_find reply')
        latest_block_height = latest_block_height_find[0].strip().split(' ')[-1][1:-2]

        catching_up_find = list(
            filter(lambda x: 'catching_up' in x, answer[::-1]))
        if not len(catching_up_find):
            return (False, 'Wrong catching_up reply')
        catching_up = catching_up_find[0].strip().split(' ')[-1]
        if catching_up != 'false':
            return (False, f'Wrong catching_up status {catching_up}, current_block {lava_current_height} latest_block_height {latest_block_height}')
        print(lava_current_height, latest_block_height)
        if lava_current_height and abs(int(lava_current_height) - int(latest_block_height)) > 30000:
            return (False, f'Something wrong in sync process, current_block {lava_current_height}, latest_block_height {latest_block_height}')

        return (True, f'Node is OK, current_block {lava_current_height} latest_block_height {latest_block_height}, amount: {lava_current_wallet}', lava_current_wallet)


class IronfishNodeChecker(BaseNodeCheckerSSH):

    def __init__(self, ip: str, username: str, password: str, screen: bool, sudo: bool):
        self.cmds = [". $HOME/.bashrc && . $HOME/.bash_profile && ironfish status"]
        super().__init__(ip, username, password, screen, sudo,
                         after_command_wait=6, max_command_wait=18,
                         channel_timeout=30)

    def parse_unique_answer(self, answer: list[str]):
        node_status_find = list(filter(lambda x: 'Node ' in x, answer))
        if not len(node_status_find):
            return (False, 'Wrong node_status reply')
        node_status = remove_multiple_spaces(node_status_find[0].strip()).split(' ')[-1]
        if node_status.lower() != 'started':
            return (False, f'Wrong node_status status, {node_status}')

        node_syncer_find = list(filter(lambda x: 'Syncer ' in x, answer))
        if not len(node_syncer_find):
            return (False, 'Wrong node_syncer reply')
        node_syncer = remove_multiple_spaces(node_syncer_find[0].strip())
        if 'idle' not in node_syncer.lower():
            return (False, f'Wrong node_syncer progress, {node_syncer}')

        return (True, f'Node is OK, status {node_status}, {node_syncer}', 0)


class MasaNodeChecker(BaseNodeCheckerSSH):

    def __init__(self, ip: str, username: str, password: str, screen: bool, sudo: bool):
        self.cmds = ["docker exec -it masa-node-v10_masa-node_1 geth attach /qdata/dd/geth.ipc",
                     "net.listening", "net.peerCount", "eth.syncing", "exit"]
        super().__init__(ip, username, password, screen, sudo)

    def get_next_to_finded_line(slef, answer, line_contains):
        for index, line in enumerate(answer):
            if line_contains in line:
                if len(answer) < index:
                    return False
                return answer[index+1]
        return False

    def parse_unique_answer(self, answer: list[str]):
        node_listen_find = self.get_next_to_finded_line(
            answer, 'net.listening')
        if not node_listen_find:
            return (False, 'Wrong node_listen reply')
        if node_listen_find != 'true':
            return (False, f'Wrong node_listen reply, not true: {node_listen_find}')
        node_peer_count = self.get_next_to_finded_line(answer, 'net.peerCount')
        if not node_peer_count:
            return (False, 'Wrong node_peer_count reply')
        if int(node_peer_count) == 0:
            return (False, f'Wrong node_peer_count reply, {node_peer_count} nodes')
        node_peer_syncing = self.get_next_to_finded_line(answer, 'eth.syncing')
        if not node_peer_syncing:
            return (False, 'Wrong node_peer_syncing reply')

        if node_peer_syncing == 'false':
            return (True, f'Node is OK, peers {node_peer_count}, syncing {node_peer_syncing}', 0)

        node_current_block_find = list(
            filter(lambda x: 'currentBlock ' in x, answer[::-1]))
        if not len(node_current_block_find):
            return (False, 'Wrong node_current_block_find reply')
        node_current_block = node_current_block_find[0].strip().split(
            ' ')[-1][:-1]
        node_highest_block_find = list(
            filter(lambda x: 'highestBlock ' in x, answer[::-1]))
        if not len(node_highest_block_find):
            return (False, 'Wrong node_highest_block_find reply')
        node_highest_block = node_highest_block_find[0].strip().split(
            ' ')[-1][:-1]
        if abs(int(node_current_block) - int(node_highest_block)) > 10:
            return (False, f'Wrong node_blocks reply, current {node_current_block}, highest {node_highest_block}')

        return (True, f'Node is OK, peers {node_peer_count}, current_block {node_current_block}, highest_block {node_highest_block}', 0)


class SuiNodeChecker(BaseNodeCheckerSSH):

    def __init__(self, ip: str, username: str, password: str, screen: bool, sudo: bool):
        self.cmds = [
            "curl -s -X POST http://127.0.0.1:9000 -H 'Content-Type: application/json' -d '{ \"jsonrpc\":\"2.0\", \"method\":\"rpc.discover\",\"id\":1}' | jq .result.info"]
        super().__init__(ip, username, password, screen, False)

    def parse_unique_answer(self, answer: list[str]):
        version_find = list(filter(lambda x: 'version' in x, answer[::-1]))
        if not len(version_find):
            return (False, 'Wrong sui version reply')
        version = version_find[0].strip().split(': ')[-1]

        return (True, f'Node is OK, version {version}', 0)


class SsvNodeChecker(BaseNodeCheckerSSH):

    def __init__(self, ip: str, username: str, password: str, screen: bool, sudo: bool):
        self.cmds = ["docker inspect ssv_node | grep Status"]
        super().__init__(ip, username, password, screen, sudo)

    def parse_unique_answer(self, answer: list[str]):
        status_find = list(filter(lambda x: 'Status' in x, answer[::-1]))
        if not len(status_find):
            return (False, 'Wrong ssv status reply')
        status = status_find[0].strip().split(': ')[-1][:-1]
        if status != '"running"':
            return (False, f'Wrong ssv status reply, {status}')

        return (True, f'Node is OK, status {status}', 0)


class MinimaDockerNodeChecker(BaseNodeCheckerSSH):

    def __init__(self, ip: str, username: str, password: str, screen: bool, sudo: bool):
        self.cmds = [r'docker ps --filter status=running --format "table {{.Names}}\t{{.Status}}"']
        super().__init__(ip, username, password, screen, True)

    def parse_unique_answer(self, answer: list[str]):

        status_find = list(filter(lambda x: 'minima9001' in x, answer))
        if not len(status_find):
            return (False, 'Wrong minima status reply')
        status = status_find[0].strip()
        return (True, f'Node is OK, status {status}', 0)


CHECKER_API_CLASS = 'api'
CHECKER_SSH_CLASS = 'ssh'

NODE_TYPE_APTOS = 'aptos'
NODE_TYPE_MINIMA = 'minima'
NODE_TYPE_MINIMA_DOCKER = 'minimadocker'
NODE_TYPE_MASSA = 'massa'
NODE_TYPE_STARKNET = 'starknet'
NODE_TYPE_DEFUND = 'defund'
NODE_TYPE_IRONFISH = 'ironfish'
NODE_TYPE_MASA = 'masa'
NODE_TYPE_SUI = 'sui'
NODE_TYPE_SSV = 'ssv'
NODE_TYPE_NIBIRU = 'nibiru'
NODE_TYPE_ALEO = 'aleo'
NODE_TYPE_SHARDEUM = 'shardeum'
NODE_TYPE_LAVA = 'lava'

NODE_TYPES = {
    NODE_TYPE_APTOS: {
        'class': AptosNodeChecker,
        'checker': CHECKER_API_CLASS,
        'api': 'http://{}:{}'
    },
    NODE_TYPE_MINIMA: {
        'class': MinimaNodeChecker,
        'checker': CHECKER_API_CLASS,
        'api': 'http://{}:{}/incentivecash'
    },
    NODE_TYPE_MINIMA_DOCKER: {
        'class': MinimaDockerNodeChecker,
        'checker': CHECKER_SSH_CLASS
    },
    NODE_TYPE_MASSA: {
        'class': MassaNodeChecker,
        'checker': CHECKER_SSH_CLASS
    },
    NODE_TYPE_STARKNET: {
        'class': StarknetNodeChecker,
        'checker': CHECKER_SSH_CLASS
    },
    NODE_TYPE_DEFUND: {
        'class': DefundNodeChecker,
        'checker': CHECKER_SSH_CLASS
    },
    NODE_TYPE_IRONFISH: {
        'class': IronfishNodeChecker,
        'checker': CHECKER_SSH_CLASS
    },
    NODE_TYPE_MASA: {
        'class': MasaNodeChecker,
        'checker': CHECKER_SSH_CLASS
    },
    NODE_TYPE_SUI: {
        'class': SuiNodeChecker,
        'checker': CHECKER_SSH_CLASS
    },
    NODE_TYPE_SSV: {
        'class': SsvNodeChecker,
        'checker': CHECKER_SSH_CLASS
    },
    NODE_TYPE_NIBIRU: {
        'class': NibiruNodeChecker,
        'checker': CHECKER_SSH_CLASS
    },
    NODE_TYPE_ALEO: {
        'class': AleoNodeChecker,
        'checker': CHECKER_SSH_CLASS
    },
    NODE_TYPE_SHARDEUM: {
        'class': ShardeumNodeChecker,
        'checker': CHECKER_SSH_CLASS
    },
    NODE_TYPE_LAVA: {
        'class': LavaNodeChecker,
        'checker': CHECKER_SSH_CLASS
    },
}


def check_nodes_now(user_id, send_changes=False):
    nodes_status = ''
    nodes_status_changed = ''
    node_rewards = {}
    user_nodes = Node.objects.filter(user_id=user_id).order_by('-created')

    for index, node in enumerate(user_nodes):
        # Get node type checker
        node_context = NODE_TYPES.get(node.node_type)
        if node_context['checker'] == CHECKER_API_CLASS:
            checker = node_context['class'](node.node_ip, node.node_port)
            node_description = f'{node.node_ip}:{node.node_port}'
        else:
            checker = node_context['class'](
                node.node_ip, node.ssh_username, node.ssh_password, node.screen_name, node.sudo_flag)
            node_description = f'{node.node_ip}@{node.ssh_username}'

        # Check node status
        node_status_full = checker.health_check()
        status = node_status_full[0]
        status_text = node_status_full[1]
        try:
            reward_value = float(node_status_full[2]) if len(
                node_status_full) > 2 else 0
        except Exception:
            reward_value = 0

        nodes_status += f'{index+1}. {node.node_type} {node_description} ({status}, {status_text})\n'

        # Check if notify user need
        if node.last_status != status:
            node.same_status_count = 0
        else:
            node.same_status_count += 1

        if node.notified_status != status and \
                (
                    (not status and settings.WRONG_STATUS_COUNT_ALERT <= (node.same_status_count + 1)) or
                    (status and settings.GOOD_STATUS_COUNT_ALERT <=
                     (node.same_status_count + 1))
                ):
            node.notified_status = status
            nodes_status_changed += f'{index+1}. {node.node_type} {node_description} ({status} {(node.same_status_count + 1)} times, {status_text})\n'

        # Save node history status
        node_history = CheckHistory(
            node=node, status=status, status_text=status_text, reward_value=reward_value)
        node_history.save()

        # Save node satus
        node.last_checked = node_history.checked
        node.last_status = status
        node.last_status_text = status_text
        node.last_reward_value = reward_value
        node.save()

        # Collect all rewards
        if node.node_type not in node_rewards:
            node_rewards[node.node_type] = 0
        node_rewards[node.node_type] += node.last_reward_value

    if send_changes and nodes_status_changed:
        _send_message(user_id=user_id,
                      text=f'Nodes status changed!\n{nodes_status_changed}')

    if len(node_rewards):
        nodes_status += '\nAll metrics: '
        for key, value in node_rewards.items():
            nodes_status += f'\n{key}: {value}'

    return nodes_status or 'No node exists'


def check_nodes_cached(user_id):
    nodes_status = ''
    checked_dt = None
    node_rewards = {}
    user_nodes = Node.objects.filter(user_id=user_id).order_by('-created')

    for index, node in enumerate(user_nodes):
        node_context = NODE_TYPES.get(node.node_type)
        if node_context['checker'] == CHECKER_API_CLASS:
            node_description = f'{node.node_ip}:{node.node_port}'
        else:
            node_description = f'{node.node_ip}@{node.ssh_username}'
        node_status = (node.last_status, node.last_status_text)
        if node.last_checked and checked_dt != node.last_checked.replace(microsecond=0, second=0):
            checked_dt = node.last_checked.replace(microsecond=0, second=0)
            nodes_status += 'Checked at ' + \
                timezone.localtime(node.last_checked).strftime(
                    '%Y-%m-%d %H:%M') + ':\n'
        nodes_status += f'{index+1}. {node.node_type} {node_description} {node_status}\n '

        # Collect all rewards
        if node.node_type not in node_rewards:
            node_rewards[node.node_type] = 0
        node_rewards[node.node_type] += node.last_reward_value

    if len(node_rewards):
        nodes_status += '\nAll metrics: '
        for key, value in node_rewards.items():
            nodes_status += f'\n{key}: {value}'

    return nodes_status or 'No node exists'


def list_nodes(user_id):
    nodes_status = ''
    user_nodes = Node.objects.filter(user_id=user_id).order_by('-created')
    for index, node in enumerate(user_nodes):
        nodes_status += f'{index+1}. {node.node_type}: {node.node_ip}:{node.node_port or 22}'
        if node.ssh_username:
            nodes_status += f', with user {node.ssh_username}'
        if node.screen_name:
            nodes_status += f', with screen {node.screen_name}'
        if node.sudo_flag:
            nodes_status += ', with sudo'
        nodes_status += '\n'

    return nodes_status or 'No node exists'


def is_valid_ip(ip):
    m = re.match(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$", ip)
    return bool(m) and all(map(lambda n: 0 <= int(n) <= 255, m.groups()))


def create_user_node(user_id, node_type, node_ip, node_port=None,
                     ssh_username=None, ssh_password=None, screen_name=None, sudo_flag=False):

    if not is_valid_ip(node_ip):
        return f'Wrong node_ip, not valid: {node_ip}'
    if node_type not in NODE_TYPES.keys():
        return f'Wrong node_type, supported: {NODE_TYPES.keys()}'
    if node_port is not None and (not node_port.isdigit() or int(node_port) < 0 or int(node_port) > 65535):
        return f'Wrong port number: {node_port}'
    sudo_flag = True if sudo_flag in ['True', 'true', 1, True] else False
    screen_name = None if screen_name in [
        'False', 'false', 0, False, 'None', 'none'] else screen_name

    new_node = Node(user_id=user_id, node_type=node_type, node_ip=node_ip,
                    node_port=node_port, screen_name=screen_name,
                    sudo_flag=sudo_flag, ssh_username=ssh_username,
                    ssh_password=ssh_password)
    new_node.save()

    added_node = f'{new_node.node_type} {new_node.node_ip}'
    if new_node.node_port:
        added_node += f' {new_node.node_port}'
    if new_node.ssh_username:
        added_node += f' {new_node.ssh_username}'
    if new_node.ssh_password:
        added_node += f' {new_node.ssh_password}'
    if new_node.screen_name:
        added_node += f' {new_node.screen_name}'
    if new_node.sudo_flag:
        added_node += f' {new_node.sudo_flag}'

    return f'Done. {added_node}'


def delete_user_node(user_id, node_number):
    user_nodes = Node.objects.filter(user_id=user_id).order_by('-created')
    deleted_node = 'No node deleted'
    for index, node in enumerate(user_nodes):
        if str(index + 1) == node_number:
            deleted_node = f'{node.node_type} {node.node_ip} {node.node_port}'
            node.delete()

    return f'Done. {deleted_node}'
