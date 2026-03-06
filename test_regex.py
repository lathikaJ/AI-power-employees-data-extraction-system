import re
import json

content = """
{
  "employees": [
    {
      "name": "Isaac Cody",
      "designation": "Executive Vice President, Store Operations, Walmart U.S.",
      "email": null,
      "phone": null,
      "linkedin": null,
      "instagram": null,
      "profile_url": "https://corporate.walmart.com/about/leadership/isaac-cody",
      "department": "Walmart U.S."
    }
  ]
}
"""

old_regex = r'(\{.*?\})'
new_regex = r'(\{.*\})'

m1 = re.search(old_regex, content, re.DOTALL)
m2 = re.search(new_regex, content, re.DOTALL)

print(f"Old regex output matches till index {len(m1.group(1))} and causes valid JSON? {m1.group(1).endswith(']}')}")
print(f"Old matched str: {m1.group(1)}")

print(f"New regex output matches till index {len(m2.group(1))} and causes valid JSON? {m2.group(1).endswith(']}')}")
try:
    json.loads(m2.group(1))
    print("New regex parsed cleanly.")
except Exception as e:
    print(f"New regex parse fail: {e}")
