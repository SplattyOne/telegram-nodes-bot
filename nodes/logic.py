from abc import abstractmethod
from datetime import timedelta
import re
import requests
import json
import traceback

from django.utils import timezone

from nodes.ssh_logic import SSHConnector
from nodes.models import Node, CheckHistory
from tgbot.handlers.broadcast_message.utils import _send_message


MAX_ERROR_LEN = 50


class BaseNodeCheckerAPI():
    node_type = None
    node_api = None

    def __init__(self, ip, port):
        node_api_template = NODE_TYPES[self.node_type].get('api')
        self.node_api = node_api_template.format(ip, port)

    def health_check(self):
        try:
            return self.parse_answer(requests.get(self.node_api))
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

    def __init__(self, ip, username, password, screen, sudo):
        self.ssh = SSHConnector(ip, username, password)
        self.screen = screen
        self.sudo = sudo

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
        aptos_ledger_version = requests.get('https://fullnode.devnet.aptoslabs.com/').json().get('ledger_version')

        sync_lines = list(filter(lambda x: 'aptos_state_sync_version' in x, answer.split('\n')))
        if not len(sync_lines):
            return (False, f'Wrong aptos_state_sync_version reply')
        
        applied_block_find = list(filter(lambda x: 'applied_transaction_outputs' in x, sync_lines))
        if not len(applied_block_find):
            return (False, f'Wrong aptos_state_sync_version applied reply')
        applied_block = applied_block_find[0].split(' ')[-1]

        synced_block_find = list(filter(lambda x: 'synced' in x, sync_lines))
        if not len(synced_block_find):
            return (False, f'Wrong aptos_state_sync_version synced reply')
        synced_block = synced_block_find[0].split(' ')[-1]

        if abs(int(aptos_ledger_version) - int(synced_block)) > 10:
            return (False, f'Something wrong in sync process, ledger {aptos_ledger_version}, synced {synced_block}')

        if abs(int(aptos_ledger_version) - int(applied_block)) > 10:
            return (False, f'Something wrong in sync process, ledger {aptos_ledger_version}, applied {applied_block}')

        return (True, f'Node is OK, ledger {aptos_ledger_version}, applied {applied_block}, synced {synced_block}', 0)


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


class DefundNodeChecker(BaseNodeCheckerSSH):

    def __init__(self, ip, port):
        self.node_type = NODE_TYPE_DEFUND
        super().__init__(ip, port)

    def parse_unique_answer(self, answer):
        answer = json.loads(answer)
        if answer.get('result', {}).get('sync_info', {}).get('catching_up', {}) is not False:
            return (False, f'Node is catching_up, and not syncronized yet')
        latest_block_height = answer.get('result', {}).get('sync_info', {}).get('latest_block_height', {})
        
        return (True, f'Node is OK, latest_block_height: {latest_block_height}', 0)


class MassaNodeChecker(BaseNodeCheckerSSH):

    def __init__(self, ip, username, password, screen, sudo):
        # self.cmds = ['. <(wget -qO- https://raw.githubusercontent.com/SecorD0/Massa/main/insert_variables.sh)', 'massa_node_info']
        self.cmds = ["wallet_info"]
        super().__init__(ip, username, password, screen, sudo)

    def parse_unique_answer(self, answer):
        # active_nodes_in_find = list(filter(lambda x: 'Входящих подключений:' in x, answer[::-1]))
        # active_nodes_out_find = list(filter(lambda x: 'Исходящих подключений:' in x, answer[::-1]))
        # if not len(active_nodes_in_find) or not len(active_nodes_out_find):
        #     return (False, f'Wrong active nodes reply')
        # active_nodes_in = active_nodes_in_find[0].strip().split(' ')[-1]
        # active_nodes_out = active_nodes_out_find[0].strip().split(' ')[-1]
        
        active_rolls_find = list(filter(lambda x: 'Active rolls:' in x, answer[::-1]))
        if not len(active_rolls_find):
            return (False, f'Wrong active rolls reply')
        active_rolls = active_rolls_find[0].strip().split(' ')[-1]

        candidate_rolls_find = list(filter(lambda x: 'Candidate rolls:' in x, answer[::-1]))
        if not len(candidate_rolls_find):
            return (False, f'Wrong candidate rolls reply')
        candidate_rolls = candidate_rolls_find[0].strip().split(' ')[-1]

        balance_find = list(filter(lambda x: 'Final balance:' in x, answer[::-1]))
        if not len(balance_find):
            return (False, f'Wrong balance reply')
        balance = balance_find[0].strip().split(' ')[-1]

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
        answer = json.loads(answer)
        if answer.get('result', {}).get('sync_info', {}).get('catching_up', {}) is not False:
            return (False, f'Node is catching_up, and not syncronized yet')
        latest_block_height = answer.get('result', {}).get('sync_info', {}).get('latest_block_height', {})
        
        return (True, f'Node is OK, latest_block_height: {latest_block_height}', 0)

    def parse_unique_answer(self, answer):
        catching_up_find = list(filter(lambda x: 'catching_up' in x, answer[::-1]))
        if not len(catching_up_find):
            return (False, f'Wrong catching_up reply')
        catching_up = catching_up_find[0].strip().split(' ')[-1]
        if catching_up != 'false':
            return (False, f'Wrong catching_up status, {catching_up}')
        
        latest_block_height_find = list(filter(lambda x: 'latest_block_height' in x, answer[::-1]))
        if not len(latest_block_height_find):
            return (False, f'Wrong latest_block_height_find reply')
        latest_block_height = latest_block_height_find[0].strip().split(' ')[-1]
        
        return (True, f'Node is OK, latest_block_height {latest_block_height}', 0)


CHECKER_API_CLASS = 'api'
CHECKER_SSH_CLASS = 'ssh'

NODE_TYPE_APTOS = 'aptos'
NODE_TYPE_MINIMA = 'minima'
NODE_TYPE_MASSA = 'massa'
NODE_TYPE_STARKNET = 'starknet'
NODE_TYPE_DEFUND = 'defund'

NODE_TYPES = {
    NODE_TYPE_APTOS: {'class': AptosNodeChecker, 'checker': CHECKER_API_CLASS, 'api': 'http://{}:{}/metrics'},
    NODE_TYPE_MINIMA: {'class': MinimaNodeChecker, 'checker': CHECKER_API_CLASS, 'api': 'http://{}:{}/incentivecash'},
    NODE_TYPE_MASSA: {'class': MassaNodeChecker, 'checker': CHECKER_SSH_CLASS},
    NODE_TYPE_STARKNET: {'class': StarknetNodeChecker, 'checker': CHECKER_SSH_CLASS},
    NODE_TYPE_DEFUND: {'class': DefundNodeChecker, 'checker': CHECKER_SSH_CLASS},
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
            nodes_status_changed += f'{index+1}. {node.node_type} {node_description} ({status}, {status_text})\n'

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
        nodes_status += f'{index+1}. {node.node_type}: {node.node_ip}:{node.node_port}, {node.ssh_username}/{node.ssh_password} (screen {node.screen_name}, sudo {node.sudo_flag})\n'
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