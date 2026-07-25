# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Samuel Amen Ague
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import socket
import unittest
from unittest.mock import MagicMock, patch

from pycompiler_ark.Core.Compiler.utils import check_internet_connection


class TestUtils(unittest.TestCase):
    @patch("socket.create_connection")
    @patch("socket.gethostbyname")
    def test_check_internet_connection_success_ip(self, mock_dns, mock_create):
        # Case 1: TCP connection to IP works
        # Mock DNS to fail for all domains so it reaches the IP host
        mock_dns.side_effect = Exception("DNS Fail")
        mock_create.return_value.__enter__.return_value = MagicMock()

        self.assertTrue(check_internet_connection(timeout=0.1))
        # It should be called for 1.1.1.1
        self.assertTrue(mock_create.called)

    @patch("socket.create_connection")
    @patch("socket.gethostbyname")
    @patch("http.client.HTTPSConnection")
    def test_check_internet_connection_success_dns_http(
        self, mock_http, mock_dns, mock_create
    ):
        # Case 2: TCP to IPs fails, but DNS + HTTP works
        mock_create.side_effect = socket.error("Fail")
        mock_dns.return_value = "1.2.3.4"

        mock_conn = MagicMock()
        mock_http.return_value = mock_conn
        mock_res = MagicMock()
        mock_res.status = 200
        mock_conn.getresponse.return_value = mock_res

        self.assertTrue(check_internet_connection(timeout=0.1))
        self.assertTrue(mock_dns.called)
        self.assertTrue(mock_http.called)

    @patch("socket.create_connection")
    @patch("socket.gethostbyname")
    def test_check_internet_connection_fail(self, mock_dns, mock_create):
        # Case 3: Everything fails
        mock_create.side_effect = socket.error("Fail")
        mock_dns.side_effect = Exception("DNS Fail")

        self.assertFalse(check_internet_connection(timeout=0.1, retries=0))


if __name__ == "__main__":
    unittest.main()
