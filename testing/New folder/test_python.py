#!/usr/bin/env python3
"""
Lutervyn IDE — Python Syntax Highlighting Test File
====================================================
This file tests every Python syntax element for color accuracy.
Compare against VS Code Dark+ theme.
"""

# ══════════════════════════════════════════════════════════════
# IMPORTS (should be PURPLE — keyword.control)
# ══════════════════════════════════════════════════════════════
import os
import sys
import json
import math
import re
import datetime
from pathlib import Path
from collections import defaultdict, OrderedDict
from typing import (
    List, Dict, Tuple, Optional, Union, Any,
    Callable, Generator, AsyncGenerator, TypeVar,
    Generic, Protocol, runtime_checkable
)
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import wraps, lru_cache, partial
from contextlib import contextmanager, asynccontextmanager
import asyncio
import threading
import logging

# ══════════════════════════════════════════════════════════════
# CONSTANTS (identifiers = LIGHT BLUE, numbers = LIGHT GREEN)
# ══════════════════════════════════════════════════════════════
MAX_RETRIES = 3
TIMEOUT_SECONDS = 30.0
PI = 3.14159265358979323846
EULER = 2.71828182845904523536
HEX_VALUE = 0xFF00FF
OCTAL_VALUE = 0o755
BINARY_VALUE = 0b10101010
COMPLEX_NUMBER = 3 + 4j
LARGE_NUMBER = 1_000_000_000
SCIENTIFIC = 6.022e23
NEGATIVE_EXPONENT = 1.6e-19

# String constants (should be ORANGE-BROWN)
GREETING = "Hello, World!"
SINGLE_QUOTED = 'Single quoted string'
RAW_STRING = r"Raw string with \n no escapes"
BYTE_STRING = b"Byte string content"
EMPTY_STRING = ""
MULTILINE = """
This is a multiline
string that spans
several lines
"""

# Boolean and None (should be BLUE — storage/constant)
DEBUG_MODE = True
VERBOSE = False
NOTHING = None

# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════
class Color(Enum):
    """Color enumeration for testing class highlighting."""
    RED = auto()
    GREEN = auto()
    BLUE = auto()
    ALPHA = 255


class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# ══════════════════════════════════════════════════════════════
# DECORATORS (should be YELLOW — entity.name.decorator)
# ══════════════════════════════════════════════════════════════
def timer_decorator(func):
    """Decorator to time function execution."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        import time
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"Function {func.__name__} took {elapsed:.4f}s")
        return result
    return wrapper


def retry(max_attempts=3, delay=1.0):
    """Parameterized retry decorator."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        import time
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


def validate_input(validator):
    """Decorator factory for input validation."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for arg in args:
                if not validator(arg):
                    raise ValueError(f"Invalid input: {arg}")
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ══════════════════════════════════════════════════════════════
# DATACLASSES
# ══════════════════════════════════════════════════════════════
@dataclass
class Point:
    """A 2D point with x and y coordinates."""
    x: float = 0.0
    y: float = 0.0

    def distance_to(self, other: 'Point') -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def __add__(self, other: 'Point') -> 'Point':
        return Point(self.x + other.x, self.y + other.y)

    def __repr__(self) -> str:
        return f"Point({self.x}, {self.y})"


@dataclass
class Rectangle:
    """Rectangle defined by two corners."""
    top_left: Point = field(default_factory=Point)
    bottom_right: Point = field(default_factory=Point)

    @property
    def width(self) -> float:
        return abs(self.bottom_right.x - self.top_left.x)

    @property
    def height(self) -> float:
        return abs(self.bottom_right.y - self.top_left.y)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def perimeter(self) -> float:
        return 2 * (self.width + self.height)


# ══════════════════════════════════════════════════════════════
# ABSTRACT BASE CLASSES & PROTOCOLS
# ══════════════════════════════════════════════════════════════
class Shape(ABC):
    """Abstract base class for geometric shapes."""

    @abstractmethod
    def area(self) -> float:
        """Calculate the area."""
        pass

    @abstractmethod
    def perimeter(self) -> float:
        """Calculate the perimeter."""
        pass

    def describe(self) -> str:
        return f"{self.__class__.__name__}: area={self.area():.2f}, perimeter={self.perimeter():.2f}"


@runtime_checkable
class Drawable(Protocol):
    """Protocol for drawable objects."""
    def draw(self, canvas: Any) -> None: ...
    def get_bounds(self) -> Tuple[float, float, float, float]: ...


# ══════════════════════════════════════════════════════════════
# CLASSES WITH INHERITANCE
# ══════════════════════════════════════════════════════════════
class Circle(Shape):
    """Circle implementation."""

    def __init__(self, radius: float, center: Optional[Point] = None):
        self.radius = radius
        self.center = center or Point(0, 0)
        self._color = Color.RED

    def area(self) -> float:
        return PI * self.radius ** 2

    def perimeter(self) -> float:
        return 2 * PI * self.radius

    def contains(self, point: Point) -> bool:
        return self.center.distance_to(point) <= self.radius

    @classmethod
    def from_diameter(cls, diameter: float) -> 'Circle':
        return cls(radius=diameter / 2)

    @staticmethod
    def is_valid_radius(r: float) -> bool:
        return r > 0

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Circle):
            return NotImplemented
        return self.radius == other.radius

    def __hash__(self) -> int:
        return hash(self.radius)

    def __str__(self) -> str:
        return f"Circle(r={self.radius}, center={self.center})"


class Triangle(Shape):
    """Triangle with three sides."""

    def __init__(self, a: float, b: float, c: float):
        if not self._is_valid(a, b, c):
            raise ValueError("Invalid triangle sides")
        self.a = a
        self.b = b
        self.c = c

    @staticmethod
    def _is_valid(a: float, b: float, c: float) -> bool:
        return a + b > c and b + c > a and a + c > b

    def area(self) -> float:
        s = (self.a + self.b + self.c) / 2
        return math.sqrt(s * (s - self.a) * (s - self.b) * (s - self.c))

    def perimeter(self) -> float:
        return self.a + self.b + self.c

    @property
    def is_equilateral(self) -> bool:
        return self.a == self.b == self.c

    @property
    def is_right(self) -> bool:
        sides = sorted([self.a, self.b, self.c])
        return math.isclose(sides[0]**2 + sides[1]**2, sides[2]**2)


# ══════════════════════════════════════════════════════════════
# GENERIC CLASSES
# ══════════════════════════════════════════════════════════════
T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


class Stack(Generic[T]):
    """Generic stack implementation."""

    def __init__(self) -> None:
        self._items: List[T] = []

    def push(self, item: T) -> None:
        self._items.append(item)

    def pop(self) -> T:
        if self.is_empty:
            raise IndexError("Stack is empty")
        return self._items.pop()

    def peek(self) -> T:
        if self.is_empty:
            raise IndexError("Stack is empty")
        return self._items[-1]

    @property
    def is_empty(self) -> bool:
        return len(self._items) == 0

    @property
    def size(self) -> int:
        return len(self._items)

    def __iter__(self):
        return reversed(self._items)

    def __len__(self) -> int:
        return self.size

    def __contains__(self, item: T) -> bool:
        return item in self._items


class Cache(Generic[K, V]):
    """Simple LRU-like cache."""

    def __init__(self, max_size: int = 128):
        self._store: OrderedDict[K, V] = OrderedDict()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        if key in self._store:
            self._hits += 1
            self._store.move_to_end(key)
            return self._store[key]
        self._misses += 1
        return default

    def put(self, key: K, value: V) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = value
        if len(self._store) > self._max_size:
            self._store.popitem(last=False)

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0


# ══════════════════════════════════════════════════════════════
# CONTROL FLOW (if/for/while/try/with — should be PURPLE)
# ══════════════════════════════════════════════════════════════
def demonstrate_control_flow():
    """Showcase all control flow keywords."""

    # if / elif / else
    x = 42
    if x > 100:
        print("Large")
    elif x > 50:
        print("Medium")
    elif x > 10:
        print("Small")
    else:
        print("Tiny")

    # for loop with range, enumerate, zip
    for i in range(10):
        if i % 2 == 0:
            continue
        if i > 7:
            break
        print(i)

    fruits = ["apple", "banana", "cherry"]
    for index, fruit in enumerate(fruits):
        print(f"{index}: {fruit}")

    names = ["Alice", "Bob", "Charlie"]
    ages = [30, 25, 35]
    for name, age in zip(names, ages):
        print(f"{name} is {age}")

    # while loop
    count = 0
    while count < 5:
        count += 1
    else:
        print("Loop completed")

    # try / except / else / finally
    try:
        result = 10 / 3
        data = json.loads('{"key": "value"}')
    except ZeroDivisionError as e:
        print(f"Division error: {e}")
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Parse error: {e}")
    except Exception as e:
        raise RuntimeError("Unexpected") from e
    else:
        print(f"Success: {result}")
    finally:
        print("Cleanup done")

    # with statement (context manager)
    with open(__file__, 'r') as f:
        first_line = f.readline()

    # Ternary operator
    status = "even" if x % 2 == 0 else "odd"

    # Walrus operator
    if (n := len(fruits)) > 2:
        print(f"Got {n} fruits")

    # assert
    assert x > 0, "x must be positive"

    # del
    temp = [1, 2, 3]
    del temp[0]

    # pass
    if True:
        pass

    # yield (in generator)
    return status


# ══════════════════════════════════════════════════════════════
# COMPREHENSIONS & GENERATORS
# ══════════════════════════════════════════════════════════════
def comprehension_examples():
    """List, dict, set comprehensions and generators."""

    # List comprehension
    squares = [x ** 2 for x in range(20)]
    evens = [x for x in range(100) if x % 2 == 0]
    matrix = [[i * j for j in range(5)] for i in range(5)]
    flattened = [val for row in matrix for val in row]

    # Dict comprehension
    word_lengths = {word: len(word) for word in ["hello", "world", "python"]}
    inverted = {v: k for k, v in word_lengths.items()}

    # Set comprehension
    unique_lengths = {len(word) for word in ["hi", "hey", "hello", "hi"]}

    # Generator expression
    total = sum(x ** 2 for x in range(1000))
    first_big = next(x for x in range(1000) if x ** 2 > 500)

    return squares, word_lengths, unique_lengths, total


def fibonacci_generator(limit: int) -> Generator[int, None, None]:
    """Infinite Fibonacci generator."""
    a, b = 0, 1
    count = 0
    while count < limit:
        yield a
        a, b = b, a + b
        count += 1


# ══════════════════════════════════════════════════════════════
# ASYNC / AWAIT (keywords should be PURPLE)
# ══════════════════════════════════════════════════════════════
async def fetch_data(url: str) -> dict:
    """Simulate async data fetching."""
    await asyncio.sleep(0.1)
    return {"url": url, "status": 200, "data": "sample"}


async def process_batch(urls: List[str]) -> List[dict]:
    """Process multiple URLs concurrently."""
    tasks = [fetch_data(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return list(results)


async def async_generator_example() -> AsyncGenerator[int, None]:
    """Async generator yielding values."""
    for i in range(10):
        await asyncio.sleep(0.01)
        yield i * i


async def main_async():
    """Main async entry point."""
    urls = [f"https://api.example.com/item/{i}" for i in range(5)]

    async for value in async_generator_example():
        if value > 20:
            break

    results = await process_batch(urls)
    for r in results:
        print(r)


# ══════════════════════════════════════════════════════════════
# CONTEXT MANAGERS
# ══════════════════════════════════════════════════════════════
@contextmanager
def managed_resource(name: str):
    """Custom context manager."""
    print(f"Acquiring {name}")
    resource = {"name": name, "active": True}
    try:
        yield resource
    except Exception as e:
        print(f"Error with {name}: {e}")
        raise
    finally:
        resource["active"] = False
        print(f"Released {name}")


# ══════════════════════════════════════════════════════════════
# LAMBDA & HIGHER ORDER FUNCTIONS
# ══════════════════════════════════════════════════════════════
def functional_examples():
    """Functional programming patterns."""

    # Lambda
    double = lambda x: x * 2
    add = lambda a, b: a + b
    identity = lambda x: x

    numbers = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5]

    # map, filter, reduce
    doubled = list(map(lambda x: x * 2, numbers))
    odds = list(filter(lambda x: x % 2 != 0, numbers))

    from functools import reduce
    product = reduce(lambda a, b: a * b, numbers)

    # sorted with key
    words = ["banana", "apple", "cherry", "date"]
    by_length = sorted(words, key=lambda w: len(w))
    by_last_char = sorted(words, key=lambda w: w[-1])

    # Partial application
    multiply_by_ten = partial(lambda a, b: a * b, 10)

    return doubled, odds, product


# ══════════════════════════════════════════════════════════════
# F-STRINGS & STRING FORMATTING
# ══════════════════════════════════════════════════════════════
def string_formatting_examples():
    """Various string formatting patterns."""
    name = "World"
    count = 42
    price = 19.99

    # f-strings (should be ORANGE-BROWN with expressions)
    greeting = f"Hello, {name}!"
    formatted_num = f"Count: {count:05d}"
    formatted_price = f"Price: ${price:.2f}"
    expression = f"Result: {2 ** 10}"
    nested = f"{'Yes' if True else 'No'}"
    multiline_f = f"""
    Name: {name}
    Count: {count}
    Price: {price}
    """

    # .format() method
    template = "Hello, {}! You have {} items.".format(name, count)
    named = "Hello, {name}! Price: {price}".format(name=name, price=price)

    # % formatting (old style)
    old_style = "Hello, %s! Count: %d, Price: %.2f" % (name, count, price)

    # Raw strings
    regex_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    windows_path = r'C:\Users\Documents\file.txt'

    return greeting, template, old_style


# ══════════════════════════════════════════════════════════════
# OPERATORS & SPECIAL SYNTAX
# ══════════════════════════════════════════════════════════════
def operator_examples():
    """Test all Python operators."""
    a, b = 10, 3

    # Arithmetic
    add = a + b
    sub = a - b
    mul = a * b
    div = a / b
    floor_div = a // b
    mod = a % b
    power = a ** b

    # Comparison
    eq = a == b
    ne = a != b
    lt = a < b
    gt = a > b
    le = a <= b
    ge = a >= b

    # Logical (should be PURPLE — keywords)
    and_result = True and False
    or_result = True or False
    not_result = not True

    # Bitwise
    bit_and = a & b
    bit_or = a | b
    bit_xor = a ^ b
    bit_not = ~a
    left_shift = a << 2
    right_shift = a >> 1

    # Identity and Membership (should be PURPLE)
    is_none = a is None
    is_not_none = a is not None
    in_list = a in [1, 2, 3, 10]
    not_in = a not in [1, 2, 3]

    # Unpacking
    first, *rest = [1, 2, 3, 4, 5]
    head, *middle, tail = [1, 2, 3, 4, 5]

    # Dictionary unpacking
    d1 = {"a": 1, "b": 2}
    d2 = {"c": 3, "d": 4}
    merged = {**d1, **d2}

    return add, merged


# ══════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # All keyword colors should be verified:
    # PURPLE: if, elif, else, for, while, try, except, finally,
    #         import, from, return, yield, raise, break, continue,
    #         with, as, assert, del, pass, and, or, not, in, is,
    #         lambda, global, nonlocal, async, await
    # BLUE:   def, class, self, cls, None, True, False
    # YELLOW: function names, decorator names
    # TEAL:   class names
    # ORANGE: strings
    # GREEN:  comments
    # LIGHT BLUE: variables/identifiers
    # LIGHT GREEN: numbers

    print("=" * 60)
    print("Python Syntax Highlighting Test")
    print("=" * 60)

    demonstrate_control_flow()
    comprehension_examples()
    functional_examples()
    string_formatting_examples()
    operator_examples()

    c = Circle(5.0, Point(1, 2))
    print(c.describe())

    s = Stack[int]()
    for i in range(10):
        s.push(i)

    cache = Cache[str, int](max_size=10)
    cache.put("answer", 42)

    fibs = list(fibonacci_generator(20))
    print(f"Fibonacci: {fibs}")

    print("All tests passed!")
