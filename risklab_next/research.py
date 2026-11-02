"""Register current tools while keeping the v1 scientific implementation immutable."""
import sys
from . import research_v1 as legacy
from .observatory import register_observatory
_register_v1 = legacy.register_research

def register_research(blueprint, store, geography):
    _register_v1(blueprint, store, geography)
    register_observatory(blueprint, store, geography)

legacy.register_research = register_research
sys.modules[__name__] = legacy
