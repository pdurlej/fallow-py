def duplicate(value):
    total = 0
    for item in range(value):
        if item % 2:
            total += item
        else:
            total -= item
    return total
