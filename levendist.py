def levendist(s, t, matrix=False, subst_cost=1):
    if not matrix:
        if s == t:
            return 0
        elif s in t or t in s:
            return abs(len(s) - len(t))

    x_max = len(s)
    y_max = len(t)
    
    #Initialize an (x_max + 1)-by-(y_max + 1) matrix with 0s
    #except the sides, where distance from/to "" is non-empty string's length
    d = {(x, y): 0 if x * y != 0 else max(x, y)
         for x in range(x_max + 1)
         for y in range(y_max + 1)}

    #Populate the matrix with real values.
    #Start each for loop at 1 to skip the already-computed values for the
    #low-index sides.
    #the distance from the x-character (0-char, 1-char, 2-char, etc.) prefix
    #substring of s to the y-character prefix substring of t is:
    for y in range(1, y_max + 1):
        for x in range(1, x_max + 1):
            substitute_cost = 0 if s[x - 1] == t[y - 1] else subst_cost
            d[x, y] = min(
                d[x-1, y  ] + 1,               #deletion
                d[x  , y-1] + 1,               #insertion
                d[x-1, y-1] + substitute_cost) #substitution
    
    return d if matrix else d[x_max, y_max]
