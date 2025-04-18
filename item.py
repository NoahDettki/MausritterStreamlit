from enum import Enum

class ItemType(Enum):
    ITEM = "Gegenstand"
    WEAPON = "Waffe"
    ARMOR = "Rüstung"
    RUNE = "Rune"
    CONDITION = "Zustand"

class Item:
    def __init__(self, id, name, type:ItemType, space:tuple, condition=None, dice=None, armor=None, description=None):
        self.id = id
        self.name = name
        self.type = type
        self.primary, self.secondary, self.body1, self.body2, self.weight = space
        self.condition = condition
        self.dice = dice
        self.armor = armor
        self.description = description