from bs4 import BeautifulSoup

def clean(raw_html):
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup(["style", "meta", "noscript", "svg", "path", "head"]):
        tag.decompose()
    for a in soup.find_all("a", href=True):
        link_text = a.get_text(strip=True)
        href = a["href"]
        if any(domain in href.lower() for domain in ["linkedin", "instagram", "twitter", "facebook", "mailto", "tel"]):
            a.replace_with(f" [Link: {link_text} ({href})] ")
        else:
            if "/leadership/" in href or "/team/" in href:
                a.replace_with(f" [Profile: {link_text} ({href})] ")
            else:
                a.replace_with(link_text)
    return soup.get_text(separator=" ", strip=True)

with open('walmart_leadership.html', encoding='utf-8') as f:
    res = clean(f.read())
    idx = res.find("John Furner")
    print(f"John Furner at index: {idx}")
    print(f"Total length: {len(res)}")
    if idx != -1:
        print("SURROUNDING CONTENT:")
        print(res[max(0, idx-500):idx+500])
