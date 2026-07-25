# entities.py  ─  Mobs, animals, farming, and entity rendering for Saikai
# ──────────────────────────────────────────────────────────────────────────
#
#  ENTITY MODEL SYSTEM
#  ───────────────────
#  Entities can define a multi-part 3D model as a list of box parts.
#  Each part is a dict with keys:
#    offset (ox, oy, oz)  centre of box relative to entity foot-centre
#    size   (sx, sy, sz)  full dimensions
#    tex    str | None    key into ENTITY_TEXTURES (cube-wrap skin texture)
#    shade  float         brightness multiplier 0-1
#
#  UV cube-unwrap layout on a 64x32 skin texture (4 cols x 2 rows of tiles):
#    col 0 row 1 = left face    col 1 row 0 = top face
#    col 1 row 1 = front face   col 2 row 0 = bottom face
#    col 2 row 1 = right face   col 3 row 1 = back face
#
#  If kind has no entry in ENTITY_MODELS  -> plain cube (textured or white).
#  If a part's tex key is absent/unloaded -> that part renders solid white.
# ──────────────────────────────────────────────────────────────────────────

import math, os, random

from OpenGL.GL import (
    glBegin, glEnd, glVertex3f, glColor3f,
    glEnable, glDisable, glBindTexture, glGenTextures,
    glTexParameteri, glTexImage2D, glPushMatrix, glPopMatrix,
    glTranslatef, glRotatef, glTexCoord2f,
    GL_QUADS, GL_TEXTURE_2D, GL_DEPTH_TEST,
    GL_TEXTURE_MIN_FILTER, GL_TEXTURE_MAG_FILTER,
    GL_NEAREST, GL_RGBA, GL_UNSIGNED_BYTE,
)

# ── Constants injected by main.py via init() ────────────────────────────
SOLID_SET         = None
RENDER_DIST       = None
CHUNK_S           = None
GRAVITY           = None
JUMP_SPEED        = None
GAMEMODE_SURVIVAL = None
AIR = KEIRO_GRASS = KEIRO_SOIL = MORI_MOSS = FARMLAND = None
WHEAT_STAGE0 = WHEAT_STAGE1 = WHEAT_STAGE2 = WHEAT_STAGE3 = None
ITEM_WOOD_SWORD = ITEM_STONE_SWORD = ITEM_TRICKSABRE = None
ITEM_WHEAT = ITEM_WHEAT_SEEDS = ITEM_RAW_MEAT = ITEM_WOOL = None
WHEAT_STAGES = []


def init(solid_set, render_dist, chunk_s, gravity, jump_speed,
         gamemode_survival,
         air, keiro_grass, keiro_soil, mori_moss, farmland,
         wheat_stage0, wheat_stage1, wheat_stage2, wheat_stage3,
         item_wood_sword, item_stone_sword,
         item_wheat, item_wheat_seeds, item_raw_meat, item_wool,
         item_tricksabre=None):
    global SOLID_SET, RENDER_DIST, CHUNK_S, GRAVITY, JUMP_SPEED
    global GAMEMODE_SURVIVAL
    global AIR, KEIRO_GRASS, KEIRO_SOIL, MORI_MOSS, FARMLAND
    global WHEAT_STAGE0, WHEAT_STAGE1, WHEAT_STAGE2, WHEAT_STAGE3
    global ITEM_WOOD_SWORD, ITEM_STONE_SWORD, ITEM_TRICKSABRE
    global ITEM_WHEAT, ITEM_WHEAT_SEEDS, ITEM_RAW_MEAT, ITEM_WOOL
    global WHEAT_STAGES
    SOLID_SET         = solid_set
    RENDER_DIST       = render_dist
    CHUNK_S           = chunk_s
    GRAVITY           = gravity
    JUMP_SPEED        = jump_speed
    GAMEMODE_SURVIVAL = gamemode_survival
    AIR               = air
    KEIRO_GRASS       = keiro_grass
    KEIRO_SOIL        = keiro_soil
    MORI_MOSS         = mori_moss
    FARMLAND          = farmland
    WHEAT_STAGE0      = wheat_stage0
    WHEAT_STAGE1      = wheat_stage1
    WHEAT_STAGE2      = wheat_stage2
    WHEAT_STAGE3      = wheat_stage3
    ITEM_WOOD_SWORD   = item_wood_sword
    ITEM_STONE_SWORD  = item_stone_sword
    ITEM_TRICKSABRE   = item_tricksabre
    ITEM_WHEAT        = item_wheat
    ITEM_WHEAT_SEEDS  = item_wheat_seeds
    ITEM_RAW_MEAT     = item_raw_meat
    ITEM_WOOL         = item_wool
    WHEAT_STAGES      = [wheat_stage0, wheat_stage1, wheat_stage2, wheat_stage3]


# ══════════════════════════════════════════════════════════════════════════
#  SHARED MOVEMENT HELPERS
# ══════════════════════════════════════════════════════════════════════════

def _entity_move(ent, world, move_x, move_z, dt):
    hw = ent.width / 2

    def body_blocked(nx, nz):
        for ox, oz in ((hw,0),(-hw,0),(0,hw),(0,-hw),(hw,hw),(-hw,-hw),(hw,-hw),(-hw,hw)):
            bx  = int(math.floor(nx + ox))
            bz2 = int(math.floor(nz + oz))
            for by_off in (0.05, 0.5, ent.height - 0.05):
                if world.get_block(bx, int(math.floor(ent.y + by_off)), bz2) in SOLID_SET:
                    return True
        return False

    blocked_x = body_blocked(ent.x + move_x * dt, ent.z)
    blocked_z = body_blocked(ent.x, ent.z + move_z * dt)

    if (blocked_x or blocked_z) and ent.on_ground and ent.vy == 0:
        bx_c  = int(math.floor(ent.x + (move_x * dt if blocked_x else 0)))
        bz_c2 = int(math.floor(ent.z + (move_z * dt if blocked_z else 0)))
        wall_top   = int(math.floor(ent.y + 1.0))
        head_clear = world.get_block(bx_c, wall_top + int(math.ceil(ent.height)), bz_c2)
        ledge_top  = world.get_block(bx_c, wall_top, bz_c2)
        if ledge_top not in SOLID_SET and head_clear not in SOLID_SET:
            ent.vy = JUMP_SPEED * 0.7
            ent.on_ground = False

    if not blocked_x:
        ent.x += move_x * dt
    if not blocked_z:
        ent.z += move_z * dt

    ent.vy = max(ent.vy + GRAVITY * dt, -30)
    ny     = ent.y + ent.vy * dt

    foot_cols = [
        (int(math.floor(ent.x - hw + 0.01)), int(math.floor(ent.z - hw + 0.01))),
        (int(math.floor(ent.x + hw - 0.01)), int(math.floor(ent.z - hw + 0.01))),
        (int(math.floor(ent.x - hw + 0.01)), int(math.floor(ent.z + hw - 0.01))),
        (int(math.floor(ent.x + hw - 0.01)), int(math.floor(ent.z + hw - 0.01))),
    ]
    by_feet = int(math.floor(ny))
    by_head = int(math.floor(ny + ent.height - 0.05))

    hit_floor = ent.vy < 0 and any(
        world.get_block(cx, by_feet, cz) in SOLID_SET for cx, cz in foot_cols)
    hit_ceil  = ent.vy > 0 and any(
        world.get_block(cx, by_head, cz) in SOLID_SET for cx, cz in foot_cols)

    if hit_floor:
        ent.vy = 0; ent.on_ground = True; ent.y = float(by_feet + 1)
    elif hit_ceil:
        ent.vy = 0; ent.y = ny
    else:
        ent.y = ny
        if ent.vy < -0.5:
            ent.on_ground = False

    stuck = any(
        world.get_block(cx, int(math.floor(ent.y + 0.05)), cz) in SOLID_SET
        for cx, cz in foot_cols)
    if stuck:
        ent.y = math.floor(ent.y + 0.05) + 1.0
        ent.vy = 0; ent.on_ground = True


def _entity_spawn_safe(world, sx, sy, sz, width, height):
    hw = width / 2
    for oy in range(int(math.ceil(height)) + 1):
        for ox, oz in ((hw,0),(-hw,0),(0,hw),(0,-hw),(0,0)):
            if world.get_block(int(math.floor(sx+ox)), sy+oy,
                               int(math.floor(sz+oz))) in SOLID_SET:
                return False
    if world.get_block(int(math.floor(sx)), sy-1, int(math.floor(sz))) not in SOLID_SET:
        return False
    return True


# ══════════════════════════════════════════════════════════════════════════
#  ENTITY TEXTURE SYSTEM
# ══════════════════════════════════════════════════════════════════════════

ENTITY_TEXTURES: dict = {}


def load_entity_textures(tex_dir):
    """Load 64x32 cube-wrap skin textures for each entity type.
    Generates a coloured placeholder if the PNG file is absent."""
    from PIL import Image as PILImage
    entries = [
        ('grunt_body',   64, 32),
        ('brute_body',   64, 32),
        ('lurker_body',  64, 32),
        ('sheep_body',   64, 32),
        ('pig_body',     64, 32),
        ('chicken_body', 64, 32),
    ]
    for stem, tw, th in entries:
        path = os.path.join(tex_dir, f"{stem}.png")
        if os.path.exists(path):
            img = PILImage.open(path).convert("RGBA").resize((tw, th), PILImage.NEAREST)
        else:
            img = _make_default_entity_tex(stem, tw, th)
        data = img.tobytes("raw", "RGBA", 0, -1)
        tid  = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tid)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, tw, th, 0,
                     GL_RGBA, GL_UNSIGNED_BYTE, data)
        glBindTexture(GL_TEXTURE_2D, 0)
        ENTITY_TEXTURES[stem] = tid
    print(f"Loaded {len(ENTITY_TEXTURES)} entity textures")


def _make_default_entity_tex(name, tw, th):
    """Procedurally generated 64x32 placeholder skin with shaded faces."""
    from PIL import Image as PILImage, ImageDraw
    img = PILImage.new("RGBA", (tw, th), (0,0,0,0))
    d   = ImageDraw.Draw(img)
    bases = {
        'grunt':   (210, 55, 55),
        'brute':   (150, 35,170),
        'lurker':  ( 35,155,195),
        'sheep':   (225,225,225),
        'pig':     (240,175,155),
        'chicken': (240,230,195),
    }
    base = (170,170,170)
    for key, col in bases.items():
        if key in name:
            base = col; break

    # 4 cols x 2 rows; each tile shaded differently
    cw, ch = tw//4, th//2
    tile_shades = [
        # (col, row, brightness)
        (0,0, 0.82),(1,0, 1.00),(2,0, 0.68),(3,0, 0.80),
        (0,1, 0.76),(1,1, 0.96),(2,1, 0.82),(3,1, 0.72),
    ]
    for tx, ty, br in tile_shades:
        x0, y0 = tx*cw, ty*ch
        r = min(255, int(base[0]*br))
        g = min(255, int(base[1]*br))
        b = min(255, int(base[2]*br))
        d.rectangle([x0, y0, x0+cw-1, y0+ch-1], fill=(r,g,b,220))
        d.rectangle([x0, y0, x0+cw-1, y0+ch-1], outline=(0,0,0,55))

    # Eyes on front-face tile (col 1, row 1)
    fx, fy = cw, ch
    ew, eh = max(2, cw//5), max(2, ch//3)
    ec = (20,15,15,255)
    d.ellipse([fx+ew,      fy+eh,      fx+ew*2,   fy+eh*2],  fill=ec)
    d.ellipse([fx+cw-ew*2, fy+eh,      fx+cw-ew,  fy+eh*2],  fill=ec)
    return img


# ══════════════════════════════════════════════════════════════════════════
#  ENTITY MODEL LOADER  (.obj  and  .smodel)
# ══════════════════════════════════════════════════════════════════════════
#
#  Models live in the  models/  folder next to main.py.
#  One file per entity kind, named after the kind:
#     models/grunt.obj      <- preferred  (standard Wavefront OBJ)
#     models/grunt.smodel   <- fallback   (Saikai box-part format)
#
#  If both exist for the same kind, .obj takes priority.
#  If neither exists, that entity falls back to a plain cube at runtime.
#
# -- OBJ -------------------------------------------------------------------
#  Standard Wavefront OBJ is supported:
#    v   x y z        vertex positions
#    vt  u v          UV coordinates  (optional -- defaults to 0,0)
#    vn  x y z        normals         (parsed but ignored)
#    f   v[/t[/n]]    faces           (tris or quads; quads are split)
#    mtllib <file>    companion .mtl  (looked up in models/)
#    usemtl <name>    switch material
#
#  .mtl fields used:
#    newmtl <name>
#    map_Kd <file>    diffuse texture PNG (searched in models/, then textures/)
#    Kd r g b         diffuse colour fallback when no texture is set
#
# -- .smodel ---------------------------------------------------------------
#  Box-part format kept for hand-authoring:
#    part <n>  offset <ox> <oy> <oz>  size <sx> <sy> <sz>  [tex <key>]  [shade <f>]
#  Lines starting with # are comments.
#
# ══════════════════════════════════════════════════════════════════════════

# OBJ mesh models: kind -> list of draw-group dicts
#   each group: {'tex': GL_id|None, 'color': (r,g,b), 'tris': [...]}
ENTITY_OBJ_MODELS: dict = {}

# .smodel box-part models: kind -> list of part dicts
ENTITY_MODELS:     dict = {}


def load_entity_models(models_dir):
    """
    Scan models_dir for *.obj and *.smodel files.
    .obj takes priority when both exist for the same kind.
    """
    ENTITY_OBJ_MODELS.clear()
    ENTITY_MODELS.clear()

    if not os.path.isdir(models_dir):
        print(f"[models] directory not found: {models_dir}  -- entities will use cube fallback")
        return

    stems = {}   # stem -> {'obj': path, 'smodel': path}
    for fname in os.listdir(models_dir):
        if fname.endswith('.obj'):
            stem = fname[:-4]
            stems.setdefault(stem, {})['obj'] = os.path.join(models_dir, fname)
        elif fname.endswith('.smodel'):
            stem = fname[:-7]
            stems.setdefault(stem, {})['smodel'] = os.path.join(models_dir, fname)

    obj_loaded = []
    smodel_loaded = []

    for kind, paths in stems.items():
        if 'obj' in paths:
            mesh = _parse_obj(paths['obj'], models_dir, kind)
            if mesh is not None:
                ENTITY_OBJ_MODELS[kind] = mesh
                obj_loaded.append(kind)
                continue
        if 'smodel' in paths:
            parts = _parse_smodel(paths['smodel'], kind)
            if parts is not None:
                ENTITY_MODELS[kind] = parts
                smodel_loaded.append(kind)

    if obj_loaded:
        print(f"[models] OBJ:    {len(obj_loaded)} model(s): {', '.join(sorted(obj_loaded))}")
    if smodel_loaded:
        print(f"[models] smodel: {len(smodel_loaded)} model(s): {', '.join(sorted(smodel_loaded))}")
    if not obj_loaded and not smodel_loaded:
        print(f"[models] no model files found in {models_dir}")


# -- OBJ helpers -----------------------------------------------------------

def _load_texture_file(image_path):
    """Load a PNG from disk into a GL texture. Returns GL id or None."""
    try:
        from PIL import Image as PILImage
        img  = PILImage.open(image_path).convert("RGBA")
        data = img.tobytes("raw", "RGBA", 0, -1)
        w, h = img.size
        tid  = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tid)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glBindTexture(GL_TEXTURE_2D, 0)
        return tid
    except Exception as e:
        print(f"[models] could not load texture {image_path}: {e}")
        return None


def _parse_mtl(mtl_path, models_dir, tex_dir):
    """Parse a .mtl file; returns dict: name -> {'tex': GL_id|None, 'color': (r,g,b)}"""
    materials = {}
    current   = None
    try:
        raw_lines = open(mtl_path, 'r', errors='replace').readlines()
    except OSError as e:
        print(f"[models] could not read {mtl_path}: {e}")
        return materials

    for raw in raw_lines:
        parts = raw.strip().split()
        if not parts or parts[0].startswith('#'):
            continue
        d = parts[0].lower()

        if d == 'newmtl':
            current = parts[1] if len(parts) > 1 else '__default__'
            materials[current] = {'tex': None, 'color': (1.0, 1.0, 1.0)}

        elif d == 'kd' and current and len(parts) >= 4:
            materials[current]['color'] = (float(parts[1]), float(parts[2]), float(parts[3]))

        elif d == 'map_kd' and current and len(parts) >= 2:
            img_name = parts[-1]
            for search_dir in (models_dir, tex_dir):
                candidate = os.path.join(search_dir, img_name)
                if os.path.exists(candidate):
                    tid = _load_texture_file(candidate)
                    if tid is not None:
                        materials[current]['tex'] = tid
                    break
            else:
                print(f"[models] map_Kd '{img_name}' not found (searched models/ and textures/)")

    return materials


def _parse_obj(obj_path, models_dir, kind):
    """
    Parse a Wavefront .obj file.
    Returns a list of draw-group dicts, or None on hard error.

    Draw group: {'tex': GL_id|None, 'color': (r,g,b), 'tris': [tri, ...]}
    Each tri:   ( (x,y,z),(u,v),  (x,y,z),(u,v),  (x,y,z),(u,v) )
    """
    tex_dir = os.path.join(os.path.dirname(models_dir), "textures")

    try:
        raw_lines = open(obj_path, 'r', errors='replace').readlines()
    except OSError as e:
        print(f"[models] could not read {obj_path}: {e}")
        return None

    positions = []
    uvs       = []
    materials = {}
    cur_mat   = '__default__'
    groups    = {}   # mat_name -> list of tris

    def get_group(mat):
        if mat not in groups:
            groups[mat] = []
        return groups[mat]

    for lineno, raw in enumerate(raw_lines, 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        d = parts[0].lower()

        if d == 'v' and len(parts) >= 4:
            positions.append((float(parts[1]), float(parts[2]), float(parts[3])))

        elif d == 'vt' and len(parts) >= 3:
            uvs.append((float(parts[1]), float(parts[2])))

        elif d == 'vn':
            pass   # normals not used

        elif d == 'mtllib' and len(parts) >= 2:
            mtl_path = os.path.join(models_dir, parts[1])
            if os.path.exists(mtl_path):
                materials.update(_parse_mtl(mtl_path, models_dir, tex_dir))
            else:
                print(f"[models] {kind}.obj:{lineno}: mtllib '{parts[1]}' not found")

        elif d == 'usemtl' and len(parts) >= 2:
            cur_mat = parts[1]

        elif d == 'f' and len(parts) >= 4:
            def parse_idx(token):
                sub = token.split('/')
                vi = int(sub[0]) - 1
                ti = (int(sub[1]) - 1) if len(sub) > 1 and sub[1] else None
                return vi, ti

            try:
                corners = [parse_idx(t) for t in parts[1:]]
            except (ValueError, IndexError) as e:
                print(f"[models] {kind}.obj:{lineno}: bad face -- {e}")
                continue

            def corner(vi, ti):
                pos = positions[vi] if 0 <= vi < len(positions) else (0.0, 0.0, 0.0)
                uv  = uvs[ti]       if ti is not None and 0 <= ti < len(uvs) else (0.0, 0.0)
                return pos, uv

            face_verts = [corner(vi, ti) for vi, ti in corners]
            tris = get_group(cur_mat)
            # Fan-triangulate (correct for convex polygons)
            for i in range(1, len(face_verts) - 1):
                tris.append((face_verts[0], face_verts[i], face_verts[i + 1]))

    if not any(groups.values()):
        print(f"[models] {kind}.obj: no faces found")
        return None

    draw_groups = []
    for mat_name, tris in groups.items():
        if not tris:
            continue
        mat = materials.get(mat_name, {})
        draw_groups.append({
            'tex':   mat.get('tex',   None),
            'color': mat.get('color', (1.0, 1.0, 1.0)),
            'tris':  tris,
        })

    total_tris = sum(len(g['tris']) for g in draw_groups)
    print(f"[models] {kind}.obj: {total_tris} tris, {len(draw_groups)} material group(s)")
    return draw_groups


# -- .smodel parser --------------------------------------------------------

def _parse_smodel(path, kind):
    """
    Parse a .smodel file.  Returns a list of part dicts, or None on hard error.
    Unknown / malformed lines are skipped with a warning.
    """
    parts = []
    try:
        with open(path, 'r') as f:
            raw_lines = f.readlines()
    except OSError as e:
        print(f"[models] could not read {path}: {e}")
        return None

    for lineno, raw in enumerate(raw_lines, 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue

        tokens = line.split()
        if not tokens or tokens[0].lower() != 'part':
            print(f"[models] {kind}.smodel:{lineno}: skipping unknown directive")
            continue

        try:
            part_name = tokens[1]
            rest = tokens[2:]
            kv = {}
            i = 0
            while i < len(rest):
                key = rest[i].lower()
                if key == 'offset' and i + 3 < len(rest):
                    kv['offset'] = (float(rest[i+1]), float(rest[i+2]), float(rest[i+3]))
                    i += 4
                elif key == 'size' and i + 3 < len(rest):
                    kv['size'] = (float(rest[i+1]), float(rest[i+2]), float(rest[i+3]))
                    i += 4
                elif key == 'tex' and i + 1 < len(rest):
                    val = rest[i+1]
                    kv['tex'] = None if val.lower() == 'none' else val
                    i += 2
                elif key == 'shade' and i + 1 < len(rest):
                    kv['shade'] = float(rest[i+1])
                    i += 2
                else:
                    print(f"[models] {kind}.smodel:{lineno}: unrecognised token '{rest[i]}'")
                    break

            if 'offset' not in kv or 'size' not in kv:
                print(f"[models] {kind}.smodel:{lineno}: part missing offset or size -- skipped")
                continue

            parts.append({
                'name':   part_name,
                'offset': kv['offset'],
                'size':   kv['size'],
                'tex':    kv.get('tex', None),
                'shade':  kv.get('shade', 1.0),
            })

        except (IndexError, ValueError) as e:
            print(f"[models] {kind}.smodel:{lineno}: parse error ({e}) -- skipped")
            continue

    return parts

# ══════════════════════════════════════════════════════════════════════════
#  DRAWING
# ══════════════════════════════════════════════════════════════════════════

def _draw_model_part(ox, oy, oz, sx, sy, sz, tex_name, shade, hurt_flash):
    """Render one box part with cube-unwrap UV mapping."""
    hw, hh, hd = sx*0.5, sy*0.5, sz*0.5
    x0, x1 = ox-hw, ox+hw
    y0, y1 = oy-hh, oy+hh
    z0, z1 = oz-hd, oz+hd

    has_tex = bool(tex_name and tex_name in ENTITY_TEXTURES)

    if has_tex and not hurt_flash:
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, ENTITY_TEXTURES[tex_name])
        # 4-col x 2-row tile layout on 64x32 tex
        tw, th = 0.25, 0.5
        def tile(col, row):
            u0,v0 = col*tw, row*th
            return (u0, v0, u0+tw, v0+th)
        top   = tile(1,0); bot   = tile(2,0)
        front = tile(1,1); back  = tile(3,1)
        left  = tile(0,1); right = tile(2,1)
        glColor3f(shade, shade, shade)
    else:
        glDisable(GL_TEXTURE_2D)
        if hurt_flash:
            glColor3f(1.0, 0.25, 0.25)
        else:
            glColor3f(shade, shade, shade)
        top = bot = front = back = left = right = (0.0, 0.0, 1.0, 1.0)

    def quad(verts, u0,v0,u1,v1):
        uvs = [(u0,v1),(u1,v1),(u1,v0),(u0,v0)]
        glBegin(GL_QUADS)
        for (vx,vy,vz_),(u,v) in zip(verts, uvs):
            glTexCoord2f(u, v); glVertex3f(vx, vy, vz_)
        glEnd()

    quad([(x0,y1,z0),(x1,y1,z0),(x1,y1,z1),(x0,y1,z1)], *top)   # top
    quad([(x0,y0,z1),(x1,y0,z1),(x1,y0,z0),(x0,y0,z0)], *bot)   # bottom
    quad([(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)], *front) # front +Z
    quad([(x1,y0,z0),(x0,y0,z0),(x0,y1,z0),(x1,y1,z0)], *back)  # back  -Z
    quad([(x0,y0,z0),(x0,y0,z1),(x0,y1,z1),(x0,y1,z0)], *left)  # left  -X
    quad([(x1,y0,z1),(x1,y0,z0),(x1,y1,z0),(x1,y1,z1)], *right) # right +X

    if has_tex and not hurt_flash:
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)
    elif not has_tex:
        glEnable(GL_TEXTURE_2D)  # restore


def _draw_obj_model(draw_groups, hurt_flash):
    """Render a parsed OBJ model (list of draw-group dicts)."""
    from OpenGL.GL import GL_TRIANGLES
    for group in draw_groups:
        tex = group['tex']
        cr, cg, cb = group['color']

        if hurt_flash:
            glDisable(GL_TEXTURE_2D)
            glColor3f(1.0, 0.25, 0.25)
        elif tex is not None:
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, tex)
            glColor3f(1.0, 1.0, 1.0)
        else:
            glDisable(GL_TEXTURE_2D)
            glColor3f(cr, cg, cb)

        glBegin(GL_TRIANGLES)
        for (p0, uv0), (p1, uv1), (p2, uv2) in group['tris']:
            glTexCoord2f(*uv0); glVertex3f(*p0)
            glTexCoord2f(*uv1); glVertex3f(*p1)
            glTexCoord2f(*uv2); glVertex3f(*p2)
        glEnd()

        if not hurt_flash and tex is not None:
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)
        elif not hurt_flash and tex is None:
            glEnable(GL_TEXTURE_2D)   # restore for rest of frame


def draw_entity_box(x, y, z, w, h, base_color, face_tex_name, yaw_to_player,
                    hurt_flash=False, kind=None):
    """
    Draw an entity at world position (x, y, z).

    Priority:
      1. kind in ENTITY_OBJ_MODELS  -> render OBJ triangle mesh
      2. kind in ENTITY_MODELS      -> render .smodel box parts
      3. fallback                   -> single textured/white cube
    hurt_flash: render the whole model solid red (hit indicator).
    """
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(yaw_to_player, 0, 1, 0)

    if kind and kind in ENTITY_OBJ_MODELS:
        _draw_obj_model(ENTITY_OBJ_MODELS[kind], hurt_flash)

    elif kind and kind in ENTITY_MODELS:
        for part in ENTITY_MODELS[kind]:
            _draw_model_part(
                part['offset'][0], part['offset'][1], part['offset'][2],
                part['size'][0],   part['size'][1],   part['size'][2],
                part.get('tex'), part.get('shade', 1.0), hurt_flash)
    else:
        # Fallback: single cube
        hw = w * 0.5
        has_tex = bool(face_tex_name and face_tex_name in ENTITY_TEXTURES)
        if has_tex and not hurt_flash:
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, ENTITY_TEXTURES[face_tex_name])
        else:
            glDisable(GL_TEXTURE_2D)

        if hurt_flash:
            r, g, b = 1.0, 0.25, 0.25
        else:
            r, g, b = [c/255.0 for c in base_color]

        faces = [
            ([(- hw,h,-hw),(hw,h,-hw),(hw,h, hw),(-hw,h, hw)], 1.00),  # top
            ([(- hw,0, hw),(hw,0, hw),(hw,0,-hw),(-hw,0,-hw)], 0.50),  # bottom
            ([(- hw,0, hw),(hw,0, hw),(hw,h, hw),(-hw,h, hw)], 0.85),  # front
            ([( hw,0,-hw),(-hw,0,-hw),(-hw,h,-hw),(hw,h,-hw)], 0.75),  # back
            ([( hw,0, hw),(hw,0,-hw),(hw,h,-hw),(hw,h, hw)],   0.65),  # right
            ([(- hw,0,-hw),(-hw,0, hw),(-hw,h, hw),(-hw,h,-hw)],0.65),# left
        ]
        uv = [(0,1),(1,1),(1,0),(0,0)]
        for verts, shade in faces:
            glColor3f(r*shade, g*shade, b*shade)
            glBegin(GL_QUADS)
            for (vx,vy,vz_),(u,v) in zip(verts, uv):
                glTexCoord2f(u,v); glVertex3f(vx,vy,vz_)
            glEnd()

        if has_tex and not hurt_flash:
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)
        elif not has_tex:
            glEnable(GL_TEXTURE_2D)

    glPopMatrix()


# ══════════════════════════════════════════════════════════════════════════
#  ENEMIES
# ══════════════════════════════════════════════════════════════════════════

class Enemy:
    TYPES = {
        'grunt':  {'color':(220, 60, 60), 'hp':10, 'speed':3.2, 'damage':2.0,
                   'size':0.7, 'height':1.75, 'attack_range':1.4, 'attack_cd':1.2},
        'brute':  {'color':(160, 40,180), 'hp':25, 'speed':2.2, 'damage':4.0,
                   'size':0.9, 'height':2.40, 'attack_range':1.8, 'attack_cd':2.0},
        'lurker': {'color':( 40,160,200), 'hp': 6, 'speed':5.0, 'damage':1.0,
                   'size':0.5, 'height':1.10, 'attack_range':1.2, 'attack_cd':0.6},
    }

    def __init__(self, x, y, z, kind='grunt'):
        self.x=float(x); self.y=float(y); self.z=float(z)
        self.vy=0.0;      self.on_ground=False
        self.kind=kind
        s=self.TYPES[kind]
        self.color=s['color']; self.hp=s['hp'];    self.max_hp=s['hp']
        self.speed=s['speed']; self.damage=s['damage']
        self.width=s['size'];  self.height=s['height']
        self.attack_range=s['attack_range']; self.attack_cd=s['attack_cd']
        self._attack_timer=0.0; self._hurt_flash=0.0; self.yaw=0.0

    def update(self, world, player, dt):
        dx=player.x-self.x; dz=player.z-self.z
        dist=math.sqrt(dx*dx+dz*dz)
        move_x=move_z=0.0
        if 0.1<dist<32:
            move_x=dx/dist*self.speed; move_z=dz/dist*self.speed
        _entity_move(self, world, move_x, move_z, dt)
        if move_x*move_x+move_z*move_z>0.01:
            self.yaw=math.degrees(math.atan2(move_x,move_z))
        elif dist>0:
            self.yaw=math.degrees(math.atan2(dx,dz))
        if self._attack_timer>0: self._attack_timer-=dt
        if dist<self.attack_range and abs(player.y-self.y)<2 and self._attack_timer<=0:
            player.take_damage(self.damage); self._attack_timer=self.attack_cd
        if self._hurt_flash>0: self._hurt_flash-=dt

    def take_hit(self, dmg):
        self.hp-=dmg; self._hurt_flash=0.25

    def dead(self): return self.hp<=0

    def draw(self):
        draw_entity_box(self.x,self.y,self.z,self.width,self.height,
                        self.color,f"{self.kind}_body",self.yaw,
                        self._hurt_flash>0, kind=self.kind)
        bw=self.width*1.2; bh=0.08; by_bar=self.y+self.height+0.2
        glDisable(GL_DEPTH_TEST); glDisable(GL_TEXTURE_2D)
        glColor3f(0.3,0.05,0.05)
        glBegin(GL_QUADS)
        glVertex3f(self.x-bw/2,by_bar,self.z);   glVertex3f(self.x+bw/2,by_bar,self.z)
        glVertex3f(self.x+bw/2,by_bar+bh,self.z);glVertex3f(self.x-bw/2,by_bar+bh,self.z)
        glEnd()
        frac=max(0,self.hp/self.max_hp); filled=self.x-bw/2+bw*frac
        glColor3f(0.1+0.8*frac,0.7*frac,0.05)
        glBegin(GL_QUADS)
        glVertex3f(self.x-bw/2,by_bar,self.z);glVertex3f(filled,by_bar,self.z)
        glVertex3f(filled,by_bar+bh,self.z);  glVertex3f(self.x-bw/2,by_bar+bh,self.z)
        glEnd()
        glEnable(GL_DEPTH_TEST); glEnable(GL_TEXTURE_2D)


class EnemyManager:
    def __init__(self):
        self.enemies=[]; self._spawn_timer=0.0

    def update(self, world, player, dt, tod=0.0):
        self._spawn_timer+=dt
        is_night=tod<0.25 or tod>0.75
        if self._spawn_timer>8.0 and player.gamemode==GAMEMODE_SURVIVAL and is_night:
            self._spawn_timer=0.0; self._try_spawn(world,player)
        for e in self.enemies: e.update(world,player,dt)
        self.enemies=[e for e in self.enemies if not e.dead()]

    def _try_spawn(self, world, player):
        if len(self.enemies)>=12: return
        rng=random.Random()
        for _ in range(20):
            angle=rng.uniform(0,math.pi*2); dist=rng.uniform(12,28)
            sx=player.x+math.cos(angle)*dist; sz=player.z+math.sin(angle)*dist
            sy=world.gen.surface(int(sx),int(sz))+1
            kind=rng.choices(['grunt','lurker','brute'],[6,3,1])[0]
            stats=Enemy.TYPES[kind]
            if not _entity_spawn_safe(world,sx,sy,sz,stats['size'],stats['height']): continue
            self.enemies.append(Enemy(sx,sy,sz,kind)); return

    def hit_scan(self, player, world, tricksabre_combo=False):
        """Returns True if any enemy was hit."""
        tool=player.selected_block()
        if tool==ITEM_TRICKSABRE:   dmg=10 if tricksabre_combo else 5
        elif tool==ITEM_WOOD_SWORD:  dmg=4
        elif tool==ITEM_STONE_SWORD: dmg=7
        else: return False
        dx,dy,dz=player.look_dir()
        ex=player.x+dx*3.5; ey=player.y+player.height*0.8+dy*3.5; ez=player.z+dz*3.5
        for e in self.enemies:
            ddx=e.x-ex; ddy=e.y+e.height/2-ey; ddz=e.z-ez
            if math.sqrt(ddx*ddx+ddy*ddy+ddz*ddz)<e.width+1.4:
                e.take_hit(dmg); return True
        return False

    def draw(self, px, pz):
        for e in self.enemies:
            if abs(e.x-px)<RENDER_DIST*CHUNK_S and abs(e.z-pz)<RENDER_DIST*CHUNK_S:
                e.draw()


# ══════════════════════════════════════════════════════════════════════════
#  FARMING
# ══════════════════════════════════════════════════════════════════════════

WHEAT_GROW_TIME = 60.0


class FarmingManager:
    def __init__(self):
        self._timers={}

    def tick(self, world, dt):
        to_advance=[]
        for pos,t in list(self._timers.items()):
            t-=dt
            if t<=0: to_advance.append(pos)
            else: self._timers[pos]=t
        for pos in to_advance:
            wx,wy,wz=pos
            bid=world.get_block(wx,wy,wz)
            if bid in (WHEAT_STAGE0,WHEAT_STAGE1,WHEAT_STAGE2):
                if world.get_block(wx,wy-1,wz)==FARMLAND:
                    nxt=WHEAT_STAGES[WHEAT_STAGES.index(bid)+1]
                    world.set_block(wx,wy,wz,nxt)
                    if nxt!=WHEAT_STAGE3:
                        self._timers[pos]=WHEAT_GROW_TIME*random.uniform(0.7,1.4)
                else:
                    world.set_block(wx,wy,wz,AIR)
            del self._timers[pos]

    def plant(self, world, wx, wy, wz):
        if world.get_block(wx,wy,wz)!=AIR: return False
        if world.get_block(wx,wy-1,wz)!=FARMLAND: return False
        world.set_block(wx,wy,wz,WHEAT_STAGE0)
        self._timers[(wx,wy,wz)]=WHEAT_GROW_TIME*random.uniform(0.7,1.4)
        return True

    def harvest(self, world, player, wx, wy, wz):
        bid=world.get_block(wx,wy,wz)
        if bid not in WHEAT_STAGES: return False
        world.set_block(wx,wy,wz,AIR); self._timers.pop((wx,wy,wz),None)
        if bid==WHEAT_STAGE3:
            player.add_to_inv(ITEM_WHEAT,random.randint(1,3))
            player.add_to_inv(ITEM_WHEAT_SEEDS,1)
        else:
            player.add_to_inv(ITEM_WHEAT_SEEDS,1)
        player._sync_hotbar(); return True

    def till(self, world, player, wx, wy, wz):
        if world.get_block(wx,wy,wz) in (KEIRO_GRASS,KEIRO_SOIL):
            world.set_block(wx,wy,wz,FARMLAND); return True
        return False

    def get_state(self):
        return {f"{k[0]},{k[1]},{k[2]}":v for k,v in self._timers.items()}

    def set_state(self, d):
        self._timers={}
        for ks,v in d.items():
            p=ks.split(',')
            if len(p)==3: self._timers[(int(p[0]),int(p[1]),int(p[2]))]=float(v)


# ══════════════════════════════════════════════════════════════════════════
#  ANIMALS
# ══════════════════════════════════════════════════════════════════════════

class Animal:
    TYPES = {
        'sheep':   {'color':(230,230,230),'hp': 8,'speed':2.0,'size':0.7, 'height':1.20,'face':'sheep_body'},
        'pig':     {'color':(240,180,160),'hp':10,'speed':2.2,'size':0.80,'height':1.10,'face':'pig_body'},
        'chicken': {'color':(245,235,200),'hp': 4,'speed':2.8,'size':0.5, 'height':0.90,'face':'chicken_body'},
    }

    def __init__(self, x, y, z, kind='sheep'):
        self.x=float(x); self.y=float(y); self.z=float(z)
        self.vy=0.0; self.on_ground=False; self.kind=kind
        s=self.TYPES[kind]
        self.color=s['color']; self.hp=s['hp']; self.max_hp=s['hp']
        self.speed=s['speed']; self.width=s['size']; self.height=s['height']
        self.face=s['face']
        self._wander_timer=random.uniform(1,4); self._wander_dx=0.0; self._wander_dz=0.0
        self._hurt_flash=0.0; self._flee_timer=0.0; self.yaw=0.0

    def update(self, world, player, dt):
        dx=player.x-self.x; dz=player.z-self.z
        dist=math.sqrt(dx*dx+dz*dz)
        move_x=move_z=0.0
        if self._flee_timer>0:
            self._flee_timer-=dt
            if dist>0.1:
                move_x=(-dx/dist)*self.speed*1.8; move_z=(-dz/dist)*self.speed*1.8
        else:
            self._wander_timer-=dt
            if self._wander_timer<=0:
                ang=random.uniform(0,math.pi*2)
                self._wander_dx=math.cos(ang); self._wander_dz=math.sin(ang)
                self._wander_timer=random.uniform(2,5)
            move_x=self._wander_dx*self.speed*0.5; move_z=self._wander_dz*self.speed*0.5
        _entity_move(self,world,move_x,move_z,dt)
        if move_x*move_x+move_z*move_z>0.01:
            self.yaw=math.degrees(math.atan2(move_x,move_z))
        elif dist>0:
            self.yaw=math.degrees(math.atan2(dx,dz))
        if self._hurt_flash>0: self._hurt_flash-=dt

    def take_hit(self, dmg):
        self.hp-=dmg; self._hurt_flash=0.25; self._flee_timer=4.0

    def dead(self): return self.hp<=0

    def draw(self):
        draw_entity_box(self.x,self.y,self.z,self.width,self.height,
                        self.color,self.face,self.yaw,
                        self._hurt_flash>0, kind=self.kind)


class AnimalManager:
    def __init__(self):
        self.animals=[]; self._spawn_timer=0.0

    def update(self, world, player, dt):
        self._spawn_timer+=dt
        if self._spawn_timer>15.0:
            self._spawn_timer=0.0; self._try_spawn(world,player)
        for a in self.animals: a.update(world,player,dt)
        dead=[a for a in self.animals if a.dead()]
        for a in dead:
            player.add_to_inv(ITEM_RAW_MEAT,random.randint(1,2))
            if a.kind=='sheep' and ITEM_WOOL is not None:
                player.add_to_inv(ITEM_WOOL,random.randint(1,3))
            player._sync_hotbar()
        self.animals=[a for a in self.animals if not a.dead()]

    def _try_spawn(self, world, player):
        if len(self.animals)>=16: return
        rng=random.Random()
        for _ in range(16):
            angle=rng.uniform(0,math.pi*2); d=rng.uniform(8,20)
            sx=player.x+math.cos(angle)*d; sz=player.z+math.sin(angle)*d
            sy=world.gen.surface(int(sx),int(sz))+1
            surf_bid=world.get_block(int(sx),sy-1,int(sz))
            if surf_bid not in (KEIRO_GRASS,MORI_MOSS): continue
            kind=rng.choices(['sheep','pig','chicken'],[5,3,2])[0]
            stats=Animal.TYPES[kind]
            if not _entity_spawn_safe(world,sx,sy,sz,stats['size'],stats['height']): continue
            self.animals.append(Animal(sx,sy,sz,kind)); return

    def hit_scan(self, player, world, tricksabre_combo=False):
        """Returns True if any animal was hit."""
        tool=player.selected_block()
        if tool==ITEM_TRICKSABRE:    dmg=10 if tricksabre_combo else 5
        elif tool==ITEM_WOOD_SWORD:  dmg=4
        elif tool==ITEM_STONE_SWORD: dmg=7
        else: return False
        dx,dy,dz=player.look_dir()
        ex=player.x+dx*2.5; ey=player.y+player.height*0.8+dy*2.5; ez=player.z+dz*2.5
        for a in self.animals:
            ddx=a.x-ex; ddy=a.y+a.height/2-ey; ddz=a.z-ez
            if math.sqrt(ddx*ddx+ddy*ddy+ddz*ddz)<a.width+0.8:
                a.take_hit(dmg); return True
        return False

    def draw(self, px, pz):
        for a in self.animals:
            if abs(a.x-px)<RENDER_DIST*CHUNK_S and abs(a.z-pz)<RENDER_DIST*CHUNK_S:
                a.draw()