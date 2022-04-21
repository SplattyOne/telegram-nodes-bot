from abc import abstractmethod
import requests
import json

from nodes.models import Node, CheckHistory


class BaseNodeChecker():
    node_type = None
    node_api = None

    def __init__(self, ip, port):
        node_api_template = NODE_TYPES[self.node_type].get('api')
        self.node_api = node_api_template.format(ip, port)

    def health_check(self):
        return self.parse_answer(requests.get(self.node_api))

    def parse_answer(self, answer):
        if not isinstance(answer, requests.Response):
            return (False, 'Wrong answer type')
        if answer.status_code > 300:
            return (False, f'Wrong answer code {answer.status_code}')
        return self.parse_unique_answer(answer.text)

    @abstractmethod
    def parse_unique_answer(self, answer):
        pass


class AptosNodeChecker(BaseNodeChecker):

    def __init__(self, ip, port):
        self.node_type = NODE_TYPE_APTOS
        super().__init__(ip, port)

    def parse_unique_answer(self, answer):
        sync_lines = list(filter(lambda x: 'aptos_state_sync_version' in x, answer.split('\n')))
        target_block = list(filter(lambda x: 'target' in x, sync_lines))[0].split(' ')[1]
        synced_block = list(filter(lambda x: 'synced' in x, sync_lines))[0].split(' ')[1]
        if int(target_block) - int(synced_block) > 3:
            return (False, f'Something wrong in sync process, target {target_block}, synced {synced_block}')
        return (True, f'Node is OK, target {target_block}, synced {synced_block}')


class MinimaNodeChecker(BaseNodeChecker):

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
        return (True, f'Node is OK, rewards: {rewards}')



NODE_TYPE_APTOS = 'aptos'
NODE_TYPE_MINIMA = 'minima'
NODE_TYPES = {
    NODE_TYPE_APTOS: {'api': 'http://{}:{}/metrics', 'class': AptosNodeChecker},
    NODE_TYPE_MINIMA: {'api': 'http://{}:{}/incentivecash', 'class': MinimaNodeChecker}
}


MY_NODE_IP = '95.165.31.167'
MY_NODES = [
    {'type': NODE_TYPE_APTOS, 'ip': MY_NODE_IP, 'port': 9101},
    {'type': NODE_TYPE_MINIMA, 'ip': MY_NODE_IP, 'port': 9002},
    {'type': NODE_TYPE_MINIMA, 'ip': MY_NODE_IP, 'port': 9003}
]


def check_nodes(user_id):
    nodes_status = ''
    user_nodes = Node.objects.filter(user_id=user_id)
    for index, node in enumerate(user_nodes):
        checker = NODE_TYPES.get(node.node_type)['class'](node.node_ip, node.node_port)
        nodes_status += f'{index+1}. {checker.node_type} {checker.health_check()}\n'
    return nodes_status or 'No node exists'


def create_user_node(user_id, node_type, node_ip, node_port):
    if node_type not in NODE_TYPES.keys():
        return f'Wrong node_type, supported: {NODE_TYPES.keys()}'
    
    new_node = Node(user_id=user_id, node_type=node_type, node_ip=node_ip, node_port=node_port)
    new_node.save()
    added_node = f'{new_node.node_type} {new_node.node_ip} {new_node.node_port}'
    return f'Done. {added_node}'


def delete_user_node(user_id, node_number):
    user_nodes = Node.objects.filter(user_id=user_id)
    deleted_node = 'No node deleted'
    for index, node in enumerate(user_nodes):
        if str(index + 1) == node_number:
            deleted_node = f'{node.node_type} {node.node_ip} {node.node_port}'
            node.delete()
    
    return f'Done. {deleted_node}'