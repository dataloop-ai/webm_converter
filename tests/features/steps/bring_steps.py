import os

# set var for assets
os.environ['DATALOOP_TEST_ASSETS'] = os.path.join(os.getcwd(), 'tests', 'assets')

from tests.features.steps.utilities import platform_interface_steps
from tests.features.steps.test_webm import test_webm

