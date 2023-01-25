from functools import reduce
import json
import requests

from nodes.models import NodesGuru

API_URL = 'https://nodes.guru/'
SEARCH_START = '<script id="__NEXT_DATA__" type="application/json">'
SEARCH_FINISH = '</script>'
DEFAULT_TITLE = 'SomeNotExistentNodeTitle'


def parse_answer(answer):
    answer = answer.text

    start_index = answer.find(SEARCH_START) + len(SEARCH_START)
    found_json = answer[start_index:]
    finish_index = found_json.find(SEARCH_FINISH)
    found_json = found_json[:finish_index]

    parsed_json = json.loads(found_json)
    projects = parsed_json.get('props', {}).get('pageProps', {}).get('projects', [])
    return list(reduce(lambda x, y: x + y, projects.values(), []))


def find_updated_keys(val: dict, new_val: dict) -> dict:
    updated_elem = {}
    keys = set(val.keys() + new_val.keys())
    for key in keys:
        if val.get(key) != new_val.get(key):
            updated_elem[key] = new_val.get(key)
    if len(updated_elem):
        updated_elem['titile'] = new_val.get('title')
    return updated_elem


def find_deviations(projects: list, new_projects: list) -> dict:
    deviations = {
        'missed': [x for x in projects if x.get('title', DEFAULT_TITLE) not in list(map(lambda y: y.get('title'), new_projects))],
        'new': [x for x in new_projects if x.get('title', DEFAULT_TITLE) not in list(map(lambda y: y.get('title'), projects))],
        'updated': []
    }

    for val in projects:
        for new_val in new_projects:
            if val.get('title') != new_val.get('title'):
                continue
            updated_elem = find_updated_keys(val, new_val)
            if len(updated_elem):
                deviations['updated'] += [updated_elem]
            break
    return deviations


def get_last_projects():
    last_projects = NodesGuru.objects.all().order_by('-checked')[:1]
    if len(last_projects) == 0:
        return []
    return json.loads(last_projects[0].statuses)


def insert_last_projects(projects):
    new_elem = NodesGuru(statuses=json.dumps(projects))
    new_elem.save()


def check_nodes_guru_updates():
    projects = get_last_projects()
    answer = requests.get(API_URL)
    new_projects = parse_answer(answer)
    deviations = {}

    if len(projects) == 0:
        projects = new_projects
    elif projects != new_projects:
        deviations = find_deviations(projects, new_projects)
        projects = new_projects
    
    insert_last_projects(projects)
    return deviations