'use client';

import { useEffect, useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useJobs } from '@/hooks/useJobs';
import { useLiveJob } from '@/hooks/useLiveJob';
import { STAGES, activeStage, nodeStates } from '@/lib/stages';

const PERSONAS = ['CIO', 'CTO', 'CFO', 'COO', 'CISO', 'CPO'];
const arr = (x: any): any[] => (Array.isArray(x) ? x : []);
const initials = (name: string) => (name || '').split(' ').filter(Boolean).slice(0, 2).map((p) => p[0]).join('').toUpperCase() || '··';

interface Contact { persona: string; name: string; title: string; email: string; phone: string; linkedin: string; about: string; }

export default function JobView() {
  const { jobId } = useParams<{ jobId: string }>();
  const router = useRouter();
  const { getJob } = useJobs();
  const { status, log } = useLiveJob(jobId);
  const [sel, setSel] = useState(0);

  const meta = getJob(jobId);
  const st = status?.status || meta?.status || 'pending';
  const progress = status?.progress ?? meta?.progress ?? 0;
  const result: any = status?.result || meta?.result || {};
  const company = result.company_name || meta?.companyName || 'Job';
  const domain = result.domain || meta?.domain || '';
  const done = st === 'completed';
  const failed = st === 'failed';
  const act = activeStage(progress, st);
  const states = nodeStates(progress, st);
  const apiCost = status?.api_cost || result.api_cost;

  // Live elapsed clock — ticks every second while the job is in flight so the
  // header timer (and anything else keyed off `now`) updates live, instead of
  // freezing until the job completes. Stops ticking once done/failed.
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (done || failed) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [done, failed]);

  const elapsedLabel = useMemo(() => {
    const start = meta?.createdAt ? new Date(meta.createdAt).getTime() : now;
    const end = done || failed ? (meta?.completedAt ? new Date(meta.completedAt).getTime() : now) : now;
    const s = Math.max(0, Math.floor((end - start) / 1000));
    return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
  }, [meta, done, failed, now]);

  // ---- contacts (flatten slide_contacts in persona order) ----
  const contacts: Contact[] = useMemo(() => {
    const sc = result.slide_contacts || result.contact_catalogue || {};
    const out: Contact[] = [];
    PERSONAS.forEach((p) => arr(sc[p]).forEach((c: any) => {
      if (c?.is_sentinel) return;
      out.push({
        persona: p, name: c.name || '', title: c.title || '',
        email: c.email || '', phone: c.phone || c.direct_phone || c.mobile_phone || '',
        linkedin: c.linkedin_url || '',
        about: c.about || `${c.name} is the ${p} contact at ${company}${c.title ? ` (${c.title})` : ''}.`,
      });
    }));
    return out;
  }, [result, company]);
  const cur = contacts[Math.min(sel, Math.max(0, contacts.length - 1))];

  const scrollTo = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });

  // ---- defensive section data ----
  const segments = arr(result.customer_segments);
  const products = arr(result.products);
  const technologies = arr(result.technologies);
  const competitors = arr(result.competitors);
  const geo = arr(result.geographic_reach);
  // ---- Buying signals: real shape is buying_signals.intentTopics (string[]) ----
  const intent = arr(
    result.buying_signals?.intentTopics
    || result.buying_signals?.intent_topics
    || result.buying_signals?.intentTopicsDetailed?.map((t: any) => t?.topic || t)
    || result.buying_signals?.intent_topics_detailed?.map((t: any) => t?.topic || t)
  );

  // ---- News intelligence: real shape is keyInsights (string[]) + category
  // strings (executiveChanges / funding / partnerships / expansions). Normalise
  // everything into {dt?, hl} cards; fall back to legacy article arrays. ----
  const news = useMemo(() => {
    const ni = result.news_intelligence || {};
    const out: { dt?: string; hl: string }[] = [];
    const blank = (v: any) => !v || typeof v !== 'string' || !v.trim()
      || /^(none|n\/?a|no\s|not\s|unknown|—)/i.test(v.trim());
    arr(ni.keyInsights).forEach((s: any) => {
      const hl = typeof s === 'string' ? s : (s?.title || s?.headline || s?.summary || '');
      if (hl) out.push({ hl });
    });
    ([['Exec change', 'executiveChanges'], ['Funding', 'funding'],
      ['Partnership', 'partnerships'], ['Expansion', 'expansions']] as [string, string][])
      .forEach(([label, key]) => { if (!blank(ni[key])) out.push({ dt: label, hl: ni[key] }); });
    if (!out.length) {
      arr(ni.articles || ni.news || result.news_data).forEach((n: any) =>
        out.push({ dt: (n?.date || n?.published || '').toString().slice(0, 10) || undefined, hl: n?.title || n?.headline || n?.summary || String(n) }));
    }
    return out;
  }, [result]);

  // ---- Opportunity themes: real shape is opportunity_themes.pain_points
  // (long description strings). Fall back to sales_opportunities / solution areas. ----
  const opp = result.opportunity_themes || {};
  const themes = arr(opp.pain_points).length ? arr(opp.pain_points)
    : arr(opp.themes || opp.sales_opportunities || opp.recommended_solution_areas);

  // ---- Recommended sales program: sales_program carries intentLevel/Score and
  // a (frequently empty) strategyText. The actionable "steps" live in the
  // opportunity themes' recommended solution areas / sales opportunities. ----
  const sp = result.sales_program || {};
  const intentLevel = sp.intentLevel || sp.intent_level;
  const intentScore = sp.intentScore || sp.intent_score;
  const strategyText = (sp.strategyText || sp.strategy || '').toString().trim();
  const programSteps = arr(sp.steps || sp.recommended_next_steps);
  const solutionAreas = arr(opp.recommended_solution_areas || opp.sales_opportunities);
  const hasProgram = !!(strategyText || programSteps.length || solutionAreas.length || intentLevel);

  const revenue = result.annual_revenue || result.revenue || result.revenue_range;
  const itSpend = result.executive_snapshot?.estimatedITSpend
    || result.validated_data?.estimated_it_spend
    || result.executive_snapshot?.estimated_it_spend
    || result.estimated_it_spend;

  const awaiting = (label: string) => (
    <>
      <div className="await"><span className="d" /> {label}</div>
      <div className="skel" style={{ width: '88%' }} /><div className="skel" style={{ width: '70%' }} />
    </>
  );

  return (
    <>
      <div className="jobhead">
        <a className="back" onClick={() => router.push('/dashboard/jobs')}>← Queue</a>
        <div><h2>{company}</h2><div className="dom">{domain}{meta?.sellerName ? ` · ${meta.sellerName}` : ''}</div></div>
        <div className="right">
          <span className={'badge ' + (done ? 'done' : failed ? 'fail' : 'run')} style={{ fontSize: 11, padding: '6px 11px' }}>
            <span className="d" />{done ? 'COMPLETE' : failed ? 'FAILED' : 'LIVE'}
          </span>
          <div className="stat">stage<b>{done ? '9' : act + 1} / 9</b></div>
          <div className="stat">elapsed<b>{elapsedLabel}</b></div>
          <div className="stat">api cost<b className="hp">${(apiCost?.total_usd ?? 0).toFixed(2)}</b></div>
          {result.slideshow_url
            ? <a className="hbtn prime" href={result.slideshow_url} target="_blank" rel="noreferrer">▸ Slideshow</a>
            : <a className="hbtn prime disabled">▸ Slideshow</a>}
          <Link className={'hbtn' + (done ? '' : ' disabled')} href={`/dashboard/jobs/${jobId}/debug`}>⚙ Debug</Link>
        </div>
      </div>

      {/* flowchart */}
      <div className="panel"><div className="ph"><span className="eye" /><span className="k">Pipeline</span><h3>Live execution</h3>
        <span className="n">{done ? 'complete · 9/9' : failed ? 'failed' : `running · stage ${act + 1}/9`}</span></div>
        <div className="flow"><div className="flowrow">
          {STAGES.map((s, i) => (
            <div key={i} style={{ display: 'contents' }}>
              {i > 0 && <div className={'edge ' + (states[i] === 'done' ? 'done' : (states[i] === 'act' ? 'flow-anim' : ''))} />}
              <div className={'node ' + states[i]}>
                <div className="box"><div className="ring" />
                  <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round"><path d={s.icon} /></svg>
                </div>
                <div className="lab">{s.label}</div>
                <div className="ms">{states[i] === 'done' ? '✓' : states[i] === 'act' ? 'running' : states[i] === 'fail' ? 'failed' : 'queued'}</div>
              </div>
            </div>
          ))}
        </div></div>
      </div>

      <div className="subnav">
        {[['g-company', 'Company'], ['g-people', 'People'], ['g-signals', 'Signals & News'], ['g-strategy', 'Strategy'], ['g-tech', 'Technographics'], ['g-trace', 'Trace & cost']]
          .map(([id, label]) => <a key={id} onClick={() => scrollTo(id)}>{label}</a>)}
      </div>

      {/* COMPANY */}
      <div className="group" id="g-company">
        <div className="grouphead"><div className="gi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}><path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6" /></svg></div><h4>Company</h4><span className="gn">firmographics</span></div>
        <div className="grid2">
          <div className="panel"><div className="ph"><span className="eye" /><span className="k">01</span><h3>Executive snapshot</h3></div><div className="pb"><div className="kv">
            <div className="c"><div className="l">Account</div><div className="v">{result.company_type || '—'}</div></div>
            <div className="c"><div className="l">Industry</div><div className="v">{result.industry || '—'}</div></div>
            <div className="c"><div className="l">Revenue</div><div className="v mono">{revenue || '—'}</div></div>
            <div className="c"><div className="l">Employees</div><div className="v mono">{result.employee_count || result.employees_range || '—'}</div></div>
            <div className="c"><div className="l">IT spend</div><div className="v mono">{itSpend || '—'}</div></div>
            <div className="c"><div className="l">HQ</div><div className="v">{result.headquarters || '—'}</div></div>
          </div></div></div>
          <div className="panel"><div className="ph"><span className="eye" /><span className="k">08·09·10</span><h3>Profile</h3></div><div className="pb">
            <div className="chiprow"><span className="rl">Segments</span><span className="rv">{segments.length ? segments.map((s, i) => <span key={i} className="pill">{s}</span>) : <span className="await"><span className="d" />awaiting</span>}</span></div>
            <div className="chiprow"><span className="rl">Geography</span><span className="rv">{geo.length ? geo.map((g, i) => <span key={i} className="pill">{g}</span>) : <span className="await"><span className="d" />awaiting</span>}</span></div>
            <div className="chiprow"><span className="rl">Products</span><span className="rv">{products.length ? products.map((p, i) => <span key={i} className="pill alt">{p}</span>) : <span className="await"><span className="d" />awaiting</span>}</span></div>
          </div></div>
        </div>
      </div>

      {/* PEOPLE */}
      <div className="group" id="g-people">
        <div className="grouphead"><div className="gi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}><circle cx="9" cy="8" r="3" /><path d="M3 20a6 6 0 0112 0M17 8a3 3 0 010 6" /></svg></div><h4>People</h4><span className="gn">{contacts.length} contacts</span></div>
        <div className="grid2">
          <div className="panel"><div className="ph"><span className="eye" /><span className="k">02</span><h3>Stakeholder map</h3><span className="n">{contacts.length} contacts</span></div>
            <div className="pb" style={{ paddingTop: 8 }}>
              {contacts.length === 0 && (st === 'completed' ? <div className="await">no contacts</div> : <div className="await"><span className="d" />discovering stakeholders…</div>)}
              {contacts.map((c, i) => (
                <div key={i} className={'stk' + (i === sel ? ' on' : '')} onClick={() => setSel(i)}>
                  <div className="av">{initials(c.name)}</div>
                  <div className="who"><b>{c.name}</b><small>{c.title}</small></div>
                  <span className="role">{c.persona}</span>
                  <div className="ch"><i className={c.email ? 'has' : 'no'}>@</i><i className={c.phone ? 'has' : 'no'}>☎</i><i className={c.linkedin ? 'has' : 'no'}>in</i></div>
                </div>
              ))}
            </div>
          </div>
          <div className="panel"><div className="ph"><span className="eye" /><span className="k">07</span><h3>Contact dossier</h3><span className="n">← select from the map</span></div>
            <div className="pb"><div className="dossier">
              {cur ? <>
                <div className="dh"><div className="av">{initials(cur.name)}</div><div><b>{cur.name}</b><small>{cur.title}</small></div><span className="role">{cur.persona}</span></div>
                <div className="bio"><span className="l">About</span>{cur.about}</div>
                {cur.email ? <a className="lk2" href={`mailto:${cur.email}`}>✉ {cur.email} <span className="ar">↗</span></a> : <a className="lk2" style={{ opacity: .5, pointerEvents: 'none' }}>✉ no email on file</a>}
                {cur.phone ? <a className="lk2" href={`tel:${cur.phone}`}>☎ {cur.phone} <span className="ar">↗</span></a> : <a className="lk2" style={{ opacity: .5, pointerEvents: 'none' }}>☎ no direct line on file</a>}
                {cur.linkedin ? <a className="lk2" href={cur.linkedin} target="_blank" rel="noreferrer">in {cur.linkedin.replace(/^https?:\/\//, '')} <span className="ar">↗</span></a> : <a className="lk2" style={{ opacity: .5, pointerEvents: 'none' }}>in no LinkedIn on file</a>}
              </> : <div className="await"><span className="d" />awaiting contacts…</div>}
            </div></div>
          </div>
        </div>
      </div>

      {/* SIGNALS */}
      <div className="group" id="g-signals">
        <div className="grouphead"><div className="gi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}><path d="M3 12h4l3 8 4-16 3 8h4" /></svg></div><h4>Signals &amp; News</h4><span className="gn">intent · triggers</span></div>
        <div className="grid2">
          <div className="panel"><div className="ph"><span className="eye" /><span className="k">03</span><h3>Buying signals</h3></div><div className="pb">
            {intent.length ? <div className="chiprow"><span className="rl">Active intent</span><span className="rv">{intent.map((t, i) => <span key={i} className="pill">{typeof t === 'string' ? t : t?.topic}</span>)}</span></div> : awaiting('detecting intent…')}
          </div></div>
          <div className="panel"><div className="ph"><span className="eye" /><span className="k">05</span><h3>News intelligence</h3></div><div className="pb">
            {news.length ? news.slice(0, 5).map((n, i) => (
              <div className="news" key={i}><div className="dt">{n.dt || 'Insight'}</div>
                <div className="hl">{n.hl}</div></div>
            )) : awaiting('gathering news…')}
          </div></div>
        </div>
      </div>

      {/* STRATEGY */}
      <div className="group" id="g-strategy">
        <div className="grouphead"><div className="gi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}><path d="M12 2l3 7 7 .5-5.5 4.5 2 7L12 17l-6.5 4 2-7L2 9.5 9 9z" /></svg></div><h4>Strategy</h4><span className="gn">council output</span></div>
        <div className="grid2">
          <div className="panel"><div className="ph"><span className="eye" /><span className="k">04</span><h3>Opportunity themes</h3></div><div className="pb">
            {themes.length ? <ul className="clean">{themes.slice(0, 4).map((t: any, i: number) => {
              if (typeof t === 'string') {
                // pain_points are long prose strings — split a lead clause off as the
                // bold title and keep the remainder as the supporting detail.
                const m = t.match(/^(.{12,80}?[.:—-])\s+(.*)$/s);
                const title = m ? m[1].replace(/[.:—-]\s*$/, '') : t;
                const desc = m ? m[2] : '';
                return <li key={i}><b>{title}</b>{desc && <span className="why">{desc}</span>}</li>;
              }
              return <li key={i}><b>{t.title || t.name || t.theme || t.opportunity || String(t)}</b>{(t.description || t.detail) && <span className="why">{t.description || t.detail}</span>}</li>;
            })}</ul>
              : awaiting(act < 5 ? 'pending council…' : '28 specialists deliberating…')}
          </div></div>
          <div className="panel"><div className="ph"><span className="eye" /><span className="k">06</span><h3>Recommended sales program</h3>
            {intentLevel ? <span className="n">intent: {intentLevel}{intentScore ? ` · ${intentScore}` : ''}</span> : null}</div><div className="pb">
            {hasProgram ? <>
              {strategyText && <p className="why" style={{ display: 'block', margin: '0 0 12px', lineHeight: 1.55 }}>{strategyText}</p>}
              {programSteps.length
                ? <ul className="clean">{programSteps.slice(0, 4).map((s: any, i: number) => <li key={i}><b>{`${i + 1} · ${s.step || s.title || s.name || String(s)}`}</b>{(s.why || s.rationale || s.collateral) && <span className="why">{s.why || s.rationale || s.collateral}</span>}</li>)}</ul>
                : solutionAreas.length
                  ? <ul className="clean">{solutionAreas.slice(0, 5).map((s: any, i: number) => <li key={i}><b>{typeof s === 'string' ? s : (s.title || s.name || s.area || String(s))}</b>{typeof s !== 'string' && (s.why || s.rationale) ? <span className="why">{s.why || s.rationale}</span> : null}</li>)}</ul>
                  : (!strategyText ? awaiting('awaiting council + content match…') : null)}
            </> : awaiting('awaiting council + content match…')}
          </div></div>
        </div>
      </div>

      {/* TECHNOGRAPHICS */}
      <div className="group" id="g-tech">
        <div className="grouphead"><div className="gi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}><rect x="4" y="4" width="16" height="12" rx="2" /><path d="M8 20h8M12 16v4" /></svg></div><h4>Technographics</h4><span className="gn">stack · competitive set</span></div>
        <div className="grid2">
          <div className="panel"><div className="ph"><span className="eye" /><span className="k">11</span><h3>Installed technologies</h3></div><div className="pb">
            {technologies.length ? technologies.map((t, i) => <span key={i} className="pill">{t}</span>) : <span className="await"><span className="d" />awaiting</span>}
          </div></div>
          <div className="panel"><div className="ph"><span className="eye" /><span className="k">12</span><h3>Competitors</h3></div><div className="pb">
            {competitors.length ? competitors.map((t, i) => <span key={i} className="pill">{t}</span>) : <span className="await"><span className="d" />awaiting</span>}
          </div></div>
        </div>
      </div>

      {/* TRACE */}
      <div className="group" id="g-trace">
        <div className="grouphead"><div className="gi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}><path d="M4 4v16h16M8 16l3-4 3 2 4-6" /></svg></div><h4>Trace &amp; cost</h4><span className="gn">telemetry</span></div>
        <div className="grid2">
          <div className="panel"><div className="ph"><span className="eye" /><span className="k">Spend</span><h3>API cost meter</h3></div><div className="pb"><div className="cost">
            <div className="total">${(apiCost?.total_usd ?? 0).toFixed(2)}<small> / job</small></div>
            {(() => {
              const bs = apiCost?.by_service || {};
              const a = (bs.anthropic?.usd || 0) + (bs.openai?.usd || 0);
              const z = bs.zoominfo?.usd || 0, w = bs.web_search?.usd || 0;
              const llmCalls = (bs.anthropic?.calls || 0) + (bs.openai?.calls || 0);
              const tot = a + z + w || 1;
              return <>
                <div className="costbar"><i style={{ width: `${(a / tot) * 100}%`, background: 'var(--hp)' }} /><i style={{ width: `${(z / tot) * 100}%`, background: 'var(--hp-light)' }} /><i style={{ width: `${(w / tot) * 100}%`, background: 'var(--warn)' }} /></div>
                <div className="costleg">
                  <div className="r"><span className="sw2" style={{ background: 'var(--hp)' }} />LLM · {llmCalls} calls<span className="a">${a.toFixed(3)}</span></div>
                  <div className="r"><span className="sw2" style={{ background: 'var(--hp-light)' }} />ZoomInfo · {bs.zoominfo?.calls || 0} calls<span className="a">${z.toFixed(3)}</span></div>
                  <div className="r"><span className="sw2" style={{ background: 'var(--warn)' }} />Web search · {bs.web_search?.calls || 0}<span className="a">${w.toFixed(3)}</span></div>
                </div>
              </>;
            })()}
          </div></div></div>
          <div className="panel"><div className="ph"><span className="eye" /><span className="k">Trace</span><h3>Audit log</h3><span className="n">{log.length} events</span></div>
            <div className="pb"><div className="log">
              {log.length === 0 && <div className="await"><span className="d" />waiting for events…</div>}
              {log.map((l, i) => <div className="ln" key={i}><span className="t">{l.t}</span><span className="m">{l.m}</span></div>)}
            </div></div>
          </div>
        </div>
      </div>
    </>
  );
}
