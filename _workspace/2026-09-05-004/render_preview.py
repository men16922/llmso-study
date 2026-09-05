from pathlib import Path
import markdown,re
R=Path(__file__).parent
s=Path('articles/처리량이 올랐다면 무엇이 빨라진 것인가.md').read_text().replace('<details>','<details markdown="1">')
s=s.replace('](./figures/','](/articles/figures/').replace('](./screenshots/','](/articles/screenshots/')
parts=[]
def render_detail(m):
    inner=markdown.markdown(m[2],extensions=['tables','fenced_code'])
    parts.append('<details><summary>'+m[1]+'</summary>'+inner+'</details>')
    return '\n\nDETAILPLACEHOLDER'+str(len(parts)-1)+'\n\n'
s=re.sub(r'<details markdown="1">\s*<summary>(.*?)</summary>(.*?)</details>',render_detail,s,flags=re.S)
body=markdown.markdown(s,extensions=['tables','fenced_code'])
for i,part in enumerate(parts):body=body.replace('<p>DETAILPLACEHOLDER'+str(i)+'</p>',part)
body=re.sub(r'<pre><code class="language-mermaid">(.*?)</code></pre>',r'<div class="mermaid">\1</div>',body,flags=re.S)
html='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>5주차 개정본 검토</title><style>body{margin:0;color:#242933;background:#fff;font:17px/1.85 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo",sans-serif}main{max-width:800px;margin:60px auto;padding:0 24px}h1{font-size:36px;line-height:1.35}h2{margin-top:56px;font-size:26px;line-height:1.4}p{margin:20px 0}img{max-width:100%;height:auto}table{border-collapse:collapse;display:block;overflow:auto;font-size:15px;margin:24px 0}th,td{border:1px solid #ddd;padding:10px 12px;white-space:nowrap}th{background:#f4f5f7}details{border:1px solid #dce0e5;padding:14px 20px;margin:12px 0;border-radius:7px}summary{cursor:pointer;font-weight:600}pre{background:#f6f7f9;padding:18px;overflow:auto;font-size:13px}code{background:#f1f2f4;padding:2px 4px;border-radius:3px}a{color:#286ab9}em{color:#56616f;font-size:15px}.mermaid{text-align:center}body.mobile main{max-width:390px;margin:24px auto;padding:0 18px}body.mobile h1{font-size:28px}body.mobile h2{font-size:23px}</style><main>'''+body+'''</main><script type="module">import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';mermaid.initialize({startOnLoad:true,theme:'neutral',flowchart:{curve:'linear'}});if(location.search.includes('mobile'))document.body.classList.add('mobile');</script></html>'''
(R/'preview.html').write_text(html)
