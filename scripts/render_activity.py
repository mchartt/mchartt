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


def render_snake(days, theme):
    p = PALETTES[theme]
    maximum = max(count for _, count in days) or 1
    start = days[0][0] - timedelta(days=(days[0][0].weekday()+1)%7)
    cells = {}
    for day, count in days:
        week, weekday = divmod((day-start).days, 7)
        cells[(week, weekday)] = (day, count)
    weeks = max(week for week, _ in cells)+1
    path = [(week, d) for week in range(weeks) for d in (range(7) if week%2==0 else range(6,-1,-1))]
    points = [(25+w*15, 23+d*15) for w,d in path]
    # Return outside the grid so the loop has no jump through contribution cells.
    points += [(points[-1][0]+15, points[-1][1]), (points[-1][0]+15, 8), (10,8), (10,23), points[0]]
    steps = len(points)-1
    motion = ''.join(f'{i/steps*100:.5f}%{{transform:translate({x}px,{y}px)}}' for i,(x,y) in enumerate(points))
    out = svg_start(846, 146, 'Animated snake traversing the public profile contribution calendar', p)
    out.append(f'<style>@keyframes walk{{{motion}}}.segment{{animation:walk 42s linear infinite}}@media(prefers-reduced-motion:reduce){{.segment{{display:none}}}}</style>')
    lookup = {cell:i for i,cell in enumerate(path)}
    for (w,d), (day,count) in cells.items():
        x,y = 25+w*15,23+d*15
        color=p['ramp'][level(count,maximum)]
        if count:
            # Fade a cell after the snake reaches it, restoring it on each loop.
            at=lookup[(w,d)]/steps*100
            key=f'eat{w}x{d}'
            frames = f'0%,{max(0,at-.02):.5f}%' + '{fill:'+color+'}'
            frames += f'{min(99.99,at+.02):.5f}%,99.99%' + '{fill:'+p['ramp'][0]+'}'
            frames += '100%{fill:'+color+'}'
            out.append(f'<style>@keyframes {key}{{{frames}}}@media(prefers-reduced-motion:reduce){{.c{key}{{animation:none!important}}}}</style>')
            animate=f' class="c{key}" style="animation:{key} 42s linear infinite"'
        else:
            animate=''
        out.append(f'<rect x="{x}" y="{y}" width="11" height="11" rx="2" fill="{color}"{animate}><title>{day.isoformat()}: {count} contributions</title></rect>')
    for i in reversed(range(8)):
        out.append(f'<rect class="segment" x="0" y="0" width="11" height="11" rx="3" fill="{p["cyan"] if i==0 else p["accent"]}" opacity="{1-i*.08:.2f}" style="animation-delay:{i*42/steps:.5f}s;transform:translate({points[0][0]}px,{points[0][1]}px)"/>')
    out += [text(25, 134, 'Same calendar. One continuous path.', p['muted'], 10, 'class="mono"'), '</svg>']
    return '\n'.join(out)+'\n'


def main():
    today = datetime.now(timezone.utc).date()
    if len(sys.argv)>1:
        fixture = json.loads(Path(sys.argv[1]).read_text())
        counts, today = fixture['counts'], date.fromisoformat(fixture['today'])
    else:
        counts = load_calendar(os.environ.get('PROFILE_USERNAME', 'mchartt'))
    days = calendar_days(counts, today)
    for theme in PALETTES:
        (ROOT/'assets'/f'contributions.{theme}.svg').write_text(render_skyline(days, theme))
        (ROOT/'assets'/f'snake.{theme}.svg').write_text(render_snake(days, theme))
    total, active, current, longest = stats(days)
    metadata = dict(source='GitHub public profile calendar', from_date=days[0][0].isoformat(), to_date=today.isoformat(), total=total, active_days=active, current_streak=current, longest_streak_in_window=longest)
    (ROOT/'assets'/'activity.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(f'Public profile calendar: {stats(days)[0]} contributions, {stats(days)[1]} active days, current streak {stats(days)[2]} days')


if __name__ == '__main__':
    main()
