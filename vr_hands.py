"""Simple cube hands for Saikai VR mode."""


class VRHand:
    def __init__(self, side):
        self.side = side
        self.position = [0.0, 0.0, 0.0]
        self.velocity = [0.0, 0.0, 0.0]
        self.size = 0.18

    def update_pose(self, position, velocity=None):
        self.position = position
        if velocity is not None:
            self.velocity = velocity

    def damage(self):
        return int(sum(v*v for v in self.velocity) ** 0.5 * 4)


class VRHands:
    def __init__(self):
        self.left = VRHand("left")
        self.right = VRHand("right")

    def update(self, vr):
        if vr.enabled:
            self.left.update_pose(vr.hands["left"]["position"])
            self.right.update_pose(vr.hands["right"]["position"])
