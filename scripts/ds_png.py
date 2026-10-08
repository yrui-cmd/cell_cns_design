"""Bounded PNG structure, CRC, zlib and scanline validation without dependencies."""
import struct
import zlib

def validate_png_bytes(data, max_bytes=32*1024*1024):
    if not isinstance(data, bytes) or not 45 <= len(data) <= max_bytes or data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Invalid PNG signature or size')
    pos, chunks, compressed = 8, [], bytearray()
    width = height = bits = color = interlace = None
    ended = False
    idat_closed = False
    palette = False
    while pos < len(data):
        if pos+12 > len(data): raise ValueError('Truncated PNG chunk')
        size = struct.unpack('>I',data[pos:pos+4])[0]
        tag = data[pos+4:pos+8]
        end = pos+12+size
        if end > len(data): raise ValueError('Truncated PNG payload')
        payload = data[pos+8:pos+8+size]
        crc = struct.unpack('>I',data[pos+8+size:end])[0]
        if zlib.crc32(tag+payload)&0xffffffff != crc: raise ValueError('PNG CRC mismatch')
        if not chunks and tag != b'IHDR': raise ValueError('IHDR must be first')
        if tag == b'IHDR':
            if chunks or size != 13: raise ValueError('Invalid IHDR')
            width,height,bits,color,compression,filter_method,interlace = struct.unpack('>IIBBBBB',payload)
            valid = {0:(1,2,4,8,16),2:(8,16),3:(1,2,4,8),4:(8,16),6:(8,16)}
            if not width or not height or width*height > 32000000 or bits not in valid.get(color,()) or compression or filter_method or interlace not in (0,1):
                raise ValueError('Unsupported PNG dimensions or encoding')
        elif tag == b'PLTE':
            if compressed or palette or not size or size%3 or size>768 or color in (0,4): raise ValueError('Invalid palette')
            palette=True
        elif tag == b'IDAT':
            if idat_closed or color==3 and not palette: raise ValueError('Invalid IDAT ordering')
            compressed.extend(payload)
        elif tag == b'IEND':
            if size or not compressed or end!=len(data): raise ValueError('Invalid PNG ending')
            ended=True
        elif tag in (b'acTL',b'fcTL',b'fdAT'):
            raise ValueError('A static PNG is required')
        elif not tag[0]&32:
            raise ValueError('Unknown critical PNG chunk')
        if compressed and tag != b'IDAT': idat_closed=True
        chunks.append(tag)
        pos=end
    if not ended: raise ValueError('Missing PNG IEND')
    channels={0:1,2:3,3:1,4:2,6:4}[color]
    passes=[(0,0,1,1)] if not interlace else [(0,0,8,8),(4,0,8,8),(0,4,4,8),(2,0,4,4),(0,2,2,4),(1,0,2,2),(0,1,1,2)]
    rows=[]
    for x,y,dx,dy in passes:
        w=max(0,(width-x+dx-1)//dx);h=max(0,(height-y+dy-1)//dy)
        if w and h: rows.append((h,1+(w*channels*bits+7)//8))
    expected=sum(h*n for h,n in rows)
    if expected > 256*1024*1024: raise ValueError('Decoded PNG too large')
    try:
        decoder=zlib.decompressobj()
        raw=decoder.decompress(bytes(compressed),expected+1)
    except zlib.error:
        raise ValueError('Invalid PNG compressed pixels') from None
    if len(raw)!=expected or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError('PNG pixel stream length mismatch')
    pos=0
    for row_count,stride in rows:
        for _ in range(row_count):
            if raw[pos]>4: raise ValueError('Invalid PNG filter')
            pos+=stride
    return {'format':'PNG','width':width,'height':height}
