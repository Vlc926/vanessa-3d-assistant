"""
UI Dialogs package for Vanessa.
"""
from ui.dialogs.gemini_key_dialog import GeminiApiKeyDialog
from ui.dialogs.personality_dialog import PersonalityConfigDialog
from ui.dialogs.voice_enrollment_dialog import VoiceEnrollmentDialog
from ui.dialogs.file_locator_dialog import FileLocatorDialog
from ui.dialogs.workspaces_dialog import HyprlandWorkspacesDialog
from ui.dialogs.volume_dialog import VolumeDialog
from ui.dialogs.omni_sync_dialog import OmniSyncDialog

__all__ = [
    "GeminiApiKeyDialog",
    "PersonalityConfigDialog",
    "VoiceEnrollmentDialog",
    "FileLocatorDialog",
    "HyprlandWorkspacesDialog",
    "VolumeDialog",
    "OmniSyncDialog",
]
