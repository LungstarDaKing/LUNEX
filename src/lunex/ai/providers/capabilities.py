from enum import IntFlag, auto

class ProviderCapabilities(IntFlag):
    """Bitmask of capabilities that AI providers can support"""
    NONE = 0
    TEXT = auto()           # Basic text generation
    STREAMING = auto()      # Streaming response support
    VISION = auto()         # Image/video understanding
    FUNCTION_CALLING = auto() # Tool/function calling
    EMBEDDINGS = auto()     # Embedding generation
    AUDIO = auto()          # Audio processing
    # Extend as needed

# Helper functions for capability checking
def has_capability(provider_cap: ProviderCapabilities, required_cap: ProviderCapabilities) -> bool:
    return bool(provider_cap & required_cap)