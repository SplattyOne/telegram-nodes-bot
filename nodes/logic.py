from abc import abstractmethod
from datetime import timedelta, datetime
import re
import requests
import json
import traceback

from django.utils import timezone
from django.conf import settings

from nodes.ssh_logic import SSHConnector
from nodes.models import Node, CheckHistory
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
    def parse_unique_answer(self, answer):
        pass

class BaseNodeCheckerSSH():
    node_type = None
    sudo = False
    screen = False
    cmds = None

    def __init__(self, ip, username, password, screen, sudo, **kwargs):
        self.ssh = SSHConnector(ip, username, password, **kwargs)
        self.screen = screen
        self.sudo = sudo
        self.username = username

    @staticmethod
    def external_api_check(url):
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
    def parse_unique_answer(self, answer):
        pass


class AptosNodeChecker(BaseNodeCheckerAPI):

    def __init__(self, ip, port):
        self.node_type = NODE_TYPE_APTOS
        super().__init__(ip, port)

    def parse_unique_answer(self, answer):
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
            return (False, f'Wrong aptos ledger_version reply')

        ledger_timestamp = answer.get('ledger_timestamp')
        if not ledger_timestamp:
            return (False, f'Wrong aptos ledger_timestamp reply')
        ledger_timestamp_dt = datetime.fromtimestamp(int(ledger_timestamp) // 1000 // 1000)

        return (True, f'Node is OK, ledger {ledger_version}, dt {ledger_timestamp_dt}', 0)


class MinimaNodeChecker(BaseNodeCheckerAPI):

    def __init__(self, ip, port):
        self.node_type = NODE_TYPE_MINIMA
        super().__init__(ip, port)

    def parse_unique_answer(self, answer):
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

    def __init__(self, ip, username, password, screen, sudo):
        # self.cmds = ['. <(wget -qO- https://raw.githubusercontent.com/SecorD0/Massa/main/insert_variables.sh)', 'massa_node_info']
        self.cmds = ["cd $HOME/massa/massa-client/ && ./massa-client -p $(cat $HOME/massapasswd) wallet_info"]
        super().__init__(ip, username, password, screen, sudo)

    def parse_unique_answer(self, answer):
        # active_nodes_in_find = list(filter(lambda x: 'Входящих подключений:' in x, answer[::-1]))
        # active_nodes_out_find = list(filter(lambda x: 'Исходящих подключений:' in x, answer[::-1]))
        # if not len(active_nodes_in_find) or not len(active_nodes_out_find):
        #     return (False, f'Wrong active nodes reply')
        # active_nodes_in = active_nodes_in_find[0].strip().split(' ')[-1]
        # active_nodes_out = active_nodes_out_find[0].strip().split(' ')[-1]

        rolls_find = list(filter(lambda x: 'Rolls:' in x, answer[::-1]))
        if not len(rolls_find):
            return (False, f'Wrong rolls reply')
        parse_rolls = rolls_find[0].strip().split(', ')
        if len(parse_rolls) < 3:
            return (False, f'Wrong rolls string count reply')

        active_rolls = parse_rolls[0].split('=')[-1]
        candidate_rolls = parse_rolls[2].split('=')[-1]

        balance_find = list(filter(lambda x: 'Sequential balance:' in x, answer[::-1]))
        if not len(balance_find):
            return (False, f'Wrong balance reply')
        balance = balance_find[0].strip().split(', ')[-1].split('=')[-1]

        if int(active_rolls) < 1:
            return (False, f'Wrong active rolls count {active_rolls}')
        if int(candidate_rolls) < 1:
            return (False, f'Wrong candidate rolls count {candidate_rolls}')
        # if int(active_nodes_in) + int(active_nodes_out) < 1:
        #     return (False, f'Wrong active nodes count {active_nodes_in}(in) | {active_nodes_out}(out)')
        return (True, f'Node is OK, rolls active: {active_rolls}, rolls candidate: {candidate_rolls}, balance: {balance}', balance)


class StarknetNodeChecker(BaseNodeCheckerSSH):

    def __init__(self, ip, username, password, screen, sudo):
        self.cmds = ["systemctl status starknetd | grep Active"]
        super().__init__(ip, username, password, screen, sudo)

    def parse_unique_answer(self, answer):
        
        active_find = list(filter(lambda x: 'Active:' in x, answer[::-1]))
        if not len(active_find):
            return (False, f'Wrong active reply')
        if not 'active (running)' in active_find[0].strip():
            return (False, f'Wrong active node status')
        
        return (True, f'Node is OK, active (running)', 0)


class DefundNodeChecker(BaseNodeCheckerSSH):

    def __init__(self, ip, username, password, screen, sudo):
        self.cmds = ["curl localhost:26657/status"]
        super().__init__(ip, username, password, screen, sudo)

    def parse_unique_answer(self, answer):
        defund_current_height = self.external_api_check('https://defund.api.explorers.guru/api/blocks?count=1')
        if isinstance(defund_current_height, list) and len(defund_current_height):
            defund_current_height = defund_current_height[0].get('height')
        else:
            defund_current_height = None

        if self.username == ADMIN_USERNAME:
            defund_current_wallet = self.external_api_check('https://defund.api.explorers.guru/api/accounts/defund1y2wlde84z3tqmr99nqzwlljjw67y5hg73363u0/tokens')
        else:
            defund_current_wallet = None
        if isinstance(defund_current_wallet, list) and len(defund_current_wallet):
            defund_current_wallet = round(defund_current_wallet[0].get('amount'), 2)
        else:
            defund_current_wallet = None

        catching_up_find = list(filter(lambda x: 'catching_up' in x, answer[::-1]))
        if not len(catching_up_find):
            return (False, f'Wrong catching_up reply')
        catching_up = catching_up_find[0].strip().split(' ')[-1]
        if catching_up != 'false':
            return (False, f'Wrong catching_up status, {catching_up}')
        
        latest_block_height_find = list(filter(lambda x: 'latest_block_height' in x, answer[::-1]))
        if not len(latest_block_height_find):
            return (False, f'Wrong latest_block_height_find reply')
        latest_block_height = latest_block_height_find[0].strip().split(' ')[-1][1:-2]

        if defund_current_height and abs(int(defund_current_height) - int(latest_block_height)) > 2000:
            return (False, f'Something wrong in sync process, current_block {defund_current_height}, node latest block {latest_block_height}')
        
        return (True, f'Node is OK, current_block {defund_current_height} latest_block_height {latest_block_height}, amount: {defund_current_wallet}', defund_current_wallet)


class IronfishNodeChecker(BaseNodeCheckerSSH):

    def __init__(self, ip, username, password, screen, sudo):
        self.cmds = [". $HOME/.bashrc", ". $HOME/.bash_profile", "ironfish status"]
        super().__init__(ip, username, password, screen, sudo, after_command_wait=6, max_command_wait=18, channel_timeout=30)

    def parse_unique_answer(self, answer):
        node_status_find = list(filter(lambda x: 'Node ' in x, answer))
        if not len(node_status_find):
            return (False, f'Wrong node_status reply')
        node_status = remove_multiple_spaces(node_status_find[0].strip()).split(' ')[-1]
        if node_status != 'STARTED':
            return (False, f'Wrong node_status status, {node_status}')

        node_syncer_find = list(filter(lambda x: 'Syncer ' in x, answer))
        if not len(node_syncer_find):
            return (False, f'Wrong node_syncer reply')
        node_syncer = remove_multiple_spaces(node_syncer_find[0].strip())
        if 'IDLE' not in node_syncer:
            return (False, f'Wrong node_syncer progress, {node_syncer}')
        
        return (True, f'Node is OK, status {node_status}, {node_syncer}', 0)


class MasaNodeChecker(BaseNodeCheckerSSH):

    def __init__(self, ip, username, password, screen, sudo):
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

    def parse_unique_answer(self, answer):
        node_listen_find = self.get_next_to_finded_line(answer, 'net.listening')
        if not node_listen_find:
            return (False, f'Wrong node_listen reply')
        if node_listen_find != 'true':
            return (False, f'Wrong node_listen reply, not true: {node_listen_find}')
        node_peer_count = self.get_next_to_finded_line(answer, 'net.peerCount')
        if not node_peer_count:
            return (False, f'Wrong node_peer_count reply')
        if int(node_peer_count) == 0:
            return (False, f'Wrong node_peer_count reply, {node_peer_count} nodes')
        node_peer_syncing = self.get_next_to_finded_line(answer, 'eth.syncing')
        if not node_peer_syncing:
            return (False, f'Wrong node_peer_syncing reply')
        
        if node_peer_syncing == 'false':
            return (True, f'Node is OK, peers {node_peer_count}, syncing {node_peer_syncing}', 0)
        
        node_current_block_find = list(filter(lambda x: 'currentBlock ' in x, answer[::-1]))
        if not len(node_current_block_find):
            return (False, f'Wrong node_current_block_find reply')
        node_current_block = node_current_block_find[0].strip().split(' ')[-1][:-1]
        node_highest_block_find = list(filter(lambda x: 'highestBlock ' in x, answer[::-1]))
        if not len(node_highest_block_find):
            return (False, f'Wrong node_highest_block_find reply')
        node_highest_block = node_highest_block_find[0].strip().split(' ')[-1][:-1]
        if abs(int(node_current_block) - int(node_highest_block)) > 10:
            return (False, f'Wrong node_blocks reply, current {node_current_block}, highest {node_highest_block}')
    
        return (True, f'Node is OK, peers {node_peer_count}, current_block {node_current_block}, highest_block {node_highest_block}', 0)


class SuiNodeChecker(BaseNodeCheckerSSH):

    def __init__(self, ip, username, password, screen, sudo):
        self.cmds = ["curl -s -X POST http://127.0.0.1:9000 -H 'Content-Type: application/json' -d '{ \"jsonrpc\":\"2.0\", \"method\":\"rpc.discover\",\"id\":1}' | jq .result.info"]
        super().__init__(ip, username, password, screen, sudo)

    def parse_unique_answer(self, answer):
        version_find = list(filter(lambda x: 'version' in x, answer[::-1]))
        if not len(version_find):
            return (False, f'Wrong sui version reply')
        version = version_find[0].strip().split(': ')[-1]
        
        return (True, f'Node is OK, version {version}', 0)


class SsvNodeChecker(BaseNodeCheckerSSH):

    def __init__(self, ip, username, password, screen, sudo):
        self.cmds = ["docker inspect ssv_node | grep Status"]
        super().__init__(ip, username, password, screen, sudo)

    def parse_unique_answer(self, answer):
        status_find = list(filter(lambda x: 'Status' in x, answer[::-1]))
        if not len(status_find):
            return (False, f'Wrong ssv status reply')
        status = status_find[0].strip().split(': ')[-1][:-1]
        if status != '"running"':
            return (False, f'Wrong ssv status reply, {status}')

        return (True, f'Node is OK, status {status}', 0)


CHECKER_API_CLASS = 'api'
CHECKER_SSH_CLASS = 'ssh'

NODE_TYPE_APTOS = 'aptos'
NODE_TYPE_MINIMA = 'minima'
NODE_TYPE_MASSA = 'massa'
NODE_TYPE_STARKNET = 'starknet'
NODE_TYPE_DEFUND = 'defund'
NODE_TYPE_IRONFISH = 'ironfish'
NODE_TYPE_MASA = 'masa'
NODE_TYPE_SUI = 'sui'
NODE_TYPE_SSV = 'ssv'

NODE_TYPES = {
    NODE_TYPE_APTOS: {'class': AptosNodeChecker, 'checker': CHECKER_API_CLASS, 'api': 'http://{}:{}'},
    NODE_TYPE_MINIMA: {'class': MinimaNodeChecker, 'checker': CHECKER_API_CLASS, 'api': 'http://{}:{}/incentivecash'},
    NODE_TYPE_MASSA: {'class': MassaNodeChecker, 'checker': CHECKER_SSH_CLASS},
    NODE_TYPE_STARKNET: {'class': StarknetNodeChecker, 'checker': CHECKER_SSH_CLASS},
    NODE_TYPE_DEFUND: {'class': DefundNodeChecker, 'checker': CHECKER_SSH_CLASS},
    NODE_TYPE_IRONFISH: {'class': IronfishNodeChecker, 'checker': CHECKER_SSH_CLASS},
    NODE_TYPE_MASA: {'class': MasaNodeChecker, 'checker': CHECKER_SSH_CLASS},
    NODE_TYPE_SUI: {'class': SuiNodeChecker, 'checker': CHECKER_SSH_CLASS},
    NODE_TYPE_SSV: {'class': SsvNodeChecker, 'checker': CHECKER_SSH_CLASS}
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
            checker = node_context['class'](node.node_ip, node.ssh_username, node.ssh_password, node.screen_name, node.sudo_flag)
            node_description = f'{node.node_ip}@{node.ssh_username}'
        
        # Check node status
        node_status_full = checker.health_check()
        status = node_status_full[0]
        status_text = node_status_full[1]
        reward_value = float(node_status_full[2]) if len(node_status_full) > 2 else 0

        nodes_status += f'{index+1}. {node.node_type} {node_description} ({status}, {status_text})\n'

        # Check if notify user need
        if node.last_status != status:
            node.same_status_count = 0
        else:
            node.same_status_count += 1

        if node.notified_status != status and \
            (
                (not status and settings.WRONG_STATUS_COUNT_ALERT <= (node.same_status_count + 1)) or \
                (status and settings.GOOD_STATUS_COUNT_ALERT <= (node.same_status_count + 1))
            ):
                node.notified_status = status
                nodes_status_changed += f'{index+1}. {node.node_type} {node_description} ({status} {(node.same_status_count + 1)} times, {status_text})\n'

        # Save node history status
        node_history = CheckHistory(node=node, status=status, status_text=status_text, reward_value=reward_value)
        node_history.save()

        # Save node satus
        node.last_checked = node_history.checked
        node.last_status = status
        node.last_status_text = status_text
        node.last_reward_value = reward_value
        node.save()
        
        # Collect all rewards
        if not node.node_type in node_rewards:
            node_rewards[node.node_type] = 0
        node_rewards[node.node_type] += node.last_reward_value

    if send_changes and nodes_status_changed:
        _send_message(user_id=user_id, text=f'Nodes status changed!\n{nodes_status_changed}')
    
    if len(node_rewards):
        nodes_status = nodes_status + '\nAll metrics: ' + str(node_rewards)

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
            nodes_status += 'Checked at ' + timezone.localtime(node.last_checked).strftime('%Y-%m-%d %H:%M') + ':\n'
        nodes_status += f'{index+1}. {node.node_type} {node_description} {node_status}\n '
        
        # Collect all rewards
        if not node.node_type in node_rewards:
            node_rewards[node.node_type] = 0
        node_rewards[node.node_type] += node.last_reward_value
    
    if len(node_rewards):
        nodes_status = nodes_status + '\nAll metrics: ' + str(node_rewards)
    
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
            nodes_status += f', with sudo'
        nodes_status += '\n'

    return nodes_status or 'No node exists'


def is_valid_ip(ip):
    m = re.match(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$", ip)
    return bool(m) and all(map(lambda n: 0 <= int(n) <= 255, m.groups()))


def create_user_node(user_id, node_type, node_ip, node_port=None, ssh_username=None, ssh_password=None, screen_name=None, sudo_flag=False):

    if not is_valid_ip(node_ip):
        return f'Wrong node_ip, not valid: {node_ip}'
    if node_type not in NODE_TYPES.keys():
        return f'Wrong node_type, supported: {NODE_TYPES.keys()}'
    if node_port is not None and (not node_port.isdigit() or int(node_port) < 0 or int(node_port) > 65535):
        return f'Wrong port number: {node_port}'
    sudo_flag = True if sudo_flag in ['True', 'true', 1, True] else False
    screen_name = None if screen_name in ['False', 'false', 0, False, 'None', 'none'] else screen_name
    
    new_node = Node(user_id=user_id, node_type=node_type, node_ip=node_ip, \
        node_port=node_port, screen_name=screen_name, sudo_flag=sudo_flag, \
        ssh_username=ssh_username, ssh_password=ssh_password)
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