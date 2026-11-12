import re

def natural_room_key(room_obj_or_str):
    """
    Extracts numeric parts as integers so rooms sort in natural ascending order:
    1, 2, 3, 4, ..., 10, 11, 101.
    Places None / unassigned at the end: (1, float('inf')).
    Accepts:
      - Room instance (reads .room_number)
      - Resident instance (reads .room.room_number if assigned)
      - String or integer room identifier (e.g. '1', 'Room 2', '101')
      - None / empty string
    """
    if room_obj_or_str is None:
        return (1, float('inf'))

    # If a Resident object is passed, check their assigned room
    if hasattr(room_obj_or_str, 'room') and not hasattr(room_obj_or_str, 'room_number'):
        room_obj_or_str = room_obj_or_str.room
        if room_obj_or_str is None:
            return (1, float('inf'))

    # If a Room object is passed, extract room_number
    if hasattr(room_obj_or_str, 'room_number'):
        raw_val = room_obj_or_str.room_number
    else:
        raw_val = str(room_obj_or_str)

    if raw_val is None:
        return (1, float('inf'))

    val = str(raw_val).strip()
    if not val or val.lower() in ('none', 'unassigned', '', '-'):
        return (1, float('inf'))

    # Strip prefixes like 'room ' or 'rm ' so 'Room 2' sorts directly with '2'
    normalized = re.sub(r'^(room|rm)[.\s_-]*', '', val, flags=re.IGNORECASE).strip()
    target = normalized if normalized else val

    # Extract tokens with digits converted to integers:
    # Use (0, int(part)) vs (1, part.lower()) so Python 3 comparison never throws TypeError
    tokens = []
    for part in re.split(r'(\d+)', target):
        if not part:
            continue
        if part.isdigit():
            tokens.append((0, int(part)))
        else:
            tokens.append((1, part.lower().strip()))

    if not tokens:
        return (1, float('inf'))

    return (0, tokens)


def natural_resident_key(resident):
    """
    Sorts residents room-wise (Room 1, Room 2, ..., unassigned at end),
    and secondarily by resident's full name alphabetically.
    """
    if not resident:
        return ((1, float('inf')), '')
    r_key = natural_room_key(resident.room if hasattr(resident, 'room') else None)
    name = (resident.full_name if hasattr(resident, 'full_name') else str(resident)).lower().strip()
    return (r_key, name)
