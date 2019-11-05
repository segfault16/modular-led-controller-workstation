#!/usr/bin/env python

spacing = 0.1  # m
numRows = 4*8
numCols = 6*8
lines = []
for c in range(int(-numCols/2), int(numCols/2)):
    rs = [range(numRows), reversed(range(numRows))][c % 2]
    for r in rs:
        lines.append('  {"point": [%.2f, %.2f, %.2f]}' %
                     (c*spacing, 0, (r - numRows/2)*spacing))
print('[\n' + ',\n'.join(lines) + '\n]')
