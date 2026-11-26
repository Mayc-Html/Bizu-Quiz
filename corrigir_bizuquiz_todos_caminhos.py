#!/usr/bin/env python3
"""Corrige rotas e recursos do BizuQuiz para Cloudflare Workers. Python 3.8+.
Uso: python corrigir_bizuquiz_todos_caminhos.py [pasta-do-repositorio] [--dry-run]
Nao faz commit, push ou deploy. Revise o diff antes de publicar.
"""
import argparse
import json
import os
import posixpath
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import unquote, quote, urlsplit

SUBJECTS = {'Informatica':'info.html', 'Português':'portugues.html', 'artes':'artes.html',
            'historia':'historia.html', 'matematica':'matematica.html', 'quimica':'quimica.html'}
SKIP = {'.git','.github','.wrangler','node_modules','__pycache__','.venv','venv','dist','.idea','.vscode'}
# Attribute values, CSS url(), and static JavaScript navigation/fetch calls.
REF = re.compile(r'''(?P<prefix>\b(?:href|src|poster)\s*=\s*|\b(?:window\.)?location\s*\.\s*href\s*=\s*|\b(?:window\.)?location\s*\.\s*(?:replace|assign)\s*\(\s*|\bfetch\s*\(\s*|\burl\s*\(\s*)(?P<q>["'])(?P<value>.*?)(?P=q)''', re.I)
CSS_RAW = re.compile(r'(?P<prefix>\burl\(\s*)(?P<value>[^\s"\')][^)]*?)(?P<end>\s*\))', re.I)

def read(p):
    return p.read_text(encoding='utf-8-sig')

def jsonc_load(s):
    # Preserve quoted strings while stripping comments/trailing commas.
    pat = re.compile(r'"(?:\\.|[^"\\])*"|//[^\r\n]*|/\*[\s\S]*?\*/')
    s = pat.sub(lambda m: m.group() if m.group().startswith('"') else '', s)
    s = re.sub(r',(?=\s*[}\]])', '', s)
    return json.loads(s)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('repo', nargs='?', default='.')
    ap.add_argument('--dry-run', action='store_true', help='Simula, sem escrever arquivos')
    args = ap.parse_args()
    root = Path(args.repo).expanduser().resolve()
    if not (root/'Pasta-html/index.html').is_file() or not (root/'Questoes/questoes.css').is_file():
        ap.error('Execute na raiz do BizuQuiz ou informe o caminho dessa pasta.')
    missing = [f'Questoes/{s}/{f}' for s,f in SUBJECTS.items() if not (root/'Questoes'/s/f).is_file()]
    if missing: ap.error('Estrutura diferente da esperada: '+', '.join(missing))
    edits = {}
    issues = set()
    changes = []
    def get(p): return edits[p] if p in edits else read(root/p)
    def put(p,s):
        if not (root/p).exists() or s != read(root/p): edits[p] = s
        else: edits.pop(p,None)
    # Validate configuration before touching any files.
    configs = [p for p in ('wrangler.jsonc','wrangler.json','wrangler.toml') if (root/p).exists()]
    if len(configs)>1: ap.error('Mais de uma configuracao Wrangler encontrada. Resolva o conflito primeiro.')
    cfg = configs[0] if configs else 'wrangler.jsonc'
    if cfg.endswith('.toml'): ap.error('wrangler.toml existente: revise [assets] manualmente; nada foi alterado.')
    try: config = jsonc_load(read(root/cfg)) if configs else {}
    except (ValueError,OSError) as e: ap.error('Configuracao Wrangler ilegivel: '+str(e))
    if not isinstance(config,dict) or not isinstance(config.get('assets',{}),dict): ap.error('Configuracao Wrangler invalida.')
    if any(config.get(k) for k in ('main','site','env')) or config.get('assets',{}).get('run_worker_first') or config.get('assets',{}).get('base_path'):
        ap.error('Configuracao personalizada de Worker detectada. Revise manualmente antes de alterar a publicacao.')
    if config.get('name','bizuquiz') != 'bizuquiz': ap.error('Nome do Worker diferente de bizuquiz; confira o projeto.')
    config.setdefault('name','bizuquiz')
    config.setdefault('compatibility_date',date.today().isoformat())
    config.setdefault('assets',{}).update(directory='./', html_handling='none', not_found_handling='none')
    # Avoid destroying JSONC comments unnecessarily when the effective config is already correct.
    if not configs or jsonc_load(read(root/cfg)) != config:
        put(cfg,json.dumps(config,ensure_ascii=False,indent=2)+'\n')
    # Exact / redirect is necessary because html_handling=none disables directory index rewrites.
    if not (root/'index.html').exists():
        put('index.html','''<!doctype html>\n<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bizu Quiz</title><meta http-equiv="refresh" content="0; url=./Pasta-html/index.html"></head><body><a href="./Pasta-html/index.html">Abrir Bizu Quiz</a></body></html>\n''')
    redirect_old = read(root/'_redirects') if (root/'_redirects').exists() else ''
    # Preserve custom rules except for the exact root, which must point to the entry page.
    lines = redirect_old.splitlines()
    root_rules = [l for l in lines if l.split() and l.split()[0]=='/']
    if root_rules and any(l.split()[1:2] not in [['/index.html'],['/Pasta-html/index.html']] for l in root_rules):
        ap.error('Regra personalizada para / em _redirects; revise-a antes de executar.')
    if not root_rules: put('_redirects','/ /Pasta-html/index.html 302\n'+redirect_old)
    # The static asset directory is the repo root: exclude development/config/secret files.
    ignore_old = read(root/'.assetsignore') if (root/'.assetsignore').exists() else ''
    patterns = ['.git/','.github/','.wrangler/','node_modules/','__pycache__/','.venv/','venv/','.idea/','.vscode/','dist/','.env*','.dev.vars*','**/.env*','**/.dev.vars*','*.py','*.bak','*.pem','*.key','*.pfx','*.p12','wrangler.jsonc','wrangler.json','wrangler.toml','README.md','.gitignore','.assetsignore','package.json','package-lock.json','pnpm-lock.yaml','yarn.lock']
    absent = [p for p in patterns if p not in ignore_old.splitlines()]
    if absent: put('.assetsignore',ignore_old+ ('\n' if ignore_old and not ignore_old.endswith('\n') else '')+'\n'.join(absent)+'\n')
    # Repair known missing media safely (remove unused soundtrack only, retain victory/failure effects).
    screens = ['parabens/parabens.html']+[f'Questoes/{s}/erro.html' for s in SUBJECTS]
    for p in screens:
        if not (root/p).is_file(): issues.add((p,'pagina ausente')); continue
        s=get(p)
        s=re.sub(r'\s*<audio\b(?=[^>]*\bid=["\']musica["\'])(?=[^>]*\bsrc=["\'](?:musica\.mp3|)["\'])[^>]*>\s*</audio>', '', s, flags=re.I)
        if not re.search(r'\bid=["\']musica["\']',s):
            s=re.sub(r'\s*const musica\s*=\s*document\.getElementById\(["\']musica["\']\);','',s)
            s=re.sub(r'\s*efeito\.onended\s*=\s*\(\)\s*=>\s*\{\s*musica\.play\(\);?\s*\};?','',s)
        s=s.replace('await efeito.play();','await efeito.play().catch(() => {});')
        put(p,s)
    # Keep the chosen subject on replay, using a fixed allowlist of paths.
    for subject, filename in SUBJECTS.items():
        p=f'Questoes/{subject}/{filename}'
        s=get(p)
        s=re.sub(r'(["\'])\.\./\.\./parabens/parabens\.html\1',lambda m: m.group(1)+'../../parabens/parabens.html?materia='+quote(subject)+m.group(1),s)
        # Only fix the clearly incorrect keyboard alternative; other pedagogical edits are out of scope.
        if subject=='Informatica': s=s.replace('"delete"','"Backspace"')
        put(p,s)
    p='parabens/parabens.html'
    if (root/p).is_file():
        s=get(p)
        mapping=json.dumps({k:'../Questoes/'+k+'/'+v for k,v in SUBJECTS.items()},ensure_ascii=False)
        s=re.sub(r'location\.replace\(["\'](?:\.\./)+Questoes/Portugu(?:ê|%C3%AA)s/portugues\.html["\']\);',lambda m:'const materia = new URLSearchParams(location.search).get("materia");\n            const rotas = '+mapping+';\n            location.replace(Object.prototype.hasOwnProperty.call(rotas, materia) ? rotas[materia] : "../Pasta-html/escolhas-maycol/escolha_materias.html");',s)
        put(p,s)
    # Gather actual filesystem spelling (case-sensitive, even on Windows).
    files=set(edits)
    for d, dirs, names in os.walk(root):
        dirs[:]=[x for x in dirs if x not in SKIP and not x.startswith('.')]
        for n in names: files.add((Path(d)/n).relative_to(root).as_posix())
    lookup={}
    for p in files: lookup.setdefault(p.casefold(),[]).append(p)
    def resolve(owner, raw):
        v=raw.strip()
        if not v or v.startswith(('#','//','?')) or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',v): return raw
        # Ignore javascript expressions and data placeholders; this pass handles static paths only.
        if any(c in v for c in ('${','{{','<','>','\\')): return raw
        u=urlsplit(v); path=unquote(u.path)
        if not path: return raw
        parts=[] if path.startswith('/') else owner.split('/')[:-1]
        for segment in path.split('/'):
            if segment in ('','.'): continue
            if segment=='..':
                if parts: parts.pop()
            else: parts.append(segment)
        candidate='/'.join(parts)
        if not candidate: candidate='index.html'
        if candidate in files: target=candidate
        elif len(lookup.get(candidate.casefold(),[]))==1: target=lookup[candidate.casefold()][0]
        elif candidate+'/index.html' in files: target=candidate+'/index.html'
        elif candidate+'.html' in files: target=candidate+'.html'
        else:
            # If a bad path clearly points to a known root-level project directory, recover it.
            targets=[]
            for i,part in enumerate(parts):
                if part.casefold() in ('questoes','pasta-html','parabens','creditos','songs','htmlgameplay-vitu'):
                    targets += lookup.get('/'.join(parts[i:]).casefold(),[])
            targets=list(set(targets))
            if len(targets)==1: target=targets[0]
            else:
                issues.add((owner,raw)); return raw
        rel=posixpath.relpath(target,posixpath.dirname(owner) or '.')
        # Percent-encode non-ASCII and spaces, preserving safe relative path characters.
        rel=quote(rel,safe='/.-_~!$&()+,;=@')
        new=rel+('?' + u.query if '?' in v.split('#',1)[0] else '')+('#'+u.fragment if '#' in v else '')
        if new!=raw: changes.append((owner,raw,new))
        return new
    # Scan HTML/CSS/JS, including legacy files, not just the six question pages.
    for p in sorted(files):
        if Path(p).suffix.lower() not in ('.html','.css','.js') or not ((root/p).is_file() or p in edits): continue
        try: s=get(p)
        except UnicodeError: issues.add((p,'arquivo nao UTF-8')); continue
        def replace(m): return m.group('prefix')+m.group('q')+resolve(p,m.group('value'))+m.group('q')
        # Handle literal path references, preserving the surrounding source.
        s=REF.sub(replace,s)
        s=CSS_RAW.sub(lambda m:m.group('prefix')+resolve(p,m.group('value'))+m.group('end'),s)
        put(p,s)
    # Avoid false success: unresolved references are printed, not guessed or silently deleted.
    print('Repositorio:',root)
    for p,a,b in changes: print(f'ROTA {p}: {a} -> {b}')
    for p in sorted(edits): print(('ALTERAR' if (root/p).exists() else 'CRIAR')+': '+p)
    if issues:
        print('\nREFERENCIAS PARA REVISAO MANUAL (podem estar em arquivos legados nao utilizados):')
        for p,v in sorted(issues): print(f'  {p}: {v}')
    if not args.dry_run:
        for p,s in edits.items(): (root/p).write_text(s,encoding='utf-8')
    print(f'\n{len(edits)} arquivo(s); {len(changes)} referencia(s) normalizada(s); {len(issues)} aviso(s).')
    print('Simulacao: nenhum arquivo gravado.' if args.dry_run else 'Alteracoes locais concluidas. Revise git diff e git status.')
    print('Cloudflare Workers: Build command vazio; Deploy command: npx wrangler deploy; Root directory: raiz do repositorio.')
    return 0

if __name__=='__main__':
    sys.exit(main())
