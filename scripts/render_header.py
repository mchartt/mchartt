"""Render the original profile banner. No network or third-party dependencies."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for theme in ("dark", "light"):
    dark = theme == "dark"
    bg, fg, muted, line = ("#0d1117", "#f0f6fc", "#9aa7b5", "#263242") if dark else ("#f6f8fa", "#1f2328", "#596879", "#d6dee8")
    accent, secondary = ("#b99cff", "#67e8f9") if dark else ("#7044c6", "#007f94")
    cubes = []
    for x, y, size, delay in [(900, 148, 74, 0), (1024, 200, 36, 1.5), (802, 227, 27, 3)]:
        points = lambda values: " ".join(f"{x+a*size},{y+b*size}" for a, b in values)
        cubes.append(f'''<g class="float" style="animation-delay:-{delay}s">
          <polygon points="{points([(0,-1),(.866,-.5),(0,0),(-.866,-.5)])}" fill="{accent}" fill-opacity=".13" stroke="{accent}"/>
          <polygon points="{points([(-.866,-.5),(0,0),(0,1),(-.866,.5)])}" fill="{accent}" fill-opacity=".05" stroke="{accent}"/>
          <polygon points="{points([(0,0),(.866,-.5),(.866,.5),(0,1)])}" fill="{secondary}" fill-opacity=".08" stroke="{secondary}"/>
          <path d="M{x},{y-size} V{y} L{x+.866*size},{y+.5*size}" fill="none" stroke="{secondary}" stroke-opacity=".45"/>
        </g>''')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="360" viewBox="0 0 1200 360" role="img" aria-labelledby="title desc">
      <title id="title">Matteo Cesandri — Computer Engineering</title>
      <desc id="desc">Politecnico di Milano. Java, TypeScript and databases. Floating isometric cubes orbit a wireframe platform.</desc>
      <defs>
        <pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="{line}"/></pattern>
        <linearGradient id="rule"><stop stop-color="{accent}"/><stop offset="1" stop-color="{secondary}"/></linearGradient>
      </defs>
      <style>
        text{{font-family:Arial,Helvetica,sans-serif}} .mono{{font-family:'Courier New',monospace}}
        .float{{animation:float 7s ease-in-out infinite}}
        .orbit{{stroke-dasharray:5 9;animation:orbit 45s linear infinite}}
        .cursor{{animation:blink 1.5s step-end infinite}}
        @keyframes float{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-12px)}}}}
        @keyframes orbit{{to{{stroke-dashoffset:-280}}}}
        @keyframes blink{{50%{{opacity:0}}}}
        @media(prefers-reduced-motion:reduce){{.float,.orbit,.cursor{{animation:none}}}}
      </style>
      <rect x="1" y="1" width="1198" height="358" rx="20" fill="{bg}" stroke="{line}"/>
      <path d="M22 1H1178" stroke="url(#rule)" stroke-width="2"/>
      <rect x="690" y="24" width="484" height="308" fill="url(#dots)"/>
      <text x="52" y="54" fill="{accent}" font-size="12" letter-spacing="2.3" class="mono">MCHARTT / COMPUTER ENGINEERING</text>
      <text x="48" y="128" fill="{fg}" font-size="62" font-weight="700" letter-spacing="-2.5">Matteo</text>
      <text x="48" y="193" fill="{fg}" font-size="62" font-weight="700" letter-spacing="-2.5">Cesandri<tspan fill="{accent}">.</tspan></text>
      <text x="52" y="238" fill="{muted}" font-size="19">Java · TypeScript · Databases</text>
      <path d="M52 270H615" stroke="{line}"/>
      <text x="52" y="308" fill="{muted}" font-size="13" class="mono">Politecnico di Milano</text>
      <text x="428" y="308" fill="{accent}" font-size="13" class="mono">&gt; git push<tspan class="cursor"> _</tspan></text>
      <path d="M750 270 L917 173 L1084 270 L917 328 Z M750 270 L917 270 L1084 270 M834 222 L1000 318 M1000 222 L834 318" fill="none" stroke="{line}"/>
      <ellipse class="orbit" cx="915" cy="238" rx="187" ry="63" fill="none" stroke="{accent}" stroke-opacity=".5"/>
      <circle cx="1102" cy="238" r="4" fill="{secondary}"/>
      {''.join(cubes)}
      <text x="917" y="67" fill="{muted}" font-size="10" letter-spacing="2" text-anchor="middle" class="mono">IDEA → CODE → ITERATE</text>
    </svg>'''
    (ROOT / "assets" / f"header.{theme}.svg").write_text(svg + "\n")
