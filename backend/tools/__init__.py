"""
Waiting The Longest™ - Tools
============================
Utility tools for content generation and processing.
"""

# Lazy import to avoid circular dependencies
__all__ = ["SocialVideoGenerator", "generate_animal_video", "VideoConfig"]


def __getattr__(name):
    if name in __all__:
        from .video_generator import SocialVideoGenerator, generate_animal_video, VideoConfig
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
