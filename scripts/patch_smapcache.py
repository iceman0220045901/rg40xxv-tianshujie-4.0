import sys, os

PATH = r"C:\Users\qq410\Desktop\游戏\天书劫正式版移植工作区\天书劫4.0-rg40xxv-移植\build\jysdl\src\mainmap.c"

WRAP = """/* JY_SMAP_CACHE: reuse the static scene layer when the camera did not move */
int JY_DrawSMap(int sceneid, int x, int y, int xoff, int yoff, int Mypic)
{
    SDL_Rect cr;
    static SDL_Surface *cach = NULL;
    static int ck[8] = {-99,-99,-99,-99,-99,-99,-99,-99};
    static int cw = 0, chh = 0;
    int nk[8];
    int rc;

    if (g_Rotate != 0)
    {
        return JY_DrawSMap_raw(sceneid, x, y, xoff, yoff, Mypic);
    }

    cr = g_Surface->clip_rect;
    nk[0] = sceneid; nk[1] = x; nk[2] = y; nk[3] = xoff;
    nk[4] = yoff; nk[5] = Mypic; nk[6] = cr.x; nk[7] = cr.y;

    if (cach && cw == cr.w && chh == cr.h &&
        nk[0] == ck[0] && nk[1] == ck[1] && nk[2] == ck[2] && nk[3] == ck[3] &&
        nk[4] == ck[4] && nk[5] == ck[5] && nk[6] == ck[6] && nk[7] == ck[7])
    {
        SDL_BlitSurface(cach, NULL, g_Surface, &cr);
        return 0;
    }

    rc = JY_DrawSMap_raw(sceneid, x, y, xoff, yoff, Mypic);

    if (!cach || cw != cr.w || chh != cr.h)
    {
        if (cach) { SDL_FreeSurface(cach); cach = NULL; }
        cach = SDL_CreateRGBSurface(0, cr.w, cr.h, 32,
            g_Surface->format->Rmask, g_Surface->format->Gmask,
            g_Surface->format->Bmask, g_Surface->format->Amask);
        cw = cr.w; chh = cr.h;
    }

    if (cach)
    {
        SDL_BlitSurface(g_Surface, &cr, cach, NULL);
        ck[0] = nk[0]; ck[1] = nk[1]; ck[2] = nk[2]; ck[3] = nk[3];
        ck[4] = nk[4]; ck[5] = nk[5]; ck[6] = nk[6]; ck[7] = nk[7];
    }

    return rc;
}

"""

def main():
    data = open(PATH, 'rb').read()
    if b'JY_SMAP_CACHE' in data:
        print('ALREADY_PATCHED')
        return 0
    sig = b'int JY_DrawSMap(int sceneid, int x, int y, int xoff, int yoff, int Mypic)'
    n1 = data.count(sig)
    print('sig_count=%d' % n1)
    if n1 != 1:
        print('FAIL: signature not unique')
        return 1
    anchor = b'int JY_LoadWarMap(const char* WarIDXfilename'
    n2 = data.count(anchor)
    print('anchor_count=%d' % n2)
    if n2 != 1:
        print('FAIL: anchor not unique')
        return 1

    data = data.replace(sig, b'int JY_DrawSMap_raw(int sceneid, int x, int y, int xoff, int yoff, int Mypic)')

    nl = b'\r\n' if b'\r\n' in data[:4000] else b'\n'
    wb = WRAP.replace('\n', nl.decode()).encode('ascii')
    i = data.index(anchor)
    data = data[:i] + wb + data[i:]

    open(PATH + '.orig_smap', 'wb').write(open(PATH, 'rb').read()) if not os.path.exists(PATH + '.orig_smap') else None
    open(PATH, 'wb').write(data)
    print('PATCH_OK size=%d' % len(data))
    return 0

sys.exit(main())