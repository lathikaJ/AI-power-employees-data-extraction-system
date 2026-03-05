from bs4 import BeautifulSoup

with open('walmart_leadership.html', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')
    for script in soup.find_all('script'):
        if 'John Furner' in script.get_text():
            print('Script Type:', script.get('type'))
            print('Script Content snippet:', script.get_text()[:500])
            break
