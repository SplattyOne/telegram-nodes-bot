from django.test import TestCase
from nodes.logic import check_nodes_now

# Create your tests here.
print(check_nodes_now('886232', send_changes=False))