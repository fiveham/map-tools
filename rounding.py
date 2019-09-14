_FLOAT = float

def float(string, length):
    """Round the base-10 number spelled out by `string` to `length`-many digits
       after the decimal point."""
    
    #if `string` has no decimal tail at all, just kick back the original
    try:
        int(string)
        return string
    except ValueError:
        pass
    
    #If given a negative number, round its positive counterpart and return
    #that rounded string prepended with a minus sign
    if _FLOAT(string) < 0:
        return '-' + float(string[1:], length)

    #Split the string into an int head and a decimal tail
    #raise an exception if there's more than 1 . in the string
    head, tail = string.split('.')

    #If the decimal tail fits within the prescribed length, return the original
    if len(tail) <= length:
        return string

    #Split off the parts of the tail before and beyond the length limit
    trunk, branch = tail[:length], tail[length:]

    #set state to 1 if we need to round up or -1 if we need to round down
    #for ties, round to the evens
    stick = _FLOAT('0.' + branch)
    if stick < 0.5:
        state = -1
    elif stick > 0.5:
        state = 1
    else:
        state = (-1
                 if int(trunk[-1]) % 2 == 0
                 else 1)

    #If rounding down, that's easy
    if state < 0:
        return f'{head}.{trunk}'
    #otherwise, we're definitely rounding up

    #cram the int head and the trunk part of the decimal tail together,
    #parse that as an int, 
    #add 1 to round up
    #convert back to string
    #split into two pieces for the int part and the decimal part
    #put the decimal point into the string between those two pieces and return
    stuff = str(int(head + trunk) + 1)
    new_head, new_trunk = stuff[:-length], stuff[-length:]
    return f'{new_head}.{new_trunk}'
