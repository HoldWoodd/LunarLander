"""Shared visual effects and keyboard camera controls for PyBullet GUIs."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pybullet as p



def _link_world_transform(body_id: int, link_index: int):
    if link_index == -1:
        return p.getBasePositionAndOrientation(body_id)
    state = p.getLinkState(body_id, link_index, computeForwardKinematics=True)
    return state[4], state[5]


def _quaternion_from_z(direction: tuple[float, float, float]):
    target = np.asarray(direction, dtype=np.float64)
    target /= np.linalg.norm(target)
    z_axis = np.asarray([0.0, 0.0, 1.0])
    dot = float(np.clip(np.dot(z_axis, target), -1.0, 1.0))
    if dot > 1.0 - 1e-8:
        return (0.0, 0.0, 0.0, 1.0)
    if dot < -1.0 + 1e-8:
        return p.getQuaternionFromAxisAngle([1.0, 0.0, 0.0], math.pi)
    axis = np.cross(z_axis, target)
    axis /= np.linalg.norm(axis)
    return p.getQuaternionFromAxisAngle(axis, math.acos(dot))


@dataclass
class _Flame:
    engine: EngineRuntime
    body_id: int = -1
    level: int = 0


class EngineFlameVisualizer:
    """Render throttle-scaled, collision-free translucent exhaust cones."""

    def __init__(
        self,
        lander: BuiltLander,
        levels: int = 20,
        main_max_length: float = 4.0,
        rcs_max_length: float = 1.2,
    ) -> None:
        self.lander = lander
        self.levels = levels
        self.flames = [_Flame(engine) for engine in lander.engines]
        self.visual_shapes: dict[tuple[bool, int], int] = {}
        for is_main, max_length, max_radius in (
            (True, main_max_length, 0.42),
            (False, rcs_max_length, 0.16),
        ):
            for level in range(1, levels + 1):
                fraction = level / levels
                length = max_length * fraction
                radius = max_radius * math.sqrt(fraction)
                vertices, indices = self._cone_mesh(length, radius)
                self.visual_shapes[(is_main, level)] = p.createVisualShape(
                    p.GEOM_MESH,
                    vertices=vertices,
                    indices=indices,
                    rgbaColor=[1.0, 0.35, 0.03, 0.52],
                    specularColor=[0.0, 0.0, 0.0],
                )

    @staticmethod
    def _cone_mesh(length: float, radius: float, segments: int = 20):
        vertices = [[0.0, 0.0, 0.0], [0.0, 0.0, length]]
        for index in range(segments):
            angle = 2.0 * math.pi * index / segments
            vertices.append([radius * math.cos(angle), radius * math.sin(angle), 0.0])
        indices: list[int] = []
        for index in range(segments):
            current = 2 + index
            following = 2 + (index + 1) % segments
            indices.extend([0, following, current, 1, current, following])
        return vertices, indices

    def update(self, throttles) -> None:
        for flame, raw_throttle in zip(self.flames, throttles):
            throttle = float(np.clip(raw_throttle, 0.0, 1.0))
            level = int(math.ceil(throttle * self.levels)) if throttle > 0.005 else 0
            if level != flame.level:
                if flame.body_id >= 0:
                    p.removeBody(flame.body_id)
                    flame.body_id = -1
                flame.level = level
                if level:
                    is_main = flame.engine.component_id == "main_engine"
                    flame.body_id = p.createMultiBody(
                        baseMass=0.0,
                        baseCollisionShapeIndex=-1,
                        baseVisualShapeIndex=self.visual_shapes[(is_main, level)],
                    )
            if flame.body_id >= 0:
                position, orientation = self._world_exhaust_transform(flame.engine)
                p.resetBasePositionAndOrientation(flame.body_id, position, orientation)

    def _world_exhaust_transform(self, engine: EngineRuntime):
        link_position, link_orientation = _link_world_transform(
            self.lander.body_id,
            engine.link_index,
        )
        nozzle_position, _ = p.multiplyTransforms(
            link_position,
            link_orientation,
            engine.nozzle_position,
            (0.0, 0.0, 0.0, 1.0),
        )
        exhaust_local = tuple(-component for component in engine.thrust_direction)
        exhaust_world, _ = p.multiplyTransforms(
            (0.0, 0.0, 0.0),
            link_orientation,
            exhaust_local,
            (0.0, 0.0, 0.0, 1.0),
        )
        return nozzle_position, _quaternion_from_z(tuple(exhaust_world))

    def clear(self) -> None:
        for flame in self.flames:
            if flame.body_id >= 0:
                p.removeBody(flame.body_id)
                flame.body_id = -1
            flame.level = 0


class GuiCameraController:
    """Q/E zoom and WASD orbit controls that can follow a target."""

    def __init__(
        self,
        distance: float = 40.0,
        yaw: float = 45.0,
        pitch: float = -25.0,
        min_distance: float = 3.0,
        max_distance: float = 150.0,
    ) -> None:
        self.distance = distance
        self.yaw = yaw
        self.pitch = pitch
        self.min_distance = min_distance
        self.max_distance = max_distance

    def reset(self, target_position) -> None:
        p.resetDebugVisualizerCamera(
            self.distance,
            self.yaw,
            self.pitch,
            target_position,
        )

    def update(self, target_position, keyboard_events: dict | None = None) -> None:
        keys = keyboard_events if keyboard_events is not None else p.getKeyboardEvents()
        if keys.get(ord("q"), 0) & p.KEY_IS_DOWN:
            self.distance = max(self.min_distance, self.distance - 0.2)
        if keys.get(ord("e"), 0) & p.KEY_IS_DOWN:
            self.distance = min(self.max_distance, self.distance + 0.2)
        if keys.get(ord("a"), 0) & p.KEY_IS_DOWN:
            self.yaw -= 1.5
        if keys.get(ord("d"), 0) & p.KEY_IS_DOWN:
            self.yaw += 1.5
        if keys.get(ord("w"), 0) & p.KEY_IS_DOWN:
            self.pitch = min(89.0, self.pitch + 1.2)
        if keys.get(ord("s"), 0) & p.KEY_IS_DOWN:
            self.pitch = max(-89.0, self.pitch - 1.2)
        self.reset(target_position)
