
numCols = 6*8
numRows = 4*8

def print_header(rows, cols): 
    header = """
    {
        "description":"Panel mapping that corresponds to the openpixelcontrol layout ../layouts/wall_44x22.json",
        "num_rows" : %i,
        "num_cols" : %i,
        "substrips": [
    """ % (rows, cols)

    print(header)

def print_footer():
    footer = """
        ]
    }
    """
    print(footer)

def print_substrip(start_index, row, col, dir, num_pixels):
    substrip = """
            {
            "start_index": %i,
            "row": %i,
            "col": %i,
            "dir": "%s",
            "num_pixels": %i
        }
    """ % (start_index, row, col, dir, num_pixels)
    print(substrip)

def print_substrips(rows, cols):
    start_index=0
    ud = "U"
    # n-1, n-2, n-3...
    for c in reversed(range(cols)):
        if ud == "U":
            print_substrip(start_index, rows-1, c, ud, rows)
        else:
            print_substrip(start_index, 0, c, ud, rows)
        # change direction
        if ud == "U":
            ud = "D"
        else:
            ud = "U"
        start_index += rows
        if c != 0:
            print(",")



print_header(numRows, numCols)
print_substrips(numRows, numCols)
print_footer()