from typing import Literal
import streamlit as st
from streamlit_local_storage import LocalStorage
import time
from item import Item, ItemType
from dice import Dice, Roll

st.set_page_config("Mausritter Charakterbogen")

# Session state
if "last_saved" not in st.session_state:
    st.session_state.last_saved = "Nicht in dieser Sitzung"
if "new_item_toast" not in st.session_state:
    st.session_state.new_item_toast = False
elif st.session_state.new_item_toast != False:
    st.toast(f"{st.session_state.new_item_toast} wurde dem Rucksack hinzugefügt!")
    st.session_state.new_item_toast = False
if "backpack" not in st.session_state:
    st.session_state.backpack = []
if "ignored" not in st.session_state:
    st.session_state.ignored = []
if "primary" not in st.session_state:
    st.session_state.primary = None
if "secondary" not in st.session_state:
    st.session_state.secondary = None
if "body1" not in st.session_state:
    st.session_state.body1 = None
if "body2" not in st.session_state:
    st.session_state.body2 = None
if "dice_log" not in st.session_state:
    st.session_state.dice_log = []

# Cookies
ls = LocalStorage()
cookie = ls.getItem("mausritter_cookie")
if cookie == None:
    cookie = {
        'name': "",
        'st_max': 0,
        'st_now': 0,
        'ge_max': 0,
        'ge_now': 0,
        'wi_max': 0,
        'wi_now': 0,
        'tp_max': 0,
        'tp_now': 0
    }
temp_values = {key: None for key in cookie}
HELP_SAVE = "Speichert dein Charakterblatt als Cookie, sodass es beim Neuladen der Seite erhalten bleibt."
HELP_REMOVE_ITEM = "Gegenstand wegwerfen"
HELP_REMOVE_CONDITION = "Zustand auflösen"
dice_list = [Dice(4), Dice(6), Dice(8), Dice(10), Dice(12), Dice(20), Dice(100)]

# Custom css to make sidebar always overlap content and not deform the whole layout
st.markdown("""
    <style>
    /* Sidebar überlappend machen */
    [data-testid="stMain"] {
        position: absolute;
        inset: 0px;
    }
    </style>
""", unsafe_allow_html=True)

def calculate_guts(level) -> Literal[0, 1, 2, 3]:
    '''returns: 
    - 0 on level 1,
    - 1 on level 2,
    - 2 on level 3 and 4,
    - 3 on any higher level.'''
    if level <= 3: return level - 1
    if level == 4: return 2
    return 3

def enum_value(enum):
    return enum.value

def display_equipment(item, where:Literal["Equipped", "Backpack", "Conditions"] = "Equipped"):
    # The columns have different sizes depending on the part of the app where they are listed
    _column_sizes = [6.7,2,1,1.5,1,1] if where == "Equipped" else [4.7,2,1,1.5,2.8,1]
    _item, _stat, _cond, _weig, _move, _delete = st.columns(_column_sizes)
    # Name and description
    _item.markdown(f"**{item.name}**", help=item.description)
    # Attack dice or armor value
    if item.dice != None:
        _stat.button(item.dice.get_label(), icon=":material/casino:", key=f"{item.id}-stat", help="Angriffswürfel", on_click=roll, args=(item.dice, f"{item.name} :grey[{item.dice.get_label()}] macht {{}} Schaden!"), disabled=where!="Equipped", use_container_width=True)
    elif item.armor != None:
        _stat.button(str(item.armor), disabled=True, icon=":material/shield:", key=f"{item.id}-stat", help="Verteidigung", use_container_width=True)
    # Condition
    if item.condition != None:
        _cond.button("", icon=f":material/counter_{item.condition}:", key=f"{item.id}-cond", help="Übrige Anwendungen", on_click=change_condition, args=(item,), use_container_width=True)
    # Weight
    _weig.button(str(item.weight), disabled=True, icon=":material/weight:", key=f"{item.id}-weight", help="Gewicht", use_container_width=True)
    # Moving
    if where == "Equipped":
        _move.button("", type="secondary", icon=":material/exit_to_app:", key=f"{item.id}-move", help="Gegenstand in den Rucksack verschieben", on_click=item_to_backpack, args=(item,), use_container_width=True)
    elif where == "Backpack":
        if item.type != ItemType.CONDITION:
            _selection = _move.selectbox("move", get_move_options(item), index=None, key=f"{item.id}-move", help="Gegenstand verschieben", placeholder="Verschieben", label_visibility="collapsed")
            if _selection != None:
                move_item(item, _selection)
    # Delete
    _help = HELP_REMOVE_CONDITION if item.type == ItemType.CONDITION else HELP_REMOVE_ITEM
    if where == "Equipped":
        _delete.button("", type="primary", icon=":material/delete_forever:", key=f"{item.id}-delete", help=_help, on_click=item_to_backpack, args=(item,True), use_container_width=True)
    elif where == "Backpack":
        _delete.button("", type="primary", icon=":material/delete_forever:", key=f"{item.id}-delete", help=_help, on_click=delete_item, args=(item,), use_container_width=True)
    else:
        _delete.button("", type="primary", icon=":material/delete_forever:", key=f"{item.id}-delete", help=_help, on_click=delete_item, args=(item,True), use_container_width=True)
        
def get_move_options(item):
    match(item.type):
        case ItemType.ITEM:
            if item.weight == 1:
                return ["Hauptpfote", "Nebenpfote", "Körper"]
            elif item.weight == 2:
                return ["Beide Pfoten", "Ganzer Körper"]
            else:
                return []
        case ItemType.WEAPON:
            if item.weight == 1:
                return ["Hauptpfote", "Nebenpfote", "Körper"]
            else:
                return ["Beide Pfoten", "Ganzer Körper"]
        case ItemType.ARMOR:
            if item.secondary:
                return ["Nebenpfote und Körper"]
            elif item.weight == 2:
                return ["Ganzer Körper"]
            else:
                return ["Körper"]
        case ItemType.RUNE:
            return ["Hauptpfote", "Nebenpfote", "Körper"]
        case ItemType.CONDITION:
            print("Error: This should not happen.")
            return ["Mumm"]

def move_item(item, option):
    match(option):
        case "Hauptpfote":
            if st.session_state.primary == None:
                st.session_state.primary = item
            else:
                st.toast(":red[Die Hauptpfote ist schon belegt]", icon=":material/error:")
                return
        case "Nebenpfote":
            if st.session_state.secondary == None:
                st.session_state.secondary = item
            else:
                st.toast(":red[Die Nebenpfote ist schon belegt]", icon=":material/error:")
                return
        case "Beide Pfoten":
            if st.session_state.primary != None:
                st.toast(":red[Die Hauptpfote ist schon belegt]", icon=":material/error:")
                return
            if st.session_state.secondary != None:
                st.toast(":red[Die Nebenpfote ist schon belegt]", icon=":material/error:")
                return
            st.session_state.primary = item
            st.session_state.secondary = item
        case "Nebenpfote und Körper":
            if st.session_state.secondary != None:
                st.toast(":red[Die Nebenpfote ist schon belegt]", icon=":material/error:")
                return
            if st.session_state.body2 != None:
                st.toast(":red[Der Körper ist schon belegt]", icon=":material/error:")
                return
            st.session_state.secondary = item
            st.session_state.body2 = item
        case "Körper":
            if st.session_state.body1 == None:
                st.session_state.body1 = item
            elif st.session_state.body2 == None:
                st.session_state.body2 = item
            else:
                st.toast(":red[Der Körper ist schon belegt]", icon=":material/error:")
                return
        case "Ganzer Körper":
            if st.session_state.body1 == None and st.session_state.body2 == None:
                st.session_state.body1 = item
                st.session_state.body2 = item
            else:
                st.toast(":red[Der Körper ist schon belegt]", icon=":material/error:")
                return
        case "Mumm":
            st.toast(":red[Du hast keinen Mumm, haha!]", icon=":material/error:")
            return
        case _:
            print("Wrong move option")
    # Only remove item from backpack if moving was successful
    st.session_state.backpack.remove(item)
    st.rerun()

def item_to_backpack(item, delete=False):
    if st.session_state.primary == item:
        st.session_state.primary = None
    if st.session_state.secondary == item:
        st.session_state.secondary = None
    if st.session_state.body1 == item:
        st.session_state.body1 = None
    if st.session_state.body2 == item:
        st.session_state.body2 = None
    if not delete:
        st.session_state.backpack.append(item)

def change_condition(item):
    item.condition -= 1
    if item.condition < 0:
        item.condition = 3

def delete_item(item, ignored_conditions=False):
    if not ignored_conditions:
        st.session_state.backpack.remove(item)
    else :
        st.session_state.ignored.remove(item)

def get_unique_id():
    unique_id = 0
    used_ids = {item.id for item in st.session_state.backpack}
    for condition in st.session_state.ignored:
        used_ids.add(condition.id)
    if st.session_state.primary:
        used_ids.add(st.session_state.primary.id)
    if st.session_state.secondary:
        used_ids.add(st.session_state.secondary.id)
    if st.session_state.body1:
        used_ids.add(st.session_state.body1.id)
    if st.session_state.body2:
        used_ids.add(st.session_state.body2.id)
    while unique_id in used_ids:
        unique_id += 1
    return unique_id

def roll(dice, format_text=None, against=None):
    st.session_state.dice_log.append(dice.roll(format_text=format_text, against=against))
    if len(st.session_state.dice_log) > 10:
        st.session_state.dice_log.pop(0)

# Title
st.title("Mausritter Charakterbogen")
#st.text("Zuletzt gespeichert: " + st.session_state.last_saved)

# Mouse name and saving button
nam, lvl, exp, sav = st.columns([5.3, 2, 2.25, 0.77], vertical_alignment="bottom")
with nam:
    temp_values['name'] = st.text_input("Charaktername", value=cookie['name'])
with lvl:
    level = st.number_input("Level", 1, 100, 1, 1)
    guts = calculate_guts(level)
with exp:
    st.number_input("Erfahrung", 0, None, 0, 1)
with sav:
    is_save_pressed = st.button("", key="Speichern", type="primary", icon=":material/save:", help=HELP_SAVE, use_container_width=True)

# STÄ
st1, st2, st3, st4 = st.columns([1, 2, 2, 5], vertical_alignment="bottom")
with st1:
    st.text("STÄ", help="Stärke")
with st2:
    temp_values['st_max'] = st.number_input("Maximal", 0, None, cookie['st_max'], 1, None, "st_max", label_visibility="visible")
with st3:
    temp_values['st_now'] = st.number_input("Aktuell", 0, None, cookie['st_now'], 1, None, "st_now", label_visibility="visible")
with st4:
    st.empty()

# GES
ge1, ge2, ge3, ge4 = st.columns([1, 2, 2, 5], vertical_alignment="bottom")
with ge1:
    st.text("GES", help="Geschicklichkeit")
with ge2:
    temp_values['ge_max'] = st.number_input("Maximal", 0, None, cookie['ge_max'], 1, None, "ge_max", label_visibility="collapsed")
with ge3:
    temp_values['ge_now'] = st.number_input("Aktuell", 0, None, cookie['ge_now'], 1, None, "ge_now", label_visibility="collapsed")
with ge4:
    st.empty()

# WIL
wi1, wi2, wi3, wi4 = st.columns([1, 2, 2, 5], vertical_alignment="bottom")
with wi1:
    st.text("WIL", help="Willenskraft")
with wi2:
    temp_values['wi_max'] = st.number_input("Maximal", 0, None, cookie['wi_max'], 1, None, "wi_max", label_visibility="collapsed")
with wi3:
    temp_values['wi_now'] = st.number_input("Aktuell", 0, None, cookie['wi_now'], 1, None, "wi_now", label_visibility="collapsed")
with wi4:
    st.empty()

# TP
tp1, tp2, tp3, tp4 = st.columns([1, 2, 2, 5], vertical_alignment="bottom")
with tp1:
    st.text("TP", help="Trefferschutzpunkte")
with tp2:
    temp_values['tp_max'] = st.number_input("Maximal", 0, None, cookie['tp_max'], 1, None, "tp_max", label_visibility="collapsed")
with tp3:
    temp_values['tp_now'] = st.number_input("Aktuell", 0, None, cookie['tp_now'], 1, None, "tp_now", label_visibility="collapsed")
with tp4:
    st.empty()

# Seeds
se1, se2, se3, se4 = st.columns([1, 2, 2, 5], vertical_alignment="bottom")
with se1:
    st.text("Kerne")
with se3:
    st.number_input("Kerne", 0, 250, 0, 1, label_visibility="collapsed")

# Inventory
tab1, tab2, tab3 = st.tabs(["Ausgerüstet", "Rucksack", "Neuer Gegenstand/Zustand"])
with tab1:
    _primary = st.session_state.primary
    _secondary = st.session_state.secondary
    _body1 = st.session_state.body1
    _body2 = st.session_state.body2
    # Primary
    if _primary != None:
        if _primary == _secondary:
            st.markdown(":primary[**Haupt- und Nebenpfote**]")
            display_equipment(_primary)
        else:
            st.markdown(":primary[**Hauptpfote**]")
            display_equipment(_primary)
    else:
        st.markdown(":primary[**Hauptpfote**]")
        st.markdown(f"**Leer**")
    # Secondary
    if _secondary != None:
        # Equal primary and secondary is already handled in the #Primary block
        if _secondary != _primary:
            if _secondary == _body2:
                st.markdown(":primary[**Nebenpfote und Körper**]")
                display_equipment(_secondary)
            else:
                st.markdown(":primary[**Nebenpfote**]")
                display_equipment(_secondary)
    else:
        st.markdown(":primary[**Nebenpfote**]")
        st.markdown(f"**Leer**")
    # Body
    st.markdown(":primary[**Körper**]")
    if _body1 != None:
        display_equipment(_body1)
    elif _body2 == None:
        st.markdown(f"**Leer**")
    if _body2 != None and _body2 != _body1 and _body2 != _secondary:
        display_equipment(_body2)

with tab2:
    st.text("Du kannst ohne Mühen eine Last von 6 aushalten. Alles darüber hinaus belastet dich so sehr, dass du nicht mehr rennen kannst und alle Proben mit Nachteil würfeln musst.")
    _weight = sum(item.weight for item in st.session_state.backpack)
    if _weight > 6:
        st.warning("Du bist belastet!")
    for item in st.session_state.backpack:
        display_equipment(item, "Backpack")
    # # Displaying ignored conditions
    if len(st.session_state.ignored) > 0:
        match guts:
            case 0:
                pass
            case 1:
                st.text("Durch Mumm ignorierte Zustände:", 
                        help="Auf Level 2 hast du genug Mumm um einen Zustand zu ignorieren.")
            case _:
                st.text("Durch Mumm ignorierte Zustände:",
                        help=f"Auf Level {level} hast du genug Mumm um {guts} Zustände zu ignorieren.")
    for condition in st.session_state.ignored:
        display_equipment(condition, "Conditions")

with tab3:
    st.text("Hier kannst du einen neuen Gegenstand oder Zustand erstellen, der dann in deinem Rucksack landet.")
    col_name, col_type = st.columns(2)
    with col_name:
        new_item_name = st.text_input("Bezeichnung")
    with col_type:
        new_item_type = st.selectbox("Gegenstandstyp", ItemType, format_func=enum_value,  index=0)
    new_item_space = new_item_condition = new_item_dice = new_item_armor = new_item_description = None
    with st.container(border=True):
        match new_item_type:
            case ItemType.ITEM:
                _space = st.number_input("Benötigter Platz", 0, 4, 1, 1)
                new_item_space = (False, False, False, False, _space)
                if st.toggle("Gegenstand hat Anwendungen", value=False):
                    new_item_condition = st.number_input("Übrige Anwendungen", 0, 3, 3, 1)
            case ItemType.WEAPON:
                _double_size = st.toggle("Zweipfotig")
                new_item_space = (True, True, False, False, 2 if _double_size else 1)
                new_item_dice = st.selectbox("Angriffswürfel", dice_list, index=1, format_func=Dice.get_label)
                new_item_condition = st.number_input("Übrige Anwendungen", 0, 3, 3, 1)
            case ItemType.ARMOR:
                _extra_slot = st.pills("Zusätzlich benötigter Platz", ["Nebenpfote", "Zweiter Körperplatz"], selection_mode="single")
                if _extra_slot == "Nebenpfote":
                    new_item_space = (False, True, False, True, 2)
                elif _extra_slot == "Zweiter Körperplatz":
                    new_item_space = (False, False, True, True, 2)
                else:
                    new_item_space = (False, False, True, False, 1)
                new_item_armor = st.number_input("Rüstungswert", 0, 100, 1, 1)
                new_item_condition = st.number_input("Übrige Anwendungen", 0, 3, 3, 1)
            case ItemType.RUNE:
                new_item_space = (False, False, False, False, 1)
                new_item_description = st.text_input("Beschreibung des Runenzaubers")
                new_item_condition = st.number_input("Übrige Anwendungen", 0, 3, 3, 1)
            case ItemType.CONDITION:
                _severe = st.toggle("Doppelte Schwere")
                new_item_space = (False, False, False, False, 2 if _severe else 1)
                new_item_description = st.text_input("Beschreibe den Zustand")


    if st.button(f"{new_item_type.value} hinzufügen", type="primary"):
        if new_item_name.strip() == "":
            st.toast(f":red[Jede/r {new_item_type.value} braucht einen Namen]", icon=":material/error:")
        else:
            # As two items can have the same name but every streamlit component needs a unique id,
            # it is important to give each item a unique id.
            new_item_id = get_unique_id()
            new_item = Item(new_item_id, new_item_name, new_item_type, new_item_space, new_item_condition, new_item_dice, new_item_armor, new_item_description)
            # Check if the mouse has the guts to ignore another condition
            if new_item_type == ItemType.CONDITION and guts > len(st.session_state.ignored):
                st.session_state.ignored.append(new_item)
            else:
                st.session_state.backpack.append(new_item)
            st.session_state.new_item_toast = new_item.type.value
            st.rerun()

# Sidebar
with st.sidebar:
    _selected_dice = st.selectbox("Würfel", dice_list, index=5, format_func=Dice.get_label)
    if st.button("Würfeln", use_container_width=True):
        roll(_selected_dice)
    for roll in reversed(st.session_state.dice_log):
        if roll.format_text:
            st.markdown(roll.format_text.format(roll.outcome))
        elif roll.color:
            st.markdown(f"{roll.dice_label} -> :{roll.color}[{roll.outcome}]")
        else:
            st.markdown(f"{roll.dice_label} -> {roll.outcome}")

# Logic
if is_save_pressed:
    #temp_values["items"] = json.dumps(temp_values["items"])
    #temp_values["meintollertest"] = 5
    #ls.setItem("mausritter_cookie", temp_values)
    st.session_state.last_saved = time.strftime("%H:%M")
    print("Cookie has been saved")
    st.rerun()