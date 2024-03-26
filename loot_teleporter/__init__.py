from math import sin, cos, sqrt, radians
from typing import List, Tuple, Union

import unrealsdk #type ignore
from unrealsdk.unreal import WrappedStruct, UObject
from mods_base import build_mod, keybind, get_pc, BoolOption, DropdownOption, SliderOption

if True:
    assert __import__("mods_base").__version_info__ >= (1, 0), "Please update the SDK"

__version__: str
__version_info__: tuple[int, ...]

loot_sort_type = DropdownOption(
    "loot_sort_type",
    "Rarity",
    ["Rarity", "Rarity then Type"],
    display_name="Loot Sort Type",
    description="Sort loot by rarity or rarity then type"
)

loot_distance = SliderOption(
    "loot_distance",
    75, 50, 200, 25,
    True,
    display_name="Loot Distance",
    description="Distance between sorted loot items"
)

include_echo_logs = BoolOption(
    "include_echo_logs",
    False,
    "Yes",
    "No",
    display_name="Include Echo Logs",
    description="Include Echo Logs?"
)

lay_items_flat = BoolOption(
    "flat_items",
    False,
    "Yes",
    "No",
    display_name="Lay Items Flat",
    description="If enabled, items will be laid flat on the ground (items may clip through the floor if facing upward slopes). If disabled, items will be placed in the upward/downwards direction you are facing."
)

def get_test_library() -> UObject:
    return unrealsdk.find_object('TestLibrary', '/Script/GbxTest.Default__TestLibrary')

def get_current_world() -> UObject:
    return get_test_library().GetWorldForActor(get_pc())

def get_vector(x, y, z) -> WrappedStruct:
    return unrealsdk.make_struct("Vector", X=x, Y=y, Z=z)

def add_vectors(vec1: WrappedStruct, vec2: WrappedStruct) -> WrappedStruct:
    return get_vector(vec1.X + vec2.X, vec1.Y + vec2.Y, vec1.Z + vec2.Z)

def subtract_vectors(vec1: WrappedStruct, vec2: WrappedStruct) -> WrappedStruct:
    return get_vector(vec1.X - vec2.X, vec1.Y - vec2.Y, vec1.Z - vec2.Z)

def multiply_vector_by_scalar(vec: WrappedStruct, scalar: float) -> WrappedStruct:
    return get_vector(vec.X * scalar, vec.Y * scalar, vec.Z * scalar)

def divide_vector_by_scalar(vec: WrappedStruct, scalar: float) -> WrappedStruct:
    if scalar == 0:
        raise ValueError("Cannot divide by zero")
    return get_vector(vec.X / scalar, vec.Y / scalar, vec.Z / scalar)

def rotate_vector(vector: WrappedStruct, angle_degrees: float) -> WrappedStruct:
    angle_radians = radians(angle_degrees)
    x = vector.X * cos(angle_radians) - vector.Y * sin(angle_radians)
    y = vector.X * sin(angle_radians) + vector.Y * cos(angle_radians)
    return get_vector(x, y, vector.Z)

def get_normalized_vector(rotation: WrappedStruct) -> WrappedStruct:
    yaw_rad = radians(rotation.Yaw)
    pitch_rad = radians(rotation.Pitch)

    x = cos(yaw_rad) * cos(pitch_rad)
    y = sin(yaw_rad) * cos(pitch_rad)
    z = sin(pitch_rad)

    magnitude = (x**2 + y**2 + z**2)**0.5
    if magnitude == 0:
        return get_vector(0, 0, 0)
    return get_vector(x / magnitude, y / magnitude, z / magnitude)

def get_valid_loot(items: List[UObject]) -> List[UObject]:
    valid_loot = []

    for loot in items:
        class_name = loot.Class.Name
        if not include_echo_logs.value and "EchoLogPickup" in class_name:
            continue
        if loot.Class == unrealsdk.find_class("OakMissionPickup") or loot.Class == unrealsdk.find_class("GunRackDisplayItem"):
            continue
        valid_loot.append(loot)

    return valid_loot

def try_get_item_real_category(item: UObject) -> str:
    try:
        balance_component = item.GetInventoryBalanceStateComponent()
        inv_data = balance_component.InventoryData
        return inv_data.ItemCardTypeFrameName
    except:
        return "Unknown"

class PositionedItem:
    def __init__(self, item: UObject, position: WrappedStruct | None = None):
        self.item = item
        self.position = position or item.K2_GetActorLocation()

    def teleport(self) -> None:
        self.item.K2_TeleportTo(self.position, self.item.K2_GetActorRotation())

class GroupedLoot:
    def __init__(self, items: List[PositionedItem]):
        self.items = items

    def __iter__(self):
        return iter(self.items)

    def sort(self, player_position: WrappedStruct, normalized_vector: WrappedStruct) -> None:
        player_forward_position = add_vectors(player_position, multiply_vector_by_scalar(normalized_vector, loot_distance.value))

        match loot_sort_type.value:
            case "Rarity":
                rarities = {}
                for positioned_item in self.items:
                    rarity: int = positioned_item.item.AssociatedInventoryRarityData.RaritySortValue if positioned_item.item.AssociatedInventoryRarityData else 0

                    if rarity not in rarities:
                        rarities[rarity] = []

                    rarities[rarity].append(positioned_item)

                rarities = dict(sorted(rarities.items(), key=lambda x: x[0]))

                for i, (rarity, item_array) in enumerate(rarities.items()):
                    for positioned_item in item_array:
                        item_position = add_vectors(player_position, multiply_vector_by_scalar(normalized_vector, i * loot_distance.value))
                        if lay_items_flat.value:
                            item_position.Z = player_position.Z
                        positioned_item.position = item_position

            case "Rarity then Type":
                rarities = {}
                category_names = set()

                for positioned_item in self.items:
                    rarity: int = positioned_item.item.AssociatedInventoryRarityData.RaritySortValue if positioned_item.item.AssociatedInventoryRarityData else 0
                    category_name = try_get_item_real_category(positioned_item.item)

                    if rarity not in rarities:
                        rarities[rarity] = {}

                    if category_name not in category_names:
                        category_names.add(category_name)

                    if category_name not in rarities[rarity]:
                        rarities[rarity][category_name] = []

                    rarities[rarity][category_name].append(positioned_item)

                rarities = dict(sorted(rarities.items(), key=lambda x: x[0]))

                for i, (rarity, rarity_dict) in enumerate(rarities.items()):
                    rarity_position = add_vectors(player_forward_position, multiply_vector_by_scalar(normalized_vector, i * loot_distance.value))
                    perpendicular_vector = rotate_vector(normalized_vector, 90)
                    for j, (category_name, category_array) in enumerate(rarity_dict.items()):
                        category_offset = multiply_vector_by_scalar(perpendicular_vector, j * loot_distance.value)

                        for positioned_item in category_array:
                            item_position = add_vectors(rarity_position, category_offset)
                            if lay_items_flat.value:
                                item_position.Z = player_position.Z
                            positioned_item.position = item_position


    def teleport_loot(self) -> None:
        for i, loot in enumerate(self.items):
            loot.teleport()

@keybind("Teleport Loot")
def teleport_loot() -> None:
    pc = get_pc()

    if pc is None:
        return

    player_state = pc.Pawn.PlayerState
    location = player_state.PlayerLocation
    rotation = player_state.PlayerRotation

    player_location = get_vector(location.X, location.Y, location.Z)

    normalized_vector = get_normalized_vector(rotation)

    all_items = get_current_world().GameState.PickupList
    valid_loot = get_valid_loot(all_items)

    grouped_loot = GroupedLoot([PositionedItem(loot) for loot in valid_loot])
    grouped_loot.sort(player_location, normalized_vector)
    grouped_loot.teleport_loot()

build_mod(
    options=[
        loot_distance, loot_sort_type, include_echo_logs, lay_items_flat
    ]
)