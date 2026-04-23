// Tweaks panel, Device frames, and App shell.

// ===== Frames =====
function MobileFrame({ children, label, th }) {
  return (
    <div style={{display:'flex', flexDirection:'column', gap:10, alignItems:'center'}}>
      <div style={{fontSize:11, color:'#8a7f72', fontFamily:'ui-monospace,monospace', letterSpacing:0.6, textTransform:'uppercase'}}>{label}</div>
      <div style={{
        width:390, height:780, borderRadius:46, background:'#0a0707',
        padding:10, boxShadow:'0 30px 80px -30px rgba(0,0,0,0.5), 0 0 0 1.5px rgba(0,0,0,0.15)',
        position:'relative', flexShrink:0,
      }}>
        {/* notch */}
        <div style={{position:'absolute', top:16, left:'50%', transform:'translateX(-50%)', width:110, height:30, borderRadius:999, background:'#0a0707', zIndex:10}}/>
        <div style={{width:'100%', height:'100%', borderRadius:38, overflow:'hidden', position:'relative', background:th.bg}}>
          {/* status bar spacer */}
          <div style={{position:'absolute', top:0, left:0, right:0, height:44, display:'flex', alignItems:'center', justifyContent:'space-between', padding:'0 28px', zIndex:6, color:th.ink, fontSize:13, fontWeight:600, pointerEvents:'none'}}>
            <span style={{fontVariantNumeric:'tabular-nums'}}>19:24</span>
            <span/>
            <span style={{display:'flex', gap:4, alignItems:'center', fontSize:11}}>●●●● ▰</span>
          </div>
          <div style={{position:'absolute', inset:0, paddingTop:44, overflowY:'auto', overflowX:'hidden'}}>
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}

function DesktopFrame({ children, label, th }) {
  return (
    <div style={{display:'flex', flexDirection:'column', gap:10, alignItems:'center', width:'100%'}}>
      <div style={{fontSize:11, color:'#8a7f72', fontFamily:'ui-monospace,monospace', letterSpacing:0.6, textTransform:'uppercase'}}>{label}</div>
      <div style={{
        width:'100%', maxWidth:1200, height:760, borderRadius:12, overflow:'hidden',
        boxShadow:'0 30px 80px -30px rgba(0,0,0,0.5), 0 0 0 1px rgba(0,0,0,0.12)', background:th.bg,
        display:'flex', flexDirection:'column',
      }}>
        {/* traffic lights */}
        <div style={{height:34, background:th.name==='dark'?'#1a1014':'#efe7d4', borderBottom:`1px solid ${th.line}`, display:'flex', alignItems:'center', padding:'0 14px', gap:8, flexShrink:0}}>
          {['#ff5f57','#febc2e','#28c840'].map(c=><div key={c} style={{width:11, height:11, borderRadius:999, background:c}}/>)}
          <div style={{flex:1, textAlign:'center', fontSize:11, color:th.ink3, fontFamily:'ui-monospace,monospace'}}>lentochka.app</div>
        </div>
        <div style={{flex:1, overflowY:'auto', overflowX:'hidden'}}>
          {children}
        </div>
      </div>
    </div>
  );
}

// ===== Tweaks panel =====
function TweaksPanel({ state, setState, onReset, visible, onClose }) {
  if (!visible) return null;
  const { lang, theme, data, direction, frame } = state;
  const th = THEMES.light;
  const row = (label, children) => (
    <div style={{display:'flex', flexDirection:'column', gap:6}}>
      <div style={{fontSize:10, fontFamily:'ui-monospace,monospace', color:'rgba(245,230,184,0.65)', textTransform:'uppercase', letterSpacing:0.8}}>{label}</div>
      {children}
    </div>
  );
  const seg = (opts, val, onChange) => (
    <div style={{display:'flex', gap:4, background:'rgba(245,230,184,0.08)', padding:3, borderRadius:8}}>
      {opts.map(o => (
        <button key={o.v} onClick={()=>onChange(o.v)} style={{
          flex:1, border:'none', cursor:'pointer',
          background: val===o.v ? '#e4b15c' : 'transparent',
          color: val===o.v ? '#2a1830' : '#f5e6b8',
          padding:'7px 8px', borderRadius:6, fontSize:12, fontWeight:600,
          fontFamily:'inherit', whiteSpace:'nowrap',
        }}>{o.l}</button>
      ))}
    </div>
  );
  return (
    <div style={{
      position:'fixed', right:20, bottom:20, width:280, zIndex:1000,
      background:'#2a1830', color:'#f5e6b8', borderRadius:14, padding:16,
      boxShadow:'0 30px 60px -20px rgba(0,0,0,0.6), 0 0 0 1px rgba(245,230,184,0.12)',
      display:'flex', flexDirection:'column', gap:12,
      fontFamily:'-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif',
    }}>
      <div style={{display:'flex', alignItems:'center', justifyContent:'space-between'}}>
        <div style={{fontFamily:"'Fraunces', serif", fontWeight:700, fontSize:15, letterSpacing:-0.2}}>Tweaks</div>
        <button onClick={onClose} style={{border:'none', background:'transparent', color:'rgba(245,230,184,0.6)', cursor:'pointer', fontSize:18, lineHeight:1, padding:0}}>×</button>
      </div>
      {row('Direction', seg([{v:'A',l:'A · Notes'},{v:'B',l:'B · Rails'}], direction, v=>setState({...state, direction:v})))}
      {row('Language',  seg([{v:'ru',l:'RU'},{v:'en',l:'EN'}], lang, v=>setState({...state, lang:v})))}
      {row('Theme',     seg([{v:'light',l:'Light'},{v:'dark',l:'Dark'}], theme, v=>setState({...state, theme:v})))}
      {row('Data',      seg([{v:'empty',l:'Empty'},{v:'three',l:'3'},{v:'many',l:'20+'}], data, v=>setState({...state, data:v})))}
      {row('Frame',     seg([{v:'mobile',l:'Mobile'},{v:'desktop',l:'Desktop'},{v:'both',l:'Both'}], frame, v=>setState({...state, frame:v})))}
      <button onClick={onReset} style={{
        border:'1px solid rgba(245,230,184,0.22)', background:'transparent', color:'rgba(245,230,184,0.8)',
        padding:'7px', borderRadius:8, fontSize:11.5, cursor:'pointer', fontFamily:'inherit', marginTop:4,
      }}>↺ Reset data</button>
    </div>
  );
}

// ===== App shell =====
function App() {
  // persisted state
  const load = () => {
    try { return JSON.parse(localStorage.getItem('lentochka-state')||'null'); } catch(e){ return null; }
  };
  const initial = load() || {
    lang:'ru', theme:'light', data:'many', direction:'A', frame:'mobile', tweaksOpen:true,
  };
  const [state, setState] = React.useState(initial);
  React.useEffect(() => { localStorage.setItem('lentochka-state', JSON.stringify(state)); }, [state]);

  // data state: 'empty' (no movies), 'three' (first 3), 'many' (all)
  const [addedIds, setAddedIds] = React.useState([]); // quick-add during session
  const [removedIds, setRemovedIds] = React.useState([]);

  const baseMovies = React.useMemo(() => {
    if (state.data==='empty') return [];
    if (state.data==='three') return MOVIES.slice(0,3).map(m=>({...m, watched:false}));
    return MOVIES;
  }, [state.data]);

  const activeMovies = React.useMemo(() => {
    let ms = [...baseMovies];
    // sessional additions
    addedIds.forEach(id => {
      if (!ms.find(m=>m.id===id)) {
        const src = MOVIES.find(m=>m.id===id);
        if (src) ms = [{...src, watched:false, savedDaysAgo:0}, ...ms];
      }
    });
    return ms.filter(m => !removedIds.includes(m.id));
  }, [baseMovies, addedIds, removedIds]);

  const resetSession = () => { setAddedIds([]); setRemovedIds([]); };

  // Pick-reveal state
  const [reveal, setReveal] = React.useState(null); // {movie, mood} | null
  const pickFromMood = (mood) => {
    const pool = activeMovies.filter(m=>!m.watched);
    if (pool.length===0) return;
    // simple mood → movie mapping
    const mLower = (mood||'').toLowerCase();
    let choice;
    if (/плак|cry/.test(mLower)) choice = pool.find(m=>m.id==='aftersun') || pool.find(m=>m.id==='past-lives');
    else if (/класс|classic/.test(mLower)) choice = pool.find(m=>m.id==='moonlight') || pool.find(m=>m.id==='portrait');
    else if (/друз|friend/.test(mLower)) choice = pool.find(m=>m.id==='grand-budapest') || pool.find(m=>m.id==='paddington-2');
    else if (/роман|romant/.test(mLower)) choice = pool.find(m=>m.id==='past-lives') || pool.find(m=>m.id==='portrait');
    else if (/коротк|short|90/.test(mLower)) choice = pool.filter(m=>m.runtime<=100)[0];
    else if (/стран|weird/.test(mLower)) choice = pool.find(m=>m.id==='lobster') || pool.find(m=>m.id==='poor-things');
    else if (/пиц|cozy|pizza|ламп/.test(mLower)) choice = pool.find(m=>m.id==='paddington-2') || pool.find(m=>m.id==='chef');
    choice = choice || pool[Math.floor(Math.random()*pool.length)];
    setReveal({ movie: choice, mood });
  };
  const pickDirect = (m) => setReveal({ movie:m, mood:null });
  const pickAgain = () => {
    const pool = activeMovies.filter(m=>!m.watched && m.id !== reveal?.movie?.id);
    if (pool.length===0) return;
    setReveal({ movie: pool[Math.floor(Math.random()*pool.length)], mood: reveal?.mood });
  };
  const onAddMovie = (parsed) => {
    setAddedIds(a => a.includes(parsed.id) ? a : [parsed.id, ...a]);
    setRemovedIds(r => r.filter(id=>id!==parsed.id));
  };
  const onAddClick = () => {
    // scroll to quick-add input? Just bounce-highlight; we'll emulate by picking a fresh movie
    const next = MOVIES.find(m => !activeMovies.find(a=>a.id===m.id));
    if (next) onAddMovie(next);
  };

  const th = THEMES[state.theme];

  const onPick = (arg, kind='mood') => {
    if (kind==='direct') pickDirect(arg);
    else pickFromMood(arg);
  };

  const Direction = state.direction==='A' ? DirectionA : DirectionB;

  // Layout: shows mobile, desktop, or both
  const frames = state.frame==='both' ? ['mobile','desktop'] : [state.frame];

  return (
    <>
      <style>{`
        @keyframes lfade { from { opacity:0 } to { opacity:1 } }
        @keyframes lup { from { opacity:0; transform:translateY(10px) scale(0.98) } to { opacity:1; transform:translateY(0) scale(1) } }
        ::-webkit-scrollbar { height:8px; width:8px; }
        ::-webkit-scrollbar-thumb { background:rgba(0,0,0,0.15); border-radius:999px; }
        ::-webkit-scrollbar-track { background:transparent; }
        html, body { background:#e8dfce; }
      `}</style>

      <div style={{
        minHeight:'100vh', padding:'28px 28px 160px',
        display:'flex', flexDirection:'column', alignItems:'center', gap:24,
        background:'linear-gradient(180deg, #f0e7d4 0%, #e3d6b7 100%)',
      }}>
        <div style={{maxWidth:1400, width:'100%', display:'flex', justifyContent:'space-between', alignItems:'baseline'}}>
          <div>
            <div style={{fontFamily:"'Fraunces', serif", fontWeight:700, fontSize:22, color:'#2a1830', letterSpacing:-0.4}}>
              Lentochka · Home bakeoff
            </div>
            <div style={{fontSize:12, fontFamily:'ui-monospace,monospace', color:'#8a7f72', marginTop:4, letterSpacing:0.3}}>
              Direction {state.direction} · {state.lang.toUpperCase()} · {state.theme} · {state.data} · {state.frame}
            </div>
          </div>
          {!state.tweaksOpen && (
            <button onClick={()=>setState({...state, tweaksOpen:true})} style={{
              border:'1px solid rgba(42,24,48,0.2)', background:'#2a1830', color:'#f5e6b8',
              padding:'8px 14px', borderRadius:999, fontSize:12, fontWeight:600, cursor:'pointer',
            }}>✦ Tweaks</button>
          )}
        </div>

        <div style={{
          display:'flex', gap:32, flexWrap:'wrap', justifyContent:'center',
          alignItems:'flex-start', width:'100%', maxWidth:1400,
        }}>
          {/* Top bar lives inside each frame as sticky */}
          {frames.map(f => (
            <div key={f} style={{
              width: f==='desktop' ? '100%' : 'auto',
              maxWidth: f==='desktop' ? 1200 : undefined,
              display:'flex', justifyContent:'center',
            }}>
              {f==='mobile' ? (
                <MobileFrame th={th} label={'mobile · 390×844'}>
                  <FrameContent th={th} state={state} activeMovies={activeMovies} Direction={Direction} setState={setState} onAddClick={onAddClick} onPick={onPick} onAdd={onAddMovie}/>
                </MobileFrame>
              ) : (
                <DesktopFrame th={th} label={'desktop · 1200×760'}>
                  <FrameContent th={th} state={state} activeMovies={activeMovies} Direction={Direction} setState={setState} onAddClick={onAddClick} onPick={onPick} onAdd={onAddMovie}/>
                </DesktopFrame>
              )}
            </div>
          ))}
        </div>

      </div>

      <TweaksPanel
        state={state}
        setState={setState}
        onReset={resetSession}
        visible={state.tweaksOpen!==false}
        onClose={()=>setState({...state, tweaksOpen:false})}
      />
    </>
  );
}

function FrameContent({ th, state, activeMovies, Direction, setState, onAddClick, onPick, onAdd }) {
  const [reveal, setReveal] = React.useState(null);
  const handlePick = (arg, kind='mood') => {
    if (kind==='direct') setReveal({ movie:arg, mood:null });
    else {
      const pool = activeMovies.filter(m=>!m.watched);
      if (pool.length===0) return;
      const mLower = (arg||'').toLowerCase();
      let choice;
      if (/плак|cry/.test(mLower)) choice = pool.find(m=>m.id==='aftersun') || pool.find(m=>m.id==='past-lives');
      else if (/класс|classic/.test(mLower)) choice = pool.find(m=>m.id==='moonlight') || pool.find(m=>m.id==='portrait');
      else if (/друз|friend/.test(mLower)) choice = pool.find(m=>m.id==='grand-budapest') || pool.find(m=>m.id==='paddington-2');
      else if (/роман|romant/.test(mLower)) choice = pool.find(m=>m.id==='past-lives') || pool.find(m=>m.id==='portrait');
      else if (/коротк|short|90/.test(mLower)) choice = pool.filter(m=>m.runtime<=100)[0];
      else if (/стран|weird/.test(mLower)) choice = pool.find(m=>m.id==='lobster') || pool.find(m=>m.id==='poor-things');
      else if (/пиц|cozy|pizza|ламп/.test(mLower)) choice = pool.find(m=>m.id==='paddington-2') || pool.find(m=>m.id==='chef');
      choice = choice || pool[Math.floor(Math.random()*pool.length)];
      setReveal({ movie: choice, mood: arg });
    }
  };
  const pickAgain = () => {
    const pool = activeMovies.filter(m=>!m.watched && m.id !== reveal?.movie?.id);
    if (pool.length) setReveal({ movie: pool[Math.floor(Math.random()*pool.length)], mood: reveal?.mood });
  };
  return (
    <div style={{position:'relative', minHeight:'100%'}}>
      <TopBar th={th} lang={state.lang}
        setLang={v=>setState({...state, lang:v})}
        theme={state.theme} setTheme={v=>setState({...state, theme:v})}
        onAdd={onAddClick}
        compact={true}/>
      <Direction th={th} lang={state.lang} movies={activeMovies} frame={state.frame==='both'?'mobile':state.frame} onAdd={onAdd} onPick={handlePick}/>
      <PickReveal th={th} lang={state.lang} movie={reveal?.movie} mood={reveal?.mood} onClose={()=>setReveal(null)} onAgain={pickAgain}/>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
