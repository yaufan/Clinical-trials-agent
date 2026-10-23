import pytest

from mcp_pubmed_evidence.ratelimit import TokenBucket


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.mark.anyio
async def test_bucket_allows_burst_then_spaces_calls():
    clock = FakeClock()
    sleeps: list[float] = []

    async def fake_sleep(s: float) -> None:
        sleeps.append(s)
        clock.now += s

    bucket = TokenBucket(rate=3, capacity=3, clock=clock, sleep=fake_sleep)
    for _ in range(3):
        assert await bucket.acquire() == 0.0
    waited = await bucket.acquire()
    assert waited == pytest.approx(1 / 3, abs=1e-9)
    assert sleeps and sleeps[0] == pytest.approx(1 / 3, abs=1e-9)


@pytest.mark.anyio
async def test_bucket_refills_with_time():
    clock = FakeClock()

    async def fake_sleep(s: float) -> None:
        clock.now += s

    bucket = TokenBucket(rate=10, capacity=10, clock=clock, sleep=fake_sleep)
    for _ in range(10):
        await bucket.acquire()
    clock.now += 0.5  # half a second → 5 tokens back
    for _ in range(5):
        assert await bucket.acquire() == 0.0
    assert await bucket.acquire() > 0.0


def test_bucket_rejects_bad_rate():
    with pytest.raises(ValueError):
        TokenBucket(rate=0)
