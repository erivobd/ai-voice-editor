import os, json, math, subprocess, glob
from pathlib import Path

WORK = Path(os.environ.get("WORK_DIR","/tmp/voice_job"))

def run(cmd):
    p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    if p.returncode: raise RuntimeError(f"FFmpeg failed: {p.stderr[-2500:]}")
    return p

def probe(path):
    p=run(["ffprobe","-v","error","-show_entries","format=duration:stream=sample_rate,channels,sample_fmt","-of","json",str(path)])
    d=json.loads(p.stdout); s=next(x for x in d["streams"] if "sample_rate" in x)
    return float(d["format"]["duration"]),int(s["sample_rate"]),int(s["channels"]),s.get("sample_fmt","s16")

def main():
    files=sorted(WORK.glob("original_audio.*"))
    if len(files)!=1: raise RuntimeError(f"Expected one original audio file, found {len(files)}")
    audio=files[0]; duration,sr,ch,sfmt=probe(audio)
    plan=json.loads((WORK/"approved_plan.json").read_text(encoding="utf-8"))
    cuts=[]
    for c in plan.get("approved_cuts",[]):
        a=float(c["start"]); b=float(c["end"])
        if not math.isfinite(a) or not math.isfinite(b) or a<0 or b<=a or b>duration:
            raise ValueError(f"Invalid approved cut interval: {a} - {b}")
        cuts.append((a,b))
    cuts.sort()
    merged=[]
    for a,b in cuts:
        if merged and a<=merged[-1][1]+0.02: merged[-1]=(merged[-1][0],max(merged[-1][1],b))
        else: merged.append((a,b))
    keep=[]; pos=0.0
    for a,b in merged:
        if a-pos>0.08: keep.append((pos,a))
        pos=b
    if duration-pos>0.08: keep.append((pos,duration))
    if not keep: raise ValueError("Approved cuts would remove the entire recording.")
    if sum(b-a for a,b in keep)<max(1.0,duration*0.05): raise ValueError("Too little audio would remain after cuts.")
    filters=[]; labels=[]
    for i,(a,b) in enumerate(keep):
        label=f"k{i}"; labels.append(f"[{label}]")
        length=b-a
        fade=min(0.015,length/4)
        filters.append(f"[0:a]atrim=start={a:.6f}:end={b:.6f},asetpts=PTS-STARTPTS,afade=t=in:st=0:d={fade:.4f},afade=t=out:st={max(0,length-fade):.6f}:d={fade:.4f}[{label}]")
    filters.append("".join(labels)+f"concat=n={len(keep)}:v=0:a=1[out]")
    filt=";".join(filters)
    if plan.get("noise_reduction")=="gentle": filt += ";[out]afftdn=nf=-25[final]"
    else: filt += ";[out]anull[final]"
    temp=WORK/"render_temp.wav"
    # Export 24-bit PCM as a high-quality working WAV.
    run(["ffmpeg","-y","-i",str(audio),"-filter_complex",filt,"-map","[final]","-ar",str(sr),"-ac",str(ch),"-c:a","pcm_s24le",str(temp)])
    run(["ffmpeg","-y","-i",str(temp),"-c:a","libmp3lame","-b:a","320k",str(WORK/"final_edited.mp3")])
    temp.replace(WORK/"final_edited.wav")
    saved=sum(b-a for a,b in merged)
    report={"original_duration_sec":round(duration,3),"final_duration_sec":round(sum(b-a for a,b in keep),3),
            "time_saved_sec":round(saved,3),"merged_cuts_count":len(merged),
            "noise_reduction_applied":plan.get("noise_reduction","original"),
            "sample_rate":sr,"channels":ch,"wav_codec":"pcm_s24le",
            "note":"No pitch shift, time stretch, voice conversion, or voice generation was applied."}
    (WORK/"editing_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")

if __name__=="__main__": main()
