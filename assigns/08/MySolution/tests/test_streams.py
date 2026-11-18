"""Test lifecycle and request boundaries with the real LAMBDA3 stream."""

import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch
from uuid import UUID

from MySolution.solver import force_event
from MySolution.streams import INACTIVITY_SECONDS, StreamNotFound, StreamTable


class StreamTableTests(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.table = StreamTable(clock=lambda: self.now)

    def test_open_and_read_limits_leave_each_stream_independent(self):
        with patch("MySolution.streams.force_event", wraps=force_event) as force:
            first = self.table.open(9)
            second = self.table.open(9)
            self.assertNotEqual(first, second)
            self.assertEqual(UUID(first).version, 4)
            force.assert_not_called()
            self.assertFalse(self.table._streams[first].cursor.evaluated)

            single = self.table.next(first, 1)
            self.assertEqual(len(single.events), 1)
            self.assertFalse(single.done)
            self.assertEqual(force.call_count, 1)
            self.assertFalse(self.table._streams[first].cursor.evaluated)

            batch = self.table.next(second, 32)
            self.assertEqual(len(batch.events), 32)
            self.assertFalse(batch.done)
            self.assertEqual(batch.events[:1], single.events)
            self.assertEqual(force.call_count, 33)
            self.assertFalse(self.table._streams[second].cursor.evaluated)
            self.assertEqual(self.table.next(first, 1).events, batch.events[1:2])

    def test_invalid_values_do_not_allocate_or_advance(self):
        for size in (3, 11, 8.0, True, "8"):
            with self.subTest(size=size), self.assertRaises(ValueError):
                self.table.open(size)
        self.assertEqual(self.table._streams, {})

        stream_id = self.table.open(4)
        original = self.table._streams[stream_id]
        with patch("MySolution.streams.force_event", wraps=force_event) as force:
            for limit in (0, 33, 1.0, True, "1"):
                with self.subTest(limit=limit), self.assertRaises(ValueError):
                    self.table.next(stream_id, limit)
            for invalid_id in ("", None, 1):
                with self.subTest(stream_id=invalid_id):
                    with self.assertRaises(ValueError):
                        self.table.next(invalid_id, 1)
                    with self.assertRaises(ValueError):
                        self.table.close(invalid_id)
            force.assert_not_called()
        self.assertIs(self.table._streams[stream_id], original)

    def test_completion_releases_cursor_without_forcing_done_tail(self):
        stream_id = self.table.open(4)
        done_tail = None

        def observe(cursor):
            nonlocal done_tail
            step = force_event(cursor)
            if step is not None and step[0]["event"] == "done":
                done_tail = step[1]
            return step

        with patch("MySolution.streams.force_event", side_effect=observe) as force:
            delivered = 0
            while True:
                batch = self.table.next(stream_id, 32)
                delivered += len(batch.events)
                if batch.done:
                    break
                self.assertEqual(len(batch.events), 32)
                self.assertNotIn({"event": "done"}, batch.events)

            self.assertLess(len(batch.events), 32)
            self.assertEqual(batch.events[-1], {"event": "done"})
            self.assertEqual(batch.events.count({"event": "done"}), 1)
            self.assertIsNotNone(done_tail)
            self.assertFalse(done_tail.evaluated)
            self.assertIsNone(self.table._streams[stream_id].cursor)
            for _ in range(2):
                batch = self.table.next(stream_id, 32)
                self.assertTrue(batch.done)
                self.assertEqual(batch.events, [])
            self.assertEqual(force.call_count, delivered)

        self.table.close(stream_id)
        self.assertNotIn(stream_id, self.table._streams)
        with self.assertRaises(StreamNotFound):
            self.table.next(stream_id, 1)

    def test_close_and_unknown_streams(self):
        stream_id = self.table.open(4)
        self.table.close(stream_id)
        self.assertNotIn(stream_id, self.table._streams)
        for missing in (stream_id, "unknown"):
            with self.subTest(stream_id=missing):
                with self.assertRaisesRegex(StreamNotFound, "^Stream not found$"):
                    self.table.next(missing, 1)
                with self.assertRaises(StreamNotFound):
                    self.table.close(missing)

    def test_successful_read_refreshes_deadline_and_operations_sweep(self):
        refreshed = self.table.open(4)
        inactive = self.table.open(4)
        self.now = INACTIVITY_SECONDS - 1
        self.table.next(refreshed, 1)
        self.now = INACTIVITY_SECONDS
        self.table.open(4)
        self.assertNotIn(inactive, self.table._streams)
        self.assertIn(refreshed, self.table._streams)

        self.now = 2 * INACTIVITY_SECONDS - 1
        with self.assertRaises(StreamNotFound):
            self.table.next(refreshed, 1)
        self.assertNotIn(refreshed, self.table._streams)

    def test_completed_record_expires_after_its_last_read(self):
        stream_id = self.table.open(4)
        while not self.table.next(stream_id, 32).done:
            pass
        self.now = INACTIVITY_SECONDS - 1
        self.assertTrue(self.table.next(stream_id, 1).done)
        self.now = 2 * INACTIVITY_SECONDS - 1
        with self.assertRaises(StreamNotFound):
            self.table.close(stream_id)
        self.assertNotIn(stream_id, self.table._streams)

    def test_failed_batch_leaves_cursor_and_deadline_for_retry(self):
        reference = self.table.open(4)
        expected = self.table.next(reference, 4)
        stream_id = self.table.open(4)
        original = self.table._streams[stream_id]
        self.now = 5.0
        forced = 0

        def fail_on_third_cell(cursor):
            nonlocal forced
            step = force_event(cursor)
            forced += 1
            if forced == 3:
                raise RuntimeError("injected read failure")
            return step

        with patch("MySolution.streams.force_event", side_effect=fail_on_third_cell):
            with self.assertRaisesRegex(RuntimeError, "injected read failure"):
                self.table.next(stream_id, 4)
        self.assertEqual(forced, 3)
        self.assertIs(self.table._streams[stream_id], original)
        self.assertEqual(self.table.next(stream_id, 4), expected)

    def test_overlapping_reads_return_disjoint_consecutive_batches(self):
        reference = self.table.open(4)
        expected = [self.table.next(reference, 32) for _ in range(3)]
        stream_id = self.table.open(4)
        root = self.table._streams[stream_id].cursor
        first_at_root = Event()
        another_at_root = Event()
        second_started = Event()

        def read_second():
            second_started.set()
            return self.table.next(stream_id, 32)

        def interleavable_force(cursor):
            if cursor is root:
                if first_at_root.is_set():
                    another_at_root.set()
                else:
                    first_at_root.set()
                    self.assertTrue(second_started.wait(timeout=5))
                    # Keep the batch in progress while the second reader attempts to enter.
                    another_at_root.wait(timeout=0.2)
            return force_event(cursor)

        with patch("MySolution.streams.force_event", side_effect=interleavable_force):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(self.table.next, stream_id, 32)
                self.assertTrue(first_at_root.wait(timeout=5))
                second = pool.submit(read_second)
                actual = [first.result(timeout=5), second.result(timeout=5)]

        self.assertFalse(another_at_root.is_set())
        self.assertEqual(actual, expected[:2])
        self.assertEqual(self.table.next(stream_id, 32), expected[2])
