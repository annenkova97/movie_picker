// Theme tokens and shared components used by both directions.

// ===== Theme =====
const THEMES = {
  light: {
    name:'light',
    // surfaces
    bg:        '#faf5ea',   // warm paper, not cold white
    bgAlt:     '#f3ebd9',   // shelf alt row
    surface:   '#ffffff',
    // ink
    ink:       '#2a1830',
    ink2:      '#5a4556',
    ink3:      '#8f7a88',
    // brand
    plum:      '#3d2442',
    plumInk:   '#f5e6b8',   // text on plum
    butter:    '#e4b15c',
    butterDeep:'#c78f3c',
    cream:     '#f5e6b8',
    // utility
    line:      'rgba(61,36,66,0.12)',
    lineStrong:'rgba(61,36,66,0.22)',
    chipBg:    'rgba(61,36,66,0.06)',
    posterInk: '#2a1830',
    posterPaper:'#f5e6b8',
    shadow:    '0 1px 2px rgba(61,36,66,0.08), 0 12px 28px -12px rgba(61,36,66,0.18)',
    shadowLg:  '0 1px 2px rgba(61,36,66,0.10), 0 30px 60px -20px rgba(61,36,66,0.35)',
    // dark-on-plum zones
    plumSurface:'#3d2442',
    plumLine:  'rgba(245,230,184,0.18)',
  },
  dark: {
    name:'dark',
    bg:        '#1d1218',  // warm near-black, plum-tinted
    bgAlt:     '#251620',
    surface:   '#2a1a23',
    ink:       '#f5e6b8',
    ink2:      '#d7c5a7',
    ink3:      '#9a8b78',
    plum:      '#f5e6b8',   // role-reversed for primary-on-dark
    plumInk:   '#2a1830',
    butter:    '#e4b15c',
    butterDeep:'#c78f3c',
    cream:     '#f5e6b8',
    line:      'rgba(245,230,184,0.10)',
    lineStrong:'rgba(245,230,184,0.22)',
    chipBg:    'rgba(245,230,184,0.08)',
    posterInk: '#2a1830',
    posterPaper:'#f5e6b8',
    shadow:    '0 1px 2px rgba(0,0,0,0.35), 0 12px 28px -10px rgba(0,0,0,0.55)',
    shadowLg:  '0 1px 2px rgba(0,0,0,0.45), 0 40px 60px -20px rgba(0,0,0,0.7)',
    plumSurface:'#2a1a23',
    plumLine:  'rgba(245,230,184,0.12)',
  },
};

// ===== Typographic Poster =====
// Uses per-movie hue to vary the palette. Still in brand family: paper/butter/plum.
function TypoPoster({ movie, lang='en', w=160, h=240, variant='a' }) {
  const hue = movie.hue ?? 30;
  // Build poster palette mixing brand with hue tint
  const isCool = movie.type === 'cool';
  const bg  = `oklch(0.30 0.08 ${hue})`;
  const bgB = `oklch(0.22 0.10 ${hue})`;
  const glow= `oklch(0.78 0.12 ${(hue+20)%360})`;
  const paper='#f5e6b8';
  const title = lang==='ru' ? movie.ru : movie.en;
  const year = movie.year;
  const dir  = movie.dir;
  // choose a typographic treatment by id hash for variety
  const hash = (movie.id||'').split('').reduce((s,c)=>s+c.charCodeAt(0),0);
  const layout = hash % 4; // 0: big title bottom, 1: centered, 2: vertical, 3: split

  const base = {
    width:w, height:h, borderRadius:8, overflow:'hidden',
    position:'relative', boxShadow:'0 2px 6px rgba(0,0,0,0.18), 0 12px 24px -12px rgba(0,0,0,0.35)',
    background:`linear-gradient(160deg, ${bg} 0%, ${bgB} 100%)`,
    color: paper, flexShrink:0,
  };
  const fontStack = `'Fraunces', 'Playfair Display', Georgia, serif`;
  const monoStack = `'JetBrains Mono', ui-monospace, Menlo, monospace`;

  // sub elements differ by layout
  let content;
  if (layout === 0) {
    content = (
      <>
        <div style={{position:'absolute', top:10, left:12, right:12, display:'flex', justifyContent:'space-between', fontFamily:monoStack, fontSize:Math.max(8,w*0.055), letterSpacing:0.5, opacity:0.8}}>
          <span>№{String(hash%99).padStart(2,'0')}</span>
          <span>{year}</span>
        </div>
        <div style={{position:'absolute', bottom:0, left:0, right:0, padding:'12px 12px 14px', background:`linear-gradient(0deg, ${bgB} 10%, transparent 100%)`}}>
          <div style={{fontFamily:fontStack, fontWeight:700, fontSize:Math.max(14,w*0.13), lineHeight:0.95, letterSpacing:-0.5, color:paper, textWrap:'balance'}}>{title}</div>
          <div style={{fontFamily:monoStack, fontSize:Math.max(8,w*0.05), opacity:0.7, marginTop:6, letterSpacing:0.4}}>{dir}</div>
        </div>
      </>
    );
  } else if (layout === 1) {
    content = (
      <>
        <div style={{position:'absolute', inset:0, display:'flex', alignItems:'center', justifyContent:'center', padding:14, textAlign:'center'}}>
          <div style={{fontFamily:fontStack, fontWeight:600, fontStyle:'italic', fontSize:Math.max(14,w*0.14), lineHeight:1.0, color:paper, textWrap:'balance'}}>{title}</div>
        </div>
        <div style={{position:'absolute', top:10, left:12, right:12, display:'flex', justifyContent:'space-between', fontFamily:monoStack, fontSize:Math.max(8,w*0.05), opacity:0.7}}>
          <span>{dir}</span><span>{year}</span>
        </div>
        <div style={{position:'absolute', bottom:10, left:12, right:12, borderTop:`1px solid ${paper}33`, paddingTop:6, fontFamily:monoStack, fontSize:Math.max(8,w*0.05), opacity:0.75, display:'flex', justifyContent:'space-between'}}>
          <span>{movie.runtime} min</span>
          <span>★ {movie.publicRating.toFixed(1)}</span>
        </div>
      </>
    );
  } else if (layout === 2) {
    // vertical title reads up the side
    content = (
      <>
        <div style={{position:'absolute', left:0, top:0, bottom:0, width:'48%', display:'flex', alignItems:'flex-end', padding:12}}>
          <div style={{writingMode:'vertical-rl', transform:'rotate(180deg)', fontFamily:fontStack, fontWeight:700, fontSize:Math.max(14,w*0.14), lineHeight:0.95, color:paper, letterSpacing:-0.3}}>{title}</div>
        </div>
        <div style={{position:'absolute', right:12, top:12, width:'46%', textAlign:'right', fontFamily:monoStack, fontSize:Math.max(8,w*0.05), opacity:0.75, lineHeight:1.5}}>
          <div>{year}</div>
          <div>{dir}</div>
          <div style={{marginTop:6}}>★ {movie.publicRating.toFixed(1)}</div>
        </div>
        <div style={{position:'absolute', right:12, bottom:12, width:'46%', textAlign:'right', fontFamily:monoStack, fontSize:Math.max(8,w*0.05), opacity:0.7}}>
          {movie.runtime} min
        </div>
      </>
    );
  } else {
    // split: color band + title
    content = (
      <>
        <div style={{position:'absolute', left:0, right:0, top:0, height:'38%', background:`linear-gradient(135deg, ${glow} 0%, ${bg} 100%)`, opacity:0.65}}/>
        <div style={{position:'absolute', top:12, left:12, right:12, fontFamily:monoStack, fontSize:Math.max(8,w*0.05), opacity:0.9, letterSpacing:0.5}}>{year} · {movie.runtime}&apos;</div>
        <div style={{position:'absolute', top:'38%', left:12, right:12, borderTop:`1px solid ${paper}55`, paddingTop:10, fontFamily:fontStack, fontWeight:700, fontSize:Math.max(14,w*0.14), lineHeight:0.95, color:paper, textWrap:'balance'}}>{title}</div>
        <div style={{position:'absolute', bottom:10, left:12, right:12, fontFamily:monoStack, fontSize:Math.max(8,w*0.05), opacity:0.7, letterSpacing:0.3}}>{dir}</div>
      </>
    );
  }

  return <div style={base} data-poster={movie.id}>{content}</div>;
}

// ===== Top Bar =====
function TopBar({ th, lang, setLang, theme, setTheme, onAdd, compact=false }) {
  return (
    <div style={{
      display:'flex', alignItems:'center', justifyContent:'space-between',
      padding: compact ? '12px 12px' : '18px 28px',
      gap: 8,
      borderBottom:`1px solid ${th.line}`,
      background: th.bg,
      position:'sticky', top:0, zIndex:5,
    }}>
      {/* Logo */}
      <div style={{display:'flex', alignItems:'center', gap:10, minWidth:0, flexShrink:1}}>
        <div style={{width:compact?28:32, height:compact?28:32, borderRadius:7, overflow:'hidden', flexShrink:0, boxShadow:'0 2px 6px rgba(0,0,0,0.15)'}}>
          <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
            <rect width="64" height="64" rx="14" fill="#3d2442"/>
            <rect x="10" y="18" width="22" height="32" rx="2" fill="#f5e6b8" fillOpacity="0.16"/>
            <rect x="14" y="16" width="22" height="34" rx="2" fill="#f5e6b8" fillOpacity="0.28"/>
            <g transform="rotate(8 34 32)">
              <path d="M22 14h16l8 8v26a2 2 0 0 1-2 2H22a2 2 0 0 1-2-2V16a2 2 0 0 1 2-2z" fill="#f5e6b8"/>
              <path d="M38 14l8 8h-6a2 2 0 0 1-2-2v-6z" fill="#e4b15c"/>
              <path d="M29 30 L40 36.5 L29 43 Z" fill="#2a1830"/>
            </g>
          </svg>
        </div>
        <div style={{display:'flex', flexDirection:'column', lineHeight:1, minWidth:0}}>
          <div style={{fontFamily:"'Fraunces', Georgia, serif", fontWeight:700, fontSize: compact?15:19, color:th.ink, letterSpacing:-0.3, whiteSpace:'nowrap'}}>
            {T.appName[lang]}
          </div>
          {!compact && <div style={{fontSize:11, color:th.ink3, marginTop:3, fontStyle:'italic'}}>{T.tagline[lang]}</div>}
        </div>
      </div>

      <div style={{display:'flex', alignItems:'center', gap:compact?6:12, flexShrink:0}}>
        {/* Lang switch */}
        <div style={{display:'flex', background:th.chipBg, borderRadius:999, padding:2, fontSize:11, fontWeight:600}}>
          {['ru','en'].map(l => (
            <button key={l} onClick={()=>setLang(l)} style={{
              border:'none', borderRadius:999, padding: compact?'5px 9px':'6px 12px', cursor:'pointer',
              background: lang===l ? th.plum : 'transparent',
              color: lang===l ? th.plumInk : th.ink2,
              fontWeight:600, letterSpacing:0.3, textTransform:'uppercase', fontSize: compact?10.5:12,
            }}>{l}</button>
          ))}
        </div>
        {/* Theme toggle (icon) */}
        <button onClick={()=>setTheme(theme==='light'?'dark':'light')}
          title={theme==='light'?'Dark':'Light'}
          style={{
            border:`1px solid ${th.line}`, background:'transparent', color:th.ink2,
            width: compact?30:36, height: compact?30:36, borderRadius:999, cursor:'pointer',
            display:'flex', alignItems:'center', justifyContent:'center', fontSize:14,
          }}>
          {theme==='light' ? '☾' : '☀'}
        </button>
        {/* Add CTA */}
        <button onClick={onAdd} style={{
          border:'none', background:th.plum, color:th.plumInk,
          padding: compact ? '7px 11px' : '10px 18px', borderRadius:999, cursor:'pointer',
          fontSize: compact?12:13, fontWeight:600, letterSpacing:0.2, whiteSpace:'nowrap',
          boxShadow:'0 1px 2px rgba(0,0,0,0.1)',
        }}>
          {compact ? (lang==='ru'?'+ Добавить':'+ Add') : T.addMovie[lang]}
        </button>
      </div>
    </div>
  );
}

// ===== Mood input =====
function MoodPicker({ th, lang, onPick }) {
  const [v, setV] = React.useState('');
  const chips = T.moodChips[lang];
  return (
    <div style={{display:'flex', flexDirection:'column', gap:12}}>
      <label style={{fontFamily:"'Fraunces', Georgia, serif", fontSize:14, color:th.ink2, fontWeight:500, letterSpacing:0.2, display:'flex', alignItems:'center', gap:8}}>
        <span style={{width:6, height:6, borderRadius:999, background:th.butter}}/>
        {T.mood[lang]}
      </label>
      <div style={{display:'flex', gap:10, alignItems:'stretch', background:th.surface, border:`1px solid ${th.line}`, borderRadius:14, padding:6, boxShadow:th.shadow}}>
        <input
          value={v} onChange={e=>setV(e.target.value)}
          placeholder={T.moodPh[lang]}
          style={{
            flex:1, border:'none', outline:'none', background:'transparent',
            fontSize:16, padding:'14px 14px', color:th.ink, fontFamily:'inherit',
            minWidth:0,
          }}
        />
        <button onClick={()=>onPick(v || chips[0])} style={{
          border:'none', background:th.plum, color:th.plumInk,
          padding:'0 20px', borderRadius:10, cursor:'pointer',
          fontSize:14, fontWeight:600, letterSpacing:0.2, whiteSpace:'nowrap',
        }}>{T.pick[lang]} →</button>
      </div>
      <div style={{display:'flex', gap:8, flexWrap:'wrap'}}>
        {chips.map((c,i) => (
          <button key={i} onClick={()=>{setV(c); onPick(c);}} style={{
            border:`1px solid ${th.line}`, background:'transparent', color:th.ink2,
            padding:'7px 12px', borderRadius:999, cursor:'pointer', fontSize:12.5, fontFamily:'inherit',
          }}>{c}</button>
        ))}
      </div>
    </div>
  );
}

// ===== Quick-add =====
function QuickAdd({ th, lang, onSave, movies }) {
  const [url, setUrl] = React.useState('');
  const [parsed, setParsed] = React.useState(null);
  const parse = () => {
    // fake parse — pick a candidate from MOVIES by url fragment, or default
    const candidate = movies.find(m => url.toLowerCase().includes(m.id)) || MOVIES.find(m=>m.id==='anora') || MOVIES[0];
    const srcType = /instagram|reel/.test(url.toLowerCase()) ? 'instagram'
               : /t\.me|telegram/.test(url.toLowerCase()) ? 'telegram'
               : candidate.source;
    setParsed({ ...candidate, source: srcType });
  };
  const save = () => { if (parsed) { onSave(parsed); setParsed(null); setUrl(''); } };
  const srcLabel = (s) => T['source_'+s]?.[lang] || s;

  return (
    <div style={{display:'flex', flexDirection:'column', gap:12}}>
      <label style={{fontFamily:"'Fraunces', Georgia, serif", fontSize:14, color:th.ink2, fontWeight:500, letterSpacing:0.2, display:'flex', alignItems:'center', gap:8}}>
        <span style={{width:6, height:6, borderRadius:999, background:th.plum}}/>
        {T.quickAdd[lang]}
      </label>
      <div style={{display:'flex', gap:10, alignItems:'stretch', background:th.surface, border:`1px solid ${th.line}`, borderRadius:14, padding:6, boxShadow:th.shadow}}>
        <input
          value={url} onChange={e=>{setUrl(e.target.value); setParsed(null);}}
          onKeyDown={e=>{if(e.key==='Enter')parse();}}
          placeholder={T.quickAddPh[lang]}
          style={{
            flex:1, border:'none', outline:'none', background:'transparent',
            fontSize:16, padding:'14px 14px', color:th.ink, fontFamily:'inherit',
            minWidth:0,
          }}
        />
        <button onClick={parse} style={{
          border:`1px solid ${th.lineStrong}`, background:'transparent', color:th.ink,
          padding:'0 20px', borderRadius:10, cursor:'pointer',
          fontSize:14, fontWeight:600, letterSpacing:0.2, whiteSpace:'nowrap',
        }}>{T.save[lang]}</button>
      </div>

      {parsed && (
        <div style={{
          display:'flex', gap:12, padding:12, borderRadius:14, background:th.bgAlt,
          border:`1px solid ${th.line}`, alignItems:'flex-start',
        }}>
          <TypoPoster movie={parsed} lang={lang} w={72} h={108}/>
          <div style={{flex:1, display:'flex', flexDirection:'column', gap:6}}>
            <div style={{fontSize:10, fontFamily:'ui-monospace,monospace', color:th.ink3, textTransform:'uppercase', letterSpacing:0.6}}>{T.quickParsed[lang]} · {srcLabel(parsed.source)}</div>
            <div style={{fontFamily:"'Fraunces', serif", fontWeight:700, fontSize:17, color:th.ink, lineHeight:1.1}}>{lang==='ru'?parsed.ru:parsed.en}</div>
            <div style={{fontSize:12, color:th.ink3}}>{parsed.dir} · {parsed.year} · {parsed.runtime} {T.min[lang]}</div>
            <div style={{display:'flex', gap:8, marginTop:6}}>
              <button onClick={save} style={{
                border:'none', background:th.plum, color:th.plumInk,
                padding:'7px 12px', borderRadius:8, cursor:'pointer',
                fontSize:12, fontWeight:600,
              }}>{T.quickKeep[lang]}</button>
              <button onClick={()=>setParsed(null)} style={{
                border:`1px solid ${th.line}`, background:'transparent', color:th.ink2,
                padding:'7px 12px', borderRadius:8, cursor:'pointer',
                fontSize:12, fontWeight:500,
              }}>{T.quickEdit[lang]}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ===== Pick Reveal overlay =====
function PickReveal({ th, lang, movie, mood, onClose, onAgain }) {
  if (!movie) return null;
  const title = lang==='ru'?movie.ru:movie.en;
  return (
    <div style={{
      position:'absolute', inset:0, zIndex:20,
      background: `rgba(30,15,25,0.55)`,
      backdropFilter:'blur(8px)', WebkitBackdropFilter:'blur(8px)',
      display:'flex', alignItems:'center', justifyContent:'center', padding:20,
      animation:'lfade 240ms ease-out',
    }} onClick={onClose}>
      <div onClick={e=>e.stopPropagation()} style={{
        background: th.surface, borderRadius:20, padding:24, maxWidth:460, width:'100%',
        boxShadow:th.shadowLg, border:`1px solid ${th.line}`,
        display:'flex', flexDirection:'column', gap:18,
        animation:'lup 260ms cubic-bezier(.2,.8,.2,1)',
      }}>
        <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-start'}}>
          <div>
            <div style={{fontSize:10, fontFamily:'ui-monospace,monospace', color:th.ink3, textTransform:'uppercase', letterSpacing:0.8}}>{T.pickHeader[lang]}</div>
            {mood && <div style={{fontSize:13, color:th.ink2, marginTop:4, fontStyle:'italic'}}>«{mood}»</div>}
          </div>
          <button onClick={onClose} style={{
            border:'none', background:'transparent', color:th.ink3, fontSize:22,
            cursor:'pointer', padding:0, width:28, height:28, lineHeight:1,
          }}>×</button>
        </div>
        <div style={{display:'flex', gap:16, alignItems:'flex-start'}}>
          <TypoPoster movie={movie} lang={lang} w={140} h={210}/>
          <div style={{flex:1, minWidth:0, paddingTop:4}}>
            <div style={{fontFamily:"'Fraunces', serif", fontWeight:700, fontSize:24, color:th.ink, lineHeight:1.05, textWrap:'balance'}}>{title}</div>
            <div style={{fontSize:13, color:th.ink3, marginTop:6}}>{movie.dir} · {movie.year} · {movie.runtime} {T.min[lang]}</div>
            <div style={{marginTop:14, padding:'12px 14px', background:th.bgAlt, borderRadius:10, border:`1px solid ${th.line}`}}>
              <div style={{fontSize:10, fontFamily:'ui-monospace,monospace', color:th.ink3, textTransform:'uppercase', letterSpacing:0.6, marginBottom:4}}>{T.pickBecause[lang]}</div>
              <div style={{fontSize:13, color:th.ink, lineHeight:1.45}}>{movie.why[lang]}</div>
            </div>
          </div>
        </div>
        <div style={{display:'flex', gap:10, marginTop:4}}>
          <button onClick={onAgain} style={{
            flex:1, border:`1px solid ${th.line}`, background:'transparent', color:th.ink,
            padding:'11px', borderRadius:10, cursor:'pointer', fontSize:13, fontWeight:600,
          }}>↻ {T.pickAgain[lang]}</button>
          <button onClick={onClose} style={{
            flex:2, border:'none', background:th.plum, color:th.plumInk,
            padding:'11px', borderRadius:10, cursor:'pointer', fontSize:13, fontWeight:600,
          }}>▸ Смотрим</button>
        </div>
      </div>
    </div>
  );
}

// ===== Empty state block (shared between directions, with variant-aware styling) =====
function EmptyDemo({ th, lang }) {
  return (
    <div style={{
      border:`1.5px dashed ${th.lineStrong}`, borderRadius:16, padding:20,
      background:th.bgAlt, display:'flex', gap:16, alignItems:'center',
    }}>
      <TypoPoster movie={MOVIES.find(m=>m.id==='anora')} lang={lang} w={78} h={117}/>
      <div style={{flex:1, minWidth:0}}>
        <div style={{fontSize:10, fontFamily:'ui-monospace,monospace', color:th.ink3, textTransform:'uppercase', letterSpacing:0.6, marginBottom:6}}>
          {lang==='ru'?'Вот как это выглядит →':'Here\u2019s what it looks like →'}
        </div>
        <div style={{fontFamily:"'Fraunces',serif", fontWeight:700, fontSize:17, color:th.ink, lineHeight:1.1}}>
          {lang==='ru' ? 'instagram.com/reel/DqX...' : 'instagram.com/reel/DqX...'}
        </div>
        <div style={{fontSize:12, color:th.ink3, marginTop:6, fontStyle:'italic'}}>
          {lang==='ru' ? '→ Анора · Шон Бейкер · 2024 · 139 мин' : '→ Anora · Sean Baker · 2024 · 139 min'}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { THEMES, TypoPoster, TopBar, MoodPicker, QuickAdd, PickReveal, EmptyDemo });
