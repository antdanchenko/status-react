import pytest
import time
from tests.base_test_case import BitBarTestCase
from views.console_view import ConsoleView
from tests import user_flow
from tests import transaction_users_wallet


@pytest.mark.all
class TestPerformance(BitBarTestCase):

    @pytest.mark.performance
    def test_create_user(self):
        console = ConsoleView(self.driver)
        console.request_password_icon.click()
        console.chat_request_input.send_keys('qwerty')
        console.confirm()
        console.chat_request_input.send_keys('qwerty')
        console.confirm()
        console.find_full_text("Here is your signing phrase. "
                               "You will use it to verify your transactions. "
                               "Write it down and keep it safe!")

    @pytest.mark.performance
    def test_recover_user(self):
        console_view = ConsoleView(self.driver)
        user_flow.recover_access(console_view,
                                 transaction_users_wallet['A_USER']['passphrase'],
                                 transaction_users_wallet['A_USER']['password'],
                                 transaction_users_wallet['A_USER']['username'])

    def test_console_view(self):
        ConsoleView(self.driver)
        time.sleep(25)
