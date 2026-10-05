"""Bounded WAD2 validation, original blockout textures, and PNG previews."""

from pathlib import Path
import struct
import zlib

from .geometry import texture_name


def miptex(name, width, height, pixels):
    texture_name(name)
    if width <= 0 or height <= 0 or width % 16 or height % 16 or max(width,height) > 1024:
        raise ValueError("Quake textures must be multiples of 16, up to 1024")
    if len(pixels) != width*height:
        raise ValueError("Pixel count does not match texture dimensions")
    levels, offsets = [], []
    for level in range(4):
        offsets.append(40+sum(map(len,levels)))
        step = 1 << level
        levels.append(bytes(pixels[y*width+x] for y in range(0,height,step) for x in range(0,width,step)))
    return struct.pack("<16s6I",name.encode(),width,height,*offsets)+b"".join(levels)


def write_wad(path, textures):
    data, directory = bytearray(), bytearray()
    for name,payload in textures.items():
        texture_name(name)
        directory.extend(struct.pack("<iiiBB2x16s",12+len(data),len(payload),len(payload),68,0,name.encode()))
        data.extend(payload)
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(struct.pack("<4sii",b"WAD2",len(textures),12+len(data))+data+directory)
    return path


def validate_miptex(data):
    if len(data) < 40:
        raise ValueError("Truncated miptex header")
    raw,w,h,*offsets = struct.unpack_from("<16s6I",data)
    name = raw.split(b"\0",1)[0].decode("ascii")
    texture_name(name)
    if not 0 < w <= 1024 or not 0 < h <= 1024 or w%16 or h%16:
        raise ValueError(f"{name}: invalid texture dimensions {w}x{h}")
    previous_end = 40
    for i,offset in enumerate(offsets):
        end = offset+(w>>i)*(h>>i)
        if offset < previous_end or end > len(data):
            raise ValueError(f"{name}: truncated or overlapping mip level {i}")
        previous_end = end
    return {"name":name,"width":w,"height":h,"pixels":data[offsets[0]:offsets[0]+w*h]}


def read_wad(path):
    data = Path(path).read_bytes()
    if len(data) < 12:
        raise ValueError("Truncated WAD header")
    magic,count,directory = struct.unpack_from("<4sii",data)
    if magic != b"WAD2":
        raise ValueError("Expected Quake WAD2; WAD3 requires palette conversion")
    if count < 0 or directory < 12 or directory+count*32 > len(data):
        raise ValueError("Invalid WAD directory")
    textures = {}
    for i in range(count):
        offset,disk_size,size,kind,compression,raw = struct.unpack_from("<iiiBB2x16s",data,directory+i*32)
        if offset < 12 or disk_size < 0 or offset+disk_size > directory:
            raise ValueError("WAD lump extends outside data area")
        if kind != 68:
            continue
        if compression or size != disk_size:
            raise ValueError("Compressed miptex lumps are unsupported")
        texture = validate_miptex(data[offset:offset+disk_size])
        name = raw.split(b"\0",1)[0].decode("ascii")
        if name.casefold() != texture["name"].casefold() or name.casefold() in textures:
            raise ValueError("Duplicate or mismatched WAD texture name")
        textures[name.casefold()] = texture
    return textures


def make_blockout(path):
    # Original procedural art, expressed directly as Quake palette indices.
    # No id palette bytes, downloaded textures, or Makkon assets are needed.
    schemes = {"bh_wall":(5,9),"bh_floor":(2,5),"bh_ceil":(8,11),
               "bh_trim":(96,101),"bh_accent":(160,166),"bh_light":(230,234),
               "trigger":(0,0),"clip":(0,0),"skip":(0,0),"black":(0,0)}
    textures = {}
    for name,(dark,light) in schemes.items():
        pixels = bytes(dark if x%32<2 or y%32<2 else light for y in range(64) for x in range(64))
        textures[name] = miptex(name,64,64,pixels)
    # Classic 256x128 two-layer sky: opaque background on the right, index-0
    # transparent overlay on the left. Both halves are original patterns.
    sky = bytes((0 if (x//16+y//12)%4 else 8) if x<128 else 18+(x//32+y//16)%6
                for y in range(128) for x in range(256))
    textures["sky_bh"] = miptex("sky_bh",256,128,sky)
    return write_wad(path,textures)


def png(path, width, height, rgb):
    def chunk(kind,payload):
        return struct.pack(">I",len(payload))+kind+payload+struct.pack(">I",zlib.crc32(kind+payload)&0xffffffff)
    rows = b"".join(b"\0"+rgb[y*width*3:(y+1)*width*3] for y in range(height))
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,2,0,0,0))+
                          chunk(b"IDAT",zlib.compress(rows))+chunk(b"IEND",b""))


def preview(wad, palette, output):
    colors = Path(palette).read_bytes()
    if len(colors) != 768:
        raise ValueError("Quake palette.lmp must be 768 bytes")
    output = Path(output)
    output.mkdir(parents=True,exist_ok=True)
    result = []
    for index,texture in enumerate(read_wad(wad).values()):
        filename = f"{index:04d}.png"
        rgb = b"".join(colors[p*3:p*3+3] for p in texture["pixels"])
        png(output/filename,texture["width"],texture["height"],rgb)
        result.append({k:v for k,v in texture.items() if k != "pixels"}|{"preview":filename})
    import html, json
    (output/"textures.json").write_text(json.dumps(result,indent=2)+"\n")
    cards = "".join(f'<figure><img src="{t["preview"]}"><figcaption>{html.escape(t["name"])} '
                    f'{t["width"]}x{t["height"]}</figcaption></figure>' for t in result)
    (output/"index.html").write_text('<!doctype html><meta charset="utf-8"><title>WAD preview</title>'
        '<style>body{background:#202126;color:#eee;font:14px monospace}main{display:flex;flex-wrap:wrap}'
        'figure{margin:12px}img{max-width:256px;image-rendering:pixelated}</style><main>'+cards+'</main>')
    return output/"index.html"
