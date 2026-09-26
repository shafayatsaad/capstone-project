"""
One shared Limiter instance. Routers import `limiter` to decorate endpoints;
main.py registers it on the app and wires the 429 exception handler. Keeping it
here (rather than defining it in main.py) avoids a circular import between
main and the routers that need to decorate their routes with it.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
