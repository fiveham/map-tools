def dist2(p1, p2):
    if len(p1) != len(p2):
        raise ValueError('Mismatched lengths')
    return sum((a - b) ** 2 for a,b in zip(p1, p2))

def dist(p1, p2):
    return dist2(p1, p2) ** 0.5
