"""SteamVR/OpenXR support for Saikai.

Uses SteamVR so Meta Quest headsets can work through Steam Link,
Air Link, or ALVR.
"""

import math

try:
    import openvr
    VR_AVAILABLE = True
except ImportError:
    VR_AVAILABLE = False


class VRSystem:
    def __init__(self):
        self.enabled = False
        self.system = None
        self.hands = {
            "left": {"position": [0, 0, 0]},
            "right": {"position": [0, 0, 0]},
        }

    def start(self):
        if not VR_AVAILABLE:
            print("SteamVR Python module missing")
            return False
        try:
            openvr.init(openvr.VRApplication_Scene)
            self.system = openvr.VRSystem()
            self.enabled = True
            return True
        except Exception as error:
            print("VR startup failed:", error)
            return False

    def update(self):
        if not self.enabled:
            return
        # Controller tracking/input will be connected here.

    def punch_damage(self, velocity):
        """Convert controller swing speed into damage."""
        speed = math.sqrt(sum(v*v for v in velocity))
        return max(0, int(speed * 2))

    def shutdown(self):
        if self.enabled:
            openvr.shutdown()
            self.enabled = False
