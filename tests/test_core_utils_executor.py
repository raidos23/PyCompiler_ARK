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

from __future__ import annotations

import time
import unittest

from pycompiler_ark.Core.utils.executor import ExecutionResult, executor


class TestCoreUtilsExecutor(unittest.TestCase):

    def test_executor_success(self):
        def add(a, b):
            return a + b

        result = executor(add, 2, 3, name="addition")

        self.assertIsInstance(result, ExecutionResult)
        self.assertTrue(result.success)
        self.assertEqual(result.value, 5)
        self.assertEqual(result.error, "")
        self.assertEqual(result.name, "addition")
        self.assertGreaterEqual(result.duration_ms, 0.0)

    def test_executor_failure_caught(self):
        def boom():
            raise ValueError("something went wrong")

        result = executor(boom, name="failing_task")

        self.assertIsInstance(result, ExecutionResult)
        self.assertFalse(result.success)
        self.assertIsNone(result.value)
        self.assertIn("something went wrong", result.error)
        self.assertEqual(result.name, "failing_task")
        self.assertGreaterEqual(result.duration_ms, 0.0)

    def test_executor_failure_propagates(self):
        def boom():
            raise RuntimeError("do not catch")

        with self.assertRaises(RuntimeError) as ctx:
            executor(boom, catch_exceptions=False)

        self.assertEqual(str(ctx.exception), "do not catch")

    def test_executor_stop_requested_before_start(self):
        def never_runs():
            raise AssertionError("This should not be called")

        result = executor(
            never_runs,
            name="cancelled_task",
            stop_requested=lambda: True,
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Execution cancelled before start")
        self.assertEqual(result.name, "cancelled_task")

    def test_executor_stop_requested_not_cancelled(self):
        def compute():
            return 42

        result = executor(
            compute,
            name="compute",
            stop_requested=lambda: False,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.value, 42)

    def test_executor_log_callback(self):
        logs: list[str] = []

        def task():
            time.sleep(0.01)
            return "done"

        result = executor(
            task,
            name="logged_task",
            log_callback=logs.append,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.value, "done")
        self.assertEqual(len(logs), 2)
        self.assertIn("Start: logged_task", logs[0])
        self.assertIn("Success: logged_task", logs[1])

    def test_executor_log_callback_failure(self):
        logs: list[str] = []

        def task():
            raise KeyError("missing")

        result = executor(
            task,
            name="failing_logged_task",
            log_callback=logs.append,
        )

        self.assertFalse(result.success)
        self.assertEqual(len(logs), 2)
        self.assertIn("Start: failing_logged_task", logs[0])
        self.assertIn("Failure: failing_logged_task", logs[1])

    def test_executor_default_name_from_function(self):
        def my_function():
            return 1

        result = executor(my_function)

        self.assertTrue(result.success)
        self.assertEqual(result.name, "my_function")

    def test_executor_timing_is_positive(self):
        def slow_task():
            time.sleep(0.05)
            return None

        result = executor(slow_task)

        self.assertTrue(result.success)
        self.assertGreaterEqual(result.duration_ms, 50.0)


if __name__ == "__main__":
    unittest.main()
