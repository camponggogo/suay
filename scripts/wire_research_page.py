from pathlib import Path

thai = Path('landing/th/index.html')
text = thai.read_text(encoding='utf-8')
if 'research.html' not in text:
    text = text.replace('<a href="#installation">ติดตั้ง</a>',
                        '<a href="#installation">ติดตั้ง</a><a href="../research.html">งานวิจัย</a>', 1)
    thai.write_text(text, encoding='utf-8')
    print('th nav updated')
else:
    print('th nav already has research link')

deploy = Path('deploy/deploy_landing.py')
source = deploy.read_text(encoding='utf-8')
if 'research.html' not in source:
    source = source.replace("'language-menu.js', 'anatomy.js'",
                            "'research.html', 'language-menu.js', 'anatomy.js'", 1)
    deploy.write_text(source, encoding='utf-8')
    print('deploy whitelist updated')
else:
    print('deploy whitelist already lists research.html')
