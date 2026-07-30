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

"""
Helpers related to internet

"""


def check_internet_connection(timeout: float = 3.0, retries: int = 0) -> bool:
    """
    Check if internet connection is available with high certainty.
    Prioritizes checking connectivity to essential services like PyPI.
    """
    import http.client
    import socket
    import time

    # Essential hosts to verify connectivity for tool installation
    # pypi.org is the most important one for pip installs
    hosts = ["pypi.org", "www.google.com", "www.cloudflare.com", "1.1.1.1"]

    for attempt in range(retries + 1):
        # Try each host
        for host in hosts:
            try:
                # If it looks like an IP, use direct connection
                if host[0].isdigit():
                    with socket.create_connection((host, 53), timeout=timeout):
                        return True
                else:
                    # For domains, try both resolution and a quick HTTP HEAD request
                    # This handles environments with DNS but no real internet egress
                    socket.gethostbyname(host)
                    conn = http.client.HTTPSConnection(host, timeout=timeout)
                    conn.request("HEAD", "/")
                    res = conn.getresponse()
                    conn.close()
                    if 200 <= res.status < 400:
                        return True
            except Exception:
                continue

        if attempt < retries:
            time.sleep(1.0)

    return False
