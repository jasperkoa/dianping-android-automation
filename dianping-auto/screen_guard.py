# -*- coding: utf-8 -*-
"""Guard the Mi9SE portrait content area against sticky toolbars and tabs."""


def list_area(width, height):
    # Observed Mi9SE: top toolbar ends near 213px, bottom tabs start near 2013px.
    # Keep an extra margin so partially covered controls cannot be clicked.
    return (round(width*.02), round(height*.105), round(width*.98), round(height*.85))


def inside(rect, area):
    x1, y1, x2, y2 = rect
    left, top, right, bottom = area
    return left <= x1 < x2 <= right and top <= y1 < y2 <= bottom


def orange_button(image, rect):
    x1, y1, x2, y2 = map(int, rect)
    if not inside(rect, (0, 0, image.width, image.height)):
        return False
    pixels = list(image.crop((x1, y1, x2, y2)).convert('RGB').resize((40, 20)).getdata())
    orange = sum(r > 210 and 45 < g < 195 and b < 145 and r-g > 55 for r, g, b in pixels)
    return orange / len(pixels) >= .35


def footer_present(image):
    """Recognize the observed white three-tab footer by its three icon clusters."""
    w, h = image.size
    clusters = []
    for fraction in (1/6, .5, 5/6):
        region = image.crop((int(w*(fraction-.065)), int(h*.868),
                             int(w*(fraction+.065)), int(h*.903))).convert('RGB')
        values = list(region.getdata())
        ink = sum((max(p)-min(p) < 25 and 115 < sum(p)/3 < 225)
                  or (p[0] > 210 and 45 < p[1] < 195 and p[2] < 145) for p in values)
        clusters.append(ink / max(1, len(values)) > .025)
    return all(clusters)


def mine_selected(image):
    if not footer_present(image):
        return False
    w, h = image.size
    densities = []
    for fraction in (1/6, 5/6):
        region = image.crop((int(w*(fraction-.065)), int(h*.868),
                             int(w*(fraction+.065)), int(h*.903))).convert('RGB')
        values = list(region.getdata())
        densities.append(sum(r > 210 and 45 < g < 195 and b < 145 and r-g > 55
                             for r, g, b in values) / max(1, len(values)))
    return densities[1] > .03 and densities[0] < .02
