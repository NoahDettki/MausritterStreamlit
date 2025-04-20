import random

class Dice:
    def __init__(self, number):
        self.number = number
    
    def roll(self, format_text=None, against=None):
        _outcome = random.randint(1, self.number)
        _color = None
        if against:
            if _outcome <= against:
                _color = "green"
            else:
                _color = "orange"
        return Roll(self.get_label(), _outcome, _color, format_text)
    
    def get_label(self, dice=None):
        if dice:
            return f"W{dice.number}"
        return f"W{self.number}"

class Roll:
    def __init__(self, dice_label, outcome, color, format_text=None):
        self.dice_label = dice_label
        self.outcome = outcome
        self.color = color
        self.format_text = format_text