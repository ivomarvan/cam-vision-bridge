"""Core domain: immutable ``Frame``, asyncio ``FrameHub``, and flow-control rules.

Holds only the newest complete frame; older completed frames are dropped when newer
ones arrive.
"""

from cam_vision_bridge.core.frame import Frame
from cam_vision_bridge.core.frame_hub import FrameHub, FrameHubClosed

__all__ = ["Frame", "FrameHub", "FrameHubClosed"]
