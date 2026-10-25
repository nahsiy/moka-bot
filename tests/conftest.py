import itertools
from dataclasses import replace

import pytest

from moka.config import Config
from moka.service import Service
from moka.store import Store


class Clock:
    def __init__(self):
        self.now = 1_800_000_000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class FixedRandom:
    def __init__(self, value=0.1):
        self.value = value

    def random(self):
        return self.value

    def randint(self, low, high):
        return low

    def choice(self, values):
        return values[0]


@pytest.fixture
def service(tmp_path):
    store = Store(tmp_path / "moka.sqlite3")
    store.initialize()
    return Service(
        store, Config(guild_ids=(1, 2), data_dir=tmp_path), clock=Clock(), rng=FixedRandom()
    )


@pytest.fixture
def fund(service):
    counter = itertools.count()

    def add(user, amount=5000, guild=1):
        return service.adjust(guild, user, amount, f"fund:{next(counter)}")

    return add


@pytest.fixture
def fast_rules(service):
    service.config = replace(service.config, rules=replace(service.config.rules, words_cooldown=0))
    return service
