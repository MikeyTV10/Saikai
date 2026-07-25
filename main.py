"""
╔═══════════════════════════════════════════════════════════════╗
║                    S A I K A I                               ║
║              "The World That Remembers"                      ║
╚═══════════════════════════════════════════════════════════════╝
Controls:
  WASD       - Move          Space  - Jump
  Mouse      - Look          F      - Fly mode
  LClick     - Break block   Shift  - Sprint / Descend
  RClick     - Place block   Tab    - Debug info
  1-7/Scroll - Select block  Escape - Unlock / Quit

Requirements:  pip install pygame PyOpenGL PyOpenGL_accelerate numpy
"""

import sys, math, random, time, ctypes, os
import multiprocessing as mp
import queue
import numpy as np

try:
    import pygame
    from pygame.locals import *
except ImportError:
    sys.exit("ERROR: pip install pygame")

try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
except ImportError:
    sys.exit("ERROR: pip install PyOpenGL PyOpenGL_accelerate")

# ──────────────────────────────────────────────────────────────
#  CONSTANTS
# ──────────────────────────────────────────────────────────────
WINDOW_W, WINDOW_H = 1280, 720
FOV         = 70
RENDER_DIST = 4
CHUNK_S     = 16
CHUNK_H     = 64
GRAVITY     = -28.0
JUMP_SPEED  = 9.0
WALK_SPEED  = 5.5
SPRINT_MULT = 1.65
FLY_SPEED   = 12.0
MOUSE_SENS  = 0.15

# All block/item definitions live in blocks.py
from blocks import *
from blocks import (
    BLOCK_DEFS, BLOCK_NAMES, BLOCK_TEX_NAMES, FACE_COLORS, EMISSIVE,
    SHADE, FACE_TYPE, FACE_DIRS, FACE_VERTS,
    TRANSPARENT_SET, PASSTHROUGH_SET, NO_MESH_SET, NO_COLLIDE_SET,
    SOLID_SET, SLOW_FALL_SET, RAY_IGNORE_SET,
    TRANSPARENT_ARR, NO_MESH_ARR,
    BLOCK_HARDNESS, TOOL_MULT, get_mine_time, get_drops,
    PICK_BLOCKS, SHOVEL_BLOCKS, AXE_BLOCKS, SWORD_BLOCKS, HOE_BLOCKS,
    RECIPES, FURNACE_RECIPES, NEEDS_WORKBENCH, NEEDS_FURNACE,
    ITEM_NAMES, ITEM_COLORS, FOOD_HEAL, TOOLS, BILLBOARD_BLOCKS,
    HALF_BLOCK_SET, DOOR_OPEN_SET, SIGN_TEXTS, SIGN_MAX_CHARS,
    SKYSCREEN_POSITIONS, item_name, item_color,
    BED_BLOCK, BED_FOOT, ITEM_WOOL,
    GLASS_DOOR, GLASS_DOOR_TOP,
    NODRAW_SET,
    ITEM_TRICKSABRE, ITEM_TOOLTIPS,
)

# ──────────────────────────────────────────────────────────────
#  TEXTURE ATLAS  (GL — must live in main, not blocks.py)
# ──────────────────────────────────────────────────────────────
TILE         = 32   # pixel size of each tile in the atlas
UV_TABLE     = np.zeros((NUM_BLOCKS, 3, 4), dtype=np.float32)
ATLAS_TEX_ID = None

def build_atlas(tex_dir):
    """Load all block PNGs, pack into one GL texture atlas, fill UV_TABLE."""
    global ATLAS_TEX_ID
    from PIL import Image as PILImage

    atlas_w = NUM_BLOCKS * 3 * TILE
    atlas_h = TILE
    atlas   = PILImage.new("RGBA", (atlas_w, atlas_h), (0,0,0,0))

    for bid, (name, has_variants) in BLOCK_TEX_NAMES.items():
        path = os.path.join(tex_dir, f"{name}.png")
        if not os.path.exists(path):
            for ft in range(3):
                col     = FACE_COLORS[bid, ft]
                tile    = PILImage.new("RGBA", (TILE, TILE),
                              (int(col[0]*255), int(col[1]*255), int(col[2]*255), 255))
                col_idx = bid*3 + ft
                atlas.paste(tile, (col_idx*TILE, 0))
            continue
        src = PILImage.open(path).convert("RGBA")
        if src.size != (TILE, TILE):
            src = src.resize((TILE, TILE), PILImage.NEAREST)
        for ft in range(3):
            atlas.paste(src, ((bid*3 + ft)*TILE, 0))

    data   = atlas.tobytes("raw", "RGBA", 0, -1)
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, atlas_w, atlas_h, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, data)
    glBindTexture(GL_TEXTURE_2D, 0)
    ATLAS_TEX_ID = tex_id

    for bid in range(NUM_BLOCKS):
        for ft in range(3):
            col_idx       = bid*3 + ft
            u0            = col_idx       * TILE / atlas_w
            u1            = (col_idx + 1) * TILE / atlas_w
            UV_TABLE[bid, ft] = [u0, 0.0, u1, 1.0]

    print(f"Atlas built: {atlas_w}×{atlas_h}px, {len(BLOCK_TEX_NAMES)} blocks")

ITEM_GL_TEXTURES: dict = {}

def load_item_textures(tex_dir):
    """Load per-item PNG textures into individual GL textures for UI rendering."""
    from PIL import Image as PILImage
    mapping = {
        KEIRO_GRASS:"keiro_grass", KEIRO_SOIL:"keiro_soil", KEIRO_STONE:"keiro_stone",
        SHINEN_ROCK:"shinen_rock", SHINEN_CRYSTAL:"shinen_crystal", SHINEN_EMBER:"shinen_ember",
        KASUMI_SNOW:"kasumi_snow", KASUMI_ICE:"kasumi_ice", KASUMI_SHALE:"kasumi_shale",
        MORI_WOOD:"mori_wood", MORI_LEAVES:"mori_leaves", MORI_MOSS:"mori_moss",
        REIKI_WATER:"reiki_water", TAMASHII_LAVA:"tamashii_lava",
        CLOUD_BLOCK:"cloud", WORKBENCH:"workbench",
        ITEM_STICK:"stick", ITEM_WOOD_SWORD:"wood_sword", ITEM_STONE_SWORD:"stone_sword",
        ITEM_WOOD_PICK:"wood_pick", ITEM_STONE_PICK:"stone_pick",
        ITEM_WOOD_AXE:"wood_axe", ITEM_STONE_AXE:"stone_axe",
        ITEM_WOOD_SHOVEL:"wood_shovel", ITEM_STONE_SHOVEL:"stone_shovel",
        ITEM_BERRY:"berry", ITEM_BREAD:"bread",
        ITEM_HOE:"hoe", ITEM_WHEAT_SEEDS:"wheat_seeds",
        ITEM_WHEAT:"wheat_item", ITEM_APPLE:"apple",
        ITEM_COOKED_MEAT:"cooked_meat", ITEM_RAW_MEAT:"raw_meat",
        DOOR_BLOCK:"door", DOOR_TOP:"door_top", GLASS_DOOR:"glass_door", GLASS_DOOR_TOP:"glass_door_top",
        SAND_BLOCK:"sand", FURNACE_BLOCK:"furnace",
        GLASS_BLOCK:"glass",
        SIGN_BLOCK:"sign", SKYSCREEN_BLOCK:"skyscreen", CREDITS_BLOCK:"credits",
        BED_BLOCK:"bed_block", BED_FOOT:"bed_foot",
        ITEM_WOOL:"wool",
        ITEM_TRICKSABRE:"tricksabre",
    }
    for iid, fname in mapping.items():
        path = os.path.join(tex_dir, f"{fname}.png")
        if not os.path.exists(path): continue
        img  = PILImage.open(path).convert("RGBA")
        data = img.tobytes("raw", "RGBA", 0, -1)
        w, h = img.size
        tex  = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glBindTexture(GL_TEXTURE_2D, 0)
        ITEM_GL_TEXTURES[iid] = tex
    print(f"Loaded {len(ITEM_GL_TEXTURES)} item textures")

# ──────────────────────────────────────────────────────────────
#  NOISE
# ──────────────────────────────────────────────────────────────
class Noise:
    def __init__(self, seed):
        rng = random.Random(seed)
        p = list(range(256)); rng.shuffle(p)
        self.p = p * 2

    def _g(self, h, x, y):
        return (x+y, -x+y, x-y, -x-y)[h & 3]

    def n2(self, x, y):
        p = self.p
        xi,yi = int(x)&255, int(y)&255
        xf,yf = x-int(x), y-int(y)
        def f(t): return t*t*t*(t*(t*6-15)+10)
        def l(a,b,t): return a+t*(b-a)
        u,v = f(xf), f(yf)
        aa=p[p[xi]+yi]; ab=p[p[xi]+yi+1]
        ba=p[p[xi+1]+yi]; bb=p[p[xi+1]+yi+1]
        return (l(l(self._g(aa,xf,yf),   self._g(ba,xf-1,yf),  u),
                  l(self._g(ab,xf,yf-1), self._g(bb,xf-1,yf-1),u),v)+1)/2

    def oct(self, x, y, octs=4, pers=0.5, lac=2.0):
        v=mv=0.0; a=f=1.0
        for _ in range(octs):
            v+=self.n2(x*f,y*f)*a; mv+=a; a*=pers; f*=lac
        return v/mv


# ──────────────────────────────────────────────────────────────
#  WORLD GENERATOR
# ──────────────────────────────────────────────────────────────
class WorldGen:
    def __init__(self, seed=None):
        self.seed = seed or random.randint(1, 999999)
        self.version = WORLDGEN_VERSION
        self.hn = Noise(self.seed)
        self.bn = Noise(self.seed+1)
        self.cn = Noise(self.seed+2)
        self.dn = Noise(self.seed+3)
        self._sc = {}

    def biome(self, wx, wz):
        b  = self.bn.oct(wx*0.004, wz*0.004, octs=3)
        b2 = self.bn.oct(wx*0.002+500, wz*0.002+500, octs=2)
        if b < 0.28:              return "kasumi"
        if b < 0.45 and b2>0.55: return "shinen"
        if b < 0.55:              return "keiro"
        if b < 0.72:              return "mori"
        return                           "reiki"

    def surface(self, wx, wz):
        k = (wx,wz)
        if k in self._sc: return self._sc[k]
        bio = self.biome(wx,wz)
        h   = self.hn.oct(wx*0.007, wz*0.007, octs=4, pers=0.50)
        if   bio=="kasumi": base = 36 + h*20
        elif bio=="shinen": base = 30 + h*10
        elif bio=="mori":   base = 28 + h*8
        elif bio=="reiki":  base = 22 + h*5
        else:               base = 26 + h*8
        v = max(4, min(int(base), CHUNK_H-8))
        self._sc[k] = v
        return v

    def _place_vein(self, blocks, lx, ly, lz, ore, size, rng):
        """Carve a small blob of ore blocks around a seed position."""
        for _ in range(size):
            ox=lx+rng.randint(-1,1); oy=ly+rng.randint(-1,1); oz=lz+rng.randint(-1,1)
            if 0<=ox<CHUNK_S and 1<=oy<CHUNK_H-1 and 0<=oz<CHUNK_S:
                if blocks[ox,oy,oz] in (SHINEN_ROCK, KEIRO_STONE):
                    blocks[ox,oy,oz]=ore

    def generate(self, cx, cz):
        blocks = np.zeros((CHUNK_S, CHUNK_H, CHUNK_S), dtype=np.uint8)
        wx0,wz0 = cx*CHUNK_S, cz*CHUNK_S

        for lx in range(CHUNK_S):
            for lz in range(CHUNK_S):
                wx,wz = wx0+lx, wz0+lz
                bio   = self.biome(wx,wz)
                surf  = self.surface(wx,wz)
                blocks[lx,0,lz] = KEIRO_STONE
                if CHUNK_H > 3: blocks[lx,1:4,lz] = SHINEN_ROCK

                for ly in range(4, CHUNK_H):
                    if ly > surf:
                        if ly <= 6: blocks[lx,ly,lz] = REIKI_WATER
                        continue
                    if ly < surf-4:
                        cv = self.cn.oct(wx*0.06, ly*0.06+wz*0.04, octs=3)
                        if cv > 0.72: continue
                        blocks[lx,ly,lz]=SHINEN_ROCK if ly<15 else KEIRO_STONE
                    elif ly < surf-1:
                        if bio in ("kasumi","shinen"): blocks[lx,ly,lz]=KASUMI_SHALE
                        else: blocks[lx,ly,lz]=KEIRO_SOIL
                    elif ly == surf-1:
                        if bio in ("kasumi","shinen"): blocks[lx,ly,lz]=KASUMI_SHALE
                        else: blocks[lx,ly,lz]=KEIRO_SOIL
                    else:
                        if   bio=="kasumi": blocks[lx,ly,lz]=KASUMI_SNOW if surf>44 else KASUMI_SHALE
                        elif bio=="shinen": blocks[lx,ly,lz]=SHINEN_ROCK
                        elif bio=="mori":   blocks[lx,ly,lz]=MORI_MOSS
                        elif bio=="reiki":  blocks[lx,ly,lz]=REIKI_WATER if surf<=7 else MORI_MOSS
                        else:               blocks[lx,ly,lz]=KEIRO_GRASS

        # ── Ore vein seeding ──────────────────────────────────────────
        ore_rng = random.Random(wx0 * 92083 + wz0 * 17491 + self.seed)
        ore_table = [
            (SHINEN_CRYSTAL, 1, (2, 4),  18,  4),
            (SHINEN_EMBER,   1, (2, 3),  10,  4),
        ]
        for ore_id, max_veins, (sz_lo, sz_hi), max_y, min_y in ore_table:
            n_veins = ore_rng.randint(0, max_veins)
            for _ in range(n_veins):
                vx = ore_rng.randint(0, CHUNK_S-1)
                vz = ore_rng.randint(0, CHUNK_S-1)
                vy = ore_rng.randint(min_y, max_y)
                vsize = ore_rng.randint(sz_lo, sz_hi)
                self._place_vein(blocks, vx, vy, vz, ore_id, vsize, ore_rng)

        rng = random.Random(wx0*31337+wz0)
        centre_bio = self.biome(wx0+8,wz0+8)
        n_trees = 4 if centre_bio=="mori" else (1 if centre_bio=="keiro" else 0)
        for _ in range(n_trees):
            tx,tz=rng.randint(2,CHUNK_S-3),rng.randint(2,CHUNK_S-3)
            ts=self.surface(wx0+tx,wz0+tz)
            if ts<8 or ts>=CHUNK_H-12: continue
            if int(blocks[tx,ts,tz]) not in (KEIRO_GRASS,MORI_MOSS,KEIRO_SOIL): continue
            th=rng.randint(4,7)
            for h in range(1,th+1):
                if ts+h<CHUNK_H: blocks[tx,ts+h,tz]=MORI_WOOD
            lh=ts+th
            for dy in range(-2,3):
                for dx in range(-2,3):
                    for dz2 in range(-2,3):
                        nx2,ny2,nz2=tx+dx,lh+dy,tz+dz2
                        if (0<=nx2<CHUNK_S and 0<=ny2<CHUNK_H and 0<=nz2<CHUNK_S
                                and abs(dx)+abs(dy)+abs(dz2)<=3 and rng.random()>0.25
                                and blocks[nx2,ny2,nz2]==AIR):
                            blocks[nx2,ny2,nz2]=MORI_LEAVES
        # ── Sand patches near water (reiki biome) ──
        if centre_bio == "reiki":
            sand_rng = random.Random(wx0*54321 + wz0*12345 + self.seed + 7)
            for _ in range(3):
                sx2=sand_rng.randint(0,CHUNK_S-1); sz2=sand_rng.randint(0,CHUNK_S-1)
                ss=self.surface(wx0+sx2,wz0+sz2)
                if ss<=8:
                    for dy in range(-1,2):
                        for ddx in range(-2,3):
                            for ddz in range(-2,3):
                                nx2,ny2,nz2=sx2+ddx,ss+dy,sz2+ddz
                                if (0<=nx2<CHUNK_S and 1<=ny2<CHUNK_H-1 and 0<=nz2<CHUNK_S
                                        and blocks[nx2,ny2,nz2] in (KEIRO_GRASS,KEIRO_SOIL)):
                                    blocks[nx2,ny2,nz2]=SAND_BLOCK
        # ── Bush generation (mori biome / anywhere with BUSH_LEAVES) ──
        n_bushes = 3 if centre_bio=="mori" else (1 if centre_bio in ("keiro","reiki") else 0)
        for _ in range(n_bushes):
            bx2=rng.randint(1,CHUNK_S-2); bz2=rng.randint(1,CHUNK_S-2)
            bs=self.surface(wx0+bx2,wz0+bz2)
            if bs<6 or bs>=CHUNK_H-4: continue
            if int(blocks[bx2,bs,bz2]) not in (KEIRO_GRASS,MORI_MOSS): continue
            for dy in (0,1):
                for ddx in range(-1,2):
                    for ddz in range(-1,2):
                        nx2,ny2,nz2=bx2+ddx,bs+dy,bz2+ddz
                        if (0<=nx2<CHUNK_S and 0<=ny2<CHUNK_H and 0<=nz2<CHUNK_S
                                and rng.random()>0.3 and blocks[nx2,ny2,nz2]==AIR):
                            blocks[nx2,ny2,nz2]=BUSH_LEAVES

        return blocks


# ──────────────────────────────────────────────────────────────
#  CHUNK
# ──────────────────────────────────────────────────────────────
class Chunk:
    __slots__ = ('cx','cz','blocks','vbo','vert_count','dirty','_billboard_cache')

    def __init__(self, cx, cz, blocks):
        self.cx,self.cz = cx,cz
        self.blocks     = blocks
        self.vbo        = None
        self.vert_count = 0
        self.dirty      = True
        self._billboard_cache = None   # rebuilt when dirty

    def _build_verts(self, world):
        verts = []
        WX,WZ = self.cx*CHUNK_S, self.cz*CHUNK_S

        padded = np.zeros((CHUNK_S+2, CHUNK_H+2, CHUNK_S+2), dtype=np.uint8)
        padded[1:-1,1:-1,1:-1] = self.blocks

        for dcx,dcz in ((-1,0),(1,0),(0,-1),(0,1)):
            nk=(self.cx+dcx, self.cz+dcz)
            if nk not in world.chunks: continue
            nb=world.chunks[nk].blocks
            if dcx==-1:   padded[0,      1:-1, 1:-1] = nb[-1,:,:]
            elif dcx==1:  padded[-1,     1:-1, 1:-1] = nb[0,:,:]
            elif dcz==-1: padded[1:-1, 1:-1, 0     ] = nb[:,:,-1]
            elif dcz==1:  padded[1:-1, 1:-1, -1    ] = nb[:,:,0]

        for fi,(dx,dy,dz) in enumerate(FACE_DIRS):
            s_self  = padded[1:-1,   1:-1,   1:-1  ]
            s_neigh = padded[1+dx:CHUNK_S+1+dx,
                             1+dy:CHUNK_H+1+dy,
                             1+dz:CHUNK_S+1+dz]

            # Don't draw water faces adjacent to other water (removes internal walls)
            water_self  = (s_self  == REIKI_WATER)
            water_neigh = (s_neigh == REIKI_WATER)
            # Don't draw glass faces adjacent to other glass (merges panes)
            glass_self  = (s_self  == GLASS_BLOCK)
            glass_neigh = (s_neigh == GLASS_BLOCK)
            visible = (s_self != AIR) & ~NO_MESH_ARR[s_self] & TRANSPARENT_ARR[s_neigh] & ~(water_self & water_neigh) & ~(glass_self & glass_neigh)
            xs,ys,zs = np.where(visible)
            if xs.size == 0: continue

            bids = s_self[xs,ys,zs]
            ft   = FACE_TYPE[fi]
            em   = EMISSIVE[bids]
            sh   = np.clip(SHADE[fi] + em, 0, 1).astype(np.float32)

            uv  = UV_TABLE[bids, ft]
            u0,v0_,u1,v1_ = uv[:,0],uv[:,1],uv[:,2],uv[:,3]

            ox=(WX+xs).astype(np.float32)
            oy=ys.astype(np.float32)
            oz=(WZ+zs).astype(np.float32)

            fv = FACE_VERTS[fi]
            uv_corners = [(u0,v1_),(u1,v1_),(u1,v0_),(u0,v0_)]

            qv=[]
            for vi,voff in enumerate(fv):
                uc,vc = uv_corners[vi]
                qv.append(np.column_stack([
                    ox+voff[0], oy+voff[1], oz+voff[2],
                    uc, vc,
                    sh, sh, sh
                ]))

            N=xs.size
            idx=np.empty(N*6, dtype=np.int64)
            idx[0::6]=np.arange(N);       idx[1::6]=np.arange(N)+N
            idx[2::6]=np.arange(N)+N*2;   idx[3::6]=np.arange(N)
            idx[4::6]=np.arange(N)+N*2;   idx[5::6]=np.arange(N)+N*3
            verts.append(np.vstack(qv)[idx])

        if not verts:
            return np.empty((0,8), dtype=np.float32)
        return np.vstack(verts).astype(np.float32)

    def build_mesh(self, world):
        if not np.any(self.blocks):
            self.dirty = False
            self._billboard_cache = None
            return
        data = self._build_verts(world)
        if self.vbo is None:
            self.vbo = glGenBuffers(1)
        self.vert_count = data.shape[0]
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, data.nbytes, data, GL_DYNAMIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        self.dirty = False
        self._billboard_cache = None   # force rebuild next draw

    def get_billboard_positions(self, block_set):
        """Return cached list of (lx, ly, lz, bid) for blocks in block_set."""
        if self._billboard_cache is None:
            self._billboard_cache = {}
        key = frozenset(block_set)
        if key not in self._billboard_cache:
            idxs = np.argwhere(np.isin(self.blocks, list(block_set)))
            self._billboard_cache[key] = [(int(x),int(y),int(z), int(self.blocks[x,y,z]))
                                          for x,y,z in idxs]
        return self._billboard_cache[key]


    def render(self):
        if self.vbo is None or self.vert_count == 0: return
        stride = 32
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        glVertexPointer  (3, GL_FLOAT, stride, ctypes.c_void_p(0))
        glTexCoordPointer(2, GL_FLOAT, stride, ctypes.c_void_p(12))
        glColorPointer   (3, GL_FLOAT, stride, ctypes.c_void_p(20))

        if ATLAS_TEX_ID is not None:
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, ATLAS_TEX_ID)
            glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDrawArrays(GL_TRIANGLES, 0, self.vert_count)
        glDisable(GL_BLEND)

        if ATLAS_TEX_ID is not None:
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)

        glDisableClientState(GL_COLOR_ARRAY)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def cleanup(self):
        if self.vbo is not None:
            glDeleteBuffers(1, [self.vbo])
            self.vbo = None


# ──────────────────────────────────────────────────────────────
#  CHUNK GENERATION WORKER
# ──────────────────────────────────────────────────────────────
def _gen_chunk_worker(args):
    """Runs in a separate process — pure data, no GL."""
    seed, cx, cz = args
    gen = WorldGen(seed)
    blocks = gen.generate(cx, cz)
    return (cx, cz, blocks)


# ──────────────────────────────────────────────────────────────
#  WORLD
# ──────────────────────────────────────────────────────────────
class World:
    def __init__(self, seed=None):
        self.gen    = WorldGen(seed)
        self.chunks = {}
        self.seed   = self.gen.seed
        self.save_slot = None   # set by main loop when a save is active

        n_workers   = max(1, mp.cpu_count() - 1)
        self._pool  = mp.Pool(processes=n_workers)
        self._pending = {}
        print(f"Chunk workers: {n_workers} processes")

    def _chunk_path(self, cx, cz):
        """Absolute path for this chunk's .npy file, or None if no save slot active."""
        if not self.save_slot:
            return None
        return os.path.join(_save_dir(self.save_slot), f"c_{cx}_{cz}.npy")

    def _save_chunk(self, cx, cz, chunk):
        """Write a single chunk's blocks to disk immediately."""
        path = self._chunk_path(cx, cz)
        if path is None:
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        np.save(path, chunk.blocks)

    def _load_chunk_from_disk(self, cx, cz):
        """Try to load a chunk from disk. Returns Chunk or None."""
        path = self._chunk_path(cx, cz)
        if path is None or not os.path.exists(path):
            return None
        try:
            blocks = np.load(path)
            return Chunk(cx, cz, blocks)
        except Exception:
            return None

    def chunk_key(self, wx, wz):
        return (int(math.floor(wx/CHUNK_S)), int(math.floor(wz/CHUNK_S)))

    def get_or_gen(self, cx, cz):
        k=(cx,cz)
        if k not in self.chunks:
            # Prefer saved data over fresh generation
            saved = self._load_chunk_from_disk(cx, cz)
            if saved is not None:
                self.chunks[k] = saved
            else:
                self.chunks[k] = Chunk(cx,cz,self.gen.generate(cx,cz))
            for dcx,dcz in ((-1,0),(1,0),(0,-1),(0,1)):
                nk=(cx+dcx,cz+dcz)
                if nk in self.chunks:
                    self.chunks[nk].dirty=True
        return self.chunks[k]

    def pump_ready(self):
        done = [k for k,r in self._pending.items() if r.ready()]
        for k in done:
            result = self._pending.pop(k)
            try:
                cx,cz,blocks = result.get(timeout=0)
                if k not in self.chunks:
                    # Check disk first — player may have saved data for this chunk
                    saved = self._load_chunk_from_disk(cx, cz)
                    self.chunks[k] = saved if saved is not None else Chunk(cx,cz,blocks)
                    for dcx,dcz in ((-1,0),(1,0),(0,-1),(0,1)):
                        nk=(cx+dcx,cz+dcz)
                        if nk in self.chunks:
                            self.chunks[nk].dirty=True
            except Exception:
                pass

    def get_block(self, wx, wy, wz):
        if wy<0 or wy>=CHUNK_H: return AIR
        k=self.chunk_key(wx,wz)
        if k not in self.chunks: return AIR
        return int(self.chunks[k].blocks[int(wx)%CHUNK_S, int(wy), int(wz)%CHUNK_S])

    def set_block(self, wx, wy, wz, bid):
        if wy<0 or wy>=CHUNK_H: return
        cx,cz=self.chunk_key(wx,wz)
        k=(cx,cz)
        if k not in self.chunks: return
        lx,lz=int(wx)%CHUNK_S, int(wz)%CHUNK_S
        self.chunks[k].blocks[lx,int(wy),lz]=bid
        self.chunks[k].dirty=True
        self.chunks[k]._billboard_cache = None
        if lx==0         and (cx-1,cz) in self.chunks: self.chunks[(cx-1,cz)].dirty=True
        if lx==CHUNK_S-1 and (cx+1,cz) in self.chunks: self.chunks[(cx+1,cz)].dirty=True
        if lz==0         and (cx,cz-1) in self.chunks: self.chunks[(cx,cz-1)].dirty=True
        if lz==CHUNK_S-1 and (cx,cz+1) in self.chunks: self.chunks[(cx,cz+1)].dirty=True

    def load_around(self, px, pz):
        cx,cz=self.chunk_key(px,pz)
        needed={(cx+dx,cz+dz)
                for dx in range(-RENDER_DIST,RENDER_DIST+1)
                for dz in range(-RENDER_DIST,RENDER_DIST+1)}

        missing=sorted(
            [k for k in needed if k not in self.chunks and k not in self._pending],
            key=lambda k:(k[0]-cx)**2+(k[1]-cz)**2)
        for k in missing[:6]:
            r = self._pool.apply_async(_gen_chunk_worker, ((self.seed, k[0], k[1]),))
            self._pending[k] = r

        for k in [k for k in list(self.chunks)
                  if k not in needed
                  and (abs(k[0]-cx)>RENDER_DIST+2 or abs(k[1]-cz)>RENDER_DIST+2)]:
            # Persist to disk before evicting so player edits are never lost
            self._save_chunk(k[0], k[1], self.chunks[k])
            self.chunks[k].cleanup(); del self.chunks[k]

    def rebuild_dirty(self, px, pz):
        cx,cz=self.chunk_key(px,pz)
        dirty=sorted(
            [c for c in self.chunks.values()
             if c.dirty and abs(c.cx-cx)<=RENDER_DIST and abs(c.cz-cz)<=RENDER_DIST],
            key=lambda c:(c.cx-cx)**2+(c.cz-cz)**2)
        if dirty:
            dirty[0].build_mesh(self)

    def render(self, px, pz):
        cx,cz=self.chunk_key(px,pz)
        for (ccx,ccz),chunk in self.chunks.items():
            if abs(ccx-cx)<=RENDER_DIST and abs(ccz-cz)<=RENDER_DIST:
                chunk.render()

    def shutdown(self):
        self._pool.terminate()
        self._pool.join()


# ──────────────────────────────────────────────────────────────
#  PLAYER
# ──────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────
#  SAVE / LOAD  (JSON metadata + per-chunk .npy files)
# ──────────────────────────────────────────────────────────────
import json, glob

SAVES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saves")

def _save_dir(slot_name):
    return os.path.join(SAVES_DIR, slot_name)

def list_saves():
    """Return list of save-slot dicts sorted newest-first, or [] if none."""
    if not os.path.isdir(SAVES_DIR): return []
    slots = []
    for meta_path in glob.glob(os.path.join(SAVES_DIR, "*", "meta.json")):
        try:
            with open(meta_path) as f: m = json.load(f)
            slots.append(m)
        except Exception: pass
    slots.sort(key=lambda m: m.get("saved_at", 0), reverse=True)
    return slots

def save_game(slot_name, world, player, tod, farming=None, doors=None, beds=None):
    """Write all dirty + loaded chunks and player state to disk."""
    sdir = _save_dir(slot_name)
    os.makedirs(sdir, exist_ok=True)

    # Player + world metadata
    farming_state = farming.get_state() if farming else {}
    meta = {
        "slot":        slot_name,
        "seed":        world.seed,
        "tod":         tod,
        "saved_at":    time.time(),
        "gamemode":    player.gamemode,
        "worldgen_ver": WORLDGEN_VERSION,
        "px": player.x, "py": player.y, "pz": player.z,
        "yaw": player.yaw, "pitch": player.pitch,
        "health":   player.health,
        "hotbar":   player.hotbar,
        "inv":      {str(k): v for k, v in player.inv.items() if k is not None},
        "selected": player.selected,
        "farming":  farming_state,
        "doors":    doors.get_state() if doors else {},
        "beds":     beds.get_state()  if beds  else {},
        "sign_texts": {f"{k[0]},{k[1]},{k[2]}": v for k, v in SIGN_TEXTS.items()},
    }
    with open(os.path.join(sdir, "meta.json"), "w") as f:
        json.dump(meta, f)

    # Chunks — one .npy file per chunk key
    for (cx, cz), chunk in world.chunks.items():
        np.save(os.path.join(sdir, f"c_{cx}_{cz}.npy"), chunk.blocks)

    print(f"Saved '{slot_name}': {len(world.chunks)} chunks")

def load_game(slot_name, world):
    """
    Load chunk files for slot_name into world.chunks (does NOT create a new World).
    Returns meta dict, or None on failure.
    """
    sdir = _save_dir(slot_name)
    meta_path = os.path.join(sdir, "meta.json")
    if not os.path.exists(meta_path): return None
    try:
        with open(meta_path) as f: meta = json.load(f)
    except Exception: return None

    # Load saved chunks
    loaded = 0
    for path in glob.glob(os.path.join(sdir, "c_*.npy")):
        fname = os.path.basename(path)[2:-4]  # strip "c_" and ".npy"
        parts = fname.split("_")
        if len(parts) != 2: continue
        try:
            cx, cz = int(parts[0]), int(parts[1])
            blocks = np.load(path)
            world.chunks[(cx, cz)] = Chunk(cx, cz, blocks)
            loaded += 1
        except Exception: pass

    print(f"Loaded '{slot_name}': {loaded} chunks")
    return meta

def apply_meta_to_player(meta, player, farming=None, doors=None, beds=None, world=None):
    """Restore player state from a loaded meta dict."""
    player.x = meta.get("px", player.x)
    player.y = meta.get("py", player.y)
    player.z = meta.get("pz", player.z)
    player.yaw   = meta.get("yaw", 0)
    player.pitch = meta.get("pitch", 0)
    player.health   = meta.get("health", player.max_health)
    player.selected = meta.get("selected", 0)
    player.hotbar   = meta.get("hotbar", [None]*9)
    player.inv      = {int(k): v for k, v in meta.get("inv", {}).items() if k is not None and str(k).lstrip('-').isdigit()}
    if farming and "farming" in meta:
        farming.set_state(meta["farming"])
    if doors and "doors" in meta:
        doors.set_state(meta["doors"])
    if beds and world and "beds" in meta:
        beds.set_state(meta["beds"], world)
    if "sign_texts" in meta:
        SIGN_TEXTS.clear()
        for ks, v in meta["sign_texts"].items():
            parts = ks.split(',')
            if len(parts) == 3:
                SIGN_TEXTS[(int(parts[0]), int(parts[1]), int(parts[2]))] = v

def check_worldgen_compat(meta):
    """
    Compare saved worldgen version to current.
    If different, we keep existing chunk files but mark them dirty so
    new chunks generated around borders use updated gen.
    Returns a warning string or None.
    """
    saved_ver = meta.get("worldgen_ver", 1)
    if saved_ver != WORLDGEN_VERSION:
        return (f"Save was created with worldgen v{saved_ver}, current is v{WORLDGEN_VERSION}. "
                f"Existing chunks are preserved. New chunks will use updated generation.")
    return None

GAMEMODE_SURVIVAL = "survival"
GAMEMODE_BUILDING = "building"
GAMEMODE_MUSEUM   = "museum"    # survival look, no damage, no entities, no break/place

class Player:
    def __init__(self, x, y, z, gamemode=GAMEMODE_SURVIVAL):
        self.x=float(x); self.y=float(y); self.z=float(z)
        self.vx=self.vy=self.vz=0.0
        self.yaw=self.pitch=0.0
        self.on_ground=self.flying=False
        self._doors=None   # set each frame by update()
        self.width=0.6; self.height=1.8
        self.gamemode=gamemode

        self.hotbar=[None]*9
        self.selected=0
        self.inv={}

        if gamemode==GAMEMODE_BUILDING:
            defaults=[KEIRO_GRASS,KEIRO_SOIL,KEIRO_STONE,
                      MORI_WOOD,MORI_LEAVES,SHINEN_CRYSTAL,KASUMI_SNOW,None,None]
            self.hotbar=defaults[:]
            self.flying=True

        self.max_health=20
        self.health=20
        self.hurt_timer=0.0
        self.fall_speed=0.0

    def selected_block(self):
        return self.hotbar[self.selected]

    def add_to_inv(self, bid, count=1):
        self.inv[bid]=self.inv.get(bid,0)+count

    def remove_from_inv(self, bid, count=1):
        if self.inv.get(bid,0)>=count:
            self.inv[bid]-=count
            if self.inv[bid]<=0: del self.inv[bid]
            return True
        return False

    def can_place(self, bid):
        if self.gamemode==GAMEMODE_BUILDING: return True
        return self.inv.get(bid,0)>0

    def on_place(self, bid):
        if self.gamemode==GAMEMODE_SURVIVAL:
            self.remove_from_inv(bid)
            self._sync_hotbar()

    def on_break(self, bid):
        if self.gamemode == GAMEMODE_SURVIVAL and bid != AIR:
            for item_id, count in get_drops(bid):
                self.add_to_inv(item_id, count)
            self._sync_hotbar()

    def _sync_hotbar(self):
        for i,b in enumerate(self.hotbar):
            if b is not None and self.inv.get(b,0)<=0:
                self.hotbar[i]=None

    def look_dir(self):
        yr=math.radians(-self.yaw); pr=math.radians(self.pitch); cp=math.cos(pr)
        return math.sin(yr)*cp, math.sin(pr), -math.cos(yr)*cp

    def raycast(self, world, dist=6.0, steps=120, doors=None):
        """
        Cast a ray and return (hit_block, prev_block).
        Also detects thin door panels via DoorManager AABB test.
        Returns hit block coords and the face-before block.
        For door hits, the returned block coords are the door anchor (DOOR_BLOCK / GLASS_DOOR).
        """
        dx,dy,dz=self.look_dir()
        ex,ey,ez=self.x, self.y+self.height*0.85, self.z
        step=dist/steps; px,py,pz=ex,ey,ez
        for _ in range(steps):
            ex+=dx*step; ey+=dy*step; ez+=dz*step
            bx,by,bz=int(math.floor(ex)),int(math.floor(ey)),int(math.floor(ez))
            bl=world.get_block(bx,by,bz)
            if bl in (DOOR_BLOCK, DOOR_TOP, GLASS_DOOR, GLASS_DOOR_TOP):
                return (bx,by,bz),(int(math.floor(px)),int(math.floor(py)),int(math.floor(pz)))
            if bl not in RAY_IGNORE_SET:
                return (bx,by,bz),(int(math.floor(px)),int(math.floor(py)),int(math.floor(pz)))
            px,py,pz=ex,ey,ez
        return None,None

    def _touching_any(self, world, block_set):
        hw=self.width/2
        for bx in (self.x-hw, self.x+hw):
            for by in (self.y+0.1, self.y+0.9):
                for bz in (self.z-hw, self.z+hw):
                    if world.get_block(int(math.floor(bx)),
                                       int(math.floor(by)),
                                       int(math.floor(bz))) in block_set:
                        return True
        return False

    def use_item(self, iid):
        if iid in FOOD_HEAL and self.gamemode==GAMEMODE_SURVIVAL:
            if self.inv.get(iid,0)>0:
                self.health=min(self.max_health, self.health+FOOD_HEAL[iid])
                self.remove_from_inv(iid)
                self._sync_hotbar()
                return True
        return False

    def craft(self, output_id, at_workbench=False, at_furnace=False):
        if output_id not in RECIPES: return False
        if output_id in NEEDS_FURNACE and not at_furnace: return False
        if output_id in NEEDS_WORKBENCH and not at_workbench: return False
        recipe=RECIPES[output_id]
        for ing,cnt in recipe:
            if self.inv.get(ing,0)<cnt: return False
        for ing,cnt in recipe:
            self.remove_from_inv(ing,cnt)
        self.add_to_inv(output_id)
        self._sync_hotbar()
        return True

    def _collide(self, world, axis, delta):
        nx=self.x+(delta if axis==0 else 0)
        ny=self.y+(delta if axis==1 else 0)
        nz=self.z+(delta if axis==2 else 0)
        hw=self.width/2
        for cx2 in (nx-hw,nx+hw):
            for cy in (ny,ny+0.9,ny+self.height-0.01):
                for cz2 in (nz-hw,nz+hw):
                    if world.get_block(int(math.floor(cx2)),
                                       int(math.floor(cy)),
                                       int(math.floor(cz2))) in SOLID_SET:
                        if axis==1:
                            if delta<0: self.on_ground=True
                            self.vy=0
                        elif axis==0: self.vx=0
                        else:         self.vz=0
                        return 0.0
        # Door collision (horizontal only)
        if axis != 1 and self._doors:
            if self._doors.blocks_axis(axis, nx, ny, nz, hw, self.height - 0.01):
                if axis==0: self.vx=0
                else:       self.vz=0
                return 0.0
        return delta

    def update(self, world, dt, keys, mdx, mdy, doors=None):
        self._doors = doors  # stash for _collide
        self.yaw  =(self.yaw - mdx*MOUSE_SENS)%360
        self.pitch=max(-89,min(89, self.pitch - mdy*MOUSE_SENS))

        yr=math.radians(-self.yaw)
        fx,fz=math.sin(yr),-math.cos(yr)
        rx,rz=math.cos(yr), math.sin(yr)

        mx=mz=0.0
        if keys[K_w]: mx+=fx; mz+=fz
        if keys[K_s]: mx-=fx; mz-=fz
        if keys[K_a]: mx-=rx; mz-=rz
        if keys[K_d]: mx+=rx; mz+=rz

        spd=(FLY_SPEED if self.flying else
             WALK_SPEED*(SPRINT_MULT if keys[K_LSHIFT] and not self.flying else 1.0))
        ln=math.sqrt(mx*mx+mz*mz)
        if ln>0: mx/=ln; mz/=ln

        prev_vy=self.vy
        if self.flying:
            self.vx=mx*spd; self.vz=mz*spd
            self.vy=(FLY_SPEED if keys[K_SPACE] else
                     -FLY_SPEED if keys[K_LSHIFT] else self.vy*0.75)
        else:
            self.vx=mx*spd; self.vz=mz*spd
            self.vy=max(self.vy+GRAVITY*dt,-50)
            in_slow = self._touching_any(world, SLOW_FALL_SET)
            if in_slow:
                # Buoyancy: push upward slowly, cap fall speed
                self.vy = self.vy + 18.0 * dt   # counteract most of gravity
                self.vy = max(self.vy, -2.0)    # slow sink
                self.vy = min(self.vy,  3.5)    # cap rise
                self.vy *= (1.0 - 3.0*dt)       # dampen
                if keys[K_SPACE]:               # hold space = swim up faster
                    self.vy = min(self.vy + 14.0*dt, 4.5)

        was_on_ground=self.on_ground
        self.on_ground=False
        self.x+=self._collide(world,0,self.vx*dt)
        self.y+=self._collide(world,1,self.vy*dt)
        self.z+=self._collide(world,2,self.vz*dt)

        if self.gamemode==GAMEMODE_SURVIVAL:
            if self.on_ground and not was_on_ground and prev_vy < -18:
                if not self._touching_any(world, SLOW_FALL_SET):
                    dmg = int((-prev_vy - 18) / 3)
                    self.take_damage(dmg)
            if self.hurt_timer>0: self.hurt_timer-=dt

        if self.y<-10 and self.gamemode==GAMEMODE_SURVIVAL:
            self.take_damage(4*dt)

    def take_damage(self, amount):
        if self.gamemode==GAMEMODE_BUILDING: return
        if self.hurt_timer>0: return
        self.health=max(0, self.health-amount)
        self.hurt_timer=0.5

    def jump(self):
        if self.on_ground and not self.flying:
            self.vy=JUMP_SPEED; self.on_ground=False


# Entities (mobs, animals, farming) live in entities.py
import entity
from entity import (
    _entity_move, _entity_spawn_safe,
    ENTITY_TEXTURES, ENTITY_OBJ_MODELS, load_entity_textures, load_entity_models, draw_entity_box,
    Enemy, EnemyManager,
    FarmingManager, WHEAT_STAGES, WHEAT_GROW_TIME,
    Animal, AnimalManager,
)
# Pass all required constants into entities so it doesn't need to import main
entity.init(
    solid_set=SOLID_SET, render_dist=RENDER_DIST, chunk_s=CHUNK_S,
    gravity=GRAVITY, jump_speed=JUMP_SPEED,
    gamemode_survival=GAMEMODE_SURVIVAL,
    air=AIR, keiro_grass=KEIRO_GRASS, keiro_soil=KEIRO_SOIL,
    mori_moss=MORI_MOSS, farmland=FARMLAND,
    wheat_stage0=WHEAT_STAGE0, wheat_stage1=WHEAT_STAGE1,
    wheat_stage2=WHEAT_STAGE2, wheat_stage3=WHEAT_STAGE3,
    item_wood_sword=ITEM_WOOD_SWORD, item_stone_sword=ITEM_STONE_SWORD,
    item_wheat=ITEM_WHEAT, item_wheat_seeds=ITEM_WHEAT_SEEDS,
    item_raw_meat=ITEM_RAW_MEAT,
    item_wool=ITEM_WOOL,
    item_tricksabre=ITEM_TRICKSABRE,
)

# ──────────────────────────────────────────────────────────────
#  DOOR MANAGER
# ──────────────────────────────────────────────────────────────
DOOR_SLIDE = {
    'N': (-1,  0),
    'S': ( 1,  0),
    'E': ( 0, -1),
    'W': ( 0,  1),
}
DOOR_THICKNESS  = 0.2
DOOR_ANIM_SPEED = 5.0   # full open in ~0.2 s


def _door_aabb(bx, by, bz, facing, slide):
    """
    Return (x0,y0,z0, x1,y1,z1) world-space AABB for a door panel.
    bx,by,bz  = bottom block-grid anchor
    facing    = 'N'/'S'/'E'/'W'
    slide     = 0.0 (closed) … 1.0 (fully open), offset = slide*0.8 blocks
    """
    t   = DOOR_THICKNESS
    off = slide * 0.8
    sx, sz = DOOR_SLIDE[facing]

    if facing in ('N', 'S'):
        # Wall along X, thin in Z.  Door slides in X.
        x0 = bx + sx * off
        x1 = x0 + 1.0
        z0 = bz + 0.5 - t / 2
        z1 = bz + 0.5 + t / 2
    else:
        # Wall along Z, thin in X.  Door slides in Z.
        x0 = bx + 0.5 - t / 2
        x1 = bx + 0.5 + t / 2
        z0 = bz + sz * off
        z1 = z0 + 1.0

    return x0, float(by), z0, x1, float(by) + 2.0, z1


class DoorManager:
    """
    Thin, physically-sliding doors.
    Each entry: (bx,by,bz) → {'facing': str, 'slide': float, 'target': float}
    slide  0.0 = closed, 1.0 = fully open
    target is animated toward by update()
    """

    def __init__(self):
        self._doors = {}

    # ── public API ────────────────────────────────────────────

    def place(self, bx, by, bz, facing, kind=None):
        self._doors[(bx, by, bz)] = {'facing': facing, 'slide': 0.0, 'target': 0.0, 'kind': kind or DOOR_BLOCK}

    def _bottom_key(self, bx, by, bz):
        """Return the bottom-block key regardless of whether top or bottom was passed."""
        k = (bx, by, bz)
        if k in self._doors:
            return k
        k2 = (bx, by - 1, bz)
        if k2 in self._doors:
            return k2
        return None

    def remove(self, bx, by, bz):
        k = self._bottom_key(bx, by, bz)
        if k:
            del self._doors[k]

    def toggle(self, bx, by, bz):
        k = self._bottom_key(bx, by, bz)
        if k is None:
            return
        d = self._doors[k]
        d['target'] = 0.0 if d['slide'] > 0.5 else 1.0

    def is_open(self, bx, by, bz):
        k = self._bottom_key(bx, by, bz)
        return bool(k and self._doors[k]['slide'] > 0.5)

    def has_door(self, bx, by, bz):
        return self._bottom_key(bx, by, bz) is not None

    def get_state(self):
        out = {}
        for (bx, by, bz), d in self._doors.items():
            out[f"{bx},{by},{bz}"] = {
                'facing': d['facing'],
                'slide':  round(d['slide'],  4),
                'target': round(d['target'], 4),
                'kind':   d.get('kind', DOOR_BLOCK),
            }
        return out

    def set_state(self, raw):
        self._doors = {}
        for ks, v in raw.items():
            parts = ks.split(',')
            if len(parts) != 3:
                continue
            key = (int(parts[0]), int(parts[1]), int(parts[2]))
            self._doors[key] = {
                'facing': v.get('facing', 'N'),
                'slide':  float(v.get('slide',  0.0)),
                'target': float(v.get('target', 0.0)),
                'kind':   v.get('kind', DOOR_BLOCK),
            }

    # ── update (animation) ────────────────────────────────────

    def update(self, dt):
        for d in self._doors.values():
            diff = d['target'] - d['slide']
            if abs(diff) > 0.001:
                step = math.copysign(min(abs(diff), DOOR_ANIM_SPEED * dt), diff)
                d['slide'] = max(0.0, min(1.0, d['slide'] + step))
            else:
                d['slide'] = d['target']

    # ── collision check (used by Player._collide) ─────────────

    def blocks_axis(self, axis, nx, ny, nz, hw, ph):
        """
        Returns True if the player box at (nx,ny,nz) with half-width hw
        and height ph would be blocked by any non-fully-open door.
        Used by Player._collide to treat doors like solid blocks.
        """
        px0, px1 = nx - hw, nx + hw
        pz0, pz1 = nz - hw, nz + hw
        py0, py1 = ny, ny + ph

        for (bx, by, bz), d in self._doors.items():
            if d['slide'] >= 0.99:   # fully open → no collision
                continue
            x0, y0, z0, x1, y1, z1 = _door_aabb(bx, by, bz, d['facing'], d['slide'])
            if (px0 < x1 and px1 > x0 and
                    pz0 < z1 and pz1 > z0 and
                    py0 < y1 and py1 > y0):
                return True
        return False

    # ── draw ──────────────────────────────────────────────────

    def draw(self, px, pz):
        _tex_cache = {}

        # Nudge doors forward so they always win depth test against glass faces
        # that share the same plane (glass writes depth in the chunk VBO pass).
        glEnable(GL_POLYGON_OFFSET_FILL)
        glPolygonOffset(-1, -1)

        glEnable(GL_TEXTURE_2D)

        for (bx, by, bz), d in self._doors.items():
            if (abs(bx - px) > RENDER_DIST * CHUNK_S or
                    abs(bz - pz) > RENDER_DIST * CHUNK_S):
                continue

            f   = d['facing']
            off = d['slide'] * 0.8
            sx, sz = DOOR_SLIDE[f]
            t   = DOOR_THICKNESS

            kind     = d.get('kind', DOOR_BLOCK)
            is_glass = (kind == GLASS_DOOR)
            top_kind = GLASS_DOOR_TOP if is_glass else DOOR_TOP

            if kind not in _tex_cache:
                _tex_cache[kind]     = ITEM_GL_TEXTURES.get(kind)
                _tex_cache[top_kind] = ITEM_GL_TEXTURES.get(top_kind)

            if is_glass:
                glEnable(GL_BLEND)
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
                glColor4f(0.85, 0.85, 0.85, 0.45)
            else:
                glDisable(GL_BLEND)
                glColor3f(0.85, 0.85, 0.85)

            for half in range(2):
                tex = _tex_cache.get(kind) if half == 0 else _tex_cache.get(top_kind)
                if tex:
                    glBindTexture(GL_TEXTURE_2D, tex)
                else:
                    glDisable(GL_TEXTURE_2D)

                y0 = float(by + half)
                y1 = y0 + 1.0

                if f in ('N', 'S'):
                    px2 = bx + sx * off
                    zc  = bz + 0.5
                    _draw_door_xaxis(px2, y0, y1, zc - t/2, zc + t/2)
                else:
                    pz2 = bz + sz * off
                    xc  = bx + 0.5
                    _draw_door_zaxis(xc - t/2, xc + t/2, y0, y1, pz2)

                if not tex:
                    glEnable(GL_TEXTURE_2D)

        glDisable(GL_BLEND)
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_POLYGON_OFFSET_FILL)


def _draw_door_xaxis(x0, y0, y1, z0, z1):
    """Thin panel running along X (N/S door).  Draws +Z and -Z faces."""
    glBegin(GL_QUADS)
    # +Z face
    glTexCoord2f(0, 1); glVertex3f(x0,     y0, z1)
    glTexCoord2f(1, 1); glVertex3f(x0 + 1, y0, z1)
    glTexCoord2f(1, 0); glVertex3f(x0 + 1, y1, z1)
    glTexCoord2f(0, 0); glVertex3f(x0,     y1, z1)
    # -Z face
    glTexCoord2f(0, 1); glVertex3f(x0 + 1, y0, z0)
    glTexCoord2f(1, 1); glVertex3f(x0,     y0, z0)
    glTexCoord2f(1, 0); glVertex3f(x0,     y1, z0)
    glTexCoord2f(0, 0); glVertex3f(x0 + 1, y1, z0)
    glEnd()


def _draw_door_zaxis(x0, x1, y0, y1, z0):
    """Thin panel running along Z (E/W door).  Draws +X and -X faces."""
    glBegin(GL_QUADS)
    # +X face
    glTexCoord2f(0, 1); glVertex3f(x1, y0, z0)
    glTexCoord2f(1, 1); glVertex3f(x1, y0, z0 + 1)
    glTexCoord2f(1, 0); glVertex3f(x1, y1, z0 + 1)
    glTexCoord2f(0, 0); glVertex3f(x1, y1, z0)
    # -X face
    glTexCoord2f(0, 1); glVertex3f(x0, y0, z0 + 1)
    glTexCoord2f(1, 1); glVertex3f(x0, y0, z0)
    glTexCoord2f(1, 0); glVertex3f(x0, y1, z0)
    glTexCoord2f(0, 0); glVertex3f(x0, y1, z0 + 1)
    glEnd()


def player_facing_cardinal(yaw):
    """
    Convert player yaw to N/S/E/W for door placement.
    Yaw 0   = facing -Z → place 'N' door
    Yaw 90  = facing -X → place 'W' door
    Yaw 180 = facing +Z → place 'S' door
    Yaw 270 = facing +X → place 'E' door
    """
    yaw = yaw % 360
    if   yaw <  45 or yaw >= 315: return 'N'
    elif yaw < 135:                return 'W'
    elif yaw < 225:                return 'S'
    else:                          return 'E'




# ──────────────────────────────────────────────────────────────
#  BED MANAGER
# ──────────────────────────────────────────────────────────────
# Beds are 2 blocks long (head + foot).  The head block (BED_BLOCK)
# stores the facing direction.  The foot block (BED_FOOT) is one step
# in front of the head based on that facing.
#
# Facing offsets — the foot is placed IN FRONT of the head.
# Player places the head at their target block; foot goes one further.
BED_FACING_OFFSET = {
    'N': ( 0, 0, -1),  # player facing north  → foot one step north
    'S': ( 0, 0,  1),  # player facing south  → foot one step south
    'E': ( 1, 0,  0),  # player facing east   → foot one step east
    'W': (-1, 0,  0),  # player facing west   → foot one step west
}

# Half-height of the bed panel in world units
BED_HEIGHT = 0.55

def _draw_bed(bx, by, bz, facing, is_head, tex_id):
    """
    Draw a single bed tile (head or foot) as a flat box.
    Beds are 1 block wide, BED_HEIGHT tall, oriented along facing.
    """
    from OpenGL.GL import (glBegin, glEnd, glTexCoord2f, glVertex3f,
                           glEnable, glDisable, glBindTexture,
                           GL_QUADS, GL_TEXTURE_2D)
    x0, y0, z0 = float(bx),   float(by),   float(bz)
    x1, y1, z1 = x0 + 1.0,   y0 + BED_HEIGHT, z0 + 1.0

    if tex_id:
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, tex_id)
    glBegin(GL_QUADS)
    # Top
    glTexCoord2f(0,0); glVertex3f(x0, y1, z0)
    glTexCoord2f(1,0); glVertex3f(x1, y1, z0)
    glTexCoord2f(1,1); glVertex3f(x1, y1, z1)
    glTexCoord2f(0,1); glVertex3f(x0, y1, z1)
    # Bottom
    glTexCoord2f(0,0); glVertex3f(x0, y0, z1)
    glTexCoord2f(1,0); glVertex3f(x1, y0, z1)
    glTexCoord2f(1,1); glVertex3f(x1, y0, z0)
    glTexCoord2f(0,1); glVertex3f(x0, y0, z0)
    # Front (+Z)
    glTexCoord2f(0,0); glVertex3f(x0, y0, z1)
    glTexCoord2f(1,0); glVertex3f(x1, y0, z1)
    glTexCoord2f(1,1); glVertex3f(x1, y1, z1)
    glTexCoord2f(0,1); glVertex3f(x0, y1, z1)
    # Back  (-Z)
    glTexCoord2f(0,0); glVertex3f(x1, y0, z0)
    glTexCoord2f(1,0); glVertex3f(x0, y0, z0)
    glTexCoord2f(1,1); glVertex3f(x0, y1, z0)
    glTexCoord2f(0,1); glVertex3f(x1, y1, z0)
    # Right (+X)
    glTexCoord2f(0,0); glVertex3f(x1, y0, z1)
    glTexCoord2f(1,0); glVertex3f(x1, y0, z0)
    glTexCoord2f(1,1); glVertex3f(x1, y1, z0)
    glTexCoord2f(0,1); glVertex3f(x1, y1, z1)
    # Left  (-X)
    glTexCoord2f(0,0); glVertex3f(x0, y0, z0)
    glTexCoord2f(1,0); glVertex3f(x0, y0, z1)
    glTexCoord2f(1,1); glVertex3f(x0, y1, z1)
    glTexCoord2f(0,1); glVertex3f(x0, y1, z0)
    glEnd()
    if tex_id:
        glDisable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, 0)


class BedManager:
    """
    Manages all placed beds.
    Each entry: (bx,by,bz) of the HEAD block → {'facing': str}
    The foot block position is derived from facing.
    """

    def __init__(self):
        self._beds = {}   # (hx,hy,hz) → {'facing': str}

    # ── Placement / removal ────────────────────────────────────────────

    def place(self, hx, hy, hz, facing, world):
        """Place a bed with head at (hx,hy,hz) facing the given direction."""
        dx, dy, dz = BED_FACING_OFFSET[facing]
        fx, fy, fz = hx + dx, hy + dy, hz + dz
        if world.get_block(fx, fy, fz) != AIR:
            return False                             # no room for foot
        world.set_block(hx, hy, hz, BED_BLOCK)
        world.set_block(fx, fy, fz, BED_FOOT)
        self._beds[(hx, hy, hz)] = {'facing': facing}
        return True

    def remove(self, bx, by, bz, world):
        """
        Remove the bed that owns block (bx,by,bz) — works whether you
        break the head or the foot.  Also clears both world blocks.
        """
        key = self._head_key(bx, by, bz)
        if key is None:
            return
        hx, hy, hz = key
        facing = self._beds[key]['facing']
        dx, dy, dz = BED_FACING_OFFSET[facing]
        fx, fy, fz = hx + dx, hy + dy, hz + dz
        world.set_block(hx, hy, hz, AIR)
        world.set_block(fx, fy, fz, AIR)
        del self._beds[key]

    def _head_key(self, bx, by, bz):
        """Return the head key for the bed that owns (bx,by,bz), or None."""
        if (bx, by, bz) in self._beds:
            return (bx, by, bz)
        # Maybe it's the foot — scan beds to find the matching head
        for key, data in self._beds.items():
            hx, hy, hz = key
            dx, dy, dz = BED_FACING_OFFSET[data['facing']]
            if (hx + dx, hy + dy, hz + dz) == (bx, by, bz):
                return key
        return None

    def is_bed(self, bx, by, bz):
        return self._head_key(bx, by, bz) is not None

    # ── Collision (thin box, player can stand on it) ───────────────────

    def check_player_collide(self, player):
        hw = player.width / 2
        px0, px1 = player.x - hw, player.x + hw
        pz0, pz1 = player.z - hw, player.z + hw
        py0, py1 = player.y,       player.y + player.height

        for (hx, hy, hz), data in self._beds.items():
            facing = data['facing']
            dx, dy, dz = BED_FACING_OFFSET[facing]
            for bx, by, bz in ((hx, hy, hz), (hx+dx, hy+dy, hz+dz)):
                bx0, bx1 = float(bx), float(bx) + 1.0
                bz0, bz1 = float(bz), float(bz) + 1.0
                by0, by1 = float(by), float(by) + BED_HEIGHT
                if (px0 < bx1 and px1 > bx0 and
                    py0 < by1 and py1 > by0 and
                    pz0 < bz1 and pz1 > bz0):
                    # Push player on top
                    if player.vy <= 0:
                        player.y = by1
                        player.vy = 0
                        player.on_ground = True

    # ── Sleep ──────────────────────────────────────────────────────────

    def try_sleep(self, bx, by, bz, tod):
        """
        Return True if it is night-time and the player right-clicked a bed.
        The caller handles the actual tod skip.
        """
        if not self.is_bed(bx, by, bz):
            return False
        # Night = tod in roughly [0.5, 1.0)
        return tod >= 0.5 or tod < 0.25

    # ── Persistence ────────────────────────────────────────────────────

    def get_state(self):
        return {f"{k[0]},{k[1]},{k[2]}": v['facing']
                for k, v in self._beds.items()}

    def set_state(self, d, world):
        self._beds = {}
        for ks, facing in d.items():
            parts = ks.split(',')
            if len(parts) != 3:
                continue
            hx, hy, hz = int(parts[0]), int(parts[1]), int(parts[2])
            self._beds[(hx, hy, hz)] = {'facing': facing}
            # Re-place blocks in world (chunks already loaded)
            dx, dy, dz = BED_FACING_OFFSET[facing]
            world.set_block(hx, hy, hz, BED_BLOCK)
            world.set_block(hx+dx, hy+dy, hz+dz, BED_FOOT)

    # ── Rendering ──────────────────────────────────────────────────────

    def draw(self, px, pz, tex_head, tex_foot):
        from OpenGL.GL import glColor3f
        glColor3f(1.0, 1.0, 1.0)
        for (hx, hy, hz), data in self._beds.items():
            if abs(hx - px) > RENDER_DIST * CHUNK_S + 2:
                continue
            if abs(hz - pz) > RENDER_DIST * CHUNK_S + 2:
                continue
            facing = data['facing']
            dx, dy, dz = BED_FACING_OFFSET[facing]
            _draw_bed(hx, hy, hz, facing, True,  tex_head)
            _draw_bed(hx+dx, hy+dy, hz+dz, facing, False, tex_foot)


# ──────────────────────────────────────────────────────────────
#  BILLBOARD BLOCK RENDERER (wheat crops, signs, skyscreen)
# ──────────────────────────────────────────────────────────────

BILLBOARD_BLOCKS = frozenset({WHEAT_STAGE0, WHEAT_STAGE1, WHEAT_STAGE2, WHEAT_STAGE3})

def draw_billboard_blocks(world, player_x, player_y, player_z, player_yaw):
    """
    Draw wheat-stage blocks as camera-facing transparent X-crosshatch quads,
    plus handle SIGN_BLOCK and SKYSCREEN_BLOCK rendering.
    """
    px_rad = RENDER_DIST * CHUNK_S
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glDepthMask(False)
    glEnable(GL_TEXTURE_2D)
    glDisable(GL_CULL_FACE)

    yr = math.radians(-player_yaw)
    cam_rx = math.cos(yr); cam_rz = math.sin(yr)

    for (cx,cz),chunk in world.chunks.items():
        if (abs(cx*CHUNK_S - player_x) > px_rad or
                abs(cz*CHUNK_S - player_z) > px_rad):
            continue
        WX = cx*CHUNK_S; WZ = cz*CHUNK_S
        for bx_l, by, bz_l, bid in chunk.get_billboard_positions(BILLBOARD_BLOCKS):
            tex_name = {WHEAT_STAGE0:"wheat0", WHEAT_STAGE1:"wheat1",
                        WHEAT_STAGE2:"wheat2", WHEAT_STAGE3:"wheat3"}.get(bid)
            tex = ITEM_GL_TEXTURES.get(bid) if tex_name else None
            if tex:
                glBindTexture(GL_TEXTURE_2D, tex)
            else:
                glDisable(GL_TEXTURE_2D)
                glColor4f(0.4,0.8,0.2,0.9)

            cx2 = WX + bx_l + 0.5; cy = float(by); cz2 = WZ + bz_l + 0.5
            hw = 0.48

            for angle_off in (0.0, math.pi/2):
                ax = math.cos(angle_off)*hw; az = math.sin(angle_off)*hw
                glColor4f(1,1,1,1)
                glBegin(GL_QUADS)
                glTexCoord2f(0,1); glVertex3f(cx2-ax, cy,   cz2-az)
                glTexCoord2f(1,1); glVertex3f(cx2+ax, cy,   cz2+az)
                glTexCoord2f(1,0); glVertex3f(cx2+ax, cy+1, cz2+az)
                glTexCoord2f(0,0); glVertex3f(cx2-ax, cy+1, cz2-az)
                glEnd()
                glBegin(GL_QUADS)
                glTexCoord2f(1,1); glVertex3f(cx2-ax, cy,   cz2-az)
                glTexCoord2f(0,1); glVertex3f(cx2+ax, cy,   cz2+az)
                glTexCoord2f(0,0); glVertex3f(cx2+ax, cy+1, cz2+az)
                glTexCoord2f(1,0); glVertex3f(cx2-ax, cy+1, cz2-az)
                glEnd()

            if not tex: glEnable(GL_TEXTURE_2D)

    glDepthMask(True)
    glDisable(GL_BLEND)
    glDisable(GL_TEXTURE_2D)


def draw_sign_blocks(world, player_x, player_y, player_z, player_yaw, player_pitch, font_small):
    """Render SIGN_BLOCK text as a camera-facing text quad on the four side faces."""
    px_rad = RENDER_DIST * CHUNK_S
    for (cx,cz),chunk in world.chunks.items():
        if (abs(cx*CHUNK_S-player_x)>px_rad or abs(cz*CHUNK_S-player_z)>px_rad):
            continue
        WX=cx*CHUNK_S; WZ=cz*CHUNK_S
        for bx_l, by, bz_l, _ in chunk.get_billboard_positions({SIGN_BLOCK}):
            wx=WX+bx_l; wz=WZ+bz_l
            pos_key=(int(wx),int(by),int(wz))
            text=SIGN_TEXTS.get(pos_key,"")
            if not text: continue
            dist2=(wx+0.5-player_x)**2+(wz+0.5-player_z)**2
            if dist2>64: continue  # only render nearby signs

            surf=pygame.Surface((256,64),pygame.SRCALPHA)
            surf.fill((120,90,50,230))
            pygame.draw.rect(surf,(80,60,30,255),(0,0,256,64),3)
            tw=font_small.render(text[:SIGN_MAX_CHARS],True,(255,240,200))
            surf.blit(tw,(8,8))
            data=pygame.image.tostring(surf,"RGBA",False)
            tex=glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D,tex)
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR)
            glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,256,64,0,GL_RGBA,GL_UNSIGNED_BYTE,data)

            cx2=wx+0.5; cy=float(by)+0.5; cz2=wz+0.5
            yr=math.radians(-(math.degrees(math.atan2(player_x-cx2, player_z-cz2))))
            rax=math.cos(yr)*0.45; raz=math.sin(yr)*0.45

            glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
            glEnable(GL_TEXTURE_2D); glBindTexture(GL_TEXTURE_2D,tex)
            glColor4f(1,1,1,1)
            glBegin(GL_QUADS)
            glTexCoord2f(0,0); glVertex3f(cx2-rax, cy+0.15, cz2-raz)
            glTexCoord2f(1,0); glVertex3f(cx2+rax, cy+0.15, cz2+raz)
            glTexCoord2f(1,1); glVertex3f(cx2+rax, cy-0.15, cz2+raz)
            glTexCoord2f(0,1); glVertex3f(cx2-rax, cy-0.15, cz2-raz)
            glEnd()
            glDisable(GL_BLEND); glDisable(GL_TEXTURE_2D)
            glDeleteTextures([tex])

def draw_glass_blocks(world, player_x, player_y, player_z):
    """
    Transparent glass pass — sorted back-to-front, depth test ON, depth write OFF.

    depth test ON  → glass correctly hidden behind opaque walls
    depth write OFF → multiple glass panes don't block each other
    sorted B→F     → front panes blend over back panes correctly
    """
    px_rad = RENDER_DIST * CHUNK_S

    FACE_DIRS_G = [
        ( 0, 1, 0), ( 0,-1, 0),
        ( 0, 0,-1), ( 0, 0, 1),
        (-1, 0, 0), ( 1, 0, 0),
    ]
    FACE_QUADS_G = [
        [(0,1,0),(1,1,0),(1,1,1),(0,1,1)],  # top
        [(0,0,1),(1,0,1),(1,0,0),(0,0,0)],  # bottom
        [(0,1,0),(1,1,0),(1,0,0),(0,0,0)],  # -Z
        [(0,0,1),(1,0,1),(1,1,1),(0,1,1)],  # +Z
        [(0,0,0),(0,0,1),(0,1,1),(0,1,0)],  # -X
        [(1,0,1),(1,0,0),(1,1,0),(1,1,1)],  # +X
    ]

    faces = []
    for (cx, cz), chunk in world.chunks.items():
        if (abs(cx*CHUNK_S - player_x) > px_rad or
                abs(cz*CHUNK_S - player_z) > px_rad):
            continue
        WX = cx*CHUNK_S; WZ = cz*CHUNK_S
        positions = chunk.get_billboard_positions({GLASS_BLOCK})
        if not positions:
            continue
        for bx_l, by, bz_l, _ in positions:
            wx = WX + bx_l; wz = WZ + bz_l; wy = float(by)
            for fi, (dx, dy, dz) in enumerate(FACE_DIRS_G):
                nbid = world.get_block(int(wx+dx), int(wy+dy), int(wz+dz))
                # Skip faces against opaque blocks
                if nbid is not None and not (nbid == AIR or TRANSPARENT_ARR[nbid]):
                    continue
                # Skip internal glass-to-glass faces
                if nbid == GLASS_BLOCK:
                    continue
                fcx = wx + 0.5 + dx*0.5
                fcy = wy + 0.5 + dy*0.5
                fcz = wz + 0.5 + dz*0.5
                dsq = (fcx-player_x)**2 + (fcy-player_y)**2 + (fcz-player_z)**2
                faces.append((dsq, wx, wy, wz, fi))

    if not faces:
        return

    faces.sort(key=lambda f: -f[0])  # back-to-front

    tex = ITEM_GL_TEXTURES.get(GLASS_BLOCK)
    uvs = [(0,1),(1,1),(1,0),(0,0)]

    glEnable(GL_DEPTH_TEST)   # glass hidden behind walls
    glDepthMask(False)         # glass doesn't block other glass
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glDisable(GL_CULL_FACE)
    glColor4f(1, 1, 1, 1)

    if tex:
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, tex)
    else:
        glDisable(GL_TEXTURE_2D)
        glColor4f(0.78, 0.91, 1.0, 0.35)

    for _, wx, wy, wz, fi in faces:
        glBegin(GL_QUADS)
        for vi, (vx, vy, vz2) in enumerate(FACE_QUADS_G[fi]):
            glTexCoord2f(*uvs[vi])
            glVertex3f(wx+vx, wy+vy, wz+vz2)
        glEnd()

    glDepthMask(True)
    glDisable(GL_BLEND)
    glEnable(GL_TEXTURE_2D)


def draw_skyscreen_blocks(world, player_x, player_z, sky_color_rgb):
    """
    Render SKYSCREEN_BLOCK as a depth-only occluder.

    nodraw semantics: the block writes to the depth buffer so it occludes
    everything behind it (other blocks, entities), but never writes colour —
    the sky shader already fills those pixels, so no texture or solid fill
    is needed and z-fighting is impossible.
    """
    px_rad = RENDER_DIST * CHUNK_S

    _FACE_VERTS_SS = [
        [(0,0,0),(1,0,0),(1,0,1),(0,0,1)],  # bottom
        [(0,1,0),(1,1,0),(1,1,1),(0,1,1)],  # top
        [(0,0,0),(1,0,0),(1,1,0),(0,1,0)],  # -Z
        [(0,0,1),(1,0,1),(1,1,1),(0,1,1)],  # +Z
        [(0,0,0),(0,0,1),(0,1,1),(0,1,0)],  # -X
        [(1,0,0),(1,0,1),(1,1,1),(1,1,0)],  # +X
    ]

    # ── Pass 1: depth-only for nodraw blocks (SKYSCREEN) ──────────────
    # Write depth so the block occludes geometry behind it, but suppress
    # all colour output so the sky shader pixels show through unmodified.
    glDisable(GL_TEXTURE_2D)
    glColorMask(False, False, False, False)   # no colour writes
    glDepthMask(True)

    for (cx,cz),chunk in world.chunks.items():
        if abs(cx*CHUNK_S-player_x)>px_rad or abs(cz*CHUNK_S-player_z)>px_rad:
            continue
        WX=cx*CHUNK_S; WZ=cz*CHUNK_S
        sky_positions = chunk.get_billboard_positions({SKYSCREEN_BLOCK})
        if not sky_positions: continue
        for bx_l,by,bz_l,_ in sky_positions:
            wx=WX+bx_l; wy=float(by); wz=WZ+bz_l
            glBegin(GL_QUADS)
            for face_verts in _FACE_VERTS_SS:
                for vx,vy,vz2 in face_verts:
                    glVertex3f(wx+vx, wy+vy, wz+vz2)
            glEnd()

    glColorMask(True, True, True, True)       # restore colour writes
    glEnable(GL_TEXTURE_2D)


# ──────────────────────────────────────────────────────────────
#  SKY
# ──────────────────────────────────────────────────────────────
def sky_color(t):
    def l3(a,b,f): return (a[0]+(b[0]-a[0])*f, a[1]+(b[1]-a[1])*f, a[2]+(b[2]-a[2])*f)
    if   t<0.25: return l3((0.04,0.03,0.12),(0.90,0.55,0.30), t/0.25)
    elif t<0.50: return l3((0.90,0.55,0.30),(0.55,0.78,0.95),(t-0.25)/0.25)
    elif t<0.75: return l3((0.55,0.78,0.95),(0.90,0.45,0.20),(t-0.50)/0.25)
    else:        return l3((0.90,0.45,0.20),(0.04,0.03,0.12),(t-0.75)/0.25)


# ──────────────────────────────────────────────────────────────
#  HUD
# ──────────────────────────────────────────────────────────────
class HUD:
    def __init__(self,w,h,font_med,font_sm):
        self.w=w; self.h=h; self.fm=font_med; self.fs=font_sm
        self.tex, self.tex_overlay = glGenTextures(2)
        for t in (self.tex, self.tex_overlay):
            glBindTexture(GL_TEXTURE_2D,t)
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR)
            glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,w,h,0,GL_RGBA,GL_UNSIGNED_BYTE,
                         np.zeros((h,w,4),dtype=np.uint8))
        glBindTexture(GL_TEXTURE_2D,0)
        self._cache_key = None
        self._icons = {}
        self._load_icons()
        # Tooltip hover tracking: {item_id: hover_seconds}
        self._tooltip_hover = {}       # iid -> seconds hovered
        self._tooltip_item  = None     # currently shown tooltip item
        # "why couldn't i" death message state
        self.death_msg_timer = 0.0     # counts down from 5.0

    def _load_icons(self, tex_dir=None):
        if tex_dir is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            tex_dir = os.path.join(script_dir, "textures")
        if not os.path.isdir(tex_dir):
            return
        mapping = {
            KEIRO_GRASS:"keiro_grass", KEIRO_SOIL:"keiro_soil", KEIRO_STONE:"keiro_stone",
            SHINEN_ROCK:"shinen_rock", SHINEN_CRYSTAL:"shinen_crystal", SHINEN_EMBER:"shinen_ember",
            KASUMI_SNOW:"kasumi_snow", KASUMI_ICE:"kasumi_ice", KASUMI_SHALE:"kasumi_shale",
            MORI_WOOD:"mori_wood", MORI_LEAVES:"mori_leaves", MORI_MOSS:"mori_moss",
            REIKI_WATER:"reiki_water", TAMASHII_LAVA:"tamashii_lava",
            CLOUD_BLOCK:"cloud", WORKBENCH:"workbench",
            ITEM_STICK:"stick", ITEM_WOOD_SWORD:"wood_sword", ITEM_STONE_SWORD:"stone_sword",
            ITEM_WOOD_PICK:"wood_pick", ITEM_STONE_PICK:"stone_pick",
            ITEM_WOOD_AXE:"wood_axe", ITEM_STONE_AXE:"stone_axe",
            ITEM_WOOD_SHOVEL:"wood_shovel", ITEM_STONE_SHOVEL:"stone_shovel",
            ITEM_BERRY:"berry", ITEM_BREAD:"bread",
            ITEM_HOE:"hoe", ITEM_WHEAT_SEEDS:"wheat_seeds",
            ITEM_WHEAT:"wheat_item", ITEM_APPLE:"apple",
            ITEM_COOKED_MEAT:"cooked_meat", ITEM_RAW_MEAT:"raw_meat",
            GLASS_BLOCK:"glass", DOOR_BLOCK:"door", DOOR_TOP:"door_top", GLASS_DOOR:"glass_door", GLASS_DOOR_TOP:"glass_door_top", GLASS_DOOR:"glass_door", GLASS_DOOR_TOP:"glass_door_top",
            FARMLAND:"farmland", SAND_BLOCK:"sand", FURNACE_BLOCK:"furnace",
            GLASS_BLOCK:"glass",
        SIGN_BLOCK:"sign", SKYSCREEN_BLOCK:"skyscreen", CREDITS_BLOCK:"credits",
            BUSH_LEAVES:"bush_leaves", DOG_STATUE:"dog_statue", CAT_STATUE:"cat_statue",
            ITEM_TRICKSABRE:"tricksabre",
        }
        for iid, fname in mapping.items():
            path = os.path.join(tex_dir, f"{fname}.png")
            if os.path.exists(path):
                try:
                    surf = pygame.image.load(path).convert_alpha()
                    self._icons[iid] = surf
                except Exception:
                    pass

    def _icon(self, iid, size):
        if iid in self._icons:
            return pygame.transform.scale(self._icons[iid], (size, size))
        c = item_color(iid)
        surf = pygame.Surface((size,size), pygame.SRCALPHA)
        surf.fill((*c, 220))
        return surf

    def _draw_icon(self, s, iid, x, y, size):
        icon = self._icon(iid, size)
        s.blit(icon, (x, y))

    def _upload(self, surf, tex=None):
        if tex is None: tex=self.tex
        data=pygame.image.tostring(surf,"RGBA",True)
        glBindTexture(GL_TEXTURE_2D,tex)
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,self.w,self.h,GL_RGBA,GL_UNSIGNED_BYTE,data)
        glBindTexture(GL_TEXTURE_2D,0)

    def _draw_tex(self, tex):
        W,H=self.w,self.h
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
        glOrtho(0,W,0,H,-1,1)
        glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D); glBindTexture(GL_TEXTURE_2D,tex)
        glColor4f(1,1,1,1)
        glBegin(GL_QUADS)
        glTexCoord2f(0,0); glVertex2f(0,0)
        glTexCoord2f(1,0); glVertex2f(W,0)
        glTexCoord2f(1,1); glVertex2f(W,H)
        glTexCoord2f(0,1); glVertex2f(0,H)
        glEnd()
        glBindTexture(GL_TEXTURE_2D,0); glDisable(GL_TEXTURE_2D)
        glDisable(GL_BLEND); glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION); glPopMatrix()
        glMatrixMode(GL_MODELVIEW); glPopMatrix()

    def update(self, player, world, fps, debug, tod, mining_progress=0.0,
               tooltip_item=None, tooltip_hover_t=0.0, death_msg_timer=0.0):
        cache_key = (
            player.selected, int(tod*4), debug,
            round(player.x,1), round(player.y,1), round(player.z,1),
            int(fps/2), tuple(player.hotbar),
            int(player.health), player.gamemode,
            tuple(sorted((k,v) for k,v in player.inv.items() if k is not None)) if player.gamemode==GAMEMODE_SURVIVAL else (),
            round(mining_progress,1),
            tooltip_item, round(tooltip_hover_t,1),
            round(death_msg_timer,2),
        )
        if cache_key == self._cache_key:
            return
        self._cache_key = cache_key
        W,H=self.w,self.h
        s=pygame.Surface((W,H),pygame.SRCALPHA)

        cx2,cy=W//2,H//2
        pygame.draw.line(s,(220,220,220,200),(cx2-12,cy),(cx2+12,cy),2)
        pygame.draw.line(s,(220,220,220,200),(cx2,cy-12),(cx2,cy+12),2)

        if mining_progress>0:
            bw2=160; bh2=10; bx3=W//2-bw2//2; by3=cy+22
            pygame.draw.rect(s,(20,18,30,200),(bx3-2,by3-2,bw2+4,bh2+4),border_radius=4)
            pygame.draw.rect(s,(200,160,60,230),(bx3,by3,int(bw2*mining_progress),bh2),border_radius=3)

        ss=52; pad=4
        bw=9*(ss+pad)+pad; bx2=(W-bw)//2; by2=H-ss-16
        pygame.draw.rect(s,(20,18,30,190),(bx2-6,by2-6,bw+12,ss+16),border_radius=8)
        for i in range(9):
            bid=player.hotbar[i]
            sx2=bx2+pad+i*(ss+pad); sel=(i==player.selected)
            pygame.draw.rect(s,(220,195,100,255) if sel else (60,55,80,180),
                             (sx2-2,by2-2,ss+4,ss+4),border_radius=4)
            if bid is not None:
                self._draw_icon(s, bid, sx2, by2, ss)
                if player.gamemode==GAMEMODE_SURVIVAL:
                    cnt=player.inv.get(bid,0)
                    ct=self.fs.render(str(cnt),True,(240,235,200))
                    bg=pygame.Surface((ct.get_width()+2,ct.get_height()),pygame.SRCALPHA)
                    bg.fill((0,0,0,140)); s.blit(bg,(sx2+ss-ct.get_width()-3,by2+ss-ct.get_height()-2))
                    s.blit(ct,(sx2+ss-ct.get_width()-3, by2+ss-ct.get_height()-2))
            s.blit(self.fs.render(str(i+1),True,(200,195,220)),(sx2+3,by2+3))
            if sel and bid is not None:
                nm=self.fs.render(item_name(bid),True,(230,215,180))
                s.blit(nm,(W//2-nm.get_width()//2,by2-26))

        if player.gamemode==GAMEMODE_SURVIVAL:
            hbw=180; hbh=14; hbx=bx2; hby=by2-50
            pygame.draw.rect(s,(40,20,20,200),(hbx,hby,hbw,hbh),border_radius=4)
            filled=int(hbw*(player.health/player.max_health))
            hp_col=(220,60,60,230) if player.health>6 else (240,180,40,230)
            if filled>0:
                pygame.draw.rect(s,hp_col,(hbx,hby,filled,hbh),border_radius=4)
            htxt=self.fs.render(f"♥ {int(player.health)}/{player.max_health}",True,(240,200,200))
            s.blit(htxt,(hbx+hbw+8,hby))

        gm_col=(100,200,140,200) if player.gamemode==GAMEMODE_BUILDING else (200,120,80,200)
        gm_txt=self.fs.render(player.gamemode.upper(),True,gm_col)
        s.blit(gm_txt,(W-gm_txt.get_width()-14, H-gm_txt.get_height()-14))

        tod_s=["Night","Dawn","Day","Dusk"][int(tod*4)%4]
        ts=self.fs.render(f"⊙ {tod_s}",True,(200,195,220))
        s.blit(ts,(W-ts.get_width()-14,14))

        if debug:
            lines=[f"Saikai | FPS:{fps:.0f}",
                   f"Pos:{player.x:.1f} {player.y:.1f} {player.z:.1f}",
                   f"Chunk:{world.chunk_key(player.x,player.z)} | Loaded:{len(world.chunks)}",
                   f"Fly:{player.flying}  Seed:{world.seed}"]
            yo=14
            for ln in lines:
                r=self.fs.render(ln,True,(200,240,200))
                bg=pygame.Surface((r.get_width()+8,r.get_height()+2),pygame.SRCALPHA)
                bg.fill((0,0,0,120)); s.blit(bg,(8,yo-1)); s.blit(r,(12,yo))
                yo+=r.get_height()+3

        # ── "why couldn't i" death message ──────────────────────────
        if death_msg_timer > 0:
            fade = min(1.0, death_msg_timer) if death_msg_timer < 1.0 else 1.0
            alpha = int(255 * fade)
            msg_surf = self.fs.render("why couldn't i", True, (220, 200, 255))
            msg_surf.set_alpha(alpha)
            ss2=52; pad2=4; bw2=9*(ss2+pad2)+pad2; bx2=(W-bw2)//2; by2=H-ss2-16
            mx2 = W//2 - msg_surf.get_width()//2
            my2 = by2 - 52
            bg2 = pygame.Surface((msg_surf.get_width()+12, msg_surf.get_height()+4), pygame.SRCALPHA)
            bg2.fill((0, 0, 0, int(120*fade)))
            s.blit(bg2, (mx2-6, my2-2))
            s.blit(msg_surf, (mx2, my2))

        self._upload(s)

    def draw(self):
        self._draw_tex(self.tex)

    def resize(self,w,h):
        self.w=w; self.h=h
        blank=np.zeros((h,w,4),dtype=np.uint8)
        for t in (self.tex, self.tex_overlay):
            glBindTexture(GL_TEXTURE_2D,t)
            glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,w,h,0,GL_RGBA,GL_UNSIGNED_BYTE,blank)
        glBindTexture(GL_TEXTURE_2D,0)
        self._cache_key=None

    def title(self, font_big, font_med, hovered=None, saves=None):
        """Title screen. hovered may be a mode key or a save-slot name.
        Returns dict with 'survival', 'building' rects and 'saves' list of (slot_name, rect)."""
        import time as _time
        W,H=self.w,self.h
        s=pygame.Surface((W,H),pygame.SRCALPHA); s.fill((8,6,18,255))
        for i in range(12):
            pygame.draw.line(s,(25,20,50,60),(0,H*i//12),(W,H*i//12),1)

        title=font_big.render("SAIKAI",True,(180,210,255))
        sub=font_med.render("The World That Remembers",True,(120,155,200))
        s.blit(title,(W//2-title.get_width()//2, 60))
        s.blit(sub,  (W//2-sub.get_width()//2,  60+title.get_height()+6))

        bw,bh=240,100; gap=36
        total=bw*2+gap; bx=W//2-total//2; by=200

        ng_label=self.fm.render("New Game",True,(160,155,195))
        s.blit(ng_label,(W//2-ng_label.get_width()//2, by-28))

        rects={}
        for mode,label,desc1,desc2 in [
            ("survival","Survival",  "Collect resources","Health & fall damage"),
            ("building","Building",  "Infinite blocks",  "Immortal, fly enabled"),
        ]:
            hot=(hovered==mode)
            col=(55,45,90,230) if hot else (30,25,55,210)
            border=(160,140,220,255) if hot else (70,60,110,200)
            pygame.draw.rect(s,col,(bx,by,bw,bh),border_radius=10)
            pygame.draw.rect(s,border,(bx,by,bw,bh),2,border_radius=10)
            lbl=self.fm.render(label,True,(220,215,255) if hot else (170,165,210))
            d1=self.fs.render(desc1,True,(160,155,200))
            d2=self.fs.render(desc2,True,(130,125,170))
            s.blit(lbl,(bx+bw//2-lbl.get_width()//2, by+14))
            s.blit(d1, (bx+bw//2-d1.get_width()//2,  by+52))
            s.blit(d2, (bx+bw//2-d2.get_width()//2,  by+70))
            rects[mode]=pygame.Rect(bx,by,bw,bh)
            bx+=bw+gap

        save_rects=[]
        if saves:
            sl_label=self.fm.render("Continue",True,(160,155,195))
            sl_y=by+bh+36
            s.blit(sl_label,(W//2-sl_label.get_width()//2, sl_y))
            sl_y+=sl_label.get_height()+8

            sw=W-120; sh=58; sx2=60
            for m in saves[:4]:
                slot=m["slot"]
                hot=(hovered==slot)
                col=(50,42,80,220) if hot else (28,23,48,200)
                border=(140,120,200,220) if hot else (60,52,95,180)
                pygame.draw.rect(s,col,(sx2,sl_y,sw,sh),border_radius=8)
                pygame.draw.rect(s,border,(sx2,sl_y,sw,sh),2,border_radius=8)

                saved_ts=m.get("saved_at",0)
                age=_time.time()-saved_ts
                if age<60: age_s=f"{int(age)}s ago"
                elif age<3600: age_s=f"{int(age/60)}m ago"
                else: age_s=f"{int(age/3600)}h ago"

                nm_t=self.fm.render(slot, True,(220,215,255) if hot else (180,175,220))
                info_t=self.fs.render(
                    f"{m.get('gamemode','?').capitalize()}  |  Seed {m.get('seed','?')}  |  Saved {age_s}",
                    True,(140,135,175))
                s.blit(nm_t, (sx2+14, sl_y+6))
                s.blit(info_t,(sx2+14, sl_y+sh-info_t.get_height()-6))
                save_rects.append((slot, pygame.Rect(sx2,sl_y,sw,sh)))
                sl_y+=sh+8

        hint=self.fs.render("New game — pick a mode above  |  Continue — click a save slot",True,(70,65,100))
        s.blit(hint,(W//2-hint.get_width()//2, H-30))

        self._upload(s, self.tex_overlay)
        self._draw_tex(self.tex_overlay)
        rects["saves"]=save_rects
        return rects

    def inventory(self, player, search_text=""):
        W,H=self.w,self.h
        s=pygame.Surface((W,H),pygame.SRCALPHA)
        s.fill((0,0,0,170))

        ALL_PLACEABLE=[b for b in range(1,NUM_BLOCKS)
                       if b not in (REIKI_WATER,TAMASHII_LAVA,AIR)]

        if player.gamemode==GAMEMODE_BUILDING:
            return self._inv_building(s, player, W, H, ALL_PLACEABLE, search_text)
        else:
            return self._inv_survival(s, player, W, H, ALL_PLACEABLE)

    def _inv_building(self, s, player, W, H, all_blocks, search_text):
        filtered=[b for b in all_blocks
                  if search_text.lower() in BLOCK_NAMES[b].lower()]

        lw=320; lh=H-80; lx=30; ly=40
        pygame.draw.rect(s,(18,15,30,220),(lx,ly,lw,lh),border_radius=10)
        t=self.fm.render("Hotbar",True,(200,195,240))
        s.blit(t,(lx+lw//2-t.get_width()//2, ly+12))

        ss=48; pad=8
        for i in range(9):
            bid=player.hotbar[i]
            sx2=lx+pad+(i%3)*(ss+pad+4)
            sy2=ly+50+(i//3)*(ss+pad+4)
            sel=(i==player.selected)
            pygame.draw.rect(s,(220,195,100,200) if sel else (50,45,70,200),
                             (sx2-2,sy2-2,ss+4,ss+4),border_radius=4)
            if bid is not None:
                self._draw_icon(s, bid, sx2, sy2, ss)
                nm=self.fs.render(item_name(bid),True,(180,175,210))
                s.blit(nm,(sx2+ss+6,sy2+ss//2-nm.get_height()//2))
            else:
                et=self.fs.render(f"Slot {i+1} — empty",True,(80,75,100))
                s.blit(et,(sx2+ss+6,sy2+ss//2-et.get_height()//2))
            nt=self.fs.render(str(i+1),True,(180,175,210))
            s.blit(nt,(sx2+3,sy2+3))

        rw=W-lx-lw-50; rx=lx+lw+20; ry=ly
        pygame.draw.rect(s,(18,15,30,220),(rx,ry,rw,lh),border_radius=10)
        bt=self.fm.render("Blocks",True,(200,195,240))
        s.blit(bt,(rx+rw//2-bt.get_width()//2, ry+12))

        sbh=28; sbx=rx+12; sby=ry+46; sbw=rw-24
        pygame.draw.rect(s,(35,30,50,230),(sbx,sby,sbw,sbh),border_radius=5)
        pygame.draw.rect(s,(100,95,130,200),(sbx,sby,sbw,sbh),2,border_radius=5)
        disp=search_text if search_text else "Search blocks..."
        col=(230,225,255) if search_text else (100,95,120)
        st=self.fs.render(disp,True,col)
        s.blit(st,(sbx+8, sby+sbh//2-st.get_height()//2))

        bss=44; bpad=6
        cols=max(1,(rw-12)//(bss+bpad))
        gx=rx+8; gy=sby+sbh+10
        grid_blocks=[]; max_rows=(lh-sbh-60)//(bss+bpad)
        for i,bid in enumerate(filtered):
            col2=i%cols; row=i//cols
            if row>=max_rows: break
            ix=gx+col2*(bss+bpad); iy=gy+row*(bss+bpad)
            in_hotbar=bid in player.hotbar
            pygame.draw.rect(s,(180,160,80,200) if in_hotbar else (45,40,65,160),
                             (ix-2,iy-2,bss+4,bss+4),border_radius=3)
            self._draw_icon(s, bid, ix, iy, bss)
            grid_blocks.append((bid,ix,iy,bss))

        hint=self.fs.render("Click block to toggle in hotbar  |  Click hotbar slot then block to assign  |  E/Esc to close",
                            True,(100,95,125))
        s.blit(hint,(W//2-hint.get_width()//2, H-28))

        self._upload(s, self.tex_overlay)
        self._draw_tex(self.tex_overlay)
        return {'mode':'building','grid':grid_blocks,'hotbar_slots':(lx+pad,ly+50,ss,pad)}

    def _inv_survival(self, s, player, W, H, all_blocks):
        pw=560; ph=420; px2=(W-pw)//2; py2=(H-ph)//2
        pygame.draw.rect(s,(18,15,30,230),(px2-6,py2-6,pw+12,ph+12),border_radius=10)
        pygame.draw.rect(s,(30,26,45,210),(px2,py2,pw,ph),border_radius=8)
        t=self.fm.render("Inventory",True,(200,195,240))
        s.blit(t,(px2+pw//2-t.get_width()//2, py2+10))

        ss=52; pad=8; cols=7
        grid_blocks=[]
        items=[(iid,cnt) for iid,cnt in sorted((k,v) for k,v in player.inv.items() if k is not None) if cnt>0]
        if not items:
            et=self.fm.render("No items yet — break some blocks!",True,(140,130,160))
            s.blit(et,(px2+pw//2-et.get_width()//2, py2+ph//2-et.get_height()//2))
        for i,(iid,cnt) in enumerate(items):
            col2=i%cols; row=i//cols
            ix=px2+pad+col2*(ss+pad); iy=py2+50+row*(ss+pad+18)
            if iy+ss>py2+ph-24: break
            in_hotbar=iid in player.hotbar
            pygame.draw.rect(s,(180,160,80,180) if in_hotbar else (45,40,65,180),
                             (ix-2,iy-2,ss+4,ss+4),border_radius=3)
            self._draw_icon(s, iid, ix, iy, ss)
            ct=self.fs.render(str(cnt),True,(240,230,180))
            bg=pygame.Surface((ct.get_width()+2,ct.get_height()),pygame.SRCALPHA)
            bg.fill((0,0,0,140)); s.blit(bg,(ix+ss-ct.get_width()-3,iy+ss-ct.get_height()-2))
            s.blit(ct,(ix+ss-ct.get_width()-3,iy+ss-ct.get_height()-2))
            grid_blocks.append((iid,ix,iy,ss))

        craft_y=py2+ph-60
        hand_recipes=[(out,r) for out,r in RECIPES.items() if out not in NEEDS_WORKBENCH]
        cx2_=px2+8
        ct2=self.fs.render("Hand craft:",True,(160,155,190))
        s.blit(ct2,(cx2_,craft_y-18))
        for out,recipe in hand_recipes:
            can=all(player.inv.get(ing,0)>=cnt for ing,cnt in recipe)
            bc=(80,160,80,200) if can else (50,45,70,160)
            pygame.draw.rect(s,bc,(cx2_,craft_y,44,44),border_radius=4)
            self._draw_icon(s, out, cx2_, craft_y, 44)
            grid_blocks.append(('craft_'+str(out), cx2_, craft_y, 44))
            cx2_+=50

        hint=self.fs.render("Click item → hotbar  |  Click recipe → craft  |  E/Esc close",True,(100,95,125))
        s.blit(hint,(W//2-hint.get_width()//2, py2+ph+10))

        self._upload(s, self.tex_overlay)
        self._draw_tex(self.tex_overlay)
        return {'mode':'survival','grid':grid_blocks}

    def tooltip_overlay(self, item_id, hover_t):
        """Draw an item tooltip popup when hover_t >= 2.0 seconds."""
        if hover_t < 2.0 or item_id not in ITEM_TOOLTIPS:
            return
        W, H = self.w, self.h
        text = ITEM_TOOLTIPS[item_id]
        fade = min(1.0, (hover_t - 2.0) / 0.4)   # 0.4 s fade-in
        alpha = int(255 * fade)

        s = pygame.Surface((W, H), pygame.SRCALPHA)
        name_surf = self.fm.render(item_name(item_id), True, (230, 220, 255))
        tip_surf  = self.fs.render(f'"{text}"', True, (180, 170, 210))
        tip_surf.set_alpha(alpha); name_surf.set_alpha(alpha)

        tw = max(name_surf.get_width(), tip_surf.get_width()) + 24
        th = name_surf.get_height() + tip_surf.get_height() + 18
        tx = W // 2 - tw // 2
        # Position above the hotbar
        ss2 = 52; pad2 = 4; by2 = H - ss2 - 16
        ty = by2 - th - 64

        bg = pygame.Surface((tw, th), pygame.SRCALPHA)
        bg.fill((15, 12, 28, int(210 * fade)))
        pygame.draw.rect(bg, (120, 90, 180, int(180 * fade)), (0, 0, tw, th), 2, border_radius=6)
        s.blit(bg, (tx, ty))
        s.blit(name_surf, (tx + 12, ty + 8))
        s.blit(tip_surf,  (tx + 12, ty + 8 + name_surf.get_height() + 4))

        self._upload(s, self.tex_overlay)
        self._draw_tex(self.tex_overlay)

    def sign_overlay(self, sign_input):
        """Sign text editor at bottom of screen."""
        W,H=self.w,self.h
        s=pygame.Surface((W,80),pygame.SRCALPHA)
        s.fill((60,40,20,220))
        pygame.draw.line(s,(200,160,80,255),(0,0),(W,0),2)
        lbl=self.fm.render("Sign Text:",True,(220,190,120))
        s.blit(lbl,(12,8))
        txt=self.fs.render(sign_input[:40]+"_",True,(255,240,200))
        s.blit(txt,(12,36))
        hint=self.fs.render(f"Enter=save  Esc=cancel  ({len(sign_input)}/40 chars)",True,(160,130,80))
        s.blit(hint,(12,58))
        tmp=pygame.Surface((W,H),pygame.SRCALPHA); tmp.fill((0,0,0,0))
        tmp.blit(s,(0,H-80))
        self._upload(tmp, self.tex_overlay)
        self._draw_tex(self.tex_overlay)

    def cheats_overlay(self, cheat_input):
        """Draw cheat console at bottom of screen."""
        W,H=self.w,self.h
        s=pygame.Surface((W,60),pygame.SRCALPHA)
        s.fill((0,0,0,200))
        pygame.draw.line(s,(80,200,80,255),(0,0),(W,0),2)
        label=self.fs.render("CHEATS >  " + cheat_input + "_",True,(0,255,0))
        s.blit(label,(12,20))
        hint=self.fs.render("Enter=confirm  Esc=cancel  | gm survival/building/museum  heal  fly  tp x y z  day  night",True,(0,150,0))
        s.blit(hint,(12,38))

        tmp=pygame.Surface((W,H),pygame.SRCALPHA); tmp.fill((0,0,0,0))
        tmp.blit(s,(0,H-60))
        self._upload(tmp, self.tex_overlay)
        self._draw_tex(self.tex_overlay)

    def crafting(self, player, scroll=0):
        W,H=self.w,self.h
        s=pygame.Surface((W,H),pygame.SRCALPHA)
        s.fill((0,0,0,180))

        pw=660; ph=480; px2=(W-pw)//2; py2=(H-ph)//2
        pygame.draw.rect(s,(22,18,35,235),(px2-6,py2-6,pw+12,ph+12),border_radius=10)
        pygame.draw.rect(s,(32,28,48,215),(px2,py2,pw,ph),border_radius=8)

        t=self.fm.render("⚒  Workbench",True,(220,200,140))
        s.blit(t,(px2+pw//2-t.get_width()//2, py2+10))

        ss=56; pad=10; cols=4
        row_h=ss+pad+30
        visible_rows=(ph-50-30)//row_h   # how many rows fit in the panel
        all_recipes=list(RECIPES.items())
        total_rows=(len(all_recipes)+cols-1)//cols
        max_scroll=max(0, total_rows-visible_rows)
        scroll=max(0,min(scroll,max_scroll))

        grid=[]
        for i,(out,recipe) in enumerate(all_recipes):
            col2=i%cols; row=i//cols
            vis_row=row-scroll
            if vis_row<0 or vis_row>=visible_rows: continue
            ix=px2+pad+col2*(ss+pad+80); iy=py2+50+vis_row*row_h

            can=all(player.inv.get(ing,0)>=cnt for ing,cnt in recipe)
            bc=(55,130,65,210) if can else (45,40,65,170)
            pygame.draw.rect(s,bc,(ix-2,iy-2,ss+4,ss+4),border_radius=5)
            self._draw_icon(s, out, ix, iy, ss)

            nm=self.fs.render(item_name(out),True,(200,195,230))
            s.blit(nm,(ix+ss+8,iy))
            ry2=iy+18
            for ing,cnt in recipe:
                have=player.inv.get(ing,0)
                ic=(100,220,100) if have>=cnt else (220,100,100)
                ing_t=self.fs.render(f"  {item_name(ing)} x{cnt}  [{have}]",True,ic)
                s.blit(ing_t,(ix+ss+8,ry2)); ry2+=14

            grid.append((out,ix,iy,ss))

        # Scroll indicator
        if max_scroll>0:
            si=self.fs.render(f"▲▼ scroll  ({scroll+1}/{max_scroll+1})",True,(140,130,170))
            s.blit(si,(px2+pw-si.get_width()-10, py2+ph-22))

        hint=self.fs.render("Click green recipe to craft  |  Scroll to see more  |  E or Esc to close",True,(100,95,125))
        s.blit(hint,(W//2-hint.get_width()//2, py2+ph+10))

        self._upload(s, self.tex_overlay)
        self._draw_tex(self.tex_overlay)
        return grid


# ──────────────────────────────────────────────────────────────
#  BLOCK HIGHLIGHT
# ──────────────────────────────────────────────────────────────
_EDGES=[((0,0,0),(1,0,0)),((1,0,0),(1,0,1)),((1,0,1),(0,0,1)),((0,0,1),(0,0,0)),
        ((0,1,0),(1,1,0)),((1,1,0),(1,1,1)),((1,1,1),(0,1,1)),((0,1,1),(0,1,0)),
        ((0,0,0),(0,1,0)),((1,0,0),(1,1,0)),((1,0,1),(1,1,1)),((0,0,1),(0,1,1))]

def draw_highlight(bx,by,bz):
    glDisable(GL_DEPTH_TEST); glColor4f(1,1,1,0.6); glLineWidth(2.0)
    glBegin(GL_LINES)
    for a,b_ in _EDGES:
        glVertex3f(bx+a[0],by+a[1],bz+a[2])
        glVertex3f(bx+b_[0],by+b_[1],bz+b_[2])
    glEnd()
    glEnable(GL_DEPTH_TEST)


# ──────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────
def main():
    pygame.init()
    pygame.display.set_caption("Saikai — The World That Remembers")

    pygame.display.gl_set_attribute(pygame.GL_ACCELERATED_VISUAL, 1)
    pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)
    pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
    pygame.display.gl_set_attribute(pygame.GL_STENCIL_SIZE, 8)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 2)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 1)

    screen=pygame.display.set_mode((WINDOW_W,WINDOW_H),DOUBLEBUF|OPENGL|RESIZABLE)

    renderer = glGetString(GL_RENDERER).decode() if glGetString(GL_RENDERER) else "Unknown"
    vendor   = glGetString(GL_VENDOR).decode()   if glGetString(GL_VENDOR)   else "Unknown"
    version  = glGetString(GL_VERSION).decode()  if glGetString(GL_VERSION)  else "Unknown"
    print(f"GPU: {vendor} — {renderer}")
    print(f"OpenGL: {version}")
    if "microsoft" in renderer.lower() or "software" in renderer.lower() or "llvmpipe" in renderer.lower():
        print("WARNING: Running on software renderer! Install GPU drivers for better performance.")
    else:
        print("Hardware GPU confirmed.")

    glEnable(GL_DEPTH_TEST); glDepthFunc(GL_LEQUAL); glShadeModel(GL_SMOOTH)
    glHint(GL_FOG_HINT,                    GL_FASTEST)
    glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_FASTEST)
    glHint(GL_LINE_SMOOTH_HINT,            GL_FASTEST)
    glEnable(GL_FOG); glFogi(GL_FOG_MODE,GL_LINEAR)
    glFogf(GL_FOG_START,(RENDER_DIST-1.5)*CHUNK_S)
    glFogf(GL_FOG_END,   RENDER_DIST*CHUNK_S)

    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _tex_dir    = os.path.join(_script_dir, "textures")
    build_atlas(_tex_dir)
    load_item_textures(_tex_dir)
    load_entity_textures(_tex_dir)
    _models_dir = os.path.join(_script_dir, "models")
    load_entity_models(_models_dir)

    def set_proj(w,h):
        glMatrixMode(GL_PROJECTION); glLoadIdentity()
        gluPerspective(FOV,w/max(1,h),0.05,600.0)
        glMatrixMode(GL_MODELVIEW)

    set_proj(WINDOW_W,WINDOW_H)

    try:
        fb=pygame.font.SysFont("Georgia",68,bold=True)
        fm=pygame.font.SysFont("Georgia",26)
        fs=pygame.font.SysFont("Consolas",15)
    except:
        fb=pygame.font.Font(None,68); fm=pygame.font.Font(None,30); fs=pygame.font.Font(None,18)

    print("Generating Saikai world…")
    world=World()
    sx,sz=CHUNK_S//2,CHUNK_S//2
    sy=world.gen.surface(sx,sz)+10
    player=Player(sx+0.5,sy,sz+0.5)

    for dx in range(-2,3):
        for dz in range(-2,3):
            world.get_or_gen(dx,dz)
    for chunk in list(world.chunks.values()):
        chunk.build_mesh(world)

    hud=HUD(WINDOW_W,WINDOW_H,fm,fs)
    enemies=EnemyManager()
    animals=AnimalManager()
    farming=FarmingManager()
    doors=DoorManager()
    beds=BedManager()
    clock=pygame.time.Clock()
    mouse_locked=False; debug=False
    showing_title=True; showing_inv=False; showing_craft=False
    title_buttons=None; title_hovered=None
    gamemode=None
    player=None
    tod=0.35; chunk_timer=0.0; last_t=time.time()
    current_slot=None
    autosave_timer=0.0
    AUTOSAVE_INTERVAL=120
    saves_list=list_saves()
    inv_layout=None; craft_layout=None; search_text=""
    craft_scroll=0
    showing_cheats=False; cheat_input=""
    showing_sign=False; sign_pos=None; sign_input=""
    mining_target=None
    mining_progress=0.0
    lmb_held=False
    pygame.mouse.set_visible(True)

    # ── Tricksabre combo state ───────────────────────────────────
    _trick_yaw_start    = None   # yaw when jump began (while holding tricksabre)
    _trick_yaw_accum    = 0.0   # degrees rotated since jump
    _trick_combo_ready  = False  # True for 1s after a full 360 spin in the air
    _trick_combo_timer  = 0.0   # countdown after completing spin
    _trick_last_yaw     = 0.0   # previous frame's yaw for delta calc
    _trick_jumped       = False  # True once we've left ground with tricksabre
    _trick_was_ground   = True   # previous on_ground state

    # ── Death message state ──────────────────────────────────────
    death_msg_timer     = 0.0   # counts down; >0 means show message
    _player_was_alive   = True  # to detect transition from alive → dead

    # ── Inventory tooltip hover ──────────────────────────────────
    _inv_hover_item     = None   # which item is being hovered
    _inv_hover_time     = 0.0   # how long it's been hovered

    while True:
        now=time.time(); dt=min(now-last_t,0.05); last_t=now
        fps=clock.get_fps(); W,H=screen.get_size()
        mx,my=pygame.mouse.get_pos()

        if showing_title and title_buttons:
            title_hovered=None
            for mode,rect in title_buttons.items():
                if mode=='saves': continue
                if isinstance(rect,pygame.Rect) and rect.collidepoint(mx,my):
                    title_hovered=mode
            for slot_name,rect in title_buttons.get('saves',[]):
                if rect.collidepoint(mx,my): title_hovered=slot_name

        for ev in pygame.event.get():
            if ev.type==QUIT:
                if player and current_slot:
                    save_game(current_slot, world, player, tod, farming, doors, beds)
                world.shutdown(); pygame.quit(); sys.exit()

            elif ev.type==VIDEORESIZE:
                screen=pygame.display.set_mode((ev.w,ev.h),DOUBLEBUF|OPENGL|RESIZABLE)
                set_proj(ev.w,ev.h); glViewport(0,0,ev.w,ev.h); hud.resize(ev.w,ev.h)

            elif ev.type==KEYDOWN:
                if showing_title:
                    continue

                if showing_sign:
                    if ev.key==K_ESCAPE:
                        showing_sign=False; sign_pos=None; sign_input=""
                        pygame.mouse.set_visible(False)
                        pygame.event.set_grab(True); mouse_locked=True
                        pygame.mouse.get_rel()
                    elif ev.key==K_RETURN:
                        if sign_pos: SIGN_TEXTS[sign_pos]=sign_input[:SIGN_MAX_CHARS]
                        showing_sign=False; sign_pos=None; sign_input=""
                        pygame.mouse.set_visible(False)
                        pygame.event.set_grab(True); mouse_locked=True
                        pygame.mouse.get_rel()
                    elif ev.key==K_BACKSPACE:
                        sign_input=sign_input[:-1]
                    elif ev.unicode and ev.unicode.isprintable():
                        if len(sign_input)<SIGN_MAX_CHARS: sign_input+=ev.unicode
                    continue

                if showing_cheats:
                    if ev.key==K_ESCAPE:
                        showing_cheats=False; cheat_input=""
                        pygame.mouse.set_visible(False)
                        pygame.event.set_grab(True); mouse_locked=True
                        pygame.mouse.get_rel()
                    elif ev.key==K_RETURN:
                        cmd=cheat_input.strip().lstrip('/').lower()
                        if cmd in ('survival','building','museum','gm survival','gm building','gm museum'):
                            gm=cmd.split()[-1]
                            player.gamemode=gm
                            if gm==GAMEMODE_BUILDING: player.flying=True
                            else: player.flying=False
                        elif cmd in ('gm 0','gamemode survival'): player.gamemode=GAMEMODE_SURVIVAL; player.flying=False
                        elif cmd in ('gm 1','gamemode building'): player.gamemode=GAMEMODE_BUILDING; player.flying=True
                        elif cmd in ('gm 2','gamemode museum'):   player.gamemode=GAMEMODE_MUSEUM; player.flying=False
                        elif cmd=='heal' or cmd=='health': player.health=player.max_health
                        elif cmd=='fly': player.flying=not player.flying; player.vy=0
                        elif cmd.startswith('tp '):
                            try:
                                parts=cmd.split(); player.x=float(parts[1]); player.y=float(parts[2]); player.z=float(parts[3])
                            except: pass
                        elif cmd=='day': tod=0.4
                        elif cmd=='night': tod=0.8
                        showing_cheats=False; cheat_input=""
                        pygame.mouse.set_visible(False)
                        pygame.event.set_grab(True); mouse_locked=True
                        pygame.mouse.get_rel()
                    elif ev.key==K_BACKSPACE:
                        cheat_input=cheat_input[:-1]
                    elif ev.unicode and ev.unicode.isprintable():
                        if len(cheat_input)<60: cheat_input+=ev.unicode
                    continue

                if showing_inv or showing_craft:
                    if ev.key==K_ESCAPE or ev.key==K_e:
                        showing_inv=False; showing_craft=False; search_text=""
                        pygame.mouse.set_visible(False)
                        pygame.event.set_grab(True); mouse_locked=True
                        pygame.mouse.get_rel()
                    elif showing_craft and ev.key==K_UP:
                        craft_scroll=max(0, craft_scroll-1)
                    elif showing_craft and ev.key==K_DOWN:
                        craft_scroll+=1
                    elif showing_inv and ev.key==K_BACKSPACE:
                        search_text=search_text[:-1]
                    elif showing_inv and ev.unicode and ev.unicode.isprintable():
                        search_text+=ev.unicode
                    continue

                if ev.key==K_ESCAPE:
                    if mouse_locked:
                        pygame.mouse.set_visible(True); pygame.event.set_grab(False)
                        mouse_locked=False
                    else:
                        if player and current_slot:
                            save_game(current_slot, world, player, tod, farming, doors, beds)
                        world.shutdown(); pygame.quit(); sys.exit()
                elif ev.key==K_SPACE:   player.jump()
                elif ev.key==K_f:
                    player.flying=not player.flying; player.vy=0
                elif ev.key==K_TAB:     debug=not debug
                elif ev.key in (K_1,K_2,K_3,K_4,K_5,K_6,K_7,K_8,K_9):
                    player.selected=ev.key-K_1
                elif ev.key==K_e:
                    showing_inv=True; showing_craft=False
                    pygame.mouse.set_visible(True); pygame.event.set_grab(False)
                    mouse_locked=False; search_text=""
                elif ev.key==K_SLASH and player:
                    showing_cheats=True; cheat_input="/"
                    pygame.mouse.set_visible(True); pygame.event.set_grab(False)
                    mouse_locked=False

            elif ev.type==MOUSEBUTTONDOWN:
                if showing_title:
                    if ev.button==1 and title_buttons:
                        for mode,rect in title_buttons.items():
                            if mode=='saves': continue
                            if isinstance(rect,pygame.Rect) and rect.collidepoint(mx,my):
                                gamemode=mode
                                slot_name=f"{mode}_{int(time.time())}"
                                current_slot=slot_name
                                world.save_slot=slot_name
                                player=Player(sx+0.5,sy,sz+0.5, gamemode)
                                saves_list=list_saves()
                                showing_title=False
                                pygame.mouse.set_visible(False)
                                pygame.event.set_grab(True); mouse_locked=True
                                break
                        else:
                            for slot_name,rect in title_buttons.get('saves',[]):
                                if rect.collidepoint(mx,my):
                                    meta=load_game(slot_name, world)
                                    if meta:
                                        gamemode=meta.get('gamemode', GAMEMODE_SURVIVAL)
                                        player=Player(sx+0.5,sy,sz+0.5, gamemode)
                                        apply_meta_to_player(meta, player, farming, doors, beds, world)
                                        tod=meta.get('tod', 0.35)
                                        current_slot=slot_name
                                        world.save_slot=slot_name
                                        wg_warn=check_worldgen_compat(meta)
                                        if wg_warn: print(f"[COMPAT] {wg_warn}")
                                        for chunk in list(world.chunks.values()):
                                            chunk.dirty=True
                                        saves_list=list_saves()
                                        showing_title=False
                                        pygame.mouse.set_visible(False)
                                        pygame.event.set_grab(True); mouse_locked=True
                                    break
                    continue

                if showing_inv or showing_craft:
                    if ev.button==1:
                        if showing_craft and craft_layout:
                            for out,ix,iy,bss2 in craft_layout:
                                if ix<=mx<ix+bss2 and iy<=my<iy+bss2:
                                    player.craft(out, at_workbench=True)
                                    break
                        elif showing_inv and inv_layout:
                            if player.gamemode==GAMEMODE_BUILDING:
                                for bid,ix,iy,bss2 in inv_layout.get('grid',[]):
                                    if ix<=mx<ix+bss2 and iy<=my<iy+bss2:
                                        if bid in player.hotbar:
                                            idx=player.hotbar.index(bid)
                                            player.hotbar[idx]=None
                                        else:
                                            for i in range(9):
                                                if player.hotbar[i] is None:
                                                    player.hotbar[i]=bid; break
                                            else:
                                                player.hotbar[player.selected]=bid
                                        break
                            else:
                                for entry in inv_layout.get('grid',[]):
                                    iid,ix,iy,bss2=entry[0],entry[1],entry[2],entry[3]
                                    if ix<=mx<ix+bss2 and iy<=my<iy+bss2:
                                        if isinstance(iid,str) and iid.startswith('craft_'):
                                            player.craft(int(iid[6:]), at_workbench=False)
                                        elif iid in FOOD_HEAL:
                                            player.use_item(iid)
                                        else:
                                            if iid in player.hotbar:
                                                idx=player.hotbar.index(iid)
                                                player.hotbar[idx]=None
                                            else:
                                                for i in range(9):
                                                    if player.hotbar[i] is None:
                                                        player.hotbar[i]=iid; break
                                                else:
                                                    player.hotbar[player.selected]=iid
                                        break
                    continue

                if not mouse_locked:
                    pygame.mouse.set_visible(False); pygame.event.set_grab(True)
                    mouse_locked=True
                    pygame.mouse.get_rel()
                    continue

                if ev.button==1:
                    if player.gamemode==GAMEMODE_SURVIVAL:
                        hit_e = enemies.hit_scan(player,world, tricksabre_combo=_trick_combo_ready)
                        hit_a = animals.hit_scan(player,world, tricksabre_combo=_trick_combo_ready)
                        if hit_e or hit_a:
                            if _trick_combo_ready:
                                _trick_combo_ready = False
                                _trick_combo_timer = 0.0
                        if not hit_e and not hit_a:
                            lmb_held=True
                    else:
                        hit,_=player.raycast(world)
                        if hit:
                            bid=world.get_block(*hit)
                            player.on_break(bid)
                            world.set_block(*hit,AIR)
                            bx3,by3,bz3=hit
                            if bid in (DOOR_BLOCK, GLASS_DOOR):
                                world.set_block(bx3,by3+1,bz3,AIR)
                                doors.remove(bx3,by3,bz3)
                            elif bid in (DOOR_TOP, GLASS_DOOR_TOP):
                                world.set_block(bx3,by3-1,bz3,AIR)
                                doors.remove(bx3,by3-1,bz3)
                            elif bid in (BED_BLOCK, BED_FOOT):
                                beds.remove(bx3,by3,bz3,world)
                elif ev.button==3:
                    hit,prev=player.raycast(world)
                    selected_bid=player.selected_block()
                    if hit and world.get_block(*hit)==SIGN_BLOCK:
                        bx2,by2,bz2=hit
                        sign_pos=(int(bx2),int(by2),int(bz2))
                        sign_input=SIGN_TEXTS.get(sign_pos,"")
                        showing_sign=True; showing_inv=False; showing_craft=False
                        pygame.mouse.set_visible(True); pygame.event.set_grab(False)
                        mouse_locked=False; pygame.mouse.get_rel()
                    elif hit and world.get_block(*hit)==WORKBENCH and player.gamemode==GAMEMODE_SURVIVAL:
                        showing_craft=True; showing_inv=False; craft_scroll=0
                        pygame.mouse.set_visible(True); pygame.event.set_grab(False)
                        mouse_locked=False
                        pygame.mouse.get_rel()
                    elif hit and world.get_block(*hit)==FURNACE_BLOCK and player.gamemode==GAMEMODE_SURVIVAL:
                        smelted=False
                        for src,dst in FURNACE_RECIPES.items():
                            if player.inv.get(src,0)>0:
                                player.remove_from_inv(src,1)
                                player.add_to_inv(dst,1)
                                player._sync_hotbar()
                                smelted=True
                                break
                    elif hit and world.get_block(*hit) in (DOOR_BLOCK, DOOR_TOP, GLASS_DOOR, GLASS_DOOR_TOP):
                        bx2,by2,bz2=hit
                        if world.get_block(bx2,by2,bz2) in (DOOR_TOP, GLASS_DOOR_TOP):
                            by2-=1
                        doors.toggle(bx2,by2,bz2)
                    elif hit and world.get_block(*hit) in (BED_BLOCK, BED_FOOT):
                        bx2,by2,bz2=hit
                        if beds.try_sleep(bx2,by2,bz2,tod):
                            tod=0.28   # skip to early morning
                    elif selected_bid in (ITEM_WOOD_SHOVEL, ITEM_STONE_SHOVEL) and hit and player.gamemode==GAMEMODE_SURVIVAL:
                        if world.get_block(*hit)==KEIRO_GRASS:
                            player.add_to_inv(ITEM_WHEAT_SEEDS, random.randint(1,2))
                            player._sync_hotbar()
                    elif selected_bid==ITEM_HOE and hit and player.gamemode==GAMEMODE_SURVIVAL:
                        farming.till(world, player, *hit)
                    elif selected_bid==ITEM_WHEAT_SEEDS and hit and player.gamemode==GAMEMODE_SURVIVAL:
                        bx2,by2,bz2=hit
                        if farming.plant(world,bx2,by2+1,bz2):
                            player.remove_from_inv(ITEM_WHEAT_SEEDS,1)
                            player._sync_hotbar()
                    elif selected_bid in FOOD_HEAL and player.gamemode==GAMEMODE_SURVIVAL:
                        player.use_item(selected_bid)
                    elif player.gamemode!=GAMEMODE_MUSEUM and selected_bid is not None and player.can_place(selected_bid) and isinstance(selected_bid,int) and selected_bid < NUM_BLOCKS:
                        if hit and prev:
                            bx2,by2,bz2=prev; hw=player.width/2
                            if not(player.x-hw<bx2+1 and player.x+hw>bx2 and
                                   player.y<by2+1 and player.y+player.height>by2 and
                                   player.z-hw<bz2+1 and player.z+hw>bz2):
                                world.set_block(bx2,by2,bz2,selected_bid)
                                player.on_place(selected_bid)
                                if selected_bid in (DOOR_BLOCK, GLASS_DOOR) and by2+1<CHUNK_H:
                                    top_bid = GLASS_DOOR_TOP if selected_bid==GLASS_DOOR else DOOR_TOP
                                    if world.get_block(bx2,by2+1,bz2)==AIR:
                                        world.set_block(bx2,by2+1,bz2,top_bid)
                                    facing=player_facing_cardinal(player.yaw)
                                    doors.place(bx2,by2,bz2,facing,kind=selected_bid)
                                elif selected_bid==BED_BLOCK:
                                    # Cancel the default set_block — BedManager does both tiles
                                    world.set_block(bx2,by2,bz2,AIR)
                                    facing=player_facing_cardinal(player.yaw)
                                    if not beds.place(bx2,by2,bz2,facing,world):
                                        player.add_to_inv(BED_BLOCK,1)  # refund if blocked
                elif ev.button==4:
                    if showing_craft: craft_scroll=max(0,craft_scroll-1)
                    else: player.selected=(player.selected-1)%9
                elif ev.button==5:
                    if showing_craft: craft_scroll+=1
                    else: player.selected=(player.selected+1)%9

            elif ev.type==MOUSEBUTTONUP:
                if ev.button==1:
                    lmb_held=False
                    mining_target=None; mining_progress=0.0

        if showing_title:
            glClearColor(0.03,0.02,0.07,1); glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
            title_buttons=hud.title(fb,fm,title_hovered, saves=saves_list)
            pygame.display.flip(); clock.tick(60); continue

        mdx,mdy=pygame.mouse.get_rel() if mouse_locked else (0,0)
        if not showing_inv and not showing_craft and mouse_locked:
            player.update(world,dt,pygame.key.get_pressed(),mdx,mdy,doors)

        if lmb_held and mouse_locked and not showing_inv and not showing_craft and player:
            hit,_=player.raycast(world)
            if hit:
                if hit!=mining_target:
                    mining_target=hit; mining_progress=0.0
                bid=world.get_block(*hit)
                mine_t=get_mine_time(bid, player.selected_block())
                if mine_t==0:
                    player.on_break(bid); world.set_block(*hit,AIR)
                    mining_target=None; mining_progress=0.0
                else:
                    mining_progress+=dt/mine_t
                    if mining_progress>=1.0:
                        player.on_break(bid); world.set_block(*hit,AIR)
                        bx3,by3,bz3=hit
                        if bid in (DOOR_BLOCK, GLASS_DOOR):
                            if world.get_block(bx3,by3+1,bz3) in (DOOR_TOP, GLASS_DOOR_TOP):
                                world.set_block(bx3,by3+1,bz3,AIR)
                            doors.remove(bx3,by3,bz3)
                        elif bid in (DOOR_TOP, GLASS_DOOR_TOP):
                            if world.get_block(bx3,by3-1,bz3) in (DOOR_BLOCK, GLASS_DOOR):
                                world.set_block(bx3,by3-1,bz3,AIR)
                            doors.remove(bx3,by3-1,bz3)
                        elif bid in (BED_BLOCK, BED_FOOT):
                            beds.remove(bx3,by3,bz3,world)
                        mining_target=None; mining_progress=0.0
            else:
                mining_target=None; mining_progress=0.0
        elif not lmb_held:
            mining_target=None; mining_progress=0.0

        if player and player.gamemode==GAMEMODE_SURVIVAL:
            enemies.update(world,player,dt,tod)
            animals.update(world,player,dt)
        if player:
            farming.tick(world,dt)
        doors.update(dt)
        beds.check_player_collide(player)

        # ── Tricksabre 360-jump combo tracking ──────────────────────
        if player and player.gamemode==GAMEMODE_SURVIVAL:
            sel = player.selected_block()
            if sel == ITEM_TRICKSABRE:
                cur_yaw = player.yaw
                # Detect leaving ground (jump moment)
                if _trick_was_ground and not player.on_ground:
                    _trick_jumped      = True
                    _trick_yaw_start   = cur_yaw
                    _trick_yaw_accum   = 0.0
                    _trick_last_yaw    = cur_yaw
                # Accumulate rotation while airborne
                if _trick_jumped and not player.on_ground:
                    delta = (_trick_last_yaw - cur_yaw + 180) % 360 - 180  # signed delta
                    _trick_yaw_accum += abs(delta)
                    _trick_last_yaw   = cur_yaw
                    # Full 360 spin detected
                    if _trick_yaw_accum >= 360.0 and not _trick_combo_ready:
                        _trick_combo_ready = True
                        _trick_combo_timer = 1.0   # 1 second window
                # Landed — reset jump tracking
                if _trick_jumped and player.on_ground:
                    _trick_jumped    = False
                    _trick_yaw_accum = 0.0
                _trick_was_ground = player.on_ground
                # Combo window countdown
                if _trick_combo_ready:
                    _trick_combo_timer -= dt
                    if _trick_combo_timer <= 0:
                        _trick_combo_ready = False
                        _trick_combo_timer = 0.0
            else:
                # Switched away from tricksabre — reset everything
                _trick_jumped      = False
                _trick_yaw_accum   = 0.0
                _trick_combo_ready = False
                _trick_combo_timer = 0.0
                _trick_was_ground  = player.on_ground

        # ── Death detection → trigger "why couldn't i" message ──────
        if player and player.gamemode==GAMEMODE_SURVIVAL:
            is_alive = player.health > 0
            if _player_was_alive and not is_alive:
                # Player just died — check if holding tricksabre
                if player.selected_block() == ITEM_TRICKSABRE:
                    # Respawn
                    player.health = player.max_health
                    player.y = world.gen.surface(int(player.x), int(player.z)) + 2.0
                    player.vy = 0.0
                    death_msg_timer = 5.0   # show for 5 seconds
                else:
                    player.health = player.max_health
                    player.y = world.gen.surface(int(player.x), int(player.z)) + 2.0
                    player.vy = 0.0
            elif is_alive and death_msg_timer > 0:
                death_msg_timer = max(0.0, death_msg_timer - dt)
            _player_was_alive = is_alive

        # ── Inventory tooltip hover ──────────────────────────────────
        if showing_inv and inv_layout and player:
            hovered_item = None
            if inv_layout.get('mode') in ('survival', 'building'):
                for entry in inv_layout.get('grid', []):
                    iid, ix, iy, bss2 = entry[0], entry[1], entry[2], entry[3]
                    if isinstance(iid, int) and iid in ITEM_TOOLTIPS:
                        if ix <= mx < ix+bss2 and iy <= my < iy+bss2:
                            hovered_item = iid
                            break
            if hovered_item == _inv_hover_item and hovered_item is not None:
                _inv_hover_time += dt
            else:
                _inv_hover_item = hovered_item
                _inv_hover_time = 0.0
        else:
            _inv_hover_item = None
            _inv_hover_time = 0.0

        tod=(tod+dt*0.005)%1.0

        if player and current_slot:
            autosave_timer+=dt
            if autosave_timer>=AUTOSAVE_INTERVAL:
                autosave_timer=0.0
                save_game(current_slot, world, player, tod, farming, doors, beds)

        chunk_timer+=dt
        if chunk_timer>0.08:
            world.load_around(player.x,player.z); chunk_timer=0.0

        world.pump_ready()
        world.rebuild_dirty(player.x,player.z)

        sc=sky_color(tod)
        glClearColor(*sc,1.0); glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        glFogfv(GL_FOG_COLOR,[*sc,1.0])

        glLoadIdentity()
        glRotatef(-player.pitch,1,0,0)
        glRotatef(-player.yaw,  0,1,0)
        glTranslatef(-player.x,-(player.y+player.height*0.85),-player.z)

        draw_skyscreen_blocks(world, player.x, player.z, sc)  # depth-only pre-pass — must be before world.render
        world.render(player.x,player.z)
        draw_billboard_blocks(world, player.x, player.y, player.z, player.yaw)
        draw_sign_blocks(world, player.x, player.y, player.z, player.yaw, player.pitch, fs)
        enemies.draw(player.x,player.z)
        animals.draw(player.x,player.z)
        doors.draw(player.x,player.z)
        draw_glass_blocks(world, player.x, player.y, player.z)
        beds.draw(player.x, player.z,
                  ITEM_GL_TEXTURES.get(BED_BLOCK), ITEM_GL_TEXTURES.get(BED_FOOT))

        if not showing_inv and not showing_craft:
            hit,_=player.raycast(world)
            if hit and mouse_locked:
                draw_highlight(*hit)
                if mining_target==hit and mining_progress>0:
                    bx2,by2,bz2=hit
                    p=mining_progress
                    glDisable(GL_DEPTH_TEST)
                    glColor4f(0,0,0, min(0.6, p*0.7))
                    glBegin(GL_QUADS)
                    for face in [
                        [(0,0,0),(1,0,0),(1,0,1),(0,0,1)],
                        [(0,1,0),(1,1,0),(1,1,1),(0,1,1)],
                        [(0,0,0),(1,0,0),(1,1,0),(0,1,0)],
                        [(0,0,1),(1,0,1),(1,1,1),(0,1,1)],
                        [(0,0,0),(0,0,1),(0,1,1),(0,1,0)],
                        [(1,0,0),(1,0,1),(1,1,1),(1,1,0)],
                    ]:
                        for vx,vy,vz in face:
                            glVertex3f(bx2+vx,by2+vy,bz2+vz)
                    glEnd()
                    glEnable(GL_DEPTH_TEST)

        hud.update(player, world, fps, debug, tod,
                   mining_progress if mining_target else 0,
                   tooltip_item=_inv_hover_item,
                   tooltip_hover_t=_inv_hover_time,
                   death_msg_timer=death_msg_timer)
        hud.draw()

        if showing_sign:
            hud.sign_overlay(sign_input)
        elif showing_cheats:
            hud.cheats_overlay(cheat_input)
        elif showing_inv:
            inv_layout=hud.inventory(player, search_text)
            hud.tooltip_overlay(_inv_hover_item, _inv_hover_time)
        elif showing_craft:
            craft_layout=hud.crafting(player, scroll=craft_scroll)

        pygame.display.flip()
        clock.tick(60)

    world.shutdown()
    pygame.quit()
    sys.exit()


if __name__=="__main__":
    mp.freeze_support()
    main()