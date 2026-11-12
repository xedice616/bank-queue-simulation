"""A fixed-size, FIFO Circular Queue (ring buffer).

This data structure stores items in a single Python list of fixed length and
reuses the slots in a circle. It supports enqueue, dequeue, is_empty, is_full,
and size, all in O(1) time.

It deliberately does NOT use collections.deque, queue.Queue, or heapq, so the
mechanics of a circular buffer are visible and fully under our control.
"""

from typing import Any, List, Optional


class CircularQueue:
    """A FIFO queue backed by a fixed-size ring buffer.

    Internally we keep:
      - a list `buffer` of `capacity` slots,
      - `head`: the index of the front item (the next one to dequeue),
      - `count`: how many items are currently stored.

    The tail (where the next item is written) is computed on the fly as
    `(head + count) % capacity`, so we never need a separate tail pointer.
    When an index walks off the end of the list it wraps around to 0 using
    the modulo (`%`) operator -- that wrapping is what makes it "circular".
    """

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be a positive integer")

        self.capacity: int = capacity
        # Pre-allocate all slots once. `None` just marks an empty slot.
        self.buffer: List[Optional[Any]] = [None] * capacity
        self.head: int = 0   # index of the front (oldest) item
        self.count: int = 0  # number of items currently in the queue

    def is_empty(self) -> bool:
        """Return True when there are no items. O(1)."""
        return self.count == 0

    def is_full(self) -> bool:
        """Return True when every slot is used. O(1)."""
        return self.count == self.capacity

    def size(self) -> int:
        """Return how many items are currently stored. O(1)."""
        return self.count

    def enqueue(self, item: Any) -> None:
        """Add `item` to the back of the queue. O(1).

        Raises OverflowError if the queue is already full, because a fixed-size
        ring buffer must never silently overwrite an item it has not returned.
        """
        if self.is_full():
            raise OverflowError("cannot enqueue: the queue is full")

        # The next free slot is `count` steps ahead of the head, wrapped around.
        tail: int = (self.head + self.count) % self.capacity
        self.buffer[tail] = item
        self.count += 1

    def dequeue(self) -> Any:
        """Remove and return the front item. O(1).

        Raises IndexError if the queue is empty.
        """
        if self.is_empty():
            raise IndexError("cannot dequeue: the queue is empty")

        item: Any = self.buffer[self.head]
        self.buffer[self.head] = None          # clear the slot so we don't pin references
        self.head = (self.head + 1) % self.capacity  # advance the front, wrapping around
        self.count -= 1
        return item

    def peek(self) -> Any:
        """Return (without removing) the front item. O(1).

        Not strictly required by the assignment, but handy and cheap. Raises
        IndexError if the queue is empty.
        """
        if self.is_empty():
            raise IndexError("cannot peek: the queue is empty")
        return self.buffer[self.head]

    def __len__(self) -> int:
        """Allow len(queue) as a convenience; mirrors size(). O(1)."""
        return self.count
