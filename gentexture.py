"""
Saikai texture generator — updated for v2 blocks + items.
Skips any texture that already exists on disk.
Outputs to C:\\Users\\Owner\\PycharmProject\\Saikai\\textures
"""
import os, math, random
from PIL import Image

OUT = r"C:\Users\Owner\PycharmProject\Saikai\textures"
os.makedirs(OUT, exist_ok=True)
S = 32

# ─── colour helpers ───────────────────────────────────────────

def hx(r, g, b):
    return f"#{int(max(0,min(255,r))):02x}{int(max(0,min(255,g))):02x}{int(max(0,min(255,b))):02x}"

def darken(h, f=0.70):
    r,g,b = int(h[1:3],16), int(h[3:5],16), int(h[5:7],16)
    return hx(r*f, g*f, b*f)

def lighten(h, f=1.30):
    r,g,b = int(h[1:3],16), int(h[3:5],16), int(h[5:7],16)
    return hx(min(255,r*f), min(255,g*f), min(255,b*f))

def mix(h1, h2, t=0.5):
    r1,g1,b1 = int(h1[1:3],16), int(h1[3:5],16), int(h1[5:7],16)
    r2,g2,b2 = int(h2[1:3],16), int(h2[3:5],16), int(h2[5:7],16)
    return hx(r1+(r2-r1)*t, g1+(g2-g1)*t, b1+(b2-b1)*t)

def from_rgb(r,g,b): return hx(r,g,b)

# ─── direct pixel drawing ─────────────────────────────────────

def new_img():
    return Image.new("RGBA", (S,S), (0,0,0,0))

def put(img, x, y, col_hex, alpha=255):
    if not (0<=x<S and 0<=y<S): return
    if col_hex in ("none", ""): return
    try:
        r,g,b = int(col_hex[1:3],16), int(col_hex[3:5],16), int(col_hex[5:7],16)
    except Exception: return
    if alpha==255:
        img.putpixel((x,y),(r,g,b,255))
    else:
        base=img.getpixel((x,y))
        t=alpha/255
        img.putpixel((x,y),(
            int(base[0]*(1-t)+r*t),
            int(base[1]*(1-t)+g*t),
            int(base[2]*(1-t)+b*t),
            min(255,base[3]+alpha-base[3]*alpha//255)
        ))

def fill_rect(img, x, y, w, h, col, alpha=255):
    for py in range(y, min(S, y+h)):
        for px in range(x, min(S, x+w)):
            put(img, px, py, col, alpha)

def fill_circle(img, cx, cy, r, col, alpha=255):
    for dy in range(-int(r)-1, int(r)+2):
        for dx in range(-int(r)-1, int(r)+2):
            if dx*dx+dy*dy <= r*r:
                put(img, int(cx+dx), int(cy+dy), col, alpha)

def draw_line(img, x1,y1,x2,y2, col, alpha=255):
    dx,dy=x2-x1,y2-y1
    steps=max(abs(dx),abs(dy),1)
    for i in range(steps+1):
        put(img, int(x1+dx*i/steps), int(y1+dy*i/steps), col, alpha)

def bevel(img, base_col):
    for i in range(S):
        put(img, 0, i, lighten(base_col,1.35))
        put(img, i, 0, lighten(base_col,1.35))
        put(img, S-1, i, darken(base_col,0.45))
        put(img, i, S-1, darken(base_col,0.45))

# ─── EXISTING BLOCK TEXTURES (unchanged) ─────────────────────

def blk_grass():
    img=new_img(); c="#38ad8c"
    fill_rect(img,0,0,S,S,c)
    rng=random.Random(1)
    cols=["#2e9878","#44c4a0","#259068","#50d8b0","#1e7a5c","#33b888"]
    for _ in range(120):
        put(img,rng.randint(0,S-1),rng.randint(0,S-1),rng.choice(cols))
    for _ in range(18):
        x=rng.randint(1,S-2); y=rng.randint(2,S-3)
        put(img,x,y,"#55eebb"); put(img,x,y-1,"#44cc99")
    bevel(img,c)
    return img

def blk_soil():
    img=new_img(); c="#593666"
    fill_rect(img,0,0,S,S,c)
    rng=random.Random(2)
    for _ in range(80):
        put(img,rng.randint(0,S-1),rng.randint(0,S-1),
            darken(c,0.8) if rng.random()<0.6 else lighten(c,1.15))
    bevel(img,c); return img

def blk_stone():
    img=new_img(); c="#727284"
    fill_rect(img,0,0,S,S,c)
    rng=random.Random(3)
    for _ in range(70):
        put(img,rng.randint(0,S-1),rng.randint(0,S-1),
            darken(c,0.8) if rng.random()<0.6 else lighten(c,1.2))
    bevel(img,c); return img

def blk_shinen_rock():
    img=new_img(); c="#1e1929"
    fill_rect(img,0,0,S,S,c)
    rng=random.Random(4)
    for _ in range(50):
        put(img,rng.randint(0,S-1),rng.randint(0,S-1),
            darken(c,0.7) if rng.random()<0.6 else "#2e2840")
    for i in range(S):
        put(img,i,int(12+math.sin(i*0.4)*3),"#3a2a50",180)
    bevel(img,c); return img

def blk_crystal():
    img=new_img(); bg="#0a2030"; c="#19d8e5"
    fill_rect(img,0,0,S,S,bg)
    for i in range(0,S*2,5):
        x1=max(0,i-S); y1=max(0,S-i)
        x2=min(S-1,i); y2=max(0,y1+(x2-x1))
        draw_line(img,x1,y1,x2,min(S-1,y2),c,80)
    for r in range(10,0,-1):
        fill_circle(img,16,16,r,c,int((10-r)/10*180))
    fill_circle(img,16,16,4,lighten(c,1.5),220)
    put(img,15,15,"#ffffff")
    bevel(img,bg); return img

def blk_ember():
    img=new_img(); c="#f2720c"; bg="#1a0800"
    fill_rect(img,0,0,S,S,bg)
    rng=random.Random(6)
    for _ in range(8):
        x,y=rng.randint(2,S-4),rng.randint(2,S-4)
        for j in range(rng.randint(4,9)):
            dx,dy=rng.choice([-1,0,1]),rng.choice([-1,0,1])
            xx,yy=max(0,min(S-1,x+dx*j)),max(0,min(S-1,y+dy*j))
            put(img,xx,yy,lighten(c,1.6) if rng.random()<0.2 else c)
    for cx2,cy2,r in [(8,8,3),(22,20,4),(16,14,5)]:
        for dr in range(r,0,-1):
            fill_circle(img,cx2,cy2,dr,c,int((r-dr+1)/r*160))
    bevel(img,bg); return img

def blk_snow():
    img=new_img(); c="#e0e0f0"
    fill_rect(img,0,0,S,S,c)
    rng=random.Random(7)
    for _ in range(60):
        put(img,rng.randint(0,S-1),rng.randint(0,S-1),
            darken(c,0.88) if rng.random()<0.5 else lighten(c,1.05))
    bevel(img,c); return img

def blk_ice():
    img=new_img(); c="#8bb8e8"
    fill_rect(img,0,0,S,S,c)
    for pts in [[(4,4),(14,10),(8,18)],[(18,2),(26,12),(20,20),(28,28)],[(2,22),(12,26),(8,30)]]:
        for i in range(len(pts)-1):
            x1,y1=pts[i]; x2,y2=pts[i+1]
            draw_line(img,x1,y1,x2,y2,lighten(c,1.4),200)
    fill_rect(img,0,0,S,S,"#aaddff",40)
    bevel(img,c); return img

def blk_shale():
    img=new_img(); c="#827580"
    fill_rect(img,0,0,S,S,c)
    for y in range(0,S,4):
        fill_rect(img,0,y,S,1,darken(c,0.72))
        fill_rect(img,0,y+2,S,1,lighten(c,1.1))
    rng=random.Random(9)
    for _ in range(30):
        put(img,rng.randint(0,S-1),rng.randint(0,S-1),
            darken(c,0.65) if rng.random()<0.5 else lighten(c,1.2))
    bevel(img,c); return img

def blk_wood():
    img=new_img(); c="#8c5919"
    fill_rect(img,0,0,S,S,c)
    rng=random.Random(10)
    for x in range(S):
        if rng.random()<0.2:
            fill_rect(img,x,0,1,S,darken(c,0.8) if rng.random()<0.6 else lighten(c,1.15))
    for r in range(6,16,3):
        for x in range(S):
            y=int(16+r*math.sin(x/S*math.pi*2)*0.4)
            put(img,x,y,darken(c,0.78))
    bevel(img,c); return img

def blk_leaves():
    img=new_img(); bg="#1a7a40"
    fill_rect(img,0,0,S,S,bg)
    rng=random.Random(11)
    cols=["#26b259","#1e9447","#33cc66","#0f6630","#44dd77"]
    for _ in range(140):
        put(img,rng.randint(0,S-1),rng.randint(0,S-1),rng.choice(cols))
    for _ in range(20):
        put(img,rng.randint(1,S-2),rng.randint(1,S-2),"#050e08")
    return img

def blk_moss():
    img=new_img(); c="#33b226"
    fill_rect(img,0,0,S,S,c)
    rng=random.Random(12)
    for _ in range(100):
        put(img,rng.randint(0,S-1),rng.randint(0,S-1),
            rng.choice(["#4ce033","#1e8814","#66ff44","#22991a"]))
    for _ in range(12):
        fill_circle(img,rng.randint(2,S-3),rng.randint(2,S-3),1.5,"#aaff44",160)
    return img

def blk_water():
    img=new_img(); c="#1520a0"
    fill_rect(img,0,0,S,S,c)
    for y in range(S):
        off=int(math.sin(y*0.6)*2)
        for x in range(S):
            xw=(x+off)%S
            if xw<S//3:
                put(img,x,y,lighten(c,1.3),150)
            elif xw<S//3+2:
                put(img,x,y,"#6070ff",100)
    fill_rect(img,0,0,S,2,"#4060e8",120)
    return img

def blk_lava():
    img=new_img(); bg="#1a0800"
    fill_rect(img,0,0,S,S,bg)
    rng=random.Random(14)
    for _ in range(5):
        cx2,cy2=rng.randint(4,S-4),rng.randint(4,S-4)
        cols2=["#ff6600","#ff9900","#ffcc00","#ff3300"]
        for r in range(8,0,-1):
            fill_circle(img,cx2,cy2,r,rng.choice(cols2),int((8-r+1)/8*200))
    for _ in range(40):
        put(img,rng.randint(0,S-1),rng.randint(0,S-1),"#2a1000",170)
    return img

def blk_cloud():
    img=new_img(); c="#d8d8f0"
    fill_rect(img,0,0,S,S,c)
    rng=random.Random(15)
    for _ in range(5):
        fill_circle(img,rng.randint(6,26),rng.randint(6,26),rng.randint(5,9),"#f0f0ff",80)
    fill_rect(img,0,0,S,2,"#ffffff",180)
    bevel(img,c); return img

def blk_workbench():
    img=new_img(); c="#a05820"
    fill_rect(img,0,0,S,S,c)
    rng=random.Random(16)
    for y in range(S//2):
        for x in range(S):
            if rng.random()<0.1:
                put(img,x,y,darken(c,0.78))
    for i in range(0,S,8):
        fill_rect(img,i,0,1,S//2,darken(c,0.55))
    for i in range(0,S//2,4):
        fill_rect(img,0,i,S,1,darken(c,0.6))
    fill_rect(img,0,S//2,S,S//2,darken(c,0.85))
    for i in range(0,S,6):
        fill_rect(img,i,S//2,1,S//2,darken(c,0.6))
    bevel(img,c); return img

# ─── BLOCK TEXTURES ───────────────────────────────────────────

def blk_glass():
    img=new_img()
    c="#c8e8ff"
    fill_rect(img,0,0,S,S,c,40)
    for i in range(S):
        put(img,0,i,"#e8f4ff",160)
        put(img,i,0,"#e8f4ff",160)
        put(img,S-1,i,"#90c4e8",120)
        put(img,i,S-1,"#90c4e8",120)
    for i in range(4,12):
        put(img,i,i,"#ffffff",200)
        put(img,i+1,i,"#ffffff",100)
    fill_rect(img,0,0,S,2,"#d8eeff",80)
    fill_rect(img,0,S-2,S,2,"#90c4e8",80)
    fill_rect(img,0,0,2,S,"#d8eeff",80)
    fill_rect(img,S-2,0,2,S,"#90c4e8",80)
    return img

def blk_door():
    """
    Sliding door — bottom half.
    Horizontal slats running the full width, like a modern sliding panel.
    Rail channel at top. Wood frame on left/right edges.
    """
    img = new_img()
    c = "#8c5a1e"           # wood frame colour
    slat = "#7a4e18"        # slat base
    slat_hl = "#a06828"     # slat highlight edge
    slat_sh = "#5a3810"     # slat shadow edge

    # Background fill
    fill_rect(img, 0, 0, S, S, c)

    # Left / right frame rails
    fill_rect(img, 0, 0, 3, S, darken(c, 0.75))
    fill_rect(img, S-3, 0, 3, S, darken(c, 0.65))
    # Frame inner highlight/shadow
    put(img, 2, 0, lighten(c, 1.2)); put(img, 2, S-1, darken(c, 0.5))
    put(img, S-3, 0, lighten(c, 1.2)); put(img, S-3, S-1, darken(c, 0.5))

    # Horizontal slats (5 slats, each ~5px tall with 1px gap)
    slat_h = 4
    gap    = 1
    y = 2
    rng = random.Random(40)
    for _ in range(5):
        # Slat body
        fill_rect(img, 3, y, S-6, slat_h, slat)
        # Top highlight
        fill_rect(img, 3, y, S-6, 1, slat_hl)
        # Bottom shadow
        fill_rect(img, 3, y+slat_h-1, S-6, 1, slat_sh)
        # Subtle wood grain on slat
        for _ in range(3):
            gx = rng.randint(4, S-5)
            fill_rect(img, gx, y+1, 1, slat_h-2, darken(slat, 0.88))
        y += slat_h + gap

    # Top rail channel (where door slides into ceiling)
    fill_rect(img, 0, 0, S, 2, darken(c, 0.5))
    fill_rect(img, 1, 0, S-2, 1, darken(c, 0.35))

    bevel(img, c)
    return img

def blk_door_top():
    """
    Sliding door — top half.
    Continues the slat pattern upward. Rail at top.
    """
    img = new_img()
    c = "#8c5a1e"
    slat = "#7a4e18"
    slat_hl = "#a06828"
    slat_sh = "#5a3810"

    fill_rect(img, 0, 0, S, S, c)

    # Left / right frame rails (match bottom half)
    fill_rect(img, 0, 0, 3, S, darken(c, 0.75))
    fill_rect(img, S-3, 0, 3, S, darken(c, 0.65))

    # Horizontal slats — offset by half a slat so seam looks natural
    slat_h = 4
    gap    = 1
    y = -2   # start offset so slats stagger across the join
    rng = random.Random(41)
    for _ in range(6):
        if y >= 0:
            draw_y = y
            draw_h = min(slat_h, S - draw_y)
            if draw_h > 0:
                fill_rect(img, 3, draw_y, S-6, draw_h, slat)
                fill_rect(img, 3, draw_y, S-6, 1, slat_hl)
                if draw_y + slat_h - 1 < S:
                    fill_rect(img, 3, draw_y+slat_h-1, S-6, 1, slat_sh)
                for _ in range(3):
                    gx = rng.randint(4, S-5)
                    fill_rect(img, gx, draw_y+1, 1, max(1,draw_h-2), darken(slat, 0.88))
        y += slat_h + gap

    # Rail channel at top (ceiling mount point)
    fill_rect(img, 0, 0, S, 3, darken(c, 0.45))
    fill_rect(img, 2, 1, S-4, 1, darken(c, 0.3))
    # Rail bolt dots
    for bx in [6, 14, 22]:
        fill_circle(img, bx, 1, 1, darken(c, 0.55))

    bevel(img, c)
    return img

def blk_glass_door():
    """
    Glass sliding door — bottom half.
    Wood frame on left/right edges + bottom rail. Centre is glass panel.
    """
    img = new_img()
    wood = "#8c5a1e"
    glass_tint = "#c4e8ff"

    # Glass fill — semi-transparent centre
    fill_rect(img, 3, 1, S-6, S-2, glass_tint, 60)

    # Left wood frame
    fill_rect(img, 0, 0, 3, S, darken(wood, 0.75))
    fill_rect(img, 2, 0, 1, S, lighten(wood, 1.1))
    # Right wood frame
    fill_rect(img, S-3, 0, 3, S, darken(wood, 0.65))
    fill_rect(img, S-3, 0, 1, S, lighten(wood, 1.0))

    # Bottom rail
    fill_rect(img, 0, S-3, S, 3, darken(wood, 0.6))
    fill_rect(img, 0, S-3, S, 1, lighten(wood, 1.1))

    # Glass reflections / glints
    for i in range(5, 14):
        put(img, i+1, i, "#ffffff", 160)
        put(img, i+2, i, "#ffffff",  80)
    # Faint horizontal tint bands
    for y in range(4, S-4, 6):
        fill_rect(img, 3, y, S-6, 2, "#aad8ff", 30)

    # Glass edge lines
    fill_rect(img, 3, 1, S-6, 1, "#d8eeff", 140)
    fill_rect(img, 3, S-4, S-6, 1, "#90c4e8", 100)

    bevel(img, wood)
    return img

def blk_glass_door_top():
    """
    Glass sliding door — top half.
    Continues the glass panel. Rail channel + mount bolts at top.
    """
    img = new_img()
    wood = "#8c5a1e"
    glass_tint = "#c4e8ff"

    # Glass fill
    fill_rect(img, 3, 0, S-6, S-1, glass_tint, 60)

    # Left wood frame
    fill_rect(img, 0, 0, 3, S, darken(wood, 0.75))
    fill_rect(img, 2, 0, 1, S, lighten(wood, 1.1))
    # Right wood frame
    fill_rect(img, S-3, 0, 3, S, darken(wood, 0.65))
    fill_rect(img, S-3, 0, 1, S, lighten(wood, 1.0))

    # Top rail channel (ceiling mount)
    fill_rect(img, 0, 0, S, 3, darken(wood, 0.45))
    fill_rect(img, 2, 1, S-4, 1, darken(wood, 0.30))
    # Rail mount bolts
    for bx in [6, 14, 22]:
        fill_circle(img, bx, 1, 1, darken(wood, 0.55))

    # Glass reflections (continue from bottom half)
    for i in range(2, 10):
        put(img, i+2, i+2, "#ffffff", 140)
        put(img, i+3, i+2, "#ffffff",  70)
    for y in range(4, S-1, 6):
        fill_rect(img, 3, y, S-6, 2, "#aad8ff", 30)

    fill_rect(img, 3, S-2, S-6, 1, "#90c4e8", 100)

    bevel(img, wood)
    return img

def blk_farmland():
    img=new_img(); c="#5a3a18"
    fill_rect(img,0,0,S,S,c)
    rng=random.Random(19)
    for y in range(0,S,4):
        fill_rect(img,0,y,S,1,darken(c,0.55))
        fill_rect(img,0,y+2,S,1,lighten(c,1.15))
    for _ in range(50):
        put(img,rng.randint(0,S-1),rng.randint(0,S-1),
            darken(c,0.7) if rng.random()<0.5 else lighten(c,1.2))
    for _ in range(8):
        put(img,rng.randint(2,S-3),rng.randint(2,S-3),"#4466aa",60)
    bevel(img,c)
    return img

def blk_wheat(stage):
    img=new_img()
    rng=random.Random(20+stage)
    fill_rect(img,0,S-6,S,6,"#5a3a18")
    for _ in range(20):
        put(img,rng.randint(0,S-1),rng.randint(S-6,S-1),
            darken("#5a3a18",0.7) if rng.random()<0.5 else lighten("#5a3a18",1.1))
    if stage==0:
        stem_col="#78b840"; tip="#aaee66"
        for sx in [6,14,22]:
            fill_rect(img,sx,S-10,2,4,stem_col)
            put(img,sx,S-11,tip); put(img,sx+1,S-11,tip)
    elif stage==1:
        stem_col="#60a030"; tip="#88cc44"; leaf="#50901a"
        for sx in [5,13,21]:
            fill_rect(img,sx,S-16,2,10,stem_col)
            draw_line(img,sx+1,S-14,sx+4,S-17,leaf)
            put(img,sx,S-17,tip); put(img,sx+1,S-17,tip)
    elif stage==2:
        stem_col="#8cb840"; tip="#ccdd44"; leaf="#6a9028"; head="#a8c830"
        for sx in [4,12,20]:
            fill_rect(img,sx,S-22,2,16,stem_col)
            draw_line(img,sx+2,S-18,sx+6,S-22,leaf)
            draw_line(img,sx,S-14,sx-4,S-18,leaf)
            fill_rect(img,sx-1,S-25,4,4,head)
            put(img,sx,S-26,tip); put(img,sx+1,S-26,tip)
    else:
        stem_col="#c8a030"; leaf="#a88020"; head="#ddc040"; grain="#f0d060"
        for sx in [4,12,20]:
            fill_rect(img,sx,S-24,2,18,stem_col)
            draw_line(img,sx+1,S-18,sx+7,S-14,leaf)
            draw_line(img,sx,S-12,sx-6,S-8,leaf)
            for i in range(6):
                gy=S-28+i; gx=sx+i//2
                fill_rect(img,gx-1,gy,4,1,head)
                if i%2==0: put(img,gx,gy-1,grain)
                if i%2==1: put(img,gx+1,gy-1,grain)
    return img

def blk_bush_leaves():
    img=new_img(); bg="#1d5c28"
    fill_rect(img,0,0,S,S,bg)
    rng=random.Random(24)
    cols=["#276b30","#1e8030","#338840","#0f4a18","#3da048","#2d9040"]
    for _ in range(160):
        put(img,rng.randint(0,S-1),rng.randint(0,S-1),rng.choice(cols))
    for _ in range(6):
        fill_circle(img,rng.randint(4,S-5),rng.randint(4,S-5),rng.randint(3,6),"#2a7838",160)
    for _ in range(8):
        put(img,rng.randint(1,S-2),rng.randint(1,S-2),"#081008")
    return img

def blk_dog_statue():
    img=new_img(); c="#9a8878"
    fill_rect(img,0,0,S,S,c)
    rng=random.Random(25)
    for _ in range(40):
        put(img,rng.randint(0,S-1),rng.randint(0,S-1),
            darken(c,0.75) if rng.random()<0.5 else lighten(c,1.15))
    fc="#c8a870"
    fill_circle(img,16,14,10,fc)
    fill_circle(img,8,8,5,darken(fc,0.8)); fill_circle(img,24,8,5,darken(fc,0.8))
    fill_circle(img,8,9,3,darken(fc,0.7)); fill_circle(img,24,9,3,darken(fc,0.7))
    fill_circle(img,16,17,5,"#b89060"); fill_circle(img,16,16,3,"#d4a870")
    fill_circle(img,16,14,2,"#2a1808"); put(img,16,13,"#554030")
    fill_circle(img,11,12,2,"#1a1008"); fill_circle(img,21,12,2,"#1a1008")
    put(img,10,11,"#ffffff"); put(img,20,11,"#ffffff")
    put(img,13,20,"#1a1008"); put(img,14,21,"#1a1008"); put(img,15,21,"#1a1008")
    put(img,16,21,"#1a1008"); put(img,17,21,"#1a1008"); put(img,18,21,"#1a1008")
    put(img,19,20,"#1a1008")
    fill_circle(img,16,22,2,"#ee5555")
    bevel(img,c); return img

def blk_cat_statue():
    img=new_img(); c="#a8908a"
    fill_rect(img,0,0,S,S,c)
    rng=random.Random(26)
    for _ in range(40):
        put(img,rng.randint(0,S-1),rng.randint(0,S-1),
            darken(c,0.75) if rng.random()<0.5 else lighten(c,1.15))
    fc="#d8b8c0"
    fill_circle(img,16,15,10,fc)
    for ex,ey in [(9,6),(23,6)]:
        for i in range(5):
            fill_rect(img,ex-i+4,ey+i,i*2+1,1,fc)
        put(img,ex+4,ey,"#e8b0b8")
    put(img,10,9,"#e8a0a8"); put(img,11,8,"#e8a0a8")
    put(img,21,9,"#e8a0a8"); put(img,22,8,"#e8a0a8")
    fill_circle(img,12,14,3,"#1a0a10"); fill_circle(img,20,14,3,"#1a0a10")
    fill_circle(img,12,14,2,"#44cc88"); fill_circle(img,20,14,2,"#44cc88")
    fill_circle(img,12,14,1,"#050505"); fill_circle(img,20,14,1,"#050505")
    put(img,11,13,"#ffffff"); put(img,19,13,"#ffffff")
    put(img,14,19,"#1a0a10"); put(img,15,20,"#1a0a10"); put(img,16,20,"#1a0a10")
    put(img,17,20,"#1a0a10"); put(img,18,19,"#1a0a10")
    put(img,15,19,"#1a0a10"); put(img,17,19,"#1a0a10")
    draw_line(img,4,17,13,18,"#888080",180); draw_line(img,4,19,13,19,"#888080",180)
    draw_line(img,19,18,28,17,"#888080",180); draw_line(img,19,19,28,19,"#888080",180)
    put(img,16,17,"#ee8899"); put(img,15,18,"#ee8899"); put(img,17,18,"#ee8899")
    bevel(img,c); return img

def blk_bed_block():
    """Bed head — red pillow with wood headboard."""
    img = new_img(); c = "#8c3030"
    fill_rect(img, 0, 0, S, S, "#7a4010")   # wood base
    # Headboard
    fill_rect(img, 1, 1, S-2, S//3, darken("#7a4010", 0.75))
    fill_rect(img, 1, 1, S-2, 1, lighten("#7a4010", 1.3))
    # Pillow area
    fill_rect(img, 3, S//3+1, S-6, S-S//3-4, "#e8e0d8")
    fill_rect(img, 3, S//3+1, S-6, 1, "#ffffff")
    fill_rect(img, 3, S//3+1, 1, S-S//3-4, "#ffffff")
    # Blanket fold
    fill_rect(img, 3, S-6, S-6, 5, c)
    fill_rect(img, 3, S-6, S-6, 1, lighten(c, 1.2))
    bevel(img, "#7a4010"); return img

def blk_bed_foot():
    """Bed foot — continuation of mattress + footboard."""
    img = new_img()
    wood = "#7a4010"; c = "#8c3030"
    fill_rect(img, 0, 0, S, S, wood)
    # Mattress
    fill_rect(img, 3, 1, S-6, S-S//3-2, "#e8e0d8")
    fill_rect(img, 3, 1, S-6, 1, "#ffffff")
    # Blanket
    fill_rect(img, 3, S-S//3-1, S-6, S//3-2, c)
    fill_rect(img, 3, S-S//3-1, S-6, 1, lighten(c, 1.2))
    # Footboard
    fill_rect(img, 1, S-S//3, S-2, S//3, darken(wood, 0.75))
    fill_rect(img, 1, S-S//3, S-2, 1, lighten(wood, 1.2))
    bevel(img, wood); return img

def blk_sand():
    img=new_img(); c="#3a3d52"
    fill_rect(img,0,0,S,S,c)
    rng=random.Random(29)
    grain_cols=["#2e3148","#454866","#303350","#3d4060","#282b40","#4a4e6a","#252840"]
    for _ in range(180):
        px2,py2=rng.randint(0,S-1),rng.randint(0,S-1)
        put(img,px2,py2,rng.choice(grain_cols))
    for _ in range(6):
        sx2=rng.randint(0,S-1); sy2=rng.randint(0,S-1)
        draw_line(img,sx2,sy2,sx2+rng.randint(-4,4),sy2+rng.randint(-3,3),"#4a5888",80)
    for _ in range(12):
        put(img,rng.randint(1,S-2),rng.randint(1,S-2),"#6878a8",140)
    bevel(img,c); return img

def blk_furnace():
    img=new_img(); c="#5a5048"
    fill_rect(img,0,0,S,S,c)
    rng=random.Random(30)
    for _ in range(50):
        put(img,rng.randint(0,S-1),rng.randint(0,S-1),
            darken(c,0.75) if rng.random()<0.5 else lighten(c,1.15))
    for y in range(0,S,8):
        fill_rect(img,0,y,S,1,darken(c,0.6))
    for y in range(0,S,8):
        off=4 if (y//8)%2==0 else 0
        for x in range(off,S,8):
            fill_rect(img,x,y,1,8,darken(c,0.65))
    fill_rect(img,8,14,16,12,darken(c,0.3))
    fill_rect(img,9,15,14,10,"#1a0a00")
    for fx,fy,fr,fc2 in [(16,22,4,"#ff6600"),(16,20,3,"#ff9900"),(16,18,2,"#ffcc00")]:
        fill_circle(img,fx,fy,fr,fc2,160)
    for i in range(8):
        ax=8+i; ay=14-int(math.sqrt(max(0,16-(i-4)**2))*0.8)
        put(img,ax,ay,darken(c,0.5)); put(img,S-9+i,ay,darken(c,0.5))
    fill_rect(img,8,14,1,12,darken(c,0.5)); fill_rect(img,23,14,1,12,darken(c,0.5))
    for ex,ey in [(10,24),(14,26),(18,25),(22,24),(12,22)]:
        put(img,ex,ey,"#ff4400",200)
    bevel(img,c); return img

def blk_sign():
    img=new_img(); c="#a07838"
    fill_rect(img,0,0,S,S,c)
    rng=random.Random(31)
    for _ in range(40):
        put(img,rng.randint(0,S-1),rng.randint(0,S-1),darken(c,0.8) if rng.random()<0.5 else lighten(c,1.15))
    for y in range(8,S-4,8):
        fill_rect(img,4,y,S-8,1,darken(c,0.6))
    bevel(img,c); return img

def blk_skyscreen():
    img=new_img()
    for y in range(S):
        t=y/S
        r=int(80*(1-t)+20*t); g=int(140*(1-t)+60*t); b=int(220*(1-t)+130*t)
        fill_rect(img,0,y,S,1,hx(r,g,b))
    rng=random.Random(32)
    for _ in range(8):
        put(img,rng.randint(0,S-1),rng.randint(0,S//2),"#ffffff",160)
    return img

def blk_credits():
    img=new_img()
    fill_rect(img,0,0,S,S,"#000000")
    for i in range(S):
        put(img,0,i,"#00cc00"); put(img,S-1,i,"#00cc00")
        put(img,i,0,"#00cc00"); put(img,i,S-1,"#00cc00")
    for i in range(1,S-1):
        put(img,1,i,"#009900"); put(img,S-2,i,"#009900")
        put(img,i,1,"#009900"); put(img,i,S-2,"#009900")
    cx,cy=S//2,S//2+2
    put(img,cx-4,cy-4,"#00ff00"); put(img,cx-3,cy-4,"#00ff00")
    put(img,cx+3,cy-4,"#00ff00"); put(img,cx+4,cy-4,"#00ff00")
    for sx2,sy2 in [(-5,2),(-4,3),(-3,4),(-2,4),(-1,4),(0,4),(1,4),(2,4),(3,3),(4,2)]:
        put(img,cx+sx2,cy+sy2,"#00ff00")
    return img

# ─── ITEM TEXTURES ────────────────────────────────────────────

def item_stick():
    img=new_img(); c="#8b5a2b"
    for i in range(20):
        x,y=4+i,24-i
        fill_rect(img,x,y,3,3,c)
        put(img,x,y,lighten(c,1.4))
        put(img,x+2,y+2,darken(c,0.6))
    return img

def item_sword(blade, guard, handle):
    img=new_img()
    bl=lighten(blade,1.5); bd=darken(blade,0.65)
    for i in range(16):
        x,y=20-i,4+i
        fill_rect(img,x-1,y,3,2,blade)
        put(img,x,y,bl); put(img,x-1,y+1,bd)
    fill_rect(img,4,20,2,2,bl)
    fill_rect(img,9,19,10,3,guard)
    fill_rect(img,9,19,10,1,lighten(guard,1.3))
    h="#7a4010"
    for i in range(7):
        fill_rect(img,12,22+i,5,1,h if i%2==0 else darken(h,0.8))
    fill_circle(img,14,30,2,lighten(h,1.2))
    return img

def item_pickaxe(head, handle):
    img=new_img()
    hl=lighten(head,1.4); hd=darken(head,0.65)
    for i in range(14):
        fill_rect(img,16+i,16+i,3,2,handle if i%2==0 else darken(handle,0.75))
    fill_rect(img,4,10,20,4,head)
    fill_rect(img,4,10,20,1,hl); fill_rect(img,4,13,20,1,hd)
    for i in range(4): put(img,3-i,11+i,hl)
    for i in range(4): put(img,24+i,10-i,hl)
    fill_rect(img,14,13,4,4,head)
    return img

def item_axe(head, handle):
    img=new_img()
    hl=lighten(head,1.4); hd=darken(head,0.65)
    for i in range(15):
        fill_rect(img,16+i,14+i,3,2,handle if i%2==0 else darken(handle,0.75))
    for y in range(14):
        curve=int(math.sqrt(max(0,49-(y-7)**2)))
        fill_rect(img,4,4+y,4+curve,1,head)
        put(img,4,4+y,hl); put(img,4+curve+3,4+y,hl)
    fill_rect(img,13,11,4,4,head)
    return img

def item_shovel(head, handle):
    img=new_img()
    hl=lighten(head,1.4); hd=darken(head,0.65)
    for i in range(16):
        fill_rect(img,13,3+i,4,1,handle if i%2==0 else darken(handle,0.75))
    fill_rect(img,9,18,12,10,head)
    fill_rect(img,9,18,12,1,hl); fill_rect(img,9,18,1,10,hl)
    fill_rect(img,20,18,1,10,hd); fill_rect(img,9,27,12,1,hd)
    fill_rect(img,10,28,10,2,head); fill_rect(img,11,29,8,1,darken(head,0.5))
    fill_rect(img,12,14,6,5,head)
    return img

def item_berry():
    img=new_img()
    fill_rect(img,15,3,2,7,"#2a5c10")
    fill_rect(img,10,6,5,2,"#2a5c10"); fill_rect(img,17,5,5,2,"#2a5c10")
    for bx2,by2,r in [(11,14,5),(21,12,4),(16,21,5)]:
        for dy in range(-r,r+1):
            for dx in range(-r,r+1):
                if dx*dx+dy*dy<=r*r:
                    f=1.0-(dx+dy)/(r*2+1)*0.5
                    g=int(min(255,190*f)); gr=int(min(255,55*f))
                    fill_rect(img,bx2+dx,by2+dy,1,1,hx(gr,g,int(45*f)))
        put(img,bx2-1,by2-1,"#ccff88"); put(img,bx2-2,by2-1,"#aaf060")
    return img

def item_bread():
    img=new_img()
    for y in range(S):
        for x in range(S):
            cx2,cy2=x-16,y-17
            if (cx2/12)**2+(cy2/9)**2<=1:
                edge=(cx2/12)**2+(cy2/9)**2
                if edge>0.82:   r2,g2,b2=130,72,18
                elif edge>0.55: r2,g2,b2=195,132,48
                else:           r2,g2,b2=228,182,95
                if cy2<-3 and edge<0.65:
                    r2=min(255,r2+28); g2=min(255,g2+18)
                fill_rect(img,x,y,1,1,hx(r2,g2,b2))
    for sx in [10,17,24]:
        for sy in range(10,23):
            if (sx-16)**2/144+(sy-17)**2/81<=1:
                put(img,sx,sy,hx(105,55,12))
    return img

def item_hoe():
    img=new_img()
    handle="#8c5919"; head="#c8822a"
    hl=lighten(head,1.4); hd=darken(head,0.65)
    for i in range(16):
        fill_rect(img,14+i,14+i,3,2,handle if i%2==0 else darken(handle,0.8))
    fill_rect(img,3,8,18,4,head)
    fill_rect(img,3,8,18,1,hl); fill_rect(img,3,11,18,1,hd); fill_rect(img,3,8,1,4,hl)
    fill_rect(img,4,12,2,6,head)
    fill_rect(img,4,12,1,6,hl); fill_rect(img,5,17,2,1,hd)
    fill_rect(img,12,11,4,5,head)
    return img

def item_wheat_seeds():
    img=new_img()
    sc="#c8a030"; bg="#6a4a18"
    fill_circle(img,16,16,12,bg); fill_circle(img,16,16,10,darken(bg,0.8))
    rng=random.Random(112)
    for _ in range(14):
        sx,sy=int(16+rng.uniform(-7,7)), int(16+rng.uniform(-7,7))
        fill_circle(img,sx,sy,1.5,sc); put(img,sx,sy,lighten(sc,1.3))
    fill_circle(img,12,12,3,"#e8c860",80)
    bevel(img,bg); return img

def item_wheat_item():
    img=new_img()
    stem="#c8a030"; grain="#f0d060"; leaf="#a88020"
    for i in range(20):
        x,y=6+i,26-i
        fill_rect(img,x,y,2,2,stem)
        if i%3==0: put(img,x,y,lighten(stem,1.3))
    draw_line(img,10,22,6,18,leaf); draw_line(img,16,16,20,12,leaf)
    for i in range(7):
        gx=20+i//2; gy=8-i
        fill_rect(img,gx-1,gy,4,2,grain)
        if i%2==0: put(img,gx,gy-1,lighten(grain,1.2))
    return img

def item_apple():
    img=new_img()
    ac="#7830b0"; ahl=lighten(ac,1.5); ahd=darken(ac,0.55)
    for y in range(S):
        for x in range(S):
            cx2,cy2=x-16,y-17
            if (cx2/10)**2+(cy2/10)**2<=1:
                edge=(cx2/10)**2+(cy2/10)**2
                r2=int(min(255,int(ac[1:3],16)*(1.0-edge*0.3)))
                g2=int(min(255,int(ac[3:5],16)*(1.0-edge*0.3)))
                b2=int(min(255,int(ac[5:7],16)*(1.0-edge*0.2)))
                fill_rect(img,x,y,1,1,hx(r2,g2,b2))
    fill_circle(img,12,12,3,ahl,140)
    fill_rect(img,15,6,2,5,"#4a2808"); put(img,15,5,"#2a1404")
    for i in range(5): fill_rect(img,15+i,5-i,3,1,"#2a6010")
    for i in range(S):
        put(img,0,i,lighten(ac,1.2),100); put(img,i,0,lighten(ac,1.2),100)
        put(img,S-1,i,ahd,100); put(img,i,S-1,ahd,100)
    return img

def item_raw_meat():
    img=new_img()
    mc="#d85040"; fat="#f0c8b8"; dark=darken(mc,0.65)
    rng=random.Random(116)
    for y in range(S):
        for x in range(S):
            cx2,cy2=x-16,y-16
            if (cx2/11)**2+(cy2/9)**2<=1:
                n=math.sin(cx2*0.4+cy2*0.3)*math.cos(cy2*0.5)*0.5+0.5
                if n>0.7: put(img,x,y,fat)
                elif n<0.2: put(img,x,y,dark)
                else: put(img,x,y,mc)
    for i in range(2):
        for x in range(S):
            put(img,x,i,dark,120); put(img,x,S-1-i,dark,120)
        for y in range(S):
            put(img,i,y,dark,120); put(img,S-1-i,y,dark,120)
    return img

def item_cooked_meat():
    img=new_img()
    mc="#8a4020"; char="#2a1008"; crust="#c06030"
    rng=random.Random(115)
    for y in range(S):
        for x in range(S):
            cx2,cy2=x-16,y-16
            if (cx2/11)**2+(cy2/9)**2<=1:
                edge=(cx2/11)**2+(cy2/9)**2
                n=math.sin(cx2*0.5+cy2*0.4)*0.4+0.6
                if edge>0.82: put(img,x,y,char)
                elif edge>0.6: put(img,x,y,darken(mc,0.7) if n>0.5 else char)
                else: put(img,x,y,crust if n>0.6 else mc)
    for i in range(3):
        draw_line(img,4+i*8,8,10+i*8,22,char,180)
    return img

def item_tricksabre():
    """
    Tricksabre — pale violet blade, thin and elegant, slight shimmer.
    Crystal-set guard. Wrapped handle.
    """
    img = new_img()
    blade = "#c8b4ff"
    bl = lighten(blade, 1.4)
    bd = darken(blade, 0.6)
    guard_col = "#9070d8"
    handle_col = "#3a2060"

    # Blade — thinner than normal sword, slight curve
    for i in range(18):
        x, y = 21-i, 3+i
        fill_rect(img, x-1, y, 2, 2, blade)
        put(img, x, y, bl)
        put(img, x-1, y+1, bd)
        # Shimmer streak on blade
        if i % 4 == 0:
            put(img, x, y, "#ffffff", 180)

    # Blade tip — sharper
    put(img, 21, 3, bl); put(img, 20, 4, bl)

    # Guard — crystal-set crossguard
    fill_rect(img, 7, 20, 12, 3, guard_col)
    fill_rect(img, 7, 20, 12, 1, lighten(guard_col, 1.3))
    # Crystal gems on guard
    fill_circle(img, 8, 21, 1, "#19d8e5")
    fill_circle(img, 18, 21, 1, "#19d8e5")
    put(img, 8, 20, "#aaffff"); put(img, 18, 20, "#aaffff")

    # Handle — wrapped grip
    for i in range(7):
        wrap = lighten(handle_col, 1.1) if i % 2 == 0 else handle_col
        fill_rect(img, 11, 23+i, 5, 1, wrap)
    fill_rect(img, 11, 23, 5, 1, lighten(handle_col, 1.3))

    # Pommel
    fill_circle(img, 13, 31, 2, lighten(guard_col, 1.2))
    put(img, 13, 30, "#ffffff")

    return img

# ─── ENTITY FACE TEXTURES ─────────────────────────────────────

def face_brute():
    img=new_img()
    base="#8a2888"; hl=lighten(base,1.4)
    fill_rect(img,0,0,S,S,base)
    rng=random.Random(200)
    for _ in range(30):
        put(img,rng.randint(0,S-1),rng.randint(0,S-1),
            darken(base,0.75) if rng.random()<0.5 else hl)
    fill_circle(img,9,12,3,"#0a0010"); fill_circle(img,23,12,3,"#0a0010")
    put(img,9,11,"#cc44cc"); put(img,23,11,"#cc44cc")
    fill_rect(img,5,8,10,2,darken(base,0.5)); fill_rect(img,17,8,10,2,darken(base,0.5))
    fill_rect(img,7,20,18,4,darken(base,0.4))
    for fx in [9,13,17,21]: fill_rect(img,fx,20,2,5,"#f0e8ff")
    bevel(img,base); return img

def face_lurker():
    img=new_img()
    base="#1890b8"
    fill_rect(img,0,0,S,S,base)
    rng=random.Random(201)
    for _ in range(25):
        put(img,rng.randint(0,S-1),rng.randint(0,S-1),
            darken(base,0.7) if rng.random()<0.5 else lighten(base,1.3))
    fill_circle(img,9,13,4,"#e8f808"); fill_circle(img,23,13,4,"#e8f808")
    fill_circle(img,9,13,2,"#0a0808"); fill_circle(img,23,13,2,"#0a0808")
    put(img,8,12,"#ffffff"); put(img,22,12,"#ffffff")
    fill_rect(img,7,22,18,1,"#0a0808"); fill_rect(img,8,23,16,1,"#0a0808")
    for tx in [9,13,17,21]: put(img,tx,22,"#ffffff"); put(img,tx,23,"#ffffff")
    bevel(img,base); return img

def face_sheep():
    img=new_img(); base="#e0e0e0"
    fill_rect(img,0,0,S,S,base); fill_circle(img,16,15,12,base)
    rng=random.Random(202)
    for _ in range(40):
        fill_circle(img,rng.randint(5,27),rng.randint(4,24),rng.randint(2,4),"#f4f4f4",160)
    fill_circle(img,11,13,2,"#1a1008"); fill_circle(img,21,13,2,"#1a1008")
    put(img,10,12,"#ffffff"); put(img,20,12,"#ffffff")
    fill_circle(img,16,19,4,"#c8b0a8")
    put(img,14,19,"#8a7068"); put(img,18,19,"#8a7068")
    put(img,15,22,"#8a7068"); put(img,16,22,"#8a7068"); put(img,17,22,"#8a7068")
    return img

def face_pig():
    img=new_img(); base="#f0b4a0"
    fill_rect(img,0,0,S,S,base); fill_circle(img,16,15,12,base)
    fill_circle(img,11,12,2,"#1a0a10"); fill_circle(img,21,12,2,"#1a0a10")
    put(img,10,11,"#ffffff"); put(img,20,11,"#ffffff")
    fill_circle(img,16,19,6,"#e8a090")
    fill_circle(img,13,20,2,"#b06858"); fill_circle(img,19,20,2,"#b06858")
    fill_circle(img,9,7,4,darken(base,0.85)); fill_circle(img,23,7,4,darken(base,0.85))
    draw_line(img,11,24,16,27,"#8a5040"); draw_line(img,16,27,21,24,"#8a5040")
    return img

def face_chicken():
    img=new_img(); base="#f4ead8"
    fill_rect(img,0,0,S,S,base); fill_circle(img,16,15,11,base)
    fill_circle(img,11,13,2,"#1a1008"); fill_circle(img,21,13,2,"#1a1008")
    put(img,10,12,"#ffffff"); put(img,20,12,"#ffffff")
    fill_circle(img,11,13,1,"#f04000"); fill_circle(img,21,13,1,"#f04000")
    fill_rect(img,14,17,4,3,"#f0b800"); fill_rect(img,13,18,6,2,"#d09800")
    put(img,13,17,"#f0b800"); put(img,18,17,"#f0b800")
    fill_rect(img,13,6,6,4,"#d02020")
    fill_circle(img,13,6,2,"#e03030"); fill_circle(img,16,5,2,"#e03030"); fill_circle(img,19,6,2,"#e03030")
    fill_circle(img,16,22,2,"#d02020")
    return img

# ─── BUILD TABLE ──────────────────────────────────────────────

ALL = {
    # ── blocks ──
    "keiro_grass":    blk_grass,
    "keiro_soil":     blk_soil,
    "keiro_stone":    blk_stone,
    "shinen_rock":    blk_shinen_rock,
    "shinen_crystal": blk_crystal,
    "shinen_ember":   blk_ember,
    "kasumi_snow":    blk_snow,
    "kasumi_ice":     blk_ice,
    "kasumi_shale":   blk_shale,
    "mori_wood":      blk_wood,
    "mori_leaves":    blk_leaves,
    "mori_moss":      blk_moss,
    "reiki_water":    blk_water,
    "tamashii_lava":  blk_lava,
    "cloud":          blk_cloud,
    "workbench":      blk_workbench,
    "glass":          blk_glass,
    "door":           blk_door,           # ← sliding door (replaces swing door)
    "door_top":       blk_door_top,       # ← sliding door top
    "glass_door":     blk_glass_door,     # ← NEW
    "glass_door_top": blk_glass_door_top, # ← NEW
    "farmland":       blk_farmland,
    "wheat0":         lambda: blk_wheat(0),
    "wheat1":         lambda: blk_wheat(1),
    "wheat2":         lambda: blk_wheat(2),
    "wheat3":         lambda: blk_wheat(3),
    "bush_leaves":    blk_bush_leaves,
    "dog_statue":     blk_dog_statue,
    "cat_statue":     blk_cat_statue,
    "bed_block":      blk_bed_block,      # ← NEW (was missing)
    "bed_foot":       blk_bed_foot,       # ← NEW (was missing)
    "sand":           blk_sand,
    "furnace":        blk_furnace,
    "sign":           blk_sign,
    "skyscreen":      blk_skyscreen,
    "credits":        blk_credits,
    # ── items ──
    "stick":          item_stick,
    "wood_sword":     lambda: item_sword("#c8822a","#d4a050","#8c5919"),
    "stone_sword":    lambda: item_sword("#b0aab8","#888090","#7a7485"),
    "wood_pick":      lambda: item_pickaxe("#c8822a","#8c5919"),
    "stone_pick":     lambda: item_pickaxe("#b0aab8","#7a7485"),
    "wood_axe":       lambda: item_axe("#c8822a","#8c5919"),
    "stone_axe":      lambda: item_axe("#b0aab8","#7a7485"),
    "wood_shovel":    lambda: item_shovel("#c8822a","#8c5919"),
    "stone_shovel":   lambda: item_shovel("#b0aab8","#7a7485"),
    "berry":          item_berry,
    "bread":          item_bread,
    "hoe":            item_hoe,
    "wheat_seeds":    item_wheat_seeds,
    "wheat_item":     item_wheat_item,
    "apple":          item_apple,
    "raw_meat":       item_raw_meat,
    "cooked_meat":    item_cooked_meat,
    "tricksabre":     item_tricksabre,    # ← NEW
    # ── entity faces ──
    # grunt_face intentionally NOT generated — draw your own!
    "brute_face":     face_brute,
    "lurker_face":    face_lurker,
    "sheep_face":     face_sheep,
    "pig_face":       face_pig,
    "chicken_face":   face_chicken,
}

# ─── WRITE (skip if already exists) ──────────────────────────

generated = []
skipped   = []

for name, fn in ALL.items():
    path = os.path.join(OUT, f"{name}.png")
    if os.path.exists(path):
        skipped.append(name)
        continue
    img = fn()
    img.save(path)
    big = img.resize((256,256), Image.NEAREST)
    big.save(os.path.join(OUT, f"{name}_preview.png"))
    generated.append(name)

print(f"\nDone.")
print(f"  Generated : {len(generated)}")
for n in generated: print(f"    + {n}.png")
print(f"  Skipped (already exist): {len(skipped)}")
for n in skipped:   print(f"    ~ {n}.png")
print(f"\nNOTE: grunt_face.png was not generated — draw your own and drop it in {OUT}")