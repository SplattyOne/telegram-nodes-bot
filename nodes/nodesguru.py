from functools import reduce
import json
import requests

from nodes.models import NodesGuru

API_URL = 'https://nodes.guru/'
SEARCH_START = '<script id="__NEXT_DATA__" type="application/json">'
SEARCH_FINISH = '</script>'


def parse_answer(answer):
    answer = answer.text

    start_index = answer.find(SEARCH_START) + len(SEARCH_START)
    found_json = answer[start_index:]
    finish_index = found_json.find(SEARCH_FINISH)
    found_json = found_json[:finish_index]

    parsed_json = json.loads(found_json)
    projects = parsed_json.get('props', {}).get('pageProps', {}).get('projects', [])
    return list(reduce(lambda x, y: x + y, projects.values(), []))


def find_deviations(projects, new_projects):
    deviations = {
        'missed': [],
        'new': []
    }
    for val in projects:
        if not val in new_projects:
            deviations['missed'] += [val]
    for val in new_projects:
        if not val in projects:
            deviations['new'] += [val]
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