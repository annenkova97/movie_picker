// Direction A — "Заметки / Notes-editorial"
// Warm paper surfaces, magazine-like rhythm, big serif headings, shelves with spacing and index numbers.

function DirectionA({ th, lang, movies, frame, onAdd, onPick }) {
  const shelves = buildShelves(movies, lang);
  const [tab, setTab] = React.useState('toWatch');
  const [friendMode, setFriendMode] = React.useState(false);
  const isMobile = frame==='mobile';

  const savedCount = movies.filter(m=>!m.watched).length;
  const watchedCount = movies.filter(m=>m.watched).length;

  return (
    <div style={{background:th.bg, minHeight:'100%', color:th.ink, fontFamily:'-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif'}}>
      {/* Hero */}
      <div style={{padding: isMobile ? '18px 18px 24px' : '28px 40px 40px', display:'flex', flexDirection:'column', gap: isMobile?18:24}}>
        <div style={{display:'flex', alignItems:'flex-end', justifyContent:'space-between', gap:20, flexWrap:'wrap'}}>
          <div style={{flex:1, minWidth:240}}>
            <div style={{fontSize:11, fontFamily:'ui-monospace,monospace', color:th.ink3, textTransform:'uppercase', letterSpacing:1.2, marginBottom:8}}>
              {new Date().toLocaleDateString(lang==='ru'?'ru-RU':'en-US', {weekday:'long', day:'numeric', month:'long'})} · {savedCount} {T.saved[lang]}
            </div>
            <h1 style={{
              fontFamily:"'Fraunces', 'Playfair Display', Georgia, serif",
              fontWeight:400, fontStyle:'italic',
              fontSize: isMobile?30:44, lineHeight:1.0, letterSpacing:-1,
              margin:0, color:th.ink, textWrap:'balance',
            }}>
              {lang==='ru' ? <>что посмотрим <span style={{fontStyle:'normal', fontWeight:700}}>сегодня</span>?</> :
                             <>what’s on <span style={{fontStyle:'normal', fontWeight:700}}>tonight</span>?</>}
            </h1>
          </div>
        </div>

        {/* Two equal hero inputs */}
        <div style={{display:'grid', gridTemplateColumns: isMobile?'1fr':'1fr 1fr', gap: isMobile?16:24}}>
          <MoodPicker th={th} lang={lang} onPick={onPick}/>
          <QuickAdd th={th} lang={lang} movies={movies} onSave={onAdd}/>
        </div>

        {/* Tabs */}
        <div style={{display:'flex', alignItems:'center', gap:4, borderBottom:`1px solid ${th.line}`, marginTop:4}}>
          <TabA label={T.toWatch[lang]} count={savedCount} active={tab==='toWatch'} onClick={()=>{setTab('toWatch'); setFriendMode(false);}} th={th}/>
          <TabA label={T.watched[lang]} count={watchedCount} active={tab==='watched'} onClick={()=>{setTab('watched'); setFriendMode(false);}} th={th}/>
          <div style={{flex:1}}/>
          {tab==='watched' && watchedCount>0 && (
            <button onClick={()=>setFriendMode(!friendMode)} style={{
              border:`1px solid ${th.line}`, background: friendMode?th.plum:'transparent',
              color: friendMode?th.plumInk:th.ink2,
              padding:'6px 12px', borderRadius:999, fontSize:12, cursor:'pointer', fontWeight:500,
              marginBottom:8,
            }}>↗ {T.friendMode[lang]}</button>
          )}
        </div>
      </div>

      {/* Body */}
      {tab==='toWatch' && (
        savedCount===0 ? <EmptyA th={th} lang={lang} isMobile={isMobile}/> :
        <ShelvesA th={th} lang={lang} shelves={shelves} isMobile={isMobile} onPick={onPick}/>
      )}
      {tab==='watched' && (
        friendMode
          ? <FriendViewA th={th} lang={lang} movies={movies.filter(m=>m.watched)} isMobile={isMobile}/>
          : <WatchedA th={th} lang={lang} movies={movies.filter(m=>m.watched)} isMobile={isMobile}/>
      )}
    </div>
  );
}

function TabA({ label, count, active, onClick, th }) {
  return (
    <button onClick={onClick} style={{
      border:'none', background:'transparent', cursor:'pointer',
      padding:'14px 6px', marginRight:20, position:'relative',
      color: active?th.ink:th.ink3, fontSize:15, fontWeight:600,
      fontFamily:"'Fraunces', serif", letterSpacing:-0.2,
      display:'flex', alignItems:'baseline', gap:8,
    }}>
      {label}
      <span style={{fontSize:11, fontFamily:'ui-monospace,monospace', color:th.ink3, fontWeight:500}}>{count}</span>
      {active && <div style={{position:'absolute', left:0, right:0, bottom:-1, height:2, background:th.plum}}/>}
    </button>
  );
}

// ===== Shelves =====
function ShelvesA({ th, lang, shelves, isMobile, onPick }) {
  return (
    <div style={{display:'flex', flexDirection:'column', gap: isMobile?28:36, paddingBottom:40}}>
      {shelves.map((s, idx) => (
        <ShelfA key={s.id} shelf={s} th={th} lang={lang} isMobile={isMobile} idx={idx} onPick={onPick} hero={s.tone==='hero'}/>
      ))}
    </div>
  );
}

function ShelfA({ shelf, th, lang, isMobile, idx, onPick, hero }) {
  const pad = isMobile ? 18 : 40;
  return (
    <div>
      <div style={{display:'flex', alignItems:'baseline', gap:12, padding:`0 ${pad}px`, marginBottom:14}}>
        <span style={{fontFamily:'ui-monospace,monospace', fontSize:11, color:th.ink3, letterSpacing:0.4}}>
          {String(idx+1).padStart(2,'0')}
        </span>
        <h2 style={{
          margin:0, fontFamily:"'Fraunces', serif",
          fontWeight: hero?700:600, fontSize: hero?(isMobile?22:28):(isMobile?17:20),
          color:th.ink, letterSpacing:-0.4, lineHeight:1,
        }}>{shelf.title}</h2>
        <span style={{fontSize:12, color:th.ink3, fontFamily:'ui-monospace,monospace'}}>({shelf.items.length})</span>
      </div>
      <div style={{
        display:'flex', gap: hero? (isMobile?14:18):12, overflowX:'auto', overflowY:'hidden',
        padding: `4px ${pad}px 14px`,
        scrollbarWidth:'thin',
      }}>
        {shelf.items.map(m => (
          <PosterCardA key={m.id} m={m} th={th} lang={lang} hero={hero}
            w={hero?(isMobile?140:170):(isMobile?110:130)}
            h={hero?(isMobile?210:255):(isMobile?165:195)}
            onClick={()=>onPick(m, 'direct')}/>
        ))}
      </div>
    </div>
  );
}

function PosterCardA({ m, th, lang, hero, w, h, onClick }) {
  const src = { telegram:'✈ Telegram', instagram:'◎ Instagram', friends:'♥ '+(lang==='ru'?'Друзья':'Friends') };
  return (
    <button onClick={onClick} style={{
      border:'none', background:'transparent', padding:0, cursor:'pointer',
      display:'flex', flexDirection:'column', gap:8, width:w, textAlign:'left',
      flexShrink:0,
    }}>
      <TypoPoster movie={m} lang={lang} w={w} h={h}/>
      {hero && (
        <div style={{paddingLeft:2}}>
          <div style={{fontFamily:"'Fraunces',serif", fontWeight:600, fontSize:13.5, color:th.ink, lineHeight:1.15, textWrap:'balance'}}>{lang==='ru'?m.ru:m.en}</div>
          <div style={{fontSize:10.5, color:th.ink3, marginTop:2, fontFamily:'ui-monospace,monospace'}}>{src[m.source]} · {m.runtime}{T.min[lang]==='мин'?'':'\''}</div>
        </div>
      )}
    </button>
  );
}

// ===== 3-items A (uses its own layout, avoids feeling sparse) =====
// Handled via ShelvesA with only "Скорее всего сегодня" shelf (our builder filters <2 automatically,
// but 3 items will still show as single shelf). We'll override for exactly 3 state below.

// ===== Empty state =====
function EmptyA({ th, lang, isMobile }) {
  const pad = isMobile ? 18 : 40;
  return (
    <div style={{padding:`0 ${pad}px 40px`, display:'flex', flexDirection:'column', gap:16}}>
      <div style={{
        padding: isMobile? '24px 18px' : '32px',
        borderRadius:20, background:th.bgAlt, border:`1px solid ${th.line}`,
        display:'flex', flexDirection: isMobile?'column':'row', gap:24, alignItems:'center',
      }}>
        <div style={{flex:1}}>
          <div style={{fontSize:10, fontFamily:'ui-monospace,monospace', color:th.ink3, textTransform:'uppercase', letterSpacing:1, marginBottom:8}}>
            ✦ {lang==='ru'?'С чего начать':'Where to start'}
          </div>
          <h2 style={{
            margin:0, fontFamily:"'Fraunces',serif", fontStyle:'italic',
            fontSize: isMobile?22:30, lineHeight:1.05, color:th.ink, letterSpacing:-0.6, textWrap:'balance',
          }}>{T.emptyTitle[lang]}</h2>
          <p style={{fontSize:14, color:th.ink2, lineHeight:1.5, margin:'12px 0 0', maxWidth:420}}>{T.emptySub[lang]}</p>
        </div>
        <EmptyDemo th={th} lang={lang}/>
      </div>

      <div style={{display:'flex', gap:12, flexWrap:'wrap'}}>
        {['instagram','telegram','friends'].map(s => (
          <div key={s} style={{
            flex:'1 1 160px', padding:'14px 16px', background:th.surface, borderRadius:12,
            border:`1px solid ${th.line}`, fontSize:13, color:th.ink2,
          }}>
            <div style={{fontSize:10, fontFamily:'ui-monospace,monospace', color:th.ink3, letterSpacing:0.6, marginBottom:4}}>01 · 02 · 03</div>
            <div style={{fontFamily:"'Fraunces',serif", fontWeight:600, color:th.ink}}>{T['source_'+s][lang]}</div>
            <div style={{fontSize:12, color:th.ink3, marginTop:3}}>{s==='instagram'?(lang==='ru'?'Reel → автопарсинг названий':'Reel → auto-parse titles'):s==='telegram'?(lang==='ru'?'Ссылка → постер + описание':'Link → poster + details'):(lang==='ru'?'Фото → распознаём':'Photo → we recognise it')}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ===== Watched list (default) =====
function WatchedA({ th, lang, movies, isMobile }) {
  const pad = isMobile ? 18 : 40;
  if (movies.length===0) return (
    <div style={{padding:`0 ${pad}px 40px`, color:th.ink3, fontSize:13}}>—</div>
  );
  return (
    <div style={{padding:`0 ${pad}px 40px`, display:'flex', flexDirection:'column', gap:2}}>
      {movies.map((m,i) => (
        <div key={m.id} style={{
          display:'grid', gridTemplateColumns: isMobile?'48px 1fr auto':'60px 1fr 90px 90px',
          gap:14, alignItems:'center',
          padding:'14px 0', borderBottom: i<movies.length-1 ? `1px solid ${th.line}`:'none',
        }}>
          <TypoPoster movie={m} lang={lang} w={isMobile?44:56} h={isMobile?66:84}/>
          <div style={{minWidth:0}}>
            <div style={{fontFamily:"'Fraunces',serif", fontWeight:600, fontSize:15, color:th.ink, lineHeight:1.15, textWrap:'balance'}}>{lang==='ru'?m.ru:m.en}</div>
            <div style={{fontSize:11.5, color:th.ink3, marginTop:3, fontFamily:'ui-monospace,monospace'}}>{m.year} · {m.dir}</div>
          </div>
          <RatingPair th={th} mine={m.myRating} pub={m.publicRating} lang={lang} compact={isMobile}/>
          {!isMobile && (
            <div style={{fontSize:12, color:th.ink2, fontStyle:'italic', textAlign:'right'}}>«{m.why[lang].replace(/^«|»$/g,'')}»</div>
          )}
        </div>
      ))}
    </div>
  );
}

function RatingPair({ th, mine, pub, lang, compact }) {
  return (
    <div style={{display:'flex', gap: compact?6:10, alignItems:'center', justifyContent: compact?'flex-end':'flex-start'}}>
      <div style={{display:'flex', flexDirection:'column', alignItems:'center', padding:'6px 9px', borderRadius:8, background:th.plum, color:th.plumInk, minWidth:40}}>
        <div style={{fontSize:9, letterSpacing:0.6, opacity:0.8, fontFamily:'ui-monospace,monospace'}}>{T.myScore[lang].toUpperCase()}</div>
        <div style={{fontSize:15, fontWeight:700, fontFamily:"'Fraunces',serif"}}>{mine}</div>
      </div>
      <div style={{display:'flex', flexDirection:'column', alignItems:'center', padding:'6px 9px', borderRadius:8, border:`1px solid ${th.line}`, color:th.ink2, minWidth:40}}>
        <div style={{fontSize:9, letterSpacing:0.6, opacity:0.8, fontFamily:'ui-monospace,monospace'}}>{T.kp[lang]}</div>
        <div style={{fontSize:15, fontWeight:700, fontFamily:"'Fraunces',serif"}}>{pub.toFixed(1)}</div>
      </div>
    </div>
  );
}

// ===== Friend mode — phone-handoff friendly =====
function FriendViewA({ th, lang, movies, isMobile }) {
  const pad = isMobile ? 18 : 40;
  return (
    <div style={{padding:`0 ${pad}px 40px`, display:'flex', flexDirection:'column', gap:14}}>
      <div style={{fontSize:11, fontFamily:'ui-monospace,monospace', color:th.ink3, letterSpacing:0.6}}>↗ {T.watchedSub[lang]}</div>
      <div style={{display:'grid', gridTemplateColumns: isMobile?'1fr':'1fr 1fr', gap:12}}>
        {movies.sort((a,b)=>b.myRating-a.myRating).map(m => (
          <div key={m.id} style={{
            display:'flex', gap:14, padding:14, borderRadius:14, background:th.surface,
            border:`1px solid ${th.line}`, alignItems:'center',
          }}>
            <TypoPoster movie={m} lang={lang} w={60} h={90}/>
            <div style={{flex:1, minWidth:0}}>
              <div style={{fontFamily:"'Fraunces',serif", fontWeight:700, fontSize:16, color:th.ink, lineHeight:1.1, textWrap:'balance'}}>{lang==='ru'?m.ru:m.en}</div>
              <div style={{fontSize:11.5, color:th.ink3, marginTop:3, fontFamily:'ui-monospace,monospace'}}>{m.year} · {m.dir}</div>
              <div style={{fontSize:12, color:th.ink2, marginTop:6, fontStyle:'italic', lineHeight:1.35}}>«{m.why[lang].replace(/^«|»$/g,'')}»</div>
            </div>
            <RatingPair th={th} mine={m.myRating} pub={m.publicRating} lang={lang} compact/>
          </div>
        ))}
      </div>
    </div>
  );
}

Object.assign(window, { DirectionA });
