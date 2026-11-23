import json
import os
import re
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

HOST, PORT = "0.0.0.0", int(os.environ.get("PORT", "8766"))
HTML = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Script to Amazon Links</title><style>
*{box-sizing:border-box}body{margin:0;background:#10131b;color:#edf0f8;font:15px system-ui}main{max-width:920px;margin:40px auto;padding:24px}h1{font-size:30px;margin:0 0 8px}.sub{color:#aeb5c7;margin:0 0 24px}.card{background:#1a1f2b;border:1px solid #303849;border-radius:16px;padding:20px;margin:14px 0}label{display:block;font-weight:650;margin:0 0 7px}input,select,textarea{width:100%;padding:12px;border-radius:9px;border:1px solid #3b465a;background:#111620;color:#fff;font:inherit;margin-bottom:14px}textarea{min-height:240px;resize:vertical}button{background:#ffbd45;color:#201800;border:0;border-radius:9px;padding:12px 18px;font-weight:750;font-size:15px;cursor:pointer}button:disabled{opacity:.5}#status{color:#ffcf73;margin-left:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit;line-height:1.6}a{color:#8ecbff}.hint{color:#aeb5c7;font-size:13px}.row{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media(max-width:650px){.row{grid-template-columns:1fr}main{padding:16px;margin:10px auto}}
</style><main><h1>Script → Amazon affiliate links</h1><p class="sub">Paste your script. The tool finds product mentions and searches Amazon Creators API for affiliate links.</p><section class="card"><div class="row"><div><label>API Client ID</label><input id="client" placeholder="Paste Amazon API Client ID" autocomplete="off"></div><div><label>API Secret</label><input id="secret" type="password" placeholder="Paste Amazon API Secret" autocomplete="new-password"></div></div><div class="row"><div><label>Marketplace</label><select id="market"><option value="www.amazon.com">Amazon US</option><option value="www.amazon.co.uk">Amazon UK</option><option value="www.amazon.ca">Amazon Canada</option><option value="www.amazon.de">Amazon Germany</option><option value="www.amazon.in">Amazon India</option><option value="www.amazon.com.au">Amazon Australia</option><option value="www.amazon.co.jp">Amazon Japan</option></select></div><div><label>Associates tracking tag</label><input id="tag" placeholder="yourtag-20"></div></div><label>Video script</label><textarea id="script" placeholder="Paste the full script here…"></textarea><button id="go">Find product affiliate links</button><span id="status"></span><p class="hint">API credentials are used for this search request and are not saved by the tool. Review the product matches before using the links.</p></section><section class="card" id="results" hidden><button id="copy">Copy links</button><pre id="out"></pre></section></main><script>
const $=x=>document.getElementById(x);$('go').onclick=async()=>{if(!$('client').value.trim()||!$('secret').value.trim()||!$('tag').value.trim()||!$('script').value.trim()){ $('status').textContent='Add API credentials, tracking tag, and script.';return} $('go').disabled=true;$('status').textContent='Searching Amazon…';try{let r=await fetch('/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({clientId:$('client').value.trim(),clientSecret:$('secret').value,marketplace:$('market').value,tag:$('tag').value.trim(),script:$('script').value})});let d=await r.json();if(!r.ok)throw Error(d.error||'Request failed');$('out').textContent=d.output;$('results').hidden=false;$('status').textContent='Done';$('secret').value=''}catch(e){$('status').textContent=e.message}finally{$('go').disabled=false}};$('copy').onclick=()=>navigator.clipboard.writeText($('out').textContent);
</script></html>'''

_TOKEN_CACHE = {}

def access_token(client, secret):
    cached = _TOKEN_CACHE.get(client)
    if cached and cached[1] > time.time(): return cached[0]
    token_req=Request('https://api.amazon.com/auth/o2/token',data=json.dumps({'grant_type':'client_credentials','client_id':client,'client_secret':secret,'scope':'creatorsapi::default'}).encode(),headers={'Content-Type':'application/json'},method='POST')
    try:
        with urlopen(token_req,timeout=30) as r: result=json.load(r)
    except HTTPError as e:
        if e.code == 401: raise RuntimeError('Amazon rejected the API Client ID/Secret. Check that both are current and from the same Creators API credential.')
        if e.code == 429: raise RuntimeError('Amazon is rate-limiting token requests. Wait a few minutes, then try again.')
        raise RuntimeError(f'Amazon token request failed with HTTP {e.code}.')
    token = result['access_token']; _TOKEN_CACHE[client] = (token, time.time() + max(60, int(result.get('expires_in', 3600)) - 60))
    return token

def api_search(query, market, tag, token):
    body={'keywords':query,'partnerTag':tag,'marketplace':market,'searchIndex':'All','itemCount':5,'resources':['itemInfo.title']}
    req=Request('https://creatorsapi.amazon/catalog/v1/searchItems',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','x-marketplace':market},method='POST')
    with urlopen(req,timeout=30) as r: return json.load(r).get('searchResult',{}).get('items',[])

def product_terms(script):
    ranked = re.compile(
        r'(?i)\bAt number\s+(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+),\s*'
        r'(?:we have\s+)?(?:the\s+)?(.{3,110}?)'
        r'(?=\s*,\s*(?:Model\b|[A-Z]{2,}[A-Z0-9-]{2,}\b)|\s+(?:is|uses|has|brings|features|offers|combines|takes|comes|records|supports|includes|works|gives|provides)\b|[,.!?])'
    )
    ranked_terms=[]
    for match in ranked.finditer(script):
        term=re.sub(r'^(?:we have\s+)?(?:the\s+)?','',match.group(1).strip(),flags=re.I).strip(' ,')
        if len(term)>3 and term.lower() not in [x.lower() for x in ranked_terms]: ranked_terms.append(term)
    if ranked_terms: return ranked_terms[:10]
    # Fall back to model-like names for scripts that don't use ranked segments.
    patterns=[r'(?i)(?:product|gear|device|camera|phone|laptop|mic|microphone|headphones|keyboard|mouse|tripod|monitor|light|speaker|watch)\s+(?:is\s+)?(?:the\s+)?([A-Z][\w-]*(?:\s+[A-Z0-9][\w-]*){0,4})',r'\b(?:[A-Z][a-zA-Z0-9-]*\s+){1,4}(?:Pro|Max|Mini|Air|Ultra|4K|Mk\s?\d+)\b']
    found=[]
    for p in patterns:
        for m in re.finditer(p,script):
            term=m.group(1).strip(' .,!?;:') if m.lastindex else m.group(0).strip()
            if len(term)>2 and term.lower() not in {'the product','this product'} and term.lower() not in [x.lower() for x in found]: found.append(term)
    # Also use capitalized multiword names as likely brands/models.
    for m in re.finditer(r'\b[A-Z][a-zA-Z0-9-]*(?:\s+[A-Z0-9][a-zA-Z0-9-]*){1,3}\b',script):
        term=m.group(0).strip()
        if term.lower() not in [x.lower() for x in found] and term.lower() not in {'in this','thank you','let me','make sure','amazon associates'}: found.append(term)
    return found[:8]

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def do_GET(self):
        self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(HTML.encode())
    def do_POST(self):
        try:
            data=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))))
            script=data['script'];market=data['marketplace'];tag=data['tag'];terms=product_terms(script);client=data['clientId'];secret=data['clientSecret']
            if not terms: raise RuntimeError('Could not confidently spot product names. Mention brand/model names clearly in the script and try again.')
            lines=['PRODUCT LINKS']
            token=access_token(client,secret)
            for term in terms:
                items=api_search(term,market,tag,token)
                lines.append('\n'+term+':')
                if not items: lines.append('  No matching listing returned.');continue
                for item in items[:3]: lines.append('  - '+item.get('itemInfo',{}).get('title',{}).get('displayValue','Amazon product')+'\n    '+item.get('detailPageURL',''))
            lines += ['', 'Choose the matching product listing for each script mention. Links include your Associates tag.']
            out=json.dumps({'output':'\n'.join(lines)}).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(out)));self.end_headers();self.wfile.write(out)
        except Exception as e:
            msg=json.dumps({'error':str(e)}).encode();self.send_response(400);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(msg)

if __name__=='__main__':
    server=HTTPServer((HOST,PORT),Handler);threading.Timer(.7,lambda:webbrowser.open(f'http://{HOST}:{PORT}')).start();print(f'Tool open at http://{HOST}:{PORT} — press Ctrl+C to stop');server.serve_forever()

