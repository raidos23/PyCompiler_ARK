# SPDX-License-Identifier: Apache-2.0
import unittest
from unittest.mock import patch
from Plugins_SDK.BcPluginContext.Context import check_internet, download_file, get_external_ip

class TestPluginsSDKInternet(unittest.TestCase):

    @patch("Core.Compiler.utils.check_internet_connection")
    def test_check_internet_success(self, mock_check):
        mock_check.return_value = True
        self.assertTrue(check_internet())

    @patch("Core.Compiler.utils.check_internet_connection")
    def test_download_file_no_internet(self, mock_check):
        mock_check.return_value = False
        self.assertFalse(download_file("http://example.com", "test.txt"))

    @patch("Core.Compiler.utils.check_internet_connection")
    def test_get_external_ip_no_internet(self, mock_check):
        mock_check.return_value = False
        self.assertIsNone(get_external_ip())

if __name__ == "__main__":
    unittest.main()
