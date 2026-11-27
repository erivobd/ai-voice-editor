import React from "react";
import { AbsoluteFill, Audio, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";

type Beat = { id: number; start: number; end: number; text: string; headline?: string; tag?: string; visualType: string; video?: string; zoom?: number; grade?: string; graphic?: { heading?: string; items?: string[]; kind?: string }; position?: string; showOverlay?: boolean; sfx?: string | null };
type Scene = { fps: number; width: number; height: number; duration: number; title: string; voice: string; beats: Beat[]; subtitles: {start:number;end:number;text:string}[]; burnSubtitles: boolean };
const FONT = `"Hind Siliguri", sans-serif`;
const BeatView: React.FC<{beat:Beat}> = ({beat}) => {
 const frame=useCurrentFrame(); const len=Math.max(1,beat.end-beat.start);
 const p=interpolate(frame,[0,len],[0,1],{extrapolateLeft:"clamp",extrapolateRight:"clamp"});
 const zoom=1+(beat.zoom??0.045)*p;
 const graphic=beat.visualType!=="stock_footage" || !beat.video;
 return <AbsoluteFill style={{background:graphic?"radial-gradient(ellipse at 72% 24%, #263c54 0%, #111923 48%, #090c12 100%)":"#090c12",overflow:"hidden"}}>
  {beat.video && <OffthreadVideo src={staticFile(beat.video)} muted style={{width:"100%",height:"100%",objectFit:"cover",transform:`scale(${zoom})`,filter:beat.grade==="warm_history"?"brightness(.84) sepia(.10) saturate(1.08) contrast(1.06)":beat.grade==="cool_science"?"brightness(.84) saturate(.92) hue-rotate(5deg) contrast(1.08)":beat.grade==="cinematic_teal"?"brightness(.84) saturate(1.04) contrast(1.08)":"brightness(.84) saturate(.98) contrast(1.04)"}} />}
  {graphic && <>
   <AbsoluteFill style={{opacity:.22,backgroundImage:"linear-gradient(rgba(255,255,255,.10) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.10) 1px,transparent 1px)",backgroundSize:"64px 64px",transform:`translate(${p*18}px,${p*-12}px)`}}/>
   {beat.graphic?.kind === "stat_chart" ? <svg viewBox="0 0 700 460" style={{position:"absolute",right:120,top:260,width:700,height:460}}>
    {[0,1,2,3].map(i=><line key={i} x1="35" y1={80+i*85} x2="665" y2={80+i*85} stroke="rgba(255,255,255,.15)" strokeDasharray="6 10"/>)}
    {(beat.graphic?.items||["তথ্য","বিশ্লেষণ","প্রভাব"]).slice(0,4).map((x,i)=>{const h=(110+i*34)*(0.25+p*.75);return <g key={i}><rect x={70+i*150} y={420-h} width="82" height={h} rx="8" fill={i===1?"#FDD40D":"#F83637"} opacity=".88"/><text x={111+i*150} y="448" fill="white" fontSize="18" textAnchor="middle">{x.slice(0,9)}</text></g>})}
   </svg> : beat.graphic?.kind === "timeline" ? <svg viewBox="0 0 760 300" style={{position:"absolute",right:100,top:360,width:760,height:300}}><line x1="55" y1="145" x2="705" y2="145" stroke="rgba(255,255,255,.7)" strokeWidth="5"/>{(beat.graphic?.items||["শুরু","পরিবর্তন","বর্তমান"]).slice(0,4).map((x,i)=><g key={i}><circle cx={85+i*195} cy="145" r="15" fill="#F83637"/><text x={85+i*195} y={i%2?205:90} fill="white" fontSize="22" textAnchor="middle">{x.slice(0,14)}</text></g>)}</svg> : beat.graphic?.kind === "map_marker" ? <svg viewBox="0 0 700 560" style={{position:"absolute",right:130,top:220,width:700,height:560}}><path d="M80 100 L220 60 L330 130 L450 75 L620 140 L590 300 L650 420 L470 480 L330 410 L180 480 L90 330 Z" fill="rgba(65,105,135,.24)" stroke="rgba(255,255,255,.48)" strokeWidth="4"/><path d="M120 260 Q280 160 430 300 T600 270" fill="none" stroke="#FDD40D" strokeWidth="5" strokeDasharray="12 10"/><g transform={`translate(${350+Math.sin(p*6)*8},${260+Math.cos(p*6)*8})`}><path d="M0 55 C-80 -25 -55 -105 0 -105 C55 -105 80 -25 0 55Z" fill="#F83637"/><circle cy="-55" r="18" fill="white"/></g></svg> : <><div style={{position:"absolute",width:520,height:520,border:"1px solid rgba(255,255,255,.15)",borderRadius:"50%",right:100,top:180,transform:`scale(${.88+p*.16})`}}/><div style={{position:"absolute",width:360,height:360,border:"1px solid rgba(248,54,55,.35)",borderRadius:"50%",right:180,top:260,transform:`rotate(${p*40}deg)`}}/></>}
  </>}
  <AbsoluteFill style={{background:"linear-gradient(90deg,rgba(4,8,14,.82) 0%,rgba(4,8,14,.38) 54%,rgba(4,8,14,.08) 100%),linear-gradient(0deg,rgba(4,8,14,.62),transparent 40%)"}}/>
  {((graphic)||beat.showOverlay) && <div style={{position:"absolute",left:beat.position==="right"?"auto":112,right:beat.position==="right"?112:"auto",top:150,maxWidth:1250,textAlign:beat.position==="right"?"right":"left",transform:`translateY(${(1-p)*18}px)`,opacity:interpolate(frame,[0,12],[0,1],{extrapolateRight:"clamp"})}}>
   {beat.tag && <div style={{display:"inline-block",background:"#F83637",padding:"9px 22px",fontFamily:FONT,fontSize:25,fontWeight:700,color:"white",borderRadius:4,marginBottom:22}}>{beat.tag}</div>}
   {(beat.headline||beat.graphic?.heading) && <div style={{fontFamily:FONT,fontSize:58,lineHeight:1.22,fontWeight:700,color:"#fff",textShadow:"0 4px 22px rgba(0,0,0,.65)",maxWidth:1200}}>{beat.headline||beat.graphic?.heading}</div>}
   {beat.graphic?.items?.length ? <div style={{marginTop:32,display:"flex",gap:16,flexWrap:"wrap"}}>{beat.graphic.items.slice(0,3).map((x,i)=><div key={i} style={{fontFamily:FONT,fontSize:26,color:"#fff",padding:"12px 22px",background:"rgba(255,255,255,.12)",borderLeft:"4px solid #FDD40D",backdropFilter:"blur(8px)"}}>{x}</div>)}</div>:null}
  </div>}
  {beat.sfx && <Audio src={staticFile(beat.sfx)} volume={0.11}/>}
  <div style={{position:"absolute",right:90,top:70,width:18,height:18,background:"#F83637",borderRadius:"50%",boxShadow:"0 0 24px #F83637"}}/>
 </AbsoluteFill>;
};
const SubtitleBar: React.FC<{scene:Scene}> = ({scene}) => { const f=useCurrentFrame(); const s=scene.subtitles.find(x=>f>=Math.floor(x.start*scene.fps)&&f<Math.ceil(x.end*scene.fps)); if(!s)return null; return <div style={{position:"absolute",left:170,right:170,bottom:58,textAlign:"center",fontFamily:FONT,fontSize:31,fontWeight:600,color:"#fff",lineHeight:1.35,textShadow:"0 2px 8px #000",background:"rgba(0,0,0,.48)",padding:"12px 24px",borderRadius:8}}>{s.text}</div>; };
export const Main: React.FC<Scene> = (scene) => <AbsoluteFill style={{background:"#080b10",fontFamily:FONT}}>
 <style>{`@font-face{font-family:'Hind Siliguri';src:url('${staticFile('fonts/HindSiliguri-Regular.ttf')}')} @font-face{font-family:'Hind Siliguri';font-weight:500;src:url('${staticFile('fonts/HindSiliguri-Medium.ttf')}')} @font-face{font-family:'Hind Siliguri';font-weight:600;src:url('${staticFile('fonts/HindSiliguri-SemiBold.ttf')}')} @font-face{font-family:'Hind Siliguri';font-weight:700;src:url('${staticFile('fonts/HindSiliguri-Bold.ttf')}')} *{box-sizing:border-box}`}</style>
 {scene.beats.map(b=><Sequence key={b.id} from={b.start} durationInFrames={b.end-b.start}><BeatView beat={b}/></Sequence>)}
 <Audio src={staticFile(scene.voice)} />
 {scene.burnSubtitles && <SubtitleBar scene={scene}/>}
 </AbsoluteFill>;
