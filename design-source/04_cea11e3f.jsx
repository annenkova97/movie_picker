// Direction B — "Лента / Cinema-rails"
// Plum-dominant surface, poster-first, edge-to-edge horizontal rails with large covers.
// Feels closer to a curated cinema feed.

function DirectionB({ th, lang, movies, frame, onAdd, onPick }) {
  const shelves = buildShelves(movies, lang);
  const [tab, setTab] = React.useState('toWatch');
  const [friendMode, setFriendMode] = React.useState(false);
  const isMobile = frame==='mobile';

  // Direction-B local palette: tint the hero section plum regardless of theme,
  // but with a subtle difference so light vs dark read differently.
  const heroBg = th.name==='dark'
    ? 'linear-gradient(180deg, #2a1a23 0%, #1d1218 100%)'
    : 'linear-gradient(180deg, #3d2442 0%, #2a1830 100%)';
  const heroInk = '#f5e6b8';
  const heroInk2 = 'rgba(245,230,184,0.72)';
  const heroLine = 'rgba(245,230,184,0.18)';
  const heroChip = 'rgba(245,230,184,0.10)';

  const savedCount = movies.filter(m=>!m.watched).length;
  const watchedCount = movies.filter(m=>m.watched).length;

  return (
    <div style={{background:th.bg, minHeight:'100%', color:th.ink, fontFamily:'-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif'}}>
      {/* Hero — plum slab */}
      <div style={{background:heroBg, color:heroInk, padding: isMobile ? '20px 18px 26px' : '36px 40px 44px'}}>
        <div style={{display:'flex', alignItems:'center', gap:10, marginBottom:isMobile?16:22}}>
          <div style={{width:5, height:5, borderRadius:999, background:'#e4b15c'}}/>
          <div style={{fontSize:10.5, fontFamily:'ui-monospace,monospace', color:heroInk2, textTransform:'uppercase', letterSpacing:1.2}}>
            {lang==='ru'?'Пятница':'Friday'} · {new Date().toLocaleDateString(lang==='ru'?'ru-RU':'en-US',{day:'numeric', month:'short'})} · {savedCount} {T.saved[lang]}
          </div>
        </div>
        <h1 style={{
          margin:0, fontFamily:"'Fraunces', serif",
          fontWeight:700, fontSize: isMobile?32:52, lineHeight:0.95, letterSpacing:-1.4,
          color:heroInk, textWrap:'balance',
        }}>
          {lang==='ru' ? <>Выбери одну. <span style={{fontStyle:'italic', fontWeight:400, color:'#e4b15c'}}>остальные подождут.</span></>
                       : <>Pick one tonight. <span style={{fontStyle:'italic', fontWeight:400, color:'#e4b15c'}}>the rest can wait.</span></>}
        </h1>

        {/* Two inputs — still equal weight, dark-styled */}
        <div style={{display:'grid', gridTemplateColumns: isMobile?'1fr':'1fr 1fr', gap: isMobile?14:20, marginTop: isMobile?20:28}}>
          <MoodB lang={lang} onPick={onPick}/>
          <QuickAddB lang={lang} movies={movies} onSave={onAdd}/>
        </div>
      </div>

      {/* Tabs */}
      <div style={{
        display:'flex', alignItems:'center', gap:6, padding: isMobile?'0 18px':'0 40px',
        borderBottom:`1px solid ${th.line}`, background:th.bg, position:'sticky', top:64, zIndex:4,
      }}>
        <TabB label={T.toWatch[lang]} count={savedCount} active={tab==='toWatch'} onClick={()=>{setTab('toWatch'); setFriendMode(false);}} th={th}/>
        <TabB label={T.watched[lang]} count={watchedCount} active={tab==='watched'} onClick={()=>{setTab('watched'); setFriendMode(false);}} th={th}/>
        <div style={{flex:1}}/>
        {tab==='watched' && watchedCount>0 && (
          <button onClick={()=>setFriendMode(!friendMode)} style={{
            border:`1px solid ${th.line}`, background: friendMode?th.plum:'transparent',
            color: friendMode?th.plumInk:th.ink2,
            padding:'7px 12px', borderRadius:999, fontSize:12, cursor:'pointer', fontWeight:500,
          }}>↗ {T.friendMode[lang]}</button>
        )}
      </div>

      {/* Body */}
      {tab==='toWatch' && (
        savedCount===0 ? <EmptyB th={th} lang={lang} isMobile={isMobile}/> :
        <RailsB th={th} lang={lang} shelves={shelves} isMobile={isMobile} onPick={onPick}/>
      )}
      {tab==='watched' && (
        friendMode
          ? <FriendViewB th={th} lang={lang} movies={movies.filter(m=>m.watched)} isMobile={isMobile}/>
          : <WatchedB th={th} lang={lang} movies={movies.filter(m=>m.watched)} isMobile={isMobile}/>
      )}
    </div>
  );
}

// ===== Hero inputs (dark treatment) =====
function MoodB({ lang, onPick }) {
  const [v,setV]=React.useState('');
  const chips = T.moodChips[lang];
  return (
    <div style={{display:'flex', flexDirection:'column', gap:10}}>
      <div style={{fontSize:10, fontFamily:'ui-monospace,monospace', color:'rgba(245,230,184,0.65)', textTransform:'uppercase', letterSpacing:1}}>
        01 · {T.mood[lang]}
      </div>
      <div style={{
        display:'flex', background:'rgba(245,230,184,0.08)', border:'1px solid rgba(245,230,184,0.22)',
        borderRadius:12, padding:4,
      }}>
        <input value={v} onChange={e=>setV(e.target.value)} placeholder={T.moodPh[lang]}
          style={{
            flex:1, background:'transparent', border:'none', outline:'none',
            color:'#f5e6b8', fontSize:15, padding:'12px 12px', fontFamily:'inherit',
            minWidth:0,
          }}/>
        <button onClick={()=>onPick(v || chips[0])} style={{
          border:'none', background:'#e4b15c', color:'#2a1830',
          padding:'0 18px', borderRadius:9, cursor:'pointer', fontSize:13, fontWeight:700,
        }}>{T.pick[lang]}</button>
      </div>
      <div style={{display:'flex', gap:6, flexWrap:'wrap'}}>
        {chips.map((c,i)=>(
          <button key={i} onClick={()=>{setV(c); onPick(c);}} style={{
            border:'1px solid rgba(245,230,184,0.22)', background:'transparent',
            color:'rgba(245,230,184,0.85)', padding:'5px 10px', borderRadius:999,
            fontSize:11.5, cursor:'pointer', fontFamily:'inherit',
          }}>{c}</button>
        ))}
      </div>
    </div>
  );
}

function QuickAddB({ lang, movies, onSave }) {
  const [url,setUrl]=React.useState('');
  const [parsed,setParsed]=React.useState(null);
  const parse = () => {
    const candidate = movies.find(m=>url.toLowerCase().includes(m.id)) || MOVIES.find(m=>m.id==='look-back') || MOVIES[0];
    const src = /instagram|reel/.test(url.toLowerCase()) ? 'instagram'
             : /t\.me|telegram/.test(url.toLowerCase()) ? 'telegram' : candidate.source;
    setParsed({...candidate, source:src});
  };
  const save = () => { if (parsed) { onSave(parsed); setParsed(null); setUrl(''); } };
  return (
    <div style={{display:'flex', flexDirection:'column', gap:10}}>
      <div style={{fontSize:10, fontFamily:'ui-monospace,monospace', color:'rgba(245,230,184,0.65)', textTransform:'uppercase', letterSpacing:1}}>
        02 · {T.quickAdd[lang]}
      </div>
      <div style={{
        display:'flex', background:'rgba(245,230,184,0.08)', border:'1px solid rgba(245,230,184,0.22)',
        borderRadius:12, padding:4,
      }}>
        <input value={url} onChange={e=>{setUrl(e.target.value); setParsed(null);}}
          onKeyDown={e=>{if(e.key==='Enter')parse();}} placeholder={T.quickAddPh[lang]}
          style={{flex:1, background:'transparent', border:'none', outline:'none', color:'#f5e6b8', fontSize:15, padding:'12px 12px', fontFamily:'inherit', minWidth:0}}/>
        <button onClick={parse} style={{
          border:'1px solid rgba(245,230,184,0.4)', background:'transparent', color:'#f5e6b8',
          padding:'0 18px', borderRadius:9, cursor:'pointer', fontSize:13, fontWeight:600,
        }}>{T.save[lang]}</button>
      </div>
      {parsed && (
        <div style={{
          display:'flex', gap:12, padding:10, borderRadius:12,
          background:'rgba(245,230,184,0.08)', border:'1px solid rgba(245,230,184,0.2)',
        }}>
          <TypoPoster movie={parsed} lang={lang} w={56} h={84}/>
          <div style={{flex:1, minWidth:0}}>
            <div style={{fontSize:9.5, fontFamily:'ui-monospace,monospace', color:'rgba(245,230,184,0.65)', letterSpacing:0.6, textTransform:'uppercase'}}>{T.quickParsed[lang]}</div>
            <div style={{fontFamily:"'Fraunces',serif", fontWeight:700, fontSize:15, color:'#f5e6b8', marginTop:3, lineHeight:1.1}}>{lang==='ru'?parsed.ru:parsed.en}</div>
            <div style={{fontSize:11, color:'rgba(245,230,184,0.6)', marginTop:2, fontFamily:'ui-monospace,monospace'}}>{parsed.dir} · {parsed.year}</div>
            <button onClick={save} style={{
              marginTop:7, border:'none', background:'#e4b15c', color:'#2a1830',
              padding:'6px 10px', borderRadius:7, cursor:'pointer', fontSize:11.5, fontWeight:700,
            }}>{T.quickKeep[lang]}</button>
          </div>
        </div>
      )}
    </div>
  );
}

function TabB({ label, count, active, onClick, th }) {
  return (
    <button onClick={onClick} style={{
      border:'none', background:'transparent', cursor:'pointer',
      padding:'16px 2px', marginRight:22, position:'relative',
      color: active?th.ink:th.ink3, fontSize:14, fontWeight:600,
      display:'flex', alignItems:'baseline', gap:6,
    }}>
      {label}
      <span style={{fontSize:11, fontFamily:'ui-monospace,monospace', color:th.ink3, fontWeight:500}}>·{count}</span>
      {active && <div style={{position:'absolute', left:0, right:0, bottom:-1, height:2, background:th.butter}}/>}
    </button>
  );
}

// ===== Rails =====
function RailsB({ th, lang, shelves, isMobile, onPick }) {
  return (
    <div style={{display:'flex', flexDirection:'column', paddingBottom:40}}>
      {shelves.map((s,idx) => (
        <RailB key={s.id} shelf={s} th={th} lang={lang} isMobile={isMobile} idx={idx} hero={s.tone==='hero'} onPick={onPick}/>
      ))}
    </div>
  );
}

function RailB({ shelf, th, lang, isMobile, idx, hero, onPick }) {
  const pad = isMobile ? 18 : 40;
  const w = hero ? (isMobile?150:200) : (isMobile?110:140);
  const h = Math.round(w*1.5);
  return (
    <div style={{paddingTop: hero?(isMobile?22:30):(isMobile?20:28), background: idx%2===1 ? th.bgAlt : 'transparent'}}>
      <div style={{display:'flex', alignItems:'baseline', justifyContent:'space-between', padding:`0 ${pad}px`, marginBottom:12}}>
        <div style={{display:'flex', alignItems:'baseline', gap:10}}>
          {hero && <span style={{width:5, height:5, borderRadius:999, background:th.butter, alignSelf:'center'}}/>}
          <h2 style={{
            margin:0, fontFamily: hero?"'Fraunces',serif":'inherit',
            fontWeight: hero?700:600, fontStyle: hero?'italic':'normal',
            fontSize: hero?(isMobile?22:28):(isMobile?14:16), letterSpacing: hero?-0.5:-0.1,
            color:th.ink, lineHeight:1,
          }}>{shelf.title}</h2>
          <span style={{fontSize:11, color:th.ink3, fontFamily:'ui-monospace,monospace'}}>{shelf.items.length}</span>
        </div>
        {shelf.items.length>4 && (
          <button style={{
            border:'none', background:'transparent', color:th.ink3,
            fontSize:12, cursor:'pointer', fontFamily:'ui-monospace,monospace',
          }}>→ {lang==='ru'?'все':'all'}</button>
        )}
      </div>
      <div style={{display:'flex', gap:10, overflowX:'auto', overflowY:'hidden', padding:`2px ${pad}px 18px`}}>
        {shelf.items.map(m => (
          <button key={m.id} onClick={()=>onPick(m,'direct')} style={{
            border:'none', background:'transparent', padding:0, cursor:'pointer', flexShrink:0,
            display:'flex', flexDirection:'column', gap:6,
          }}>
            <TypoPoster movie={m} lang={lang} w={w} h={h}/>
            {hero && (
              <div style={{width:w, textAlign:'left', paddingLeft:2}}>
                <div style={{fontSize:12.5, color:th.ink, fontWeight:600, lineHeight:1.2, textWrap:'balance'}}>{lang==='ru'?m.ru:m.en}</div>
                <div style={{fontSize:10, color:th.ink3, marginTop:2, fontFamily:'ui-monospace,monospace'}}>{m.runtime}{lang==='ru'?' мин':'m'} · ★{m.publicRating.toFixed(1)}</div>
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

// ===== Empty =====
function EmptyB({ th, lang, isMobile }) {
  const pad = isMobile ? 18 : 40;
  return (
    <div style={{padding:`${isMobile?24:32}px ${pad}px 40px`}}>
      <div style={{
        padding: isMobile?20:28, borderRadius:16, background:th.bgAlt,
        border:`1px solid ${th.line}`, display:'flex', flexDirection: isMobile?'column':'row',
        gap:20, alignItems:'center',
      }}>
        <TypoPoster movie={MOVIES.find(m=>m.id==='anora')} lang={lang} w={isMobile?120:150} h={isMobile?180:225}/>
        <div style={{flex:1}}>
          <div style={{fontSize:10, fontFamily:'ui-monospace,monospace', color:th.ink3, textTransform:'uppercase', letterSpacing:1}}>01 · {lang==='ru'?'Первая ссылка':'First link'}</div>
          <h2 style={{margin:'8px 0 0', fontFamily:"'Fraunces',serif", fontWeight:700, fontSize: isMobile?22:28, color:th.ink, lineHeight:1.05, letterSpacing:-0.4, textWrap:'balance'}}>{T.emptyTitle[lang]}</h2>
          <p style={{fontSize:14, color:th.ink2, lineHeight:1.5, margin:'10px 0 14px'}}>{T.emptySub[lang]}</p>
          <div style={{display:'flex', gap:8, flexWrap:'wrap'}}>
            {['◎ Instagram','✈ Telegram','♥ '+(lang==='ru'?'Друзья':'Friends')].map((x,i)=>(
              <span key={i} style={{fontSize:11.5, padding:'6px 10px', borderRadius:999, background:th.chipBg, color:th.ink2, fontFamily:'ui-monospace,monospace'}}>{x}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ===== Watched (default) =====
function WatchedB({ th, lang, movies, isMobile }) {
  const pad = isMobile ? 18 : 40;
  if (movies.length===0) return <div style={{padding:`20px ${pad}px`, color:th.ink3, fontSize:13}}>—</div>;
  // Grid of poster-cards with ratings overlaid
  return (
    <div style={{padding:`${isMobile?20:28}px ${pad}px 40px`, display:'grid',
      gridTemplateColumns: isMobile?'repeat(3, 1fr)':'repeat(auto-fill, minmax(160px, 1fr))', gap:14}}>
      {movies.sort((a,b)=>b.myRating-a.myRating).map(m => (
        <div key={m.id} style={{display:'flex', flexDirection:'column', gap:6, position:'relative'}}>
          <div style={{position:'relative'}}>
            <TypoPoster movie={m} lang={lang} w={isMobile?100:160} h={isMobile?150:240}/>
            <div style={{
              position:'absolute', top:6, right:6, background:'rgba(42,24,48,0.85)',
              color:'#f5e6b8', borderRadius:6, padding:'3px 6px', fontSize:10.5, fontWeight:700,
              fontFamily:'ui-monospace,monospace', backdropFilter:'blur(4px)',
            }}>{m.myRating}/10</div>
          </div>
          <div style={{fontSize: isMobile?11:13, color:th.ink, fontWeight:600, lineHeight:1.15, textWrap:'balance'}}>{lang==='ru'?m.ru:m.en}</div>
          <div style={{fontSize:10.5, color:th.ink3, fontFamily:'ui-monospace,monospace'}}>★{m.publicRating.toFixed(1)} · {m.year}</div>
        </div>
      ))}
    </div>
  );
}

// ===== Friend view (B): vertical cards, one per tap-height =====
function FriendViewB({ th, lang, movies, isMobile }) {
  const pad = isMobile ? 18 : 40;
  return (
    <div style={{padding:`${isMobile?20:28}px ${pad}px 40px`, display:'flex', flexDirection:'column', gap:10}}>
      <div style={{fontSize:11, fontFamily:'ui-monospace,monospace', color:th.ink3, letterSpacing:0.6, marginBottom:4}}>↗ {T.watchedSub[lang]}</div>
      {movies.sort((a,b)=>b.myRating-a.myRating).map(m => (
        <div key={m.id} style={{
          display:'grid', gridTemplateColumns:'80px 1fr auto', gap:14, alignItems:'center',
          padding:12, borderRadius:14, background:th.surface, border:`1px solid ${th.line}`,
        }}>
          <TypoPoster movie={m} lang={lang} w={72} h={108}/>
          <div style={{minWidth:0}}>
            <div style={{fontFamily:"'Fraunces',serif", fontWeight:700, fontSize:17, color:th.ink, lineHeight:1.1, textWrap:'balance'}}>{lang==='ru'?m.ru:m.en}</div>
            <div style={{fontSize:11.5, color:th.ink3, fontFamily:'ui-monospace,monospace', marginTop:3}}>{m.year} · {m.dir} · {m.runtime}{lang==='ru'?' мин':'m'}</div>
            <div style={{fontSize:12.5, color:th.ink2, fontStyle:'italic', marginTop:6, lineHeight:1.35}}>«{m.why[lang].replace(/^«|»$/g,'')}»</div>
          </div>
          <div style={{display:'flex', flexDirection:'column', gap:4, alignItems:'stretch'}}>
            <div style={{background:th.plum, color:th.plumInk, padding:'6px 10px', borderRadius:7, textAlign:'center', minWidth:56}}>
              <div style={{fontSize:9, opacity:0.75, fontFamily:'ui-monospace,monospace', letterSpacing:0.5}}>{T.myScore[lang].toUpperCase()}</div>
              <div style={{fontSize:15, fontWeight:700, fontFamily:"'Fraunces',serif", lineHeight:1}}>{m.myRating}</div>
            </div>
            <div style={{border:`1px solid ${th.line}`, color:th.ink2, padding:'6px 10px', borderRadius:7, textAlign:'center'}}>
              <div style={{fontSize:9, opacity:0.75, fontFamily:'ui-monospace,monospace', letterSpacing:0.5}}>{T.kp[lang]}</div>
              <div style={{fontSize:14, fontWeight:700, fontFamily:"'Fraunces',serif", lineHeight:1}}>{m.publicRating.toFixed(1)}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

Object.assign(window, { DirectionB });
