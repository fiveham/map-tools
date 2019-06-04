def _is_concave(angle):
    a,b,c = angle
    ab = (b[0] - a[0], b[1] - a[1])
    bc = (c[0] - b[0], c[1] - b[1])
    x = ab[0] * bc[1] - ab[1] * bc[0]
    return x < 0

def _gen_angles(mutated_border):
    for i in range(1, len(mutated_border) - 1):
        a,b,c = mutated_border[i-1:i+2]
        yield (a,b,c)

def _has_concave_angles(mutated_border):
    return any(_is_concave(angle) 
               for angle in _gen_angles(mutated_border))

def _remove_concave_angles(mutated_border):
    return (mutated_border[:1] +
            [angle[1]
             for angle in _gen_angles(mutated_border)
             if not _is_concave(angle)] +
            mutated_border[-1:])

#This function assumes that an outer border curls counterclockwise as in KML
#Additionally, it is designed to only work on boundary segments rather than 
#on entire boundaries. It made sense at the time and was a good idea in 
#context. 
def convexify_segment(mutable_border_segment):
    mutated_border = mutable_border_segment.copy()
    while _has_concave_angles(mutated_border):
        mutated_border = _remove_concave_angles(mutated_border)
    return mutated_border
