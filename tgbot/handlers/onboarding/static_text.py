from nodes.logic import NODE_TYPES

start_created = "Sup, {first_name}!"
start_not_created = "Welcome back, {first_name}!"
check_now_button_text = "Now"
check_cached_button_text = "Cached"
list_checkers_button_text = "List"
add_checker_button_text = "Add"
delete_checker_button_text = "Delete"
add_node_guide_text = '"/add {node_type} {node_ip} {node_port}" for api checks or \n"/add {node_type} {node_ip} {ssh_user} {ssh_password} {screen_name}[optional or False] {sudo_flag}[optional or False]" for ssh checks\n\nSupported types: ' + ', '.join(list(map(lambda x: f'{x[0]} ({x[1]["checker"]})', NODE_TYPES.items())))
delete_node_guide_text = '"/delete {node_number}", where node_number is a number from /list command'
add_checker_support_text = f'Type here:\n{add_node_guide_text}'
delete_checker_support_text = f'Type here:\n{delete_node_guide_text}'
add_checker_wrong_len_text = f'Wrong parameters count,\n{add_node_guide_text}'
delete_checker_wrong_len_text = f'Wrong parameters count,\n{delete_node_guide_text}'
loading = 'Loading...'
