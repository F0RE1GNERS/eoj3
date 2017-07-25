from channels.routing import route
from eoj3.consumers import ws_message


channel_routing = [
    route("websocket.receive", ws_message)
]