"""Unit tests for the CircularQueue data structure.

Run with:  python -m unittest test_circular_queue -v
"""

import unittest

from circular_queue import CircularQueue


class TestCircularQueue(unittest.TestCase):

    def test_new_queue_is_empty(self) -> None:
        q = CircularQueue(5)
        self.assertTrue(q.is_empty())
        self.assertFalse(q.is_full())
        self.assertEqual(q.size(), 0)

    def test_enqueue_increases_size(self) -> None:
        q = CircularQueue(5)
        q.enqueue("a")
        q.enqueue("b")
        self.assertEqual(q.size(), 2)
        self.assertFalse(q.is_empty())

    def test_fifo_order(self) -> None:
        # Items must come out in the exact order they went in.
        q = CircularQueue(5)
        for value in [1, 2, 3, 4]:
            q.enqueue(value)
        result = [q.dequeue() for _ in range(4)]
        self.assertEqual(result, [1, 2, 3, 4])

    def test_is_full_at_capacity(self) -> None:
        q = CircularQueue(3)
        q.enqueue("x")
        q.enqueue("y")
        q.enqueue("z")
        self.assertTrue(q.is_full())
        self.assertEqual(q.size(), 3)

    def test_enqueue_on_full_raises(self) -> None:
        q = CircularQueue(2)
        q.enqueue(1)
        q.enqueue(2)
        with self.assertRaises(OverflowError):
            q.enqueue(3)

    def test_dequeue_on_empty_raises(self) -> None:
        q = CircularQueue(2)
        with self.assertRaises(IndexError):
            q.dequeue()

    def test_wrap_around(self) -> None:
        # The key circular-buffer behaviour: after dequeuing, freed slots at the
        # front of the list must be reused by later enqueues via wrap-around.
        q = CircularQueue(3)
        q.enqueue("a")
        q.enqueue("b")
        q.enqueue("c")          # buffer physically full: [a, b, c]
        self.assertEqual(q.dequeue(), "a")  # free slot 0
        self.assertEqual(q.dequeue(), "b")  # free slot 1
        q.enqueue("d")          # should wrap into slot 0
        q.enqueue("e")          # should wrap into slot 1
        self.assertTrue(q.is_full())
        # Remaining items must still be FIFO: c, d, e
        self.assertEqual(q.dequeue(), "c")
        self.assertEqual(q.dequeue(), "d")
        self.assertEqual(q.dequeue(), "e")
        self.assertTrue(q.is_empty())

    def test_interleaved_operations(self) -> None:
        # Mix enqueues and dequeues to stress head/count bookkeeping.
        q = CircularQueue(3)
        q.enqueue(1)
        q.enqueue(2)
        self.assertEqual(q.dequeue(), 1)
        q.enqueue(3)
        q.enqueue(4)            # fills it up again: front is 2
        self.assertTrue(q.is_full())
        self.assertEqual(q.dequeue(), 2)
        self.assertEqual(q.dequeue(), 3)
        self.assertEqual(q.dequeue(), 4)
        self.assertTrue(q.is_empty())

    def test_size_tracks_accurately_through_churn(self) -> None:
        q = CircularQueue(4)
        self.assertEqual(q.size(), 0)
        q.enqueue(10)
        q.enqueue(20)
        q.enqueue(30)
        self.assertEqual(q.size(), 3)
        q.dequeue()
        q.dequeue()
        self.assertEqual(q.size(), 1)
        q.enqueue(40)
        q.enqueue(50)
        self.assertEqual(q.size(), 3)

    def test_peek_does_not_remove(self) -> None:
        q = CircularQueue(3)
        q.enqueue("first")
        q.enqueue("second")
        self.assertEqual(q.peek(), "first")
        self.assertEqual(q.size(), 2)       # peek must not change size
        self.assertEqual(q.dequeue(), "first")

    def test_peek_on_empty_raises(self) -> None:
        q = CircularQueue(2)
        with self.assertRaises(IndexError):
            q.peek()

    def test_len_matches_size(self) -> None:
        q = CircularQueue(5)
        q.enqueue(1)
        q.enqueue(2)
        self.assertEqual(len(q), q.size())
        self.assertEqual(len(q), 2)

    def test_invalid_capacity_raises(self) -> None:
        with self.assertRaises(ValueError):
            CircularQueue(0)
        with self.assertRaises(ValueError):
            CircularQueue(-1)

    def test_reuse_after_emptying(self) -> None:
        # Draining the queue completely and refilling must behave like new.
        q = CircularQueue(2)
        q.enqueue("a")
        q.dequeue()
        self.assertTrue(q.is_empty())
        q.enqueue("b")
        q.enqueue("c")
        self.assertTrue(q.is_full())
        self.assertEqual(q.dequeue(), "b")
        self.assertEqual(q.dequeue(), "c")


if __name__ == "__main__":
    unittest.main(verbosity=2)
