"""Create a self-contained, responsive SVG terminal / ASCII-art monogram.

No webfonts, external assets, JS or tokens: GitHub can embed these images in
a profile README. Motion is decorative and respects reduced-motion settings.
"""
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MONOGRAM = [
    ("##......##", ".########."),
    ("###....###", "###......#"),
    ("####..####", "##........"),
    ("##.####.##", "##........"),
    ("##..##..##", "##........"),
    ("##......##", "##........"),
    ("##......##", "##........"),
    ("##......##", "###......#"),
    ("##......##", ".########."),
]

PALETTES = {
    "dark": dict(bg="#0d1117", surface="#111924", stroke="#334155",
                 fg="#edf3ff", muted="#97a4ba", violet="#b99cff",
                 cyan="#67e8f9", deep="#172032"),
    "light": dict(bg="#f8faff", surface="#ffffff", stroke="#d5dce8",
                  fg="#1b2433", muted="#52647b", violet="#7140c8",
                  cyan="#00849a", deep="#e9eefa"),
}


def render(theme):
    p = PALETTES[theme]
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="394" '
        'viewBox="0 0 1200 394" role="img" aria-labelledby="title desc">',
        '<title id="title">Matteo Cesandri — developer terminal with animated MC ASCII art</title>',
        '<desc id="desc">A self-contained terminal panel with a monospaced command line, '
        'an ASCII-art MC monogram, and subtle animated scanning lights.</desc>',
        '<defs>',
        f'<linearGradient id="accent"><stop stop-color="{p["violet"]}"/>'
        f'<stop offset="1" stop-color="{p["cyan"]}"/></linearGradient>',
        f'<linearGradient id="scan" x1="0" y1="0" x2="0" y2="1">'
        f'<stop stop-color="{p["cyan"]}" stop-opacity="0"/>'
        f'<stop offset=".5" stop-color="{p["cyan"]}" stop-opacity=".15"/>'
        f'<stop offset="1" stop-color="{p["cyan"]}" stop-opacity="0"/></linearGradient>',
        '<clipPath id="terminal-clip"><rect x="1" y="1" width="1198" height="392" rx="18"/></clipPath>',
        '</defs>',
        '<style><![CDATA[',
        "text{font-family:'Courier New',Consolas,monospace}",
        '.cursor{animation:blink 1.3s step-end infinite}',
        '.scan{animation:scan 10s linear infinite}',
        '.ascii{animation:fade 5s ease-in-out infinite}',
        '@keyframes blink{50%{opacity:0}}',
        '@keyframes scan{from{transform:translateY(-40px)}to{transform:translateY(420px)}}',
        '@keyframes fade{0%,100%{opacity:1}50%{opacity:.84}}',
        '@media(prefers-reduced-motion:reduce){.cursor,.scan,.ascii{animation:none!important}}',
        ']]></style>',
        f'<rect x="1" y="1" width="1198" height="392" rx="18" fill="{p["bg"]}" stroke="{p["stroke"]}"/>',
        '<g clip-path="url(#terminal-clip)">',
        f'<rect x="0" y="0" width="1200" height="40" fill="{p["surface"]}"/>',
        f'<path d="M0 40H1200" stroke="{p["stroke"]}"/>',
        f'<path d="M1 1H1199" stroke="url(#accent)" stroke-width="2"/>',
        f'<circle cx="26" cy="20" r="4" fill="{p["violet"]}" opacity=".85"/>',
        f'<circle cx="44" cy="20" r="4" fill="{p["cyan"]}" opacity=".65"/>',
        f'<circle cx="62" cy="20" r="4" fill="{p["muted"]}" opacity=".4"/>',
        f'<text x="93" y="25" font-size="11" fill="{p["muted"]}" letter-spacing="1.8">'
        'MCHARTT  /  PERSONAL WORKSPACE</text>',
        f'<text x="1169" y="25" font-size="10" fill="{p["muted"]}" text-anchor="end">'
        'TERMINAL 01</text>',
        f'<path d="M654 66V332" stroke="{p["stroke"]}" stroke-dasharray="2 7"/>',
        # Left-side command-line vignette
        f'<text x="52" y="99" fill="{p["violet"]}" font-size="13" letter-spacing="1.4">'
        '01   /   IDENTITY</text>',
        f'<text x="52" y="142" fill="{p["cyan"]}" font-size="17">$</text>',
        f'<text x="79" y="142" fill="{p["muted"]}" font-size="17">whoami --verbose</text>',
        f'<text x="52" y="201" fill="{p["fg"]}" font-size="38" font-weight="700" '
        'letter-spacing="-1.7">SOFTWARE</text>',
        f'<text x="52" y="244" fill="{p["fg"]}" font-size="38" font-weight="700" '
        'letter-spacing="-1.7">ENGINEERING<tspan fill="url(#accent)">_</tspan></text>',
        f'<text x="53" y="280" fill="{p["muted"]}" font-size="14">'
        'Backend / web / data systems</text>',
        f'<text x="53" y="320" fill="{p["cyan"]}" font-size="13">'
        '&gt; build --thoughtfully<tspan class="cursor"> &#x2588;</tspan></text>',
        # Right-side ASCII mosaic guide and gutters
        f'<text x="706" y="76" fill="{p["violet"]}" font-size="12" letter-spacing="1.8">'
        '02   /   ASCII SIGNATURE</text>',
        f'<path d="M703 93H1148" stroke="{p["stroke"]}" opacity=".75"/>',
        f'<text x="1148" y="76" fill="{p["muted"]}" font-size="11" text-anchor="end">'
        'HEX / GLYPH</text>',
    ]

    for index, (m, c) in enumerate(MONOGRAM):
        y = 125 + index * 24
        # All ASCII characters are rendered as text, not a raster screenshot.
        solid = m.replace("#", "@") + "   " + c.replace("#", "@")
        guide = "." * len(m) + "   " + "." * len(c)
        foreground = solid.replace(".", " ")
        out.append(
            f'<text x="710" y="{y}" font-size="20" font-weight="700" '
            f'letter-spacing=".35" xml:space="preserve" fill="{p["muted"]}" '
            f'opacity=".16">{escape(guide)}</text>'
        )
        out.append(
            f'<text class="ascii" x="710" y="{y}" font-size="20" font-weight="700" '
            f'letter-spacing=".35" xml:space="preserve" fill="url(#accent)">'
            f'{escape(foreground)}</text>'
        )
    out += [
        f'<rect class="scan" x="680" y="74" width="510" height="45" fill="url(#scan)" '
        'pointer-events="none"/>',
        f'<path d="M52 352H1148" stroke="{p["stroke"]}"/>',
        f'<text x="52" y="375" fill="{p["muted"]}" font-size="10" letter-spacing="1">'
        'POLITECNICO DI MILANO   //   ENGINEERING IN PROGRESS</text>',
        f'<text x="1148" y="375" fill="{p["cyan"]}" font-size="10" '
        'letter-spacing="1" text-anchor="end">[  BUILD  /  LEARN  /  ITERATE  ]</text>',
        '</g></svg>'
    ]
    return '\n'.join(out) + '\n'


def main():
    for theme in PALETTES:
        path = ROOT / "assets" / f"terminal.{theme}.svg"
        path.write_text(render(theme), encoding="utf-8")
        print(f"Rendered {path}")


if __name__ == "__main__":
    main()
