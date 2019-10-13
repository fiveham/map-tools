def dist2(p1, p2):
    if len(p1) != len(p2):
        raise ValueError('Mismatched lengths')
    return sum((a - b) ** 2 for a,b in zip(p1, p2))

def dist(p1, p2):
    return dist2(p1, p2) ** 0.5

def cross_sign(a, b, c):
    """Calculate the cross product of the vector from `a` to `b` times the
       vector from `a` to `c`. Return the sign of the z component."""
    x = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return -1 if x < 0 else 1 if x > 0 else 0
