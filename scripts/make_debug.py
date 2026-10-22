from pathlib import Path

p = Path('pasadhi/web/anatomy/pasadhi-pool.html')
t = p.read_text(encoding='utf-8')
hook = ("<script>window.onerror=function(m,s,l,c){document.title='ERR '+m+' @'+l+':'+c;};"
        "window.addEventListener('error',function(e){document.title='ERR '+e.message;});")
t = t.replace('<script>', hook, 1)
Path('pasadhi/web/anatomy/_debug.html').write_text(t, encoding='utf-8')
print('written')
