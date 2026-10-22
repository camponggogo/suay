from pathlib import Path

p = Path('scripts/build_story.py')
t = p.read_text(encoding='utf-8')

t = t.replace(
    ".chapter{display:grid;grid-template-columns:104px 1fr;gap:26px;padding:26px 0;border-bottom:1px dashed #e4efe9}",
    ".chapter{display:grid;grid-template-columns:96px 200px 1fr;gap:22px;padding:22px 0;"
    "border-bottom:1px dashed #e4efe9;align-items:start}")

old_chapter = """CHAPTER = '''<div class="chapter"><div class="when">{date}</div>
 <div class="body dot"><div class="vig-wrap">{vig}</div><h2>{title}</h2><p>{body}</p>
 <span class="metric">{metric}</span></div></div>'''"""
new_chapter = """CHAPTER = '''<div class="chapter"><div class="when">{date}</div>
 <div class="vig-wrap">{vig}</div>
 <div class="body dot"><h2>{title}</h2><p>{body}</p><span class="metric">{metric}</span></div></div>'''"""
if old_chapter in t:
    t = t.replace(old_chapter, new_chapter)
else:
    print('chapter template not found')

t = t.replace(".vig{width:100%;max-width:300px;height:auto;display:block;margin:8px 0 14px}",
              ".vig{width:100%;max-width:190px;height:auto;display:block;margin:6px 0 0}")

t = t.replace(
    "@media(max-width:760px){.tl:before{left:8px}.chapter{grid-template-columns:1fr;gap:6px;padding-left:26px}",
    "@media(max-width:860px){.chapter{grid-template-columns:74px 1fr}.vig-wrap{grid-column:2;max-width:220px}"
    ".body{grid-column:2}}\n"
    "@media(max-width:760px){.tl:before{left:8px}.chapter{grid-template-columns:1fr;gap:6px;padding-left:26px}")

p.write_text(t, encoding='utf-8')
print('patched')
