from bs4 import BeautifulSoup
import sys

with open('walmart_leadership.html', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')
    target = soup.find(string=lambda s: 'John Furner' in s)
    if not target:
        print('John Furner not found in text nodes')
        # Maybe it's in an attribute
        target = soup.find(lambda t: any('John Furner' in str(v) for v in t.attrs.values()))
        
    if target:
        print(f'Found: {target.name if hasattr(target, "name") else "text node"}')
        curr = target.parent if not hasattr(target, "name") else target
        path = []
        while curr:
            path.append(str(curr.name))
            curr = curr.parent
        print('Path:', ' -> '.join(reversed(path)))
    else:
        print('Could not find John Furner at all')
