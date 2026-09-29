import threading
import time
import unittest
from ctypes import WinDLL
from unittest.mock import Mock, patch

import comtypes.messageloop
from comtypes.messageloop import _MessageLoop

_user32 = WinDLL("user32")
_kernel32 = WinDLL("kernel32")

PostThreadMessageW = _user32.PostThreadMessageW
PostQuitMessage = _user32.PostQuitMessage
GetCurrentThreadId = _kernel32.GetCurrentThreadId

WM_QUIT = 0x0012
WM_USER = 0x0400


class InsertAndRemoveFilterTest(unittest.TestCase):
    def test_insert_and_remove_filter(self):
        msgloop = _MessageLoop()
        flt = Mock(return_value=[False])
        msgloop.insert_filter(flt)
        msgloop.remove_filter(flt)


class RunInThreadTest(unittest.TestCase):
    def setUp(self):
        self.msgloop = _MessageLoop()

    def run_msgloop_in_thread(self) -> tuple[threading.Thread, int]:
        """Helper method to run message loop in a separate thread."""
        thread_ids = []

        def thread_target():
            with threading.Lock():
                thread_ids.append(GetCurrentThreadId())
            self.msgloop.run()

        th = threading.Thread(target=thread_target, daemon=True)
        th.start()
        time.sleep(0.1)  # Give thread time to start
        assert len(thread_ids) == 1, "Thread ID was not captured"
        return th, thread_ids[0]

    def test_quit_message(self):
        th, thread_id = self.run_msgloop_in_thread()
        # Post WM_QUIT to terminate the message loop
        PostThreadMessageW(thread_id, WM_QUIT, 0, 0)
        th.join(timeout=1.0)  # Ensure the thread completes
        self.assertFalse(th.is_alive())

    def test_blocking_filter(self):
        blocking_filter = Mock(return_value=[True])  # Blocking
        self.msgloop.insert_filter(blocking_filter)
        th, thread_id = self.run_msgloop_in_thread()
        # Post a regular message first (should be filtered)
        PostThreadMessageW(thread_id, WM_USER, 0, 0)
        time.sleep(0.1)  # Give time for message processing
        # Post WM_QUIT to terminate the message loop
        PostThreadMessageW(thread_id, WM_QUIT, 0, 0)
        th.join(timeout=2.0)  # Wait for completion
        self.assertFalse(th.is_alive())
        blocking_filter.assert_called()

    def test_nonblocking_filter(self):
        message_filter = Mock(return_value=[])  # Non-blocking
        self.msgloop.insert_filter(message_filter)
        th, thread_id = self.run_msgloop_in_thread()
        # Post some test messages
        PostThreadMessageW(thread_id, WM_USER, 123, 456)
        PostThreadMessageW(thread_id, WM_USER, 789, 101112)
        time.sleep(0.3)  # Give time for message processing
        # Post WM_QUIT to terminate the message loop
        PostThreadMessageW(thread_id, WM_QUIT, 0, 0)
        th.join(timeout=2.0)  # Wait for completion
        self.assertFalse(th.is_alive())
        message_filter.assert_called()

    def test_multiple_filters(self):
        filter1 = Mock(return_value=[])  # Non-blocking
        filter2 = Mock(return_value=[True])  # Blocking
        filter3 = Mock(return_value=[])  # should not be called
        self.msgloop.insert_filter(filter1, index=0)
        self.msgloop.insert_filter(filter2, index=1)
        self.msgloop.insert_filter(filter3, index=2)
        th, thread_id = self.run_msgloop_in_thread()
        PostThreadMessageW(thread_id, WM_USER, 123, 456)
        time.sleep(1.0)  # Give time for message processing
        # Post WM_QUIT to terminate the message loop
        PostThreadMessageW(thread_id, WM_QUIT, 0, 0)
        th.join(timeout=2.0)  # Wait for completion
        self.assertFalse(th.is_alive())
        # any() evaluates filters in order: filter1 (falsy) then filter2 (truthy)
        # any() stops at filter2 because it returns a truthy value.
        filter1.assert_called()
        filter2.assert_called()
        filter3.assert_not_called()

    def test_raises_error_on_getmsg(self):
        # Mock GetMessage to return -1 (error condition)
        with patch.object(comtypes.messageloop, "GetMessage", return_value=-1):
            with self.assertRaises(OSError):
                self.msgloop.run()

    def test_exit_normally_without_error(self):
        def run_and_exit_quickly():
            PostQuitMessage(0)  # Exit immediately
            self.msgloop.run()

        th = threading.Thread(target=run_and_exit_quickly, daemon=True)
        th.start()
        th.join(timeout=1.0)
        self.assertFalse(th.is_alive())
