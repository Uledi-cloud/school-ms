# check_encoding.py
bad = []
with open("app.py", "rb") as f:
    for n, line in enumerate(f.readlines(), 1):
        nonascii = [b for b in line if b > 127]
        if nonascii:
            bad.append((n, nonascii[:5]))

if bad:
    print("Bad lines found:")
    for n, bytes_list in bad:
        print(f"  Line {n}: byte values {bytes_list}")
else:
    print("All clean!")
