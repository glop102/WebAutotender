from sse_starlette.sse import EventSourceResponse
from asyncio import Queue
from fastapi import APIRouter,Request
from enum import Enum,auto
from typing import Callable

class EventCallbacksManager:
    class Events(Enum):
        RefreshWorkflows = auto()
        RefreshInstances = auto()
        RefreshWorkflow = auto()
        RefreshInstance = auto()
        RefreshGlobals = auto()
        RefreshGlobal = auto()
        DeleteInstance = auto()
        DeleteWorkflow = auto()
        DeleteGlobal = auto()
        ClosingDown = auto()
    
    subscribers:dict[Events,list[Callable]]

    def __init__(self):
        self.subscribers = {}
    def register_callback(self,event:Events,callback:Callable):
        if not event in self.subscribers:
            self.subscribers[event] = []
        self.subscribers[event].append( callback )
    def unsubscribe_callback(self,callback:Callable):
        for e in self.Events:
            if callable in self.subscribers[e]:
                self.subscribers[e].remove(callback)
    async def signal_event(self,event:Events, uuid:str="", data:str=""):
        if not event in self.subscribers:
            return
        for callback in self.subscribers[event]:
            await callback(event,uuid,data)


eventsCallbackManager = EventCallbacksManager()

router = APIRouter(tags=["utils"])

class ServerSideSignalsQueue:
    message_queue : Queue
    client : Request
    def __init__(self,client:Request):
        self.message_queue = Queue()
        self.client = client
    async def add_new_message(self,event:EventCallbacksManager.Events,uuid:str="",data:str=""):
        await self.message_queue.put( {
            'event':event.name,
            'data':uuid
        })
    async def message_generator(self):
        while True:
            msg = await self.message_queue.get()
            if await self.client.is_disconnected():
                eventsCallbackManager.unsubscribe_callback(self.add_new_message)
                return
            yield msg

@router.get('/events_stream')
async def events_stream_registry(request:Request):
    sse = ServerSideSignalsQueue(request)
    for env in EventCallbacksManager.Events:
        eventsCallbackManager.register_callback(env, sse.add_new_message)

    return EventSourceResponse(sse.message_generator())