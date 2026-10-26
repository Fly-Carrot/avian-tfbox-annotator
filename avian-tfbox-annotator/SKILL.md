---
name: avian-tfbox-annotator
description: Mark bird sounds on real spectrograms, keep original boxes, merge sounds with gaps up to 0.5 seconds, and create an audio review page and Raven tables. Use with local 3-second or 10-second recordings.
---

# Avian TF-box Annotator

Help the user mark and review bird sounds. Use short, clear language in the results.

1. Read [the guide](references/guide.md) for audio settings and commands. Choose the 3s or 10s option that fits the user's files.
2. Keep source files and earlier results. Save each new run in a new folder. Keep the user's recording IDs.
3. Run `scripts/tfbox.py probe` to check the available tools. Use an existing Python environment where possible.
4. Render the spectrograms. For new annotations, inspect every required image with an image-reading tool. Use the real audio images for all boxes.
5. Draw close-fitting boxes around clear sound shapes. Keep separate events separate. Describe a rapid, unresolved sequence as a phrase. Record unclear edges, mixed sounds, and sounds outside the selected frequency range in the notes.
6. Fill the generated proposal file. Keep the generated file-check fields. Record the actual model, image tool, and whether you listened. Use `unknown` for missing information. If you cannot choose a clear box, use `abstained` and explain briefly.
7. Build the review page. Keep original boxes and merged boxes separate. Merge within each clip using the guide's 0.5-second rule.
8. Check playback, recording changes, both box layers, saved notes, and exports. Return the review page and a short count of recordings and boxes.

Use `unreviewed` for new boxes and keep species names as source labels until checked by a person. If the user asks to reuse saved boxes, use `replay_existing` and describe the result as a replay. If only rendering was completed, report that the images are ready for annotation.

Example request:

> Use $avian-tfbox-annotator to mark these 3-second recordings and create a review page with Raven tables.
