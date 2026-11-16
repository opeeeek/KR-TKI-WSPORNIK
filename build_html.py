"""Buduje interfejs programu z plików web/ (układ jak w programie BelkaŻB):
   app/app.html              – pełny dokument (program KrotkiWspornikST.exe i plik do otwarcia w przeglądarce),
   webapp/wspornik.html      – strona do publikacji jako artefakt claude.ai (bez doctype/html/head/body).

Przed budową odświeżane są dane normowe (tools/export_normdata.py – jedno źródło prawdy: kwst/normative_parameters.py)
i kolory rysunków dla motywu ciemnego (gen_svgtheme.py)."""
import pathlib
import subprocess
import sys

root = pathlib.Path(__file__).parent
w = root / 'web'
subprocess.run([sys.executable, str(root / 'tools' / 'export_normdata.py')], check=True, stdout=subprocess.DEVNULL)
subprocess.run([sys.executable, str(root / 'gen_svgtheme.py')], check=True, stdout=subprocess.DEVNULL)
tpl = (w / 'index.html').read_text(encoding='utf-8')
css = '\n'.join((w / f).read_text(encoding='utf-8') for f in ('style.css', 'style_ws.css', 'svgtheme.css'))
parts = {}
for tag, fns in [('/*@@NORMDATA@@*/', ['normdata.js']), ('/*@@ENGINE@@*/', ['engine_core.js', 'engine_stm.js', 'engine_analysis.js']),
                 ('/*@@DRAW@@*/', ['draw.js']), ('/*@@NORMS@@*/', ['norms.js']), ('/*@@REPORT@@*/', ['report.js']),
                 ('/*@@VIEWS@@*/', ['views.js']), ('/*@@UI@@*/', ['ui.js'])]:
    src = '\n'.join((w / fn).read_text(encoding='utf-8') for fn in fns)
    assert '</script' not in src.lower(), fns
    parts[tag] = src
head, rest = tpl.split('<!--@@BODY-->')
body, tail = rest.split('<!--@@END-->')
head = head.replace('<!--@@HEAD-->', '').lstrip()


def fill(s):
    for k, v in parts.items():
        s = s.replace(k, v)
    return s.replace('/*@@CSS@@*/', css)


full = fill(head + body.replace('<!--@@FLAGS-->', '') + tail)
(root / 'app').mkdir(exist_ok=True)
(root / 'app' / 'app.html').write_text(full, encoding='utf-8')
web = ('<title>Krótki wspornik ST</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
       '<style id="appcss">/*@@CSS@@*/</style>\n'
       + body.replace('<!--@@FLAGS-->', '<script>window.__ARTIFACT = true;</script>'))
web = fill(web)
(root / 'webapp').mkdir(exist_ok=True)
(root / 'webapp' / 'wspornik.html').write_text(web, encoding='utf-8')
print('app/app.html', len(full.encode()), 'B;  webapp/wspornik.html', len(web.encode()), 'B')
