

def stay_in_bounds(v, v_min, v_max):
    if v < v_min: return v_min
    if v > v_max: return v_max
    return v
