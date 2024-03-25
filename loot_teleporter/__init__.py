from math import cos, sin, sqrt
from typing import List, Tuple, Union

import unrealsdk #type ignore
from unrealsdk.unreal import WrappedStruct, UObject
from mods_base import build_mod, keybind, get_pc, BoolOption

if True:
    assert __import__("mods_base").__version_info__ >= (1, 0), "Please update the SDK"

__version__: str
__version_info__: tuple[int, ...]

include_echo_logs = BoolOption("include_echo_logs", False, "Yes", "No", display_name="Include Echo Logs", description="Include Echo Logs?")

def get_test_library() -> UObject:
    return unrealsdk.find_object('TestLibrary', '/Script/GbxTest.Default__TestLibrary');

def get_current_world() -> UObject:
    return get_test_library().GetWorldForActor(get_pc())

def get_vector(x, y, z) -> WrappedStruct:
    return unrealsdk.make_struct("Vector", X=x, Y=y, Z=z)

# Math stuff from Juso's mod
u_rotation_180 = 32768
u_rotation_90 = u_rotation_180 / 2
u_pi = 3.1415926
u_conversion = u_pi / u_rotation_180

def rot_to_vec3d(rotation: List[int]) -> List[float]:
    """Takes UE3 Rotation as List, returns List of normalized vector."""
    f_yaw = rotation[1] * u_conversion
    f_pitch = rotation[0] * u_conversion
    cos_pitch = cos(f_pitch)
    x = cos(f_yaw) * cos_pitch
    y = sin(f_yaw) * cos_pitch
    z = sin(f_pitch)
    return [x, y, z]

def normalize_vec(
    vector: Union[List[float], Tuple[float, float, float]]
) -> List[float]:
    _len = sqrt(sum(x * x for x in vector))
    return [x / _len for x in vector]

@keybind("Teleport Loot")
def teleport_loot() -> None:
    pc = get_pc()

    if pc is None:
        return

    pawn = pc.Pawn
    player_state = pawn.PlayerState
    location = player_state.PlayerLocation
    rotation = player_state.PlayerRotation

    px, py, pz = location.X, location.Y, location.Z

    x, y, z = rot_to_vec3d(
        [
            rotation.Pitch,
            rotation.Yaw,
            rotation.Roll,
        ]
    )
    x, y, z = normalize_vec([x, y, 0])

    valid_loot = []

    all_items = get_current_world().GameState.PickupList

    for loot in all_items:
        class_name = loot.Class.Name
        if not include_echo_logs.value and "EchoLogPickup" in class_name:
            continue
        if loot.Class == unrealsdk.find_class("OakMissionPickup") or loot.Class == unrealsdk.find_class("GunRackDisplayItem"):
            continue
        valid_loot.append(loot)

    loot_by_rarity = {}

    for loot in valid_loot:
        rarity = 0

        rarity_component = loot.AssociatedInventoryRarityData
        if rarity_component is not None:
            rarity = rarity_component.RaritySortValue

        if rarity not in loot_by_rarity:
            loot_by_rarity[rarity] = []

        loot_by_rarity[rarity].append(loot)

    for i, loot in enumerate(loot_by_rarity.values()):
        for loot_pickup in loot:
            loot_pickup.K2_TeleportTo(get_vector(px + 75 * x * i, py + 75 * y * i, pz), loot_pickup.K2_GetActorRotation())
            z += 30

build_mod(options=[include_echo_logs])