# fix_encoding.py
with open("app.py", "rb") as f:
    data = f.read()

replacements = {
    b"\xe2\x80\x94": b"-",   # em-dash
    b"\xe2\x80\x93": b"-",   # en-dash
    b"\xe2\x80\x98": b"'",   # left single quote
    b"\xe2\x80\x99": b"'",   # right single quote
    b"\xe2\x80\x9c": b'"',   # left double quote
    b"\xe2\x80\x9d": b'"',   # right double quote
    b"\xe2\x80\xa2": b"*",   # bullet
    b"\xe2\x80\xa6": b"...", # ellipsis
    b"\x97": b"-",           # Windows-1252 em-dash
    b"\x96": b"-",           # Windows-1252 en-dash
    b"\x91": b"'",           # Windows-1252 quote
    b"\x92": b"'",           # Windows-1252 quote
    b"\x93": b'"',           # Windows-1252 quote
    b"\x94": b'"',           # Windows-1252 quote
    b"\x95": b"*",           # Windows-1252 bullet
    b"\x85": b"...",         # Windows-1252 ellipsis
}

for old, new in replacements.items():
    data = data.replace(old, new)

with open("app.py", "wb") as f:
    f.write(data)

print("Fixed. Non-ASCII bytes replaced.")
