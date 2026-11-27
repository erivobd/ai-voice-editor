# In-app Remotion renderer

This renderer is part of AI Documentary Video Maker. It is invoked by `processor/remotion_render.py` and produces the final MP4 in the same worker job. It does not create a ZIP for an external rendering website.

- Remotion 4.0.517 / React 19.2.3 (aligned with the supplied Gemini reference project)
- 1920x1080, 30 FPS
- Bengali Hind Siliguri fonts bundled locally
- Scene timeline generated from the AI director's absolute narration timestamps
- Original narration is decoded to PCM WAV and included in the composition
- Stock footage and programmatic graphic scenes are composed inside Remotion
- Final voice/music mix and MP4 mux happen in the same pipeline

Run from this directory: `npm install`, then from project root `python processor/pipeline.py` after configuring the existing worker environment.
