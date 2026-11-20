"""Build profile visuals from the contribution calendar already visible publicly.

The anonymous counts include private activity only when the owner has chosen to
display it on GitHub. No private repository names, contents or tokens are read.
"""
from datetime import date, datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import json
import math
import os
import re
import random
import secrets
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PALETTES = {
    'dark': dict(bg='#0d1117', fg='#f0f6fc', muted='#9198a1', line='#30363d', panel='#161b22', accent='#b99cff', cyan='#67e8f9', ramp=['#1d2330', '#453161', '#70509e', '#9771cf', '#c0a0ff']),
    'light': dict(bg='#ffffff', fg='#1f2328', muted='#596879', line='#d1d9e0', panel='#f6f8fa', accent='#7044c6', cyan='#007f94', ramp=['#e9eaf0', '#dfd0f1', '#bda0df', '#966ccc', '#7044c6']),
}


class CalendarParser(HTMLParser):
    """Support GitHub's current tooltip counts and its older data-count format."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.cells, self.tips = {}, {}
        self.tip_id, self.tip_text = None, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'data-date' in a:
            self.cells[a['data-date']] = a
        if tag == 'tool-tip' and a.get('for'):
            self.tip_id, self.tip_text = a['for'], []

    def handle_data(self, text):
        if self.tip_id is not None:
            self.tip_text.append(text)

    def handle_endtag(self, tag):
        if tag == 'tool-tip' and self.tip_id is not None:
            self.tips[self.tip_id] = ''.join(self.tip_text).strip()
            self.tip_id, self.tip_text = None, []

    def counts(self):
        result = {}
        for day, attrs in self.cells.items():
            if 'data-count' in attrs:
                count = int(attrs['data-count'])
            else:
                text = self.tips.get(attrs.get('id'), '')
                match = re.match(r'([\d,]+) contributions?\b', text)
                if text.startswith('No contributions'):
                    count = 0
                elif match:
                    count = int(match[1].replace(',', ''))
                else:
                    raise ValueError(f'Cannot read contribution count for {day}')
            result[day] = count
        return result


def load_calendar(username):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}', username):
        raise ValueError('Invalid GitHub username')
    request = Request(f'https://github.com/users/{username}/contributions', headers={
        'User-Agent': f'{username}-profile-visuals', 'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html',
    })
    with urlopen(request, timeout=45) as response:
        markup = response.read().decode('utf-8')
    parser = CalendarParser()
    parser.feed(markup)
    return parser.counts()


def calendar_days(counts, today):
    days = [(today - timedelta(days=i)).isoformat() for i in range(364, -1, -1)]
    missing = [day for day in days if day not in counts]
    if missing:
        raise ValueError(f'Public calendar is incomplete: {len(missing)} dates missing')
    result = [(date.fromisoformat(day), int(counts[day])) for day in days]
    if any(count < 0 for _, count in result):
        raise ValueError('Contribution counts must be nonnegative')
    return result


def stats(days):
    counts = [count for _, count in days]
    longest = run = 0
    for count in counts:
        run = run + 1 if count else 0
        longest = max(longest, run)
    # Today is still in progress: an empty today does not end yesterday's streak.
    current = 0
    for count in reversed(counts if counts[-1] else counts[:-1]):
        if not count:
            break
        current += 1
    return sum(counts), sum(count > 0 for count in counts), current, longest


def text(x, y, value, fill, size=12, extra=''):
    return f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" {extra}>{escape(str(value))}</text>'


def svg_start(width, height, title, p):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">',
            f'<title id="title">{escape(title)}</title>',
            '<style>text{font-family:Arial,Helvetica,sans-serif}.mono{font-family:monospace}.rise{animation:rise .8s ease both}@keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}@media(prefers-reduced-motion:reduce){.rise{animation:none}}</style>',
            f'<rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="16" fill="{p["bg"]}" stroke="{p["line"]}"/>']


def darken(color, factor):
    return '#' + ''.join(f'{round(int(color[i:i+2], 16)*factor):02x}' for i in (1, 3, 5))


def level(count, maximum):
    return 0 if not count else min(4, max(1, math.ceil(4 * math.sqrt(count / maximum))))


def render_skyline(days, theme):
    p = PALETTES[theme]
    total, active, current, longest = stats(days)
    maximum = max(count for _, count in days) or 1
    start = days[0][0] - timedelta(days=(days[0][0].weekday() + 1) % 7)
    out = svg_start(846, 510, f'Public profile contributions: {total} contributions, current streak {current} days, longest streak in the last year {longest} days', p)
    out += [text(24, 33, 'CONTRIBUTION SKYLINE', p['accent'], 11, 'class="mono" letter-spacing="2"'),
            text(822, 33, 'LAST 365 DAYS', p['muted'], 10, 'class="mono" text-anchor="end"')]
    for i, (value, label, unit) in enumerate([(total, 'Contributions', ''), (active, 'Active days', ''), (current, 'Current streak', 'days'), (longest, 'Longest streak · past year', 'days')]):
        x = 24 + i * 202
        out.append(f'<rect x="{x}" y="55" width="190" height="89" rx="9" fill="{p["panel"]}"/>')
        out += [text(x+14, 80, label, p['muted'], 11), text(x+14, 119, value, p['fg'], 32, 'font-weight="700"')]
        if unit:
            out.append(text(x+64, 118, unit, p['muted'], 11))
    out.append(text(24, 173, 'Each block is a day. Height reflects contribution count.', p['muted'], 12))
    blocks = []
    months = set()
    for day, count in days:
        offset = (day - start).days
        week, weekday = divmod(offset, 7)
        x, y = 153 + week*11.4 - weekday*10.8, 220 + week*3 + weekday*6.8
        height = 2 if not count else 5 + 66 * math.sqrt(count/maximum)
        color = p['ramp'][level(count, maximum)]
        points = lambda pairs: ' '.join(f'{a:.2f},{b:.2f}' for a, b in pairs)
        a, b, c, d = (x,y-height), (x+10.1,y+3.2-height), (x,y+9.3-height), (x-9.6,y+6.1-height)
        sides = f'<polygon points="{points([d,c,(c[0],y+9.3),(d[0],y+6.1)])}" fill="{darken(color,.68)}"/><polygon points="{points([b,c,(c[0],y+9.3),(b[0],y+3.2)])}" fill="{darken(color,.83)}"/><polygon points="{points([a,b,c,d])}" fill="{color}" stroke="{p["bg"]}" stroke-width=".55"/>'
        blocks.append((y, f'<g><title>{day.isoformat()}: {count} contributions</title>{sides}</g>'))
        month = (day.year, day.month)
        if month not in months and day.day <= 7:
            months.add(month)
            out.append(text(73+week*11.4, 288+week*3, day.strftime('%b'), p['muted'], 10, 'class="mono"'))
    out.append('<g class="rise">'+''.join(block for _, block in sorted(blocks))+'</g>')
    peak = max(days, key=lambda day: day[1])
    out.append(text(24, 464, f'Peak {peak[1]} · {peak[0].strftime("%d %b %Y")}', p['muted'], 11, 'class="mono"'))
    for i, color in enumerate(p['ramp']):
        out.append(f'<rect x="{663+i*16}" y="452" width="11" height="11" rx="2" fill="{color}"/>')
    out += [text(650, 462, 'Less', p['muted'], 10, 'text-anchor="end"'), text(751, 462, 'More', p['muted'], 10),
            text(24, 489, 'PUBLIC PROFILE CALENDAR · INCLUDES ANONYMOUS PRIVATE COUNTS WHEN SHARED', p['muted'], 8.5, 'class="mono"'),
            text(822, 489, 'Updated '+days[-1][0].isoformat(), p['muted'], 8.5, 'class="mono" text-anchor="end"'), '</svg>']
    return '\n'.join(out)+'\n'


def snake_route(cells, seed):
    """Create a reproducibly randomized, closed, grid-adjacent route.

    Choose nearby uncollected contribution cells in a different order every
    refresh, and use randomized shortest paths between them. Crossing an
    active cell collects it even when it was not the current target. Unlike
    the old row-by-row scan, the snake actually seeks out activity.
    """
    rng = random.Random(str(seed))
    weeks = max(week for week, _ in cells) + 1
    remaining = {cell for cell, (_, count) in cells.items() if count > 0}
    start = rng.choice(sorted(remaining)) if remaining else (weeks // 2, 3)
    route = [start]
    remaining.discard(start)

    def neighbors(cell):
        w, d = cell
        choices = [(w+1, d), (w-1, d), (w, d+1), (w, d-1)]
        rng.shuffle(choices)
        return [(x, y) for x, y in choices
                if 0 <= x < weeks and 0 <= y < 7]

    def connect(source, target):
        # Randomizing BFS neighbor order produces different shortest routes.
        from collections import deque
        queue = deque([source])
        parent = {source: None}
        while queue:
            current = queue.popleft()
            if current == target:
                break
            for neighbor in neighbors(current):
                if neighbor not in parent:
                    parent[neighbor] = current
                    queue.append(neighbor)
        if target not in parent:
            raise ValueError("Contribution grid is unexpectedly disconnected")
        path = []
        cursor = target
        while cursor is not None:
            path.append(cursor)
            cursor = parent[cursor]
        return list(reversed(path))

    while remaining:
        current = route[-1]
        # Strong preference for nearby dots, but not a predictable order.
        choices = sorted(remaining, key=lambda c: (
            abs(c[0]-current[0]) + abs(c[1]-current[1])
            + rng.uniform(0, 3.5)))[:min(5, len(remaining))]
        target = rng.choice(choices)
        for cell in connect(current, target)[1:]:
            route.append(cell)
            remaining.discard(cell)

    # Loop without teleporting: after the last dot, walk back to the start.
    route.extend(connect(route[-1], route[0])[1:])
    if len(route) == 1:
        neighbor = neighbors(start)[0]
        route.extend([neighbor, start])
    assert route[0] == route[-1]
    return route


def render_snake(days, theme, seed="preview"):
    p = PALETTES[theme]
    maximum = max(count for _, count in days) or 1
    start = days[0][0] - timedelta(days=(days[0][0].weekday()+1)%7)
    cells = {}
    for day, count in days:
        week, weekday = divmod((day-start).days, 7)
        cells[(week, weekday)] = (day, count)
    route = snake_route(cells, seed)
    steps = len(route) - 1
    seconds = max(24, min(100, steps * .24))

    def percent(i):
        return f'{100*i/steps:.5f}%'

    def coords(cell):
        w, d = cell
        return 25+w*15, 23+d*15

    # Every segment follows precisely the same CLOSED route. Applying a
    # phase of -i steps puts the head at the FRONT and the tail behind it.
    motion = ''.join(
        f'{percent(i)}{{transform:translate({coords(cell)[0]}px,{coords(cell)[1]}px)}}'
        for i, cell in enumerate(route)
    )
    turns = []
    for i, cell in enumerate(route):
        following = route[i+1] if i < steps else route[1]
        dx, dy = following[0]-cell[0], following[1]-cell[1]
        angle = {(1, 0): 0, (0, 1): 90, (-1, 0): 180, (0, -1): -90}[(dx, dy)]
        turns.append(f'{percent(i)}{{transform:rotate({angle}deg)}}')

    out = svg_start(846, 162, 'Randomized contribution snake collecting every active day on the GitHub calendar', p)
    out += [
        text(25, 16, 'CONTRIBUTION SNAKE // RANDOM WALK', p['accent'], 9.5,
             'class="mono" letter-spacing="1"'),
        text(821, 16, f'{len([1 for _, count in cells.values() if count])} ACTIVE CELLS', p['muted'], 9,
             'class="mono" text-anchor="end"')
    ]

    # At 100% all eaten cells return for the next animated lap.
    # The exact *first* visit, not the target order, determines consumption.
    first_visit = {}
    for i, cell in enumerate(route[:-1]):
        if cells.get(cell, (None, 0))[1] and cell not in first_visit:
            first_visit[cell] = i
    expected = {cell for cell, (_, count) in cells.items() if count}
    if set(first_visit) != expected:
        raise ValueError('The snake must collect all active contribution cells')

    css = [
        f'@keyframes snake-walk{{{motion}}}',
        f'@keyframes snake-face{{{"".join(turns)}}}',
        f'.snake-segment{{animation:snake-walk {seconds:.3f}s linear infinite}}',
        f'.snake-face{{transform-origin:5.5px 5.5px;animation:snake-face {seconds:.3f}s step-end infinite}}',
        '@media(prefers-reduced-motion:reduce){.snake-segment,.snake-face,.edible{animation:none!important}}'
    ]
    eaten_style = {}
    for i, cell in enumerate(sorted(first_visit)):
        at = first_visit[cell]/steps * 100
        name = f'eat{i}'
        before = max(0, at-.015)
        after = min(99.80, at+.06)
        if after <= before:
            after = min(99.9, before+.001)
        color = p['ramp'][level(cells[cell][1], maximum)]
        css.append(
            f'@keyframes {name}{{0%,{before:.4f}%{{fill:{color}}}'
            f'{after:.4f}%,99.9%{{fill:{p["ramp"][0]}}}'
            f'100%{{fill:{color}}}}}'
        )
        eaten_style[cell] = f' class="edible" style="animation:{name} {seconds:.3f}s linear infinite"'
    out.append('<style>' + ''.join(css) + '</style>')

    # Calendar remains legible as a stationary background beneath the snake.
    for (w, d), (day, count) in cells.items():
        x, y = coords((w, d))
        color = p['ramp'][level(count, maximum)]
        out.append(
            f'<rect x="{x}" y="{y}" width="11" height="11" rx="2" '
            f'fill="{color}"{eaten_style.get((w, d), "")}>'
            f'<title>{day.isoformat()}: {count} contributions</title></rect>'
        )

    # Draw the tail FIRST, and the cyan head LAST so it cannot be covered.
    for i in reversed(range(9)):
        x, y = coords(route[0])
        lag = i * seconds / steps
        phase_delay = 0 if i == 0 else -(seconds-lag)
        common = (f'class="snake-segment" style="animation-delay:{phase_delay:.5f}s;'
                  f'transform:translate({x}px,{y}px)"')
        if i == 0:
            out.append(
                f'<g {common}>'
                f'<rect width="11" height="11" rx="4.2" fill="{p["cyan"]}"/>'
                f'<g class="snake-face">'
                f'<circle cx="8.2" cy="3" r="1.25" fill="{p["bg"]}"/>'
                f'<circle cx="8.2" cy="8" r="1.25" fill="{p["bg"]}"/>'
                '</g></g>'
            )
        else:
            opacity = 1 - i*.082
            out.append(
                f'<rect {common} width="11" height="11" rx="3.7" '
                f'fill="{p["accent"]}" opacity="{opacity:.2f}"/>'
            )
    out += [
        text(25, 149, 'Each run explores a new route. Active squares are collected; the grid resets each lap.',
             p['muted'], 9.5, 'class="mono"'), '</svg>'
    ]
    return '\n'.join(out)+'\n'

def main():
    today = datetime.now(timezone.utc).date()
    if len(sys.argv)>1:
        fixture = json.loads(Path(sys.argv[1]).read_text())
        counts, today = fixture['counts'], date.fromisoformat(fixture['today'])
    else:
        counts = load_calendar(os.environ.get('PROFILE_USERNAME', 'mchartt'))
    days = calendar_days(counts, today)
    # One seed per run: dark/light get the same route, each scheduled refresh
    # receives a different one. GitHub READMEs cannot execute page-load JS.
    seed = os.environ.get('SNAKE_SEED') or str(secrets.randbits(64))
    for theme in PALETTES:
        (ROOT/'assets'/f'contributions.{theme}.svg').write_text(render_skyline(days, theme))
        (ROOT/'assets'/f'snake.{theme}.svg').write_text(render_snake(days, theme, seed))
    total, active, current, longest = stats(days)
    metadata = dict(source='GitHub public profile calendar', from_date=days[0][0].isoformat(), to_date=today.isoformat(), total=total, active_days=active, current_streak=current, longest_streak_in_window=longest)
    (ROOT/'assets'/'activity.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(f'Public profile calendar: {stats(days)[0]} contributions, {stats(days)[1]} active days, current streak {stats(days)[2]} days')


if __name__ == '__main__':
    main()
