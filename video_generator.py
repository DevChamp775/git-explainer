import os
import re
import textwrap
from pathlib import Path

# =====================================================
# VIDEO GENERATOR
# Free stack:
#   gTTS  — text to speech (Google TTS, free)
#   Pillow — slide image generation
#   moviepy — combine images + audio into MP4
# =====================================================

OUTPUT_DIR = "generated_videos"


def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', name)[:50]


def generate_video_script(filename, explanation, repo_name=""):
    """
    Uses Groq to turn a file explanation into a proper video script
    with intro, sections, and outro.
    """
    try:
        from ai_explainer import generate, GROQ_MODEL, USE_GROQ, OLLAMA_MODEL
        model = GROQ_MODEL if USE_GROQ else OLLAMA_MODEL

        prompt = f"""You are a professional technical content creator making a YouTube tutorial video.

Convert this code explanation into a proper VIDEO SCRIPT.

File: {filename}
Repo: {repo_name}

Explanation:
{explanation[:3000]}

Write a complete video script with:

[INTRO - 30 seconds]
Hook the viewer, tell them what they will learn.

[SECTION 1 - PURPOSE - 45 seconds]
Explain what this file does in simple words.

[SECTION 2 - KEY COMPONENTS - 90 seconds]  
Walk through each important function/class.

[SECTION 3 - HOW IT WORKS - 90 seconds]
Step by step flow — what happens when the code runs.

[SECTION 4 - REAL WORLD USE - 30 seconds]
Why this matters, where you'd use it.

[OUTRO - 20 seconds]
Summary, what they learned, call to action.

Format each section with the header in brackets.
Write naturally as if speaking to camera.
Keep total under 5 minutes when read aloud.
"""
        return generate(prompt, status_msg=f"{model} writing video script...")
    except Exception as e:
        return f"Error generating script: {e}"


def text_to_slides(title, script, output_path):
    """
    Converts a script into slide images using Pillow.
    Returns list of image paths.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("[Video] Pillow not installed. Run: pip install Pillow")
        return []

    slides = []
    os.makedirs(output_path, exist_ok=True)

    # Split script into sections
    sections = re.split(r'\[([^\]]+)\]', script)
    slide_data = []

    # Title slide
    slide_data.append(("TITLE", title))

    # Parse sections
    i = 1
    while i < len(sections):
        if i + 1 < len(sections):
            header  = sections[i].strip()
            content = sections[i + 1].strip()[:400]
            if header and content:
                slide_data.append((header, content))
        i += 2

    # Generate each slide
    for idx, (header, content) in enumerate(slide_data):
        img_path = os.path.join(output_path, f"slide_{idx:03d}.png")

        # Create slide
        width, height = 1280, 720
        img  = Image.new("RGB", (width, height), color="#0d1117")
        draw = ImageDraw.Draw(img)

        # Try to load a font, fallback to default
        try:
            font_title = ImageFont.truetype("arial.ttf", 48)
            font_body  = ImageFont.truetype("arial.ttf", 28)
            font_head  = ImageFont.truetype("arial.ttf", 36)
        except Exception:
            font_title = ImageFont.load_default()
            font_body  = font_title
            font_head  = font_title

        # Draw accent bar
        draw.rectangle([0, 0, width, 8], fill="#6e57ff")

        if idx == 0:
            # Title slide
            draw.text((width//2, height//2 - 60), header,
                     font=font_title, fill="#ffffff", anchor="mm")
            draw.text((width//2, height//2 + 40), content,
                     font=font_head, fill="#a99fff", anchor="mm")
            draw.rectangle([0, height-8, width, height], fill="#6e57ff")
        else:
            # Content slide
            draw.text((80, 60), f"[ {header} ]",
                     font=font_head, fill="#6e57ff")
            draw.line([80, 110, width-80, 110], fill="#2a2a3a", width=2)

            # Wrap and draw body text
            wrapped = textwrap.wrap(content, width=65)
            y = 140
            for line in wrapped[:14]:
                draw.text((80, y), line, font=font_body, fill="#e8eaf0")
                y += 38

        # Footer
        draw.text((width//2, height - 30),
                 f"GitHub Code Explainer  ·  {title}",
                 font=font_body, fill="#5a6070", anchor="mm")

        img.save(img_path)
        slides.append(img_path)

    return slides


def slides_to_audio(script, output_path, filename):
    """
    Converts script text to MP3 using gTTS (Google Text-to-Speech, free).
    """
    try:
        from gtts import gTTS
    except ImportError:
        print("[Video] gTTS not installed. Run: pip install gTTS")
        return None

    try:
        os.makedirs(output_path, exist_ok=True)
        audio_path = os.path.join(output_path, f"{filename}.mp3")

        # Clean script — remove section headers for natural narration
        clean = re.sub(r'\[[^\]]+\]', '', script)
        clean = re.sub(r'\n+', ' ', clean).strip()

        tts = gTTS(text=clean[:3000], lang='en', slow=False)
        tts.save(audio_path)
        return audio_path

    except Exception as e:
        print(f"[Video] Audio generation failed: {e}")
        return None


def create_video(slides, audio_path, output_path, filename):
    """
    Combines slide images + audio into an MP4 video using moviepy.
    """
    try:
        from moviepy.editor import (
            ImageClip, AudioFileClip,
            concatenate_videoclips
        )
    except ImportError:
        print("[Video] moviepy not installed. Run: pip install moviepy")
        return None

    try:
        if not slides:
            return None

        audio     = AudioFileClip(audio_path)
        duration  = audio.duration
        per_slide = duration / len(slides)

        clips = []
        for slide_path in slides:
            clip = ImageClip(slide_path).set_duration(per_slide)
            clips.append(clip)

        video      = concatenate_videoclips(clips, method="compose")
        video      = video.set_audio(audio)
        video_path = os.path.join(output_path, f"{filename}.mp4")
        video.write_videofile(
            video_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            verbose=False,
            logger=None
        )

        return video_path

    except Exception as e:
        print(f"[Video] Video creation failed: {e}")
        return None


def generate_full_video(filename, explanation, repo_name=""):
    """
    Full pipeline: explanation → script → slides → audio → MP4
    Returns dict with script, video_path, and status.
    """
    safe_name  = sanitize_filename(filename)
    output_dir = os.path.join(OUTPUT_DIR, safe_name)
    os.makedirs(output_dir, exist_ok=True)

    result = {
        "filename":   filename,
        "script":     "",
        "video_path": None,
        "slides_dir": output_dir,
        "status":     "pending"
    }

    # Step 1 — Generate script
    print(f"[Video] Generating script for {filename}...")
    script = generate_video_script(filename, explanation, repo_name)
    result["script"] = script

    if script.startswith("Error"):
        result["status"] = "script_failed"
        return result

    # Step 2 — Generate slides
    print(f"[Video] Creating slides...")
    slides = text_to_slides(filename, script, output_dir)
    if not slides:
        result["status"] = "slides_failed"
        return result

    # Step 3 — Generate audio
    print(f"[Video] Generating narration audio...")
    audio_path = slides_to_audio(script, output_dir, safe_name)
    if not audio_path:
        result["status"] = "audio_failed"
        return result

    # Step 4 — Combine into video
    print(f"[Video] Combining into MP4...")
    video_path = create_video(slides, audio_path, output_dir, safe_name)
    if video_path:
        result["video_path"] = video_path
        result["status"]     = "done"
        print(f"[Video] ✔ Done: {video_path}")
    else:
        result["status"] = "video_failed"

    return result


def generate_playlist(files_and_explanations, repo_name=""):
    """
    Generates videos for all files and returns a playlist.
    files_and_explanations = list of (filename, explanation) tuples
    """
    playlist = []

    for filename, explanation in files_and_explanations:
        print(f"\n[Playlist] Processing: {filename}")
        result = generate_full_video(filename, explanation, repo_name)
        playlist.append({
            "title":      filename,
            "repo":       repo_name,
            "script":     result["script"],
            "video_path": result["video_path"],
            "status":     result["status"]
        })

    return playlist