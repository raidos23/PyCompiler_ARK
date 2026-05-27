# SPDX-License-Identifier: Apache-2.0
import unittest
from unittest.mock import patch, MagicMock
import socket
import http.client
from Core.Compiler.utils import check_internet_connection

class TestUtils(unittest.TestCase):

    @patch("socket.create_connection")
    def test_check_internet_connection_success_ip(self, mock_create):
        # Case 1: TCP connection to IP works
        mock_create.return_value.__enter__.return_value = MagicMock()
        self.assertTrue(check_internet_connection(timeout=0.1))
        self.assertEqual(mock_create.call_count, 1)

    @patch("socket.create_connection")
    @patch("socket.gethostbyname")
    @patch("http.client.HTTPSConnection")
    def test_check_internet_connection_success_dns_http(self, mock_http, mock_dns, mock_create):
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
