import asyncio
import pytest

from pipeline_backend.event_callbacks import (
    EventCallbacksManager,
    ServerSideSignalsQueue,
    eventsCallbackManager,
)


async def test_signal_event_dispatches_to_all_callbacks_when_one_unsubscribes():
    manager = EventCallbacksManager()
    calls = []

    async def first_callback(event, uuid="", data=""):
        calls.append("first")
        manager.unsubscribe_callback(first_callback)

    async def second_callback(event, uuid="", data=""):
        calls.append("second")

    event = EventCallbacksManager.Events.ClosingDown
    manager.register_callback(event, first_callback)
    manager.register_callback(event, second_callback)

    await manager.signal_event(event)

    assert calls == ["first", "second"]


# ---------------------------------------------------------------------------
# ServerSideSignalsQueue - the SSE stream held open per connected browser
# ---------------------------------------------------------------------------

class FakeRequest:
    """Stands in for the Starlette Request that the SSE stream watches."""
    def __init__(self, disconnected=False):
        self.disconnected = disconnected

    async def is_disconnected(self):
        return self.disconnected


@pytest.fixture
def clean_subscribers():
    """ServerSideSignalsQueue talks to the module level manager, so put it back afterwards."""
    before = {event: list(callbacks) for event, callbacks in eventsCallbackManager.subscribers.items()}
    yield
    eventsCallbackManager.subscribers.clear()
    eventsCallbackManager.subscribers.update(before)


def subscribe_to_everything(sse):
    for event in EventCallbacksManager.Events:
        eventsCallbackManager.register_callback(event, sse.add_new_message)


def registration_count(sse):
    return sum(callbacks.count(sse.add_new_message) for callbacks in eventsCallbackManager.subscribers.values())


async def drain(generator):
    async for _ in generator:
        pass


class TestServerSideSignalsQueue:
    async def test_messages_are_delivered_while_connected(self, clean_subscribers):
        sse = ServerSideSignalsQueue(FakeRequest())
        subscribe_to_everything(sse)
        received = []

        async def consume():
            async for msg in sse.message_generator():
                received.append(msg)

        task = asyncio.create_task(consume())
        await sse.add_new_message(EventCallbacksManager.Events.RefreshInstance, "inst-1")
        await asyncio.sleep(0.01)
        try:
            assert received == [{"event": "RefreshInstance", "data": "inst-1"}]
        finally:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

    async def test_cancelling_the_stream_unsubscribes(self, clean_subscribers):
        # A browser that disconnects while idle gets its generator cancelled rather than
        # ever reaching the disconnect check, which used to leak the whole subscription
        sse = ServerSideSignalsQueue(FakeRequest())
        subscribe_to_everything(sse)
        assert registration_count(sse) == len(EventCallbacksManager.Events)

        task = asyncio.create_task(drain(sse.message_generator()))
        await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert registration_count(sse) == 0

    async def test_closing_down_ends_the_stream_and_unsubscribes(self, clean_subscribers):
        sse = ServerSideSignalsQueue(FakeRequest())
        subscribe_to_everything(sse)

        task = asyncio.create_task(drain(sse.message_generator()))
        await sse.add_new_message(EventCallbacksManager.Events.ClosingDown)
        await asyncio.wait_for(task, timeout=1)

        assert registration_count(sse) == 0

    async def test_disconnected_client_ends_the_stream_and_unsubscribes(self, clean_subscribers):
        request = FakeRequest(disconnected=True)
        sse = ServerSideSignalsQueue(request)
        subscribe_to_everything(sse)

        task = asyncio.create_task(drain(sse.message_generator()))
        await sse.add_new_message(EventCallbacksManager.Events.RefreshWorkflows)
        await asyncio.wait_for(task, timeout=1)

        assert registration_count(sse) == 0
