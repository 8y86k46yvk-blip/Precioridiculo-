#!/usr/bin/env python3
"""Precio Ridículo · genera las páginas que Google puede leer, a partir de las ofertas de index.html.

Uso (desde la raíz del repo): python3 _herramientas/paginas.py
Lee CONFIG, OFERTAS e ICONOS de index.html (con node) y escribe:
  ofertas/index.html                        (todas las secciones)
  ofertas/<categoría>/index.html            (una por categoría de CONFIG: moda, gadgets, casa)
  ofertas/menos-de-3-euros/, ofertas/menos-de-5-euros/, ofertas/menos-de-10-euros/
  ofertas/<tienda>/index.html               (aliexpress y hacoo)
  11-11/index.html                          (especial 11.11 de AliExpress hasta el 18 nov 2026; después, aviso de fin)
  cupones/index.html                        (cupones de cupones.json, si hay alguno en vigor)
  assets/web/estilo.css                     (los estilos de index.html, para estas páginas)
  sitemap.xml y robots.txt
No toca index.html. Lo ejecuta la tarea diaria «Ofertas diarias Precio Ridículo» después de cambiar OFERTAS.
La carpeta _herramientas no se publica (GitHub Pages ignora las carpetas que empiezan por «_»).
"""
import datetime
import html
import json
import re
import subprocess
import unicodedata
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parent.parent
DOMINIO = "https://elprecioridiculo.com"
TRACKER = ('<script>function loadScript(a){var b=document.getElementsByTagName("head")[0],c=document.createElement("script");'
           'c.type="text/javascript",c.src="https://tracker.metricool.com/resources/be.js",c.onreadystatechange=a,c.onload=a,'
           'b.appendChild(c)}loadScript(function(){beTracker.t({hash:"264aff4a553b2930b48b16aff83f65f"})});</script>')
POSES = ["ridi-5-pulgar-guino", "ridi-2-sorpresa", "ridi-4-senala", "ridi-7-sospecha", "ridi-1-habla", "ridi-3-risa"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre",
         "diciembre"]
TIENDAS = ["AliExpress", "Hacoo"]
FIN_1111 = datetime.date(2026, 11, 18)   # el 11.11 de AliExpress dura hasta el 18 de noviembre a las 23:59
MENU_EXTRA = []                          # enlaces de temporada en la cabecera (los pone main)

# Textos propios de cada sección (para Google y para quien llega)
TEXTOS = {
    "Moda": ("Moda barata: ropa, bolsos y bisutería a precio ridículo",
             "Camisetas, bolsos, pendientes, collares y complementos que parecen caros y no lo son."),
    "Gadgets": ("Gadgets baratos: inventos y cacharros a precio ridículo",
                "Lámparas, relojes, despertadores curiosos y accesorios que dan el pego por muy poco dinero."),
    "Casa": ("Cosas baratas para casa",
             "Decoración, cocina, cojines, orden y detalles para casa por muy poco dinero."),
}


def slug(txt):
    t = unicodedata.normalize("NFD", txt.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def leer_datos(index):
    def bloque(patron):
        m = re.search(patron, index)
        if not m:
            raise SystemExit(f"No encuentro {patron!r} en index.html")
        return m.group(0)
    js = "\n".join([bloque(r"const CONFIG = \{[\s\S]*?\n\};"), bloque(r"const OFERTAS = \[[\s\S]*?\n\];"),
                    bloque(r"const ICONOS = \{[\s\S]*?\n\};"),
                    "console.log(JSON.stringify({CONFIG, OFERTAS, ICONOS}));"])
    salida = subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout
    return json.loads(salida)


def euros(x):
    if x is None:
        return ""
    s = f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if re.fullmatch(r"\d\.\d{3},\d{2}", s):
        s = s.replace(".", "")
    return s + " €"


def dto(o):
    return round((1 - o["precio"] / o["antes"]) * 100) if o.get("precio") and o.get("antes") and o["antes"] > o["precio"] else 0


def fecha_larga(d):
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def fecha_oferta(iso):
    try:
        d = datetime.date.fromisoformat(str(iso)[:10])
        return f"{d.day} {MESES[d.month - 1][:3]} {d.year}"
    except ValueError:
        return ""


def url_segura(u):
    u = str(u or "").strip()
    return u if re.match(r"^https?://", u, re.I) else ""


E = lambda s: html.escape(str(s if s is not None else ""), quote=True)  # noqa: E731
FLECHA = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" '
          'stroke-linejoin="round" aria-hidden="true"><path d="M7 17 17 7"/><path d="M8 7h9v9"/></svg>')


def icono(cat, iconos, categorias):
    return ('<svg class="icono-cat" viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="6" '
            f'stroke-linejoin="round" stroke-linecap="round" aria-hidden="true">{iconos.get(cat) or iconos.get(categorias[0], "")}</svg>')


def tarjeta(o, i, iconos, categorias):
    """La misma tarjeta que dibuja index.html, pero en HTML fijo para que Google la lea."""
    a = "≈" if o.get("aprox") else ""
    d = dto(o)
    tienda = str(o.get("tienda") or "").strip()
    src = url_segura(o.get("imagen"))
    if src:
        fondo = f'<img class="producto" src="{E(src)}" alt="{E(o.get("producto"))}" loading="lazy" onerror="this.remove()">'
    else:
        fondo = (f'<span class="etiqueta-precio">{a}{euros(o.get("precio"))}</span>{icono(o.get("categoria"), iconos, categorias)}'
                 f'<img class="mascota" src="/assets/web/{POSES[i % len(POSES)]}.webp" alt="" loading="lazy">')
    fondo += (f'<span class="pegatina-dto">-{d}%</span>' if d else "") + \
        f'<span class="chapa"><span class="numero">Nº {E(o["numero"])}</span></span>'
    precios = f'<div class="precios"><span class="precio">{a}{euros(o.get("precio"))}</span>'
    if o.get("antes"):
        precios += f'<span class="antes"><span class="oculto">Antes </span>{a}{euros(o["antes"])}</span>'
    precios += "</div>"
    if d and o["antes"] - o["precio"] >= 1:
        precios += f'<p class="ahorro">Te ahorras {a}{euros(o["antes"] - o["precio"])}</p>'
    fo = fecha_oferta(o.get("fecha"))
    if o.get("aprox"):
        nota = (f'<p class="nota">Precio aproximado{" del " + fo if fo else ""}, pasado de dólares. El precio final lo ves en '
                f'{E(tienda or "la tienda")}.</p>')
    else:
        nota = f'<p class="nota">Precio a {fo}. Puede cambiar.</p>' if fo else ""
    enlace = url_segura(o.get("enlace"))
    boton = (f'<a class="boton" href="{E(enlace)}" target="_blank" rel="sponsored nofollow noopener">'
             f'{E("Ver en " + tienda if tienda else "Ver oferta")}{FLECHA}</a>' if enlace
             else '<span class="boton pendiente">Enlace pendiente</span>')
    ficha = f'/#oferta-{E(o["numero"])}'
    etiqueta = E(o.get("categoria")) + (f'<span class="tienda">{E(tienda)}</span>' if tienda else "")
    return (f'<article class="tarjeta"><a class="cartel" href="{ficha}" tabindex="-1" aria-hidden="true">{fondo}</a>'
            f'<div class="cuerpo"><span class="categoria">{etiqueta}</span><h3><a href="{ficha}">{E(o.get("producto"))}</a></h3>'
            f'{precios}{nota}{boton}</div></article>')


def rejilla(lista, iconos, categorias, vacio):
    if not lista:
        return (f'<div class="rejilla lista-cat"><div class="vacio"><img src="/assets/web/ridi-7-sospecha.webp" alt="" '
                f'width="216" height="400"><strong>{E(vacio)}</strong><span>Ridi busca hallazgos nuevos cada mañana.</span>'
                '<a class="boton" href="/">Ver todos los hallazgos de hoy</a></div></div>')
    return '<div class="rejilla lista-cat">' + "".join(tarjeta(o, i, iconos, categorias) for i, o in enumerate(lista)) + "</div>"


AVISO_TG = ('<a class="aviso-tg" href="https://t.me/precioridiculo" target="_blank" rel="noopener">'
            '<img src="/assets/web/ridi-4-senala.webp" alt="" loading="lazy" width="216" height="400">'
            '<span class="tg-texto"><strong>¿Quieres los hallazgos al momento?</strong>Únete al canal de Telegram de Precio '
            'Ridículo: cada chollo nuevo te llega al móvil.</span><span class="tg-boton"><svg viewBox="0 0 24 24" '
            'fill="currentColor" aria-hidden="true"><path d="M21.9 4.3 18.7 19.4c-.2 1.1-.9 1.3-1.8.8l-4.9-3.6-2.4 2.3c-.3.3-.5.5-1 '
            '.5l.4-5 9.1-8.2c.4-.4-.1-.6-.6-.2L6.2 13 1.4 11.5c-1-.3-1-1 .2-1.5L20.5 2.8c.9-.3 1.6.2 1.4 1.5z"/></svg>Unirme</span></a>')

LOGO = ('<svg width="36" height="24" viewBox="0 0 120 80" aria-hidden="true" style="transform:rotate(-12deg)"><path d="M30 4 '
        'H110 A6 6 0 0 1 116 10 V70 A6 6 0 0 1 110 76 H30 L4 40 Z" fill="#111111"></path><circle cx="24" cy="40" r="7" '
        'fill="#FFD60A"></circle></svg><span>PRECIO</span><span class="banda">RIDÍCULO</span>')

TEXTO_RIDI = ('<section class="mas-info"><h2>Cómo elige Ridi los hallazgos</h2><p>Cada mañana se revisan miles de productos '
              'rebajados de AliExpress (y de Hacoo cuando hay). Solo entran cosas útiles, curiosas o bonitas, sin marcas ni '
              'imitaciones. Los precios de AliExpress vienen en dólares y aquí salen pasados a euros (≈): el que vale es el '
              'que veas en la tienda al pagar. Muchos envíos salen de China: pide con margen.</p><p>¿Vienes de un vídeo? '
              'Busca el número en <a href="/">elprecioridiculo.com</a>.</p></section>')


def leer_cupones(hoy):
    """Cupones en vigor de cupones.json (lo escribe la tarea diaria de ofertas). Sin archivo: lista vacía."""
    try:
        datos = json.loads((RAIZ / "cupones.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    lista = []
    for c in datos.get("cupones", []):
        if not url_segura(c.get("enlace")) or not str(c.get("titulo") or "").strip():
            continue
        try:
            if c.get("hasta") and datetime.date.fromisoformat(str(c["hasta"])[:10]) < hoy:
                continue
            if c.get("desde") and datetime.date.fromisoformat(str(c["desde"])[:10]) > hoy:
                continue
        except ValueError:
            continue
        lista.append(c)
    lista.sort(key=lambda c: (0 if str(c.get("codigo") or "").strip() else 1,
                              c.get("minimo") if isinstance(c.get("minimo"), (int, float)) else 0))
    return lista


def tarjeta_cupon(c):
    codigo = str(c.get("codigo") or "").strip()
    detalle = []
    if c.get("minimo"):
        m = c["minimo"]
        detalle.append(f"Compra mínima: {euros(m) if isinstance(m, (int, float)) else E(m)}")
    if c.get("hasta"):
        try:
            detalle.append(f"Hasta el {fecha_larga(datetime.date.fromisoformat(str(c['hasta'])[:10]))}")
        except ValueError:
            pass
    if c.get("condiciones"):
        detalle.append(E(c["condiciones"]))
    tienda = str(c.get("tienda") or "AliExpress").strip()
    if codigo:
        bloque = (f'<div class="codigo"><code>{E(codigo)}</code><button class="copiar" type="button" '
                  f'data-codigo="{E(codigo)}">Copiar</button></div>')
    else:
        bloque = '<p class="sin-codigo">Sin código: entra desde el botón para verlo.</p>'
    cantidad = f'<span class="cantidad">{E(c["descuento"])}</span>' if c.get("descuento") else ""
    return (f'<article class="cupon">{cantidad}<h3>{E(c["titulo"])}</h3>'
            + (f'<p class="detalle">{" · ".join(detalle)}</p>' if detalle else "") + bloque
            + f'<a class="boton" href="{E(c["enlace"])}" target="_blank" rel="sponsored nofollow noopener">'
              f'Ir a {E(tienda)}{FLECHA}</a></article>')


COPIAR = ("<script>document.querySelectorAll('.copiar').forEach(function(b){b.addEventListener('click',function(){"
          "var c=b.getAttribute('data-codigo');function ok(){b.textContent='¡Copiado!';setTimeout(function(){"
          "b.textContent='Copiar'},1800)}if(navigator.clipboard){navigator.clipboard.writeText(c).then(ok,function(){})}"
          "else{var t=document.createElement('textarea');t.value=c;document.body.appendChild(t);t.select();"
          "try{document.execCommand('copy');ok()}catch(e){}t.remove()}})})</script>")


def pie(index):
    m = re.search(r'<footer class="pie">[\s\S]*?</footer>', index)
    t = m.group(0) if m else ""
    return t.replace('href="aviso-legal.html', 'href="/aviso-legal.html')


def pagina(index, ruta, titulo, descripcion, cabeza, cuerpo, actual=None, enlaces=None, noindex=False):
    url = f"{DOMINIO}/{ruta}"
    menu_extra = "".join(f'<a class="temporada" href="/{r}">{E(t)}</a>' for r, t in MENU_EXTRA)
    robots = '\n<meta name="robots" content="noindex">' if noindex else ""
    nav = ""
    if enlaces:
        marca = ' aria-current="page"'
        nav = '<nav class="enlaces-cat" aria-label="Secciones">' + "".join(
            f'<a href="/{r}"{marca if r == actual else ""}>{E(t)}</a>' for r, t in enlaces) + "</nav>"
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(titulo)}</title>
<meta name="description" content="{E(descripcion)}">
<link rel="canonical" href="{url}">{robots}
<meta name="theme-color" content="#FFD60A">
<meta property="og:type" content="website">
<meta property="og:title" content="{E(titulo)}">
<meta property="og:description" content="{E(descripcion)}">
<meta property="og:image" content="{DOMINIO}/assets/web/compartir.jpg">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/assets/web/icono.png">
<link rel="apple-touch-icon" href="/assets/web/icono.png">
<link rel="stylesheet" href="/assets/web/estilo.css">
<!-- Contador de visitas de Metricool (sin cookies) -->
{TRACKER}
</head>
<body>
<header class="cabecera">
  <div class="wrap">
    <a class="logo" href="/" aria-label="Precio Ridículo, ir al inicio">{LOGO}</a>
    <nav class="menu menu-texto" aria-label="Menú"><a href="/">Inicio</a>{menu_extra}<a href="/ofertas/">Secciones</a></nav>
  </div>
</header>
<main>
  <div class="cabeza-cat"><div class="wrap">{cabeza}</div></div>
  <div class="wrap">{nav}{cuerpo}{AVISO_TG}</div>
</main>
{pie(index)}
</body>
</html>
"""


CSS_EXTRA = """
/* ---------- Páginas de secciones (generadas por _herramientas/paginas.py) ---------- */
.menu-texto a{white-space:nowrap;padding:0 10px}
@media (max-width:420px){.menu-texto a{font-size:12.5px;padding:0 7px}.cabecera .logo{font-size:19px}.cabecera .logo svg{width:30px}}
html,body{overflow-x:hidden}
.migas{font-size:13.5px;margin:0 0 10px;font-weight:600}
.migas a{color:var(--tinta);font-weight:800}
.cabeza-cat{background:var(--amarillo);color:var(--tinta);padding:22px 0 26px;border-bottom:var(--borde)}
.cabeza-cat h1{margin:0 0 8px;font-weight:900;font-size:clamp(30px,7vw,52px);line-height:1.02;letter-spacing:-0.045em;text-wrap:balance;max-width:22ch}
.cabeza-cat p{margin:0;max-width:60ch;font-weight:500}
.cabeza-cat .actualizado{margin-top:10px;font-size:13px;font-weight:800}
.enlaces-cat{display:flex;flex-wrap:nowrap;gap:8px;overflow-x:auto;scrollbar-width:none;padding:16px 2px 8px}
.enlaces-cat::-webkit-scrollbar{display:none}
.enlaces-cat a{flex:0 0 auto;display:inline-flex;align-items:center;min-height:42px;padding:0 15px;border-radius:999px;border:2px solid var(--tinta);background:var(--blanco);color:var(--tinta);font-weight:800;font-size:14.5px;text-decoration:none}
.enlaces-cat a[aria-current="page"]{background:var(--tinta);color:var(--amarillo)}
.lista-cat{padding:16px 0 10px}
.mas-info{background:var(--blanco);border:var(--borde);border-radius:18px;padding:18px 20px;margin:18px 0 10px;font-size:15px;box-shadow:var(--sombra)}
.mas-info h2{margin:0 0 6px;font-size:18px;font-weight:900;letter-spacing:-0.02em}
.mas-info p{margin:0 0 8px}
.indice-cat{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;padding:18px 0 24px}
@media (min-width:760px){.indice-cat{grid-template-columns:repeat(4,minmax(0,1fr))}}
.indice-cat a{display:flex;flex-direction:column;gap:2px;padding:16px;border-radius:18px;background:var(--blanco);border:var(--borde);box-shadow:var(--sombra);text-decoration:none;font-weight:900;font-size:17px;color:var(--tinta)}
.indice-cat a small{font-weight:600;font-size:13px;color:var(--gris)}
.aviso-tg{margin-bottom:34px}
/* ---------- Especial 11.11 y cupones ---------- */
.cabeza-1111{background:var(--tinta);color:var(--blanco)}
.cabeza-1111 .migas,.cabeza-1111 .migas a{color:var(--blanco)}
.cabeza-1111 h1 mark{background:var(--rojo);color:var(--blanco);padding:0 .12em;border-radius:6px}
.cabeza-1111 .actualizado{color:var(--amarillo)}
@media (max-width:520px){.menu-texto a.temporada{display:none}}
.pasos{margin:6px 0 0;padding-left:20px}.pasos li{margin:0 0 4px}
.cupones{display:grid;grid-template-columns:1fr;gap:14px;padding:16px 0 10px}
@media (min-width:760px){.cupones{grid-template-columns:repeat(2,minmax(0,1fr))}}
.cupon{display:flex;flex-direction:column;gap:8px;background:var(--blanco);border:var(--borde);border-radius:18px;padding:16px 18px;box-shadow:var(--sombra)}
.cupon .cantidad{font-weight:900;font-size:30px;line-height:1;letter-spacing:-0.03em;color:var(--rojo)}
.cupon h3{margin:0;font-size:17px;font-weight:900;letter-spacing:-0.01em}
.cupon .detalle{margin:0;font-size:14px;color:var(--gris);font-weight:600}
.cupon .codigo{display:flex;gap:8px;align-items:stretch}
.cupon .codigo code{flex:1;display:flex;align-items:center;justify-content:center;min-height:46px;border:2px dashed var(--tinta);border-radius:12px;background:var(--crema);font:900 19px/1 var(--texto);letter-spacing:.06em}
.cupon .copiar{flex:0 0 auto;min-height:46px;padding:0 14px;border-radius:12px;border:2px solid var(--tinta);background:var(--amarillo);font:800 14px/1 var(--texto);cursor:pointer}
.cupon .sin-codigo{margin:0;font-size:14px;font-weight:700}
"""


def main():
    index = (RAIZ / "index.html").read_text(encoding="utf-8")
    datos = leer_datos(index)
    categorias, iconos = datos["CONFIG"]["categorias"], datos["ICONOS"]
    ofertas = [o for o in datos["OFERTAS"] if not o.get("ejemplo") and o.get("producto")]
    ofertas.sort(key=lambda o: -(o.get("numero") or 0))
    hoy = datetime.datetime.now(ZoneInfo("Atlantic/Canary")).date()
    actualizado = f'<p class="actualizado">Actualizado el {fecha_larga(hoy)} · {{n}}</p>'

    css = re.search(r"<style>([\s\S]*?)</style>", index).group(1).replace("url(assets/", "url(/assets/")
    (RAIZ / "assets/web/estilo.css").write_text(css.strip() + "\n" + CSS_EXTRA, encoding="utf-8")

    def cuantos(n):
        return "1 hallazgo" if n == 1 else f"{n} hallazgos"

    topes = (3, 5, 10)
    tiendas = [t for t in TIENDAS if any(str(o.get("tienda", "")).lower() == t.lower() for o in ofertas)]
    ali = [o for o in ofertas if str(o.get("tienda", "")).lower() == "aliexpress"]
    campana = hoy <= FIN_1111 and bool(ali)
    cupones = leer_cupones(hoy)
    temporada = ([("11-11/", "11.11")] if campana else []) + ([("cupones/", "Cupones")] if cupones else [])
    MENU_EXTRA[:] = temporada
    enlaces = (temporada + [(f"ofertas/{slug(c)}/", c) for c in categorias]
               + [(f"ofertas/menos-de-{t}-euros/", f"Menos de {t} €") for t in topes]
               + [(f"ofertas/{slug(t)}/", t) for t in tiendas])
    paginas = []

    def escribir(ruta, contenido):
        destino = RAIZ / ruta / "index.html"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")
        paginas.append(ruta)

    def migas(nombre):
        return f'<p class="migas"><a href="/">Inicio</a> › <a href="/ofertas/">Secciones</a> › {E(nombre)}</p>'

    for c in categorias:
        lista = [o for o in ofertas if o.get("categoria") == c]
        h1, intro = TEXTOS.get(c, (f"{c} a precio ridículo", "Hallazgos baratos elegidos cada día."))
        ruta = f"ofertas/{slug(c)}/"
        cabeza = migas(c) + f"<h1>{E(h1)}</h1><p>{E(intro)} Ridi los elige cada día.</p>" + actualizado.format(n=cuantos(len(lista)))
        escribir(ruta, pagina(index, ruta, f"{h1} · Precio Ridículo", f"{intro} Hallazgos nuevos cada día en Precio Ridículo.",
                              cabeza, rejilla(lista, iconos, categorias, f"Hoy no hay hallazgos de {c.lower()}.") + TEXTO_RIDI,
                              ruta, enlaces))

    for tope in topes:
        lista = sorted([o for o in ofertas if o.get("precio") is not None and o["precio"] < tope], key=lambda o: (o["precio"], -dto(o)))
        h1 = f"Chollos por menos de {tope} €"
        intro = f"Cosas que cuestan menos de {tope} € y parecen mucho más caras: moda, gadgets y casa."
        ruta = f"ofertas/menos-de-{tope}-euros/"
        cabeza = (migas(f"Menos de {tope} €") + f"<h1>{E(h1)}</h1><p>{E(intro)} Ordenados del más barato al más caro.</p>"
                  + actualizado.format(n=cuantos(len(lista))))
        escribir(ruta, pagina(index, ruta, f"{h1} · Precio Ridículo", intro, cabeza,
                              rejilla(lista, iconos, categorias, f"Hoy no hay hallazgos de menos de {tope} €.") + TEXTO_RIDI,
                              ruta, enlaces))

    for t in tiendas:
        lista = [o for o in ofertas if str(o.get("tienda", "")).lower() == t.lower()]
        h1 = f"Chollos de {t} a precio ridículo"
        intro = (f"Lo mejor y más barato de {t}, elegido cada día." +
                 (" Los precios vienen en dólares y aquí salen pasados a euros (≈)." if any(o.get("aprox") for o in lista) else ""))
        ruta = f"ofertas/{slug(t)}/"
        cabeza = migas(t) + f"<h1>{E(h1)}</h1><p>{E(intro)}</p>" + actualizado.format(n=cuantos(len(lista)))
        escribir(ruta, pagina(index, ruta, f"{h1} · Precio Ridículo", intro, cabeza,
                              rejilla(lista, iconos, categorias, f"Hoy no hay hallazgos de {t}.") + TEXTO_RIDI, ruta, enlaces))

    # Especial 11.11 de AliExpress (hasta el 18 de noviembre)
    if campana:
        lista = sorted(ali, key=lambda o: (-dto(o), o.get("precio") or 0))
        cupon_txt = (' Y antes de pagar, mira <a href="/cupones/">los cupones del 11.11</a>.' if cupones else "")
        cabeza = ('<p class="migas"><a href="/">Inicio</a> › Especial 11.11</p>'
                  '<h1>El 11.11 de AliExpress a <mark>precio ridículo</mark></h1>'
                  '<p>El 11.11 de AliExpress dura hasta el 18 de noviembre a las 23:59. Ridi ha juntado aquí los hallazgos '
                  f'de hoy con más descuento, del más rebajado al que menos.{cupon_txt}</p>'
                  + actualizado.format(n=cuantos(len(lista))))
        consejos = ('<section class="mas-info"><h2>Cómo sacarle partido al 11.11</h2><ol class="pasos">'
                    '<li>Mira el precio final en AliExpress: aquí sale pasado de dólares a euros (≈).</li>'
                    '<li>Si hay un cupón con compra mínima, junta varias cosas baratas para llegar.</li>'
                    '<li>Pide con margen: muchos envíos salen de China y tardan.</li></ol></section>')
        escribir("11-11/", pagina(index, "11-11/", "11.11 de AliExpress: lo más rebajado de hoy · Precio Ridículo",
                                  "Lo más rebajado del 11.11 de AliExpress, elegido por Ridi cada día hasta el 18 de noviembre.",
                                  cabeza, rejilla(lista, iconos, categorias, "Hoy no hay hallazgos de AliExpress.") + consejos,
                                  "11-11/", enlaces).replace('<div class="cabeza-cat">', '<div class="cabeza-cat cabeza-1111">', 1))
    elif (RAIZ / "11-11/index.html").exists() or hoy > FIN_1111:
        destino = RAIZ / "11-11/index.html"
        destino.parent.mkdir(parents=True, exist_ok=True)
        cabeza = ('<p class="migas"><a href="/">Inicio</a> › Especial 11.11</p><h1>El 11.11 ya ha terminado</h1>'
                  '<p>La campaña del 11.11 de AliExpress acabó el 18 de noviembre. Ridi sigue buscando hallazgos cada mañana.</p>')
        destino.write_text(pagina(index, "11-11/", "El 11.11 ha terminado · Precio Ridículo",
                                  "El 11.11 de AliExpress ha terminado. Mira los hallazgos de hoy en Precio Ridículo.",
                                  cabeza, rejilla([], iconos, categorias, "El 11.11 ya ha terminado."), noindex=True),
                           encoding="utf-8")

    # Cupones (de cupones.json)
    if cupones:
        cabeza = ('<p class="migas"><a href="/">Inicio</a> › Cupones</p><h1>Cupones de descuento a precio ridículo</h1>'
                  '<p>Códigos para AliExpress que se ponen al pagar. Copia el código, entra desde el botón y escríbelo en '
                  'la casilla del cupón. Mira siempre la compra mínima y la fecha.</p>'
                  + f'<p class="actualizado">Actualizado el {fecha_larga(hoy)} · {"1 cupón" if len(cupones) == 1 else str(len(cupones)) + " cupones"}</p>')
        aviso = ('<section class="mas-info"><h2>Antes de usar un cupón</h2><p>Los cupones los pone la tienda y pueden '
                 'agotarse antes de su fecha. Si uno no te funciona, prueba otro de la lista. Son enlaces de afiliado: si '
                 'compras, ganamos una pequeña comisión y a ti te cuesta lo mismo.</p></section>')
        escribir("cupones/", pagina(index, "cupones/", "Cupones de AliExpress de hoy · Precio Ridículo",
                                    "Cupones y códigos de descuento de AliExpress en vigor, revisados cada día por Precio Ridículo.",
                                    cabeza, '<div class="cupones">' + "".join(tarjeta_cupon(c) for c in cupones) + "</div>"
                                    + aviso + COPIAR, "cupones/", enlaces))
    elif (RAIZ / "cupones/index.html").exists():
        (RAIZ / "cupones/index.html").unlink()

    # Índice de secciones
    numeros = ([sum(1 for o in ali) if r == "11-11/" else len(cupones) for r, _ in temporada]
               + [sum(o.get("categoria") == c for o in ofertas) for c in categorias]
               + [sum((o.get("precio") or 1e9) < t for o in ofertas) for t in topes]
               + [sum(str(o.get("tienda", "")).lower() == t.lower() for o in ofertas) for t in tiendas])
    def etiqueta_n(r, n):
        return (f"{n} cupón" if n == 1 else f"{n} cupones") if r == "cupones/" else cuantos(n)
    tarjetas = "".join(f'<a href="/{r}">{E(t)}<small>{etiqueta_n(r, n)}</small></a>' for (r, t), n in zip(enlaces, numeros))
    cabeza = ('<p class="migas"><a href="/">Inicio</a> › Secciones</p><h1>Todos los hallazgos de Precio Ridículo</h1>'
              '<p>Moda, gadgets y casa a precio de risa, por sección, por precio y por tienda.</p>'
              + actualizado.format(n=cuantos(len(ofertas))))
    escribir("ofertas/", pagina(index, "ofertas/", "Hallazgos baratos por sección · Precio Ridículo",
                                "Moda, gadgets y casa a precio ridículo: todas las secciones de Precio Ridículo.",
                                cabeza, f'<div class="indice-cat">{tarjetas}</div>' + TEXTO_RIDI))

    # Quita páginas de tiendas que ya no tienen ofertas (para no dejar páginas vacías en Google)
    for t in TIENDAS:
        if t not in tiendas and (RAIZ / f"ofertas/{slug(t)}/index.html").exists():
            (RAIZ / f"ofertas/{slug(t)}/index.html").unlink()

    urls = [""] + paginas + ["aviso-legal.html"]
    mapa = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    mapa += [f"  <url><loc>{DOMINIO}/{u}</loc><lastmod>{hoy.isoformat()}</lastmod></url>" for u in urls]
    mapa.append("</urlset>")
    (RAIZ / "sitemap.xml").write_text("\n".join(mapa) + "\n", encoding="utf-8")
    (RAIZ / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {DOMINIO}/sitemap.xml\n", encoding="utf-8")
    print(f"{len(paginas)} páginas, {len(ofertas)} ofertas · sitemap.xml y robots.txt")


if __name__ == "__main__":
    main()
