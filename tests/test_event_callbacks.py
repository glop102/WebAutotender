from pipeline_backend.event_callbacks import EventCallbacksManager


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
