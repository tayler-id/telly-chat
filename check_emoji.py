#!/usr/bin/env python3
"""Check the exact emoji and text used in telly_tool.py"""

# The line from telly_tool.py
text = '📊 **Full transcript:**'

print("Text representation:", repr(text))
print("Characters:")
for i, char in enumerate(text):
    print(f"  {i}: {repr(char)} (ord: {ord(char)})")
    
# Check if the emoji matches
print("\nEmoji check:")
print("Is 📊 present?", "📊" in text)
print("Is 📈 present?", "📈" in text)