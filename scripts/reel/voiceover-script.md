# Reel voiceover: "6 things I learned turning my paintings into a floating museum"

Length: 43.6 s · 9:16 (1080×1920) · 30 fps. The soundtrack is the site's own nature music (kalimba and pad over wind, waterfall and birdsong); it goes quieter and echoier in the hall shots, just like walking inside. The lesson cards are short headlines, so your voice carries the details.
Read it relaxed but upbeat. Each line fits inside its shot with a breath to spare.
The timestamps are when each caption card pops up; start each line just after it.

| Time | On screen | Say |
|---|---|---|
| 0:00 – 0:04 | Sweep round the floating island | "I turned my paintings into a museum that floats. Here's what I learned." |
| 0:04 – 0:09 | **Lesson 1: Start before you're ready.** The museum front, autumn leaves | "One: start before you're ready. I picked up a brush in 2020. No classes, just paint." |
| 0:09 – 0:18 | **Lesson 2: Make the wait part of the show.** The loading screen: unwrapping the parcels, then the crew hanging a painting | "Two: make the wait part of the show. Every painting arrives in a parcel you get to unwrap, and a little crew hangs them up while the gallery loads." |
| 0:18 – 0:23 | **Lesson 3: Details make it feel alive.** Under the island: waterfall, woods, birds | "Three: the little details are what make it feel alive. Falling leaves, geese, a waterfall." |
| 0:23 – 0:28.5 | **Lesson 4: Presentation is part of the art.** Walking down the hall to a painting under its light | "Four: presentation is part of the art. Every painting gets its own frame, its own light, its own name." |
| 0:28.5 – 0:34 | **Lesson 5: Done beats perfect. Then fix it.** Quick cuts of six paintings, close up | "Five: done beats perfect. Paintings hung sideways, the mountains glitched. I fixed it one piece at a time." |
| 0:34 – 0:38.5 | **Lesson 6: Make room for people.** Over a visitor's shoulder | "Six: make room for people. Art is how we connect." |
| 0:38.5 – 0:43.6 | **Come walk through it.** Rising away from the island | "So come walk through it. The link's in my bio." |

## Caption for the post (optional)

> I turned my paintings into a museum that floats 🍂🖼️ Here are 6 things I learned along the way. You can unwrap every painting and walk through every room: link in bio.
> #acrylicpainting #artistsoninstagram #paintingoftheday #artportfolio #JanGoghArt

## Adding your voice

Record the voiceover (a phone voice memo is fine), then do one of these:

- **In Instagram or CapCut:** upload `reel.mp4`, add your recording as a voiceover, and turn the original sound down to about 25–30% so your voice sits on top.
- **With ffmpeg:** this lowers the nature track to 30% and mixes your voice over it.

```bash
ffmpeg -i reel.mp4 -i voiceover.m4a -filter_complex "[0:a]volume=0.3[bg];[bg][1:a]amix=inputs=2:duration=first:normalize=0[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k reel-with-voice.mp4
```
