# blocks.py  ─  All block & item definitions for Saikai

import random
import numpy as np

# ── Block IDs ────────────────────────────────────────────────────────────
AIR             = 0
KEIRO_GRASS     = 1
KEIRO_SOIL      = 2
KEIRO_STONE     = 3
SHINEN_ROCK     = 4
SHINEN_CRYSTAL  = 5
SHINEN_EMBER    = 6
KASUMI_SNOW     = 7
KASUMI_ICE      = 8
KASUMI_SHALE    = 9
MORI_WOOD       = 10
MORI_LEAVES     = 11
MORI_MOSS       = 12
REIKI_WATER     = 13
TAMASHII_LAVA   = 14
CLOUD_BLOCK     = 15
WORKBENCH       = 16
GLASS_BLOCK     = 17
DOOR_BLOCK      = 18
FARMLAND        = 19
WHEAT_STAGE0    = 20
WHEAT_STAGE1    = 21
WHEAT_STAGE2    = 22
WHEAT_STAGE3    = 23
BUSH_LEAVES     = 24
DOG_STATUE      = 25
CAT_STATUE      = 26
DOOR_TOP        = 27
SAND_BLOCK      = 28
FURNACE_BLOCK   = 29
SIGN_BLOCK      = 30
SKYSCREEN_BLOCK = 31
CREDITS_BLOCK   = 32
BED_BLOCK       = 33
BED_FOOT        = 34
GLASS_DOOR      = 35
GLASS_DOOR_TOP  = 36

NUM_BLOCKS = 37

WORLDGEN_VERSION = 2

# ── Item IDs ──────────────────────────────────────────────────────────────
ITEM_STICK        = 100
ITEM_WOOD_SWORD   = 101
ITEM_STONE_SWORD  = 102
ITEM_WOOD_PICK    = 103
ITEM_STONE_PICK   = 104
ITEM_WOOD_AXE     = 105
ITEM_STONE_AXE    = 106
ITEM_WOOD_SHOVEL  = 107
ITEM_STONE_SHOVEL = 108
ITEM_BERRY        = 109
ITEM_BREAD        = 110
ITEM_HOE          = 111
ITEM_WHEAT_SEEDS  = 112
ITEM_WHEAT        = 113
ITEM_APPLE        = 114
ITEM_COOKED_MEAT  = 115
ITEM_RAW_MEAT     = 116
ITEM_WOOL         = 117
ITEM_TRICKSABRE   = 118   # stylish combo weapon

ITEM_NAMES = {
    ITEM_STICK:        "Stick",
    ITEM_WOOD_SWORD:   "Wooden Sword",
    ITEM_STONE_SWORD:  "Stone Sword",
    ITEM_WOOD_PICK:    "Wooden Pickaxe",
    ITEM_STONE_PICK:   "Stone Pickaxe",
    ITEM_WOOD_AXE:     "Wooden Axe",
    ITEM_STONE_AXE:    "Stone Axe",
    ITEM_WOOD_SHOVEL:  "Wooden Shovel",
    ITEM_STONE_SHOVEL: "Stone Shovel",
    ITEM_BERRY:        "Forest Berries",
    ITEM_BREAD:        "Bread",
    ITEM_HOE:          "Wooden Hoe",
    ITEM_WHEAT_SEEDS:  "Wheat Seeds",
    ITEM_WHEAT:        "Wheat",
    ITEM_APPLE:        "Saikai Apple",
    ITEM_COOKED_MEAT:  "Cooked Meat",
    ITEM_RAW_MEAT:     "Raw Meat",
    ITEM_WOOL:         "Wool",
    ITEM_TRICKSABRE:   "Tricksabre",
}

# ── Item tooltip text (shown after hovering for ~2 s in inventory) ────────
ITEM_TOOLTIPS = {
    ITEM_TRICKSABRE: "Show 'em one or two things",
}

ITEM_COLORS = {
    ITEM_STICK:        (139,  90,  43),
    ITEM_WOOD_SWORD:   (180, 120,  50),
    ITEM_STONE_SWORD:  (160, 158, 165),
    ITEM_WOOD_PICK:    (160, 105,  40),
    ITEM_STONE_PICK:   (140, 138, 145),
    ITEM_WOOD_AXE:     (170, 110,  45),
    ITEM_STONE_AXE:    (145, 143, 150),
    ITEM_WOOD_SHOVEL:  (155, 100,  38),
    ITEM_STONE_SHOVEL: (135, 133, 140),
    ITEM_BERRY:        ( 80, 190,  60),
    ITEM_BREAD:        (210, 170,  80),
    ITEM_HOE:          (155, 100,  38),
    ITEM_WHEAT_SEEDS:  (180, 160,  60),
    ITEM_WHEAT:        (220, 200,  50),
    ITEM_APPLE:        (130,  50, 180),
    ITEM_COOKED_MEAT:  (180,  90,  40),
    ITEM_RAW_MEAT:     (220, 100,  90),
    ITEM_WOOL:         (235, 235, 235),
    ITEM_TRICKSABRE:   (200, 180, 255),  # spectral violet
}

FOOD_HEAL = {
    ITEM_BERRY: 2, ITEM_BREAD: 5, ITEM_APPLE: 3,
    ITEM_COOKED_MEAT: 6, ITEM_RAW_MEAT: 1,
}

TOOLS = frozenset({
    ITEM_WOOD_SWORD, ITEM_STONE_SWORD,
    ITEM_WOOD_PICK,  ITEM_STONE_PICK,
    ITEM_WOOD_AXE,   ITEM_STONE_AXE,
    ITEM_WOOD_SHOVEL,ITEM_STONE_SHOVEL,
    ITEM_HOE,
    ITEM_TRICKSABRE,
})


# ── Master block definition table ─────────────────────────────────────────
BLOCK_DEFS = {

    AIR: dict(
        name="Air", tex=None, tex_variants=False,
        color_top=(0,0,0), color_bot=(0,0,0), color_side=(0,0,0),
        emissive=False, transparent=True, passthrough=True, no_mesh=False,
        ray_ignore=True, ray_blocking=False, nodraw=False,
        collideable=False, slow_fall=False, hardness=0, best_tool=None, drops=[],
    ),
    KEIRO_GRASS: dict(
        name="Keiro Grass", tex="keiro_grass", tex_variants=False,
        color_top=(56,173,140), color_bot=(89,56,102), color_side=(71,153,122),
        emissive=False, transparent=False, passthrough=False, no_mesh=False,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=0.8, best_tool='shovel',
        drops=[(KEIRO_GRASS,1,1.0)],
    ),
    KEIRO_SOIL: dict(
        name="Keiro Soil", tex="keiro_soil", tex_variants=False,
        color_top=(89,56,102), color_bot=(63,38,76), color_side=(76,45,89),
        emissive=False, transparent=False, passthrough=False, no_mesh=False,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=0.7, best_tool='shovel',
        drops=[(KEIRO_SOIL,1,1.0)],
    ),
    KEIRO_STONE: dict(
        name="Keiro Stone", tex="keiro_stone", tex_variants=False,
        color_top=(114,114,132), color_bot=(89,89,107), color_side=(102,102,119),
        emissive=False, transparent=False, passthrough=False, no_mesh=False,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=4.0, best_tool='pick',
        drops=[(KEIRO_STONE,1,1.0)],
    ),
    SHINEN_ROCK: dict(
        name="Shinen Rock", tex="shinen_rock", tex_variants=False,
        color_top=(38,33,51), color_bot=(25,20,38), color_side=(30,25,45),
        emissive=False, transparent=False, passthrough=False, no_mesh=False,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=5.0, best_tool='pick',
        drops=[(SHINEN_ROCK,1,1.0)],
    ),
    SHINEN_CRYSTAL: dict(
        name="Memory Crystal", tex="shinen_crystal", tex_variants=False,
        color_top=(25,216,229), color_bot=(20,178,204), color_side=(38,204,224),
        emissive=True, transparent=False, passthrough=False, no_mesh=False,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=6.0, best_tool='pick',
        drops=[(SHINEN_CRYSTAL,1,1.0)],
    ),
    SHINEN_EMBER: dict(
        name="Ember Ore", tex="shinen_ember", tex_variants=False,
        color_top=(242,114,12), color_bot=(204,76,5), color_side=(224,96,10),
        emissive=True, transparent=False, passthrough=False, no_mesh=False,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=6.0, best_tool='pick',
        drops=[(SHINEN_EMBER,1,1.0)],
    ),
    KASUMI_SNOW: dict(
        name="Kasumi Ash-Snow", tex="kasumi_snow", tex_variants=False,
        color_top=(229,229,242), color_bot=(204,204,224), color_side=(216,216,235),
        emissive=False, transparent=False, passthrough=False, no_mesh=False,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=0.3, best_tool='shovel',
        drops=[(KASUMI_SNOW,1,1.0)],
    ),
    KASUMI_ICE: dict(
        name="Glacier Ice", tex="kasumi_ice", tex_variants=False,
        color_top=(153,204,242), color_bot=(127,178,229), color_side=(140,191,235),
        emissive=False, transparent=False, passthrough=False, no_mesh=False,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=1.5, best_tool='pick',
        drops=[(KASUMI_ICE,1,1.0)],
    ),
    KASUMI_SHALE: dict(
        name="Kasumi Shale", tex="kasumi_shale", tex_variants=False,
        color_top=(140,132,147), color_bot=(114,107,122), color_side=(127,119,135),
        emissive=False, transparent=False, passthrough=False, no_mesh=False,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=3.5, best_tool='pick',
        drops=[(KASUMI_SHALE,1,1.0)],
    ),
    MORI_WOOD: dict(
        name="Mori Wood", tex="mori_wood", tex_variants=False,
        color_top=(140,89,25), color_bot=(114,71,20), color_side=(127,76,22),
        emissive=False, transparent=False, passthrough=False, no_mesh=False,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=2.0, best_tool='axe',
        drops=[(MORI_WOOD,1,1.0)],
    ),
    MORI_LEAVES: dict(
        name="Mori Leaves", tex="mori_leaves", tex_variants=False,
        color_top=(38,178,89), color_bot=(25,140,71), color_side=(30,158,76),
        emissive=False, transparent=False, passthrough=True, no_mesh=False,
        ray_ignore=False, ray_blocking=False,
        collideable=False, slow_fall=True, hardness=0.2, best_tool='sword',
        drops=[(MORI_LEAVES,1,0.08),(ITEM_APPLE,1,0.05)],
    ),
    MORI_MOSS: dict(
        name="Mori Moss", tex="mori_moss", tex_variants=False,
        color_top=(76,224,51), color_bot=(51,178,38), color_side=(63,198,45),
        emissive=True, transparent=False, passthrough=False, no_mesh=False,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=0.5, best_tool='shovel',
        drops=[(MORI_MOSS,1,1.0)],
    ),
    REIKI_WATER: dict(
        name="Reiki Water", tex="reiki_water", tex_variants=False,
        color_top=(25,38,178), color_bot=(20,30,153), color_side=(22,33,165),
        emissive=False, transparent=True, passthrough=True, no_mesh=False,
        ray_ignore=True, ray_blocking=False,
        collideable=False, slow_fall=True, hardness=0, best_tool=None, drops=[],
    ),
    TAMASHII_LAVA: dict(
        name="Tamashii Soul-Lava", tex="tamashii_lava", tex_variants=False,
        color_top=(249,234,140), color_bot=(229,204,102), color_side=(242,219,122),
        emissive=True, transparent=True, passthrough=True, no_mesh=False,
        ray_ignore=True, ray_blocking=False,
        collideable=False, slow_fall=False, hardness=0, best_tool=None, drops=[],
    ),
    CLOUD_BLOCK: dict(
        name="Cloud", tex="cloud", tex_variants=False,
        color_top=(244,244,255), color_bot=(224,224,244), color_side=(234,234,249),
        emissive=False, transparent=False, passthrough=False, no_mesh=False,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=0.4, best_tool=None,
        drops=[(CLOUD_BLOCK,1,1.0)],
    ),
    WORKBENCH: dict(
        name="Workbench", tex="workbench", tex_variants=True,
        color_top=(180,120,40), color_bot=(120,80,25), color_side=(160,100,30),
        emissive=False, transparent=False, passthrough=False, no_mesh=False,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=1.5, best_tool='axe',
        drops=[(WORKBENCH,1,1.0)],
    ),
    GLASS_BLOCK: dict(
        name="Glass", tex="glass", tex_variants=False,
        color_top=(200,230,255), color_bot=(180,210,245), color_side=(190,220,250),
        emissive=False, transparent=True, passthrough=False, no_mesh=True,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=0.6, best_tool='pick',
        drops=[(GLASS_BLOCK,1,1.0)],
    ),
    DOOR_BLOCK: dict(
        name="Door", tex="door", tex_variants=False,
        color_top=(160,110,40), color_bot=(120,80,25), color_side=(140,95,32),
        emissive=False, transparent=True, passthrough=True, no_mesh=True,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=1.5, best_tool='axe',
        drops=[(DOOR_BLOCK,1,1.0)],
    ),
    FARMLAND: dict(
        name="Farmland", tex="farmland", tex_variants=False,
        color_top=(110,75,40), color_bot=(85,55,28), color_side=(98,65,34),
        emissive=False, transparent=False, passthrough=False, no_mesh=False,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=0.6, best_tool='shovel',
        drops=[(KEIRO_SOIL,1,1.0)],
    ),
    WHEAT_STAGE0: dict(
        name="Wheat (sprout)", tex="wheat0", tex_variants=False,
        color_top=(120,180,60), color_bot=(90,140,40), color_side=(105,160,50),
        emissive=False, transparent=True, passthrough=True, no_mesh=True,
        ray_ignore=False, ray_blocking=False,
        collideable=False, slow_fall=False, hardness=0.0, best_tool=None,
        drops=[(ITEM_WHEAT_SEEDS,1,1.0)],
    ),
    WHEAT_STAGE1: dict(
        name="Wheat (young)", tex="wheat1", tex_variants=False,
        color_top=(140,190,50), color_bot=(110,155,35), color_side=(125,172,42),
        emissive=False, transparent=True, passthrough=True, no_mesh=True,
        ray_ignore=False, ray_blocking=False,
        collideable=False, slow_fall=False, hardness=0.0, best_tool=None,
        drops=[(ITEM_WHEAT_SEEDS,1,1.0)],
    ),
    WHEAT_STAGE2: dict(
        name="Wheat (mature)", tex="wheat2", tex_variants=False,
        color_top=(180,200,40), color_bot=(150,170,28), color_side=(165,185,34),
        emissive=False, transparent=True, passthrough=True, no_mesh=True,
        ray_ignore=False, ray_blocking=False,
        collideable=False, slow_fall=False, hardness=0.0, best_tool=None,
        drops=[(ITEM_WHEAT_SEEDS,1,1.0)],
    ),
    WHEAT_STAGE3: dict(
        name="Wheat (ripe)", tex="wheat3", tex_variants=False,
        color_top=(220,200,30), color_bot=(190,170,20), color_side=(205,185,25),
        emissive=True, transparent=True, passthrough=True, no_mesh=True,
        ray_ignore=False, ray_blocking=False,
        collideable=False, slow_fall=False, hardness=0.0, best_tool=None,
        drops=[(ITEM_WHEAT,(1,3),1.0),(ITEM_WHEAT_SEEDS,1,1.0)],
    ),
    BUSH_LEAVES: dict(
        name="Bush Leaves", tex="bush_leaves", tex_variants=False,
        color_top=(55,160,70), color_bot=(38,125,52), color_side=(46,142,60),
        emissive=False, transparent=False, passthrough=True, no_mesh=False,
        ray_ignore=False, ray_blocking=False,
        collideable=False, slow_fall=True, hardness=0.2, best_tool='sword',
        drops=[(BUSH_LEAVES,1,0.08),(ITEM_BERRY,1,0.20),(ITEM_APPLE,1,0.04)],
    ),
    DOG_STATUE: dict(
        name="Dog Statue", tex="dog_statue", tex_variants=False,
        color_top=(180,160,140), color_bot=(140,120,100), color_side=(160,140,120),
        emissive=False, transparent=False, passthrough=False, no_mesh=False,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=2.0, best_tool='pick',
        drops=[(DOG_STATUE,1,1.0)],
    ),
    CAT_STATUE: dict(
        name="Cat Statue", tex="cat_statue", tex_variants=False,
        color_top=(200,180,200), color_bot=(160,140,160), color_side=(180,160,180),
        emissive=False, transparent=False, passthrough=False, no_mesh=False,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=2.0, best_tool='pick',
        drops=[(CAT_STATUE,1,1.0)],
    ),
    DOOR_TOP: dict(
        name="Door Top", tex="door_top", tex_variants=False,
        color_top=(140,95,32), color_bot=(120,80,25), color_side=(140,95,32),
        emissive=False, transparent=True, passthrough=True, no_mesh=True,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=1.5, best_tool='axe', drops=[],
    ),
    SAND_BLOCK: dict(
        name="Sand", tex="sand", tex_variants=False,
        color_top=(55,60,85), color_bot=(40,45,70), color_side=(48,52,78),
        emissive=False, transparent=False, passthrough=False, no_mesh=False,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=0.5, best_tool='shovel',
        drops=[(SAND_BLOCK,1,1.0)],
    ),
    FURNACE_BLOCK: dict(
        name="Furnace", tex="furnace", tex_variants=True,
        color_top=(80,70,65), color_bot=(55,48,42), color_side=(70,62,57),
        emissive=False, transparent=False, passthrough=False, no_mesh=False,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=3.5, best_tool='pick',
        drops=[(FURNACE_BLOCK,1,1.0)],
    ),
    SIGN_BLOCK: dict(
        name="Sign", tex="sign", tex_variants=False,
        color_top=(160,140,100), color_bot=(130,110,75), color_side=(145,125,88),
        emissive=False, transparent=True, passthrough=True, no_mesh=True,
        ray_ignore=False, ray_blocking=False,
        collideable=False, slow_fall=False, hardness=0.8, best_tool=None,
        drops=[(SIGN_BLOCK,1,1.0)],
    ),
    SKYSCREEN_BLOCK: dict(
        name="Sky Screen", tex="skyscreen", tex_variants=False,
        color_top=(30,40,80), color_bot=(20,30,60), color_side=(25,35,70),
        emissive=True, transparent=True, passthrough=False, no_mesh=True,
        ray_ignore=False, ray_blocking=False, nodraw=True,
        collideable=True, slow_fall=False, hardness=999.0, best_tool=None, drops=[],
    ),
    BED_BLOCK: dict(
        name="Bed", tex="bed_head", tex_variants=False,
        color_top=(140,40,40), color_bot=(100,30,30), color_side=(120,35,35),
        emissive=False, transparent=True, passthrough=False, no_mesh=True,
        ray_ignore=False, ray_blocking=False, nodraw=False,
        collideable=True, slow_fall=False, hardness=0.5, best_tool=None,
        drops=[(ITEM_WOOL,3,1.0)],
    ),
    BED_FOOT: dict(
        name="Bed (Foot)", tex="bed_foot", tex_variants=False,
        color_top=(140,40,40), color_bot=(100,30,30), color_side=(120,35,35),
        emissive=False, transparent=True, passthrough=False, no_mesh=True,
        ray_ignore=False, ray_blocking=False, nodraw=False,
        collideable=True, slow_fall=False, hardness=0.5, best_tool=None, drops=[],
    ),
    GLASS_DOOR: dict(
        name="Glass Door", tex="glass_door", tex_variants=False,
        color_top=(180,210,240), color_bot=(160,190,220), color_side=(170,200,230),
        emissive=False, transparent=True, passthrough=True, no_mesh=True,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=1.2, best_tool='pick',
        drops=[(GLASS_DOOR,1,1.0)],
    ),
    GLASS_DOOR_TOP: dict(
        name="Glass Door Top", tex="glass_door_top", tex_variants=False,
        color_top=(160,190,220), color_bot=(140,170,200), color_side=(150,180,210),
        emissive=False, transparent=True, passthrough=True, no_mesh=True,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=1.2, best_tool='pick', drops=[],
    ),
    CREDITS_BLOCK: dict(
        name="Credits", tex="credits", tex_variants=False,
        color_top=(0,40,0), color_bot=(0,30,0), color_side=(0,35,0),
        emissive=True, transparent=False, passthrough=False, no_mesh=False,
        ray_ignore=False, ray_blocking=False,
        collideable=True, slow_fall=False, hardness=999.0, best_tool=None, drops=[],
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
#  Build all lookup tables from BLOCK_DEFS
# ═══════════════════════════════════════════════════════════════════════════

BLOCK_NAMES = [BLOCK_DEFS[i]['name'] if i in BLOCK_DEFS else f"Block{i}"
               for i in range(NUM_BLOCKS)]

FACE_COLORS = np.zeros((NUM_BLOCKS, 3, 3), dtype=np.float32)
EMISSIVE    = np.zeros(NUM_BLOCKS, dtype=np.float32)
for _bid, _d in BLOCK_DEFS.items():
    FACE_COLORS[_bid, 0] = [v/255 for v in _d['color_top']]
    FACE_COLORS[_bid, 1] = [v/255 for v in _d['color_bot']]
    FACE_COLORS[_bid, 2] = [v/255 for v in _d['color_side']]
    EMISSIVE[_bid] = 0.35 if _d['emissive'] else 0.0

SHADE     = np.array([1.0, 0.55, 0.80, 0.80, 0.70, 0.70], dtype=np.float32)
FACE_TYPE = [0, 1, 2, 2, 2, 2]

BLOCK_TEX_NAMES = {
    _bid: (_d['tex'], _d['tex_variants'])
    for _bid, _d in BLOCK_DEFS.items()
    if _d['tex'] is not None
}

TRANSPARENT_SET = frozenset(_bid for _bid,_d in BLOCK_DEFS.items() if _d['transparent'])
PASSTHROUGH_SET = frozenset(_bid for _bid,_d in BLOCK_DEFS.items() if _d['passthrough'])
NO_MESH_SET     = frozenset(_bid for _bid,_d in BLOCK_DEFS.items() if _d['no_mesh'])
# Collision is based on passthrough only — transparent blocks (glass, doors) are still solid
NO_COLLIDE_SET  = PASSTHROUGH_SET
SOLID_SET       = frozenset(range(NUM_BLOCKS)) - PASSTHROUGH_SET - {AIR}
SLOW_FALL_SET   = frozenset(_bid for _bid,_d in BLOCK_DEFS.items() if _d['slow_fall'])
RAY_IGNORE_SET  = frozenset(_bid for _bid,_d in BLOCK_DEFS.items() if _d['ray_ignore'])
NODRAW_SET      = frozenset(_bid for _bid,_d in BLOCK_DEFS.items() if _d.get('nodraw', False))
HALF_BLOCK_SET  = frozenset({DOG_STATUE, CAT_STATUE})
NEEDS_FURNACE   = frozenset({GLASS_BLOCK})
BILLBOARD_BLOCKS = frozenset({WHEAT_STAGE0, WHEAT_STAGE1, WHEAT_STAGE2, WHEAT_STAGE3})

TRANSPARENT_ARR = np.zeros(NUM_BLOCKS, dtype=bool)
for _b in TRANSPARENT_SET | PASSTHROUGH_SET: TRANSPARENT_ARR[_b] = True

NO_MESH_ARR = np.zeros(NUM_BLOCKS, dtype=bool)
for _b in NO_MESH_SET: NO_MESH_ARR[_b] = True

BLOCK_HARDNESS = {_bid: _d['hardness'] for _bid, _d in BLOCK_DEFS.items()}

PICK_BLOCKS   = frozenset(_bid for _bid,_d in BLOCK_DEFS.items() if _d['best_tool']=='pick')
SHOVEL_BLOCKS = frozenset(_bid for _bid,_d in BLOCK_DEFS.items() if _d['best_tool']=='shovel')
AXE_BLOCKS    = frozenset(_bid for _bid,_d in BLOCK_DEFS.items() if _d['best_tool']=='axe')
SWORD_BLOCKS  = frozenset(_bid for _bid,_d in BLOCK_DEFS.items() if _d['best_tool']=='sword')
HOE_BLOCKS    = frozenset(_bid for _bid,_d in BLOCK_DEFS.items() if _d['best_tool']=='hoe')

TOOL_MULT = {
    ITEM_WOOD_PICK:    (PICK_BLOCKS,   3.0),
    ITEM_STONE_PICK:   (PICK_BLOCKS,   6.0),
    ITEM_WOOD_SHOVEL:  (SHOVEL_BLOCKS, 3.0),
    ITEM_STONE_SHOVEL: (SHOVEL_BLOCKS, 6.0),
    ITEM_WOOD_AXE:     (AXE_BLOCKS,    3.0),
    ITEM_STONE_AXE:    (AXE_BLOCKS,    6.0),
    ITEM_WOOD_SWORD:   (SWORD_BLOCKS,  4.0),
    ITEM_STONE_SWORD:  (SWORD_BLOCKS,  4.0),
    ITEM_HOE:          (HOE_BLOCKS,    2.0),
}

def get_mine_time(block_id, tool_id):
    base = BLOCK_HARDNESS.get(block_id, 1.0)
    if base == 0: return 0
    if tool_id in TOOL_MULT:
        blocks_set, mult = TOOL_MULT[tool_id]
        if block_id in blocks_set: return base / mult
    return base

def get_drops(block_id):
    result = []
    for item_id, count, chance in BLOCK_DEFS.get(block_id, {}).get('drops', []):
        if random.random() < chance:
            if isinstance(count, tuple):
                result.append((item_id, random.randint(count[0], count[1])))
            else:
                result.append((item_id, count))
    return result


# ── Crafting recipes ──────────────────────────────────────────────────────
RECIPES = {
    ITEM_STICK:        [(MORI_WOOD,   1)],
    WORKBENCH:         [(MORI_WOOD,   4)],
    ITEM_WOOD_SWORD:   [(MORI_WOOD,   2),(ITEM_STICK,1)],
    ITEM_WOOD_PICK:    [(MORI_WOOD,   3),(ITEM_STICK,2)],
    ITEM_WOOD_AXE:     [(MORI_WOOD,   3),(ITEM_STICK,2)],
    ITEM_WOOD_SHOVEL:  [(MORI_WOOD,   1),(ITEM_STICK,2)],
    ITEM_HOE:          [(MORI_WOOD,   2),(ITEM_STICK,2)],
    ITEM_STONE_SWORD:  [(KEIRO_STONE, 2),(ITEM_STICK,1)],
    ITEM_STONE_PICK:   [(KEIRO_STONE, 3),(ITEM_STICK,2)],
    ITEM_STONE_AXE:    [(KEIRO_STONE, 3),(ITEM_STICK,2)],
    ITEM_STONE_SHOVEL: [(KEIRO_STONE, 1),(ITEM_STICK,2)],
    ITEM_BREAD:        [(ITEM_WHEAT,  3)],
    GLASS_BLOCK:       [(KASUMI_ICE,  1)],
    DOOR_BLOCK:        [(MORI_WOOD,   3),(ITEM_STICK,2)],
    DOG_STATUE:        [(KEIRO_STONE, 4),(SHINEN_CRYSTAL,1)],
    CAT_STATUE:        [(KEIRO_STONE, 4),(SHINEN_EMBER,1)],
    FURNACE_BLOCK:     [(KEIRO_STONE, 8)],
    SIGN_BLOCK:        [(MORI_WOOD,   2),(ITEM_STICK,1)],
    BED_BLOCK:         [(ITEM_WOOL,   3),(MORI_WOOD,3)],
    # Tricksabre: 1 Memory Crystal + 2 Ember Ore + 1 Stick
    ITEM_TRICKSABRE:   [(SHINEN_CRYSTAL,1),(SHINEN_EMBER,2),(ITEM_STICK,1)],
    GLASS_DOOR:        [(GLASS_BLOCK,  4),(MORI_WOOD,2)],
}

FURNACE_RECIPES = {SAND_BLOCK: GLASS_BLOCK}

NEEDS_WORKBENCH = frozenset({
    ITEM_WOOD_SWORD, ITEM_WOOD_PICK, ITEM_WOOD_AXE, ITEM_WOOD_SHOVEL, ITEM_HOE,
    ITEM_STONE_SWORD, ITEM_STONE_PICK, ITEM_STONE_AXE, ITEM_STONE_SHOVEL,
    ITEM_BREAD, DOOR_BLOCK, DOG_STATUE, CAT_STATUE, FURNACE_BLOCK, SIGN_BLOCK,
    BED_BLOCK, ITEM_TRICKSABRE, GLASS_DOOR,
})

# ── Geometry constants ────────────────────────────────────────────────────
FACE_DIRS  = [(0,1,0),(0,-1,0),(0,0,1),(0,0,-1),(1,0,0),(-1,0,0)]
FACE_VERTS = [
    [(0,1,0),(1,1,0),(1,1,1),(0,1,1)],
    [(0,0,1),(1,0,1),(1,0,0),(0,0,0)],
    [(0,0,1),(1,0,1),(1,1,1),(0,1,1)],
    [(1,0,0),(0,0,0),(0,1,0),(1,1,0)],
    [(1,0,0),(1,0,1),(1,1,1),(1,1,0)],
    [(0,0,1),(0,0,0),(0,1,0),(0,1,1)],
]

# ── Item display helpers ──────────────────────────────────────────────────
def item_name(iid):
    if iid is None:      return "Empty"
    if iid < NUM_BLOCKS: return BLOCK_NAMES[iid]
    return ITEM_NAMES.get(iid, f"Item#{iid}")

def item_color(iid):
    if iid is None: return (60, 55, 80)
    if iid < NUM_BLOCKS:
        c = FACE_COLORS[iid, 0]
        return (int(c[0]*220), int(c[1]*220), int(c[2]*220))
    return ITEM_COLORS.get(iid, (150,150,150))

# Misc flags for backwards compatibility
DOOR_OPEN_SET:    set  = set()
SIGN_TEXTS:       dict = {}
SIGN_MAX_CHARS         = 40
SKYSCREEN_POSITIONS: set = set()