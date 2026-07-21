from __future__ import annotations

from dataclasses import dataclass

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled, VideoUnavailable

from .source_types import SourceDocument
from .yt_dlp_fetch import fetch_metadata


@dataclass(frozen=True)
class YouTubeVideo:
    url: str
    video_id: str
    title: str
    uploader: str
    duration: int | None
    upload_date: str | None
    webpage_url: str
    transcript: str
    description: str


def fetch_youtube_video(url: str) -> YouTubeVideo:
    info = fetch_metadata(url)
    video_id = info.get("id")
    if not video_id:
        raise RuntimeError("yt-dlp did not return a YouTube video id")

    transcript = _fetch_transcript(video_id)
    if not transcript:
        raise RuntimeError(
            "No transcript was found for this video. Try a YouTube URL with captions enabled."
        )

    return YouTubeVideo(
        url=url,
        video_id=video_id,
        title=info.get("title") or "Untitled YouTube video",
        uploader=info.get("uploader") or info.get("channel") or "Unknown",
        duration=info.get("duration"),
        upload_date=info.get("upload_date"),
        webpage_url=info.get("webpage_url") or url,
        transcript=transcript,
        description=info.get("description") or "",
    )


def fetch_youtube_document(url: str) -> SourceDocument:
    video = fetch_youtube_video(url)
    return SourceDocument(
        source="youtube",
        source_folder="YouTube",
        source_url=video.webpage_url,
        title=video.title,
        creator=video.uploader,
        body_text=video.transcript,
        body_section_title="Transcript",
        published=video.upload_date,
        duration_seconds=video.duration,
        extra_frontmatter={"video_id": video.video_id},
    )


def _fetch_transcript(video_id: str) -> str:
    transcript_api = YouTubeTranscriptApi()
    try:
        transcript_list = transcript_api.list(video_id)
        selected = _select_transcript(transcript_list)
        transcript = selected.fetch()
    except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable) as exc:
        raise RuntimeError(f"No usable YouTube transcript was found for video {video_id}: {exc}") from exc

    parts = []
    for item in transcript:
        text = getattr(item, "text", None)
        if text is None and isinstance(item, dict):
            text = item.get("text")
        if text:
            parts.append(text.replace("\n", " ").strip())
    return " ".join(parts).strip()


def _select_transcript(transcript_list: object) -> object:
    transcripts = list(transcript_list)
    if not transcripts:
        raise RuntimeError("YouTube returned an empty transcript list")

    exact_english = [transcript for transcript in transcripts if transcript.language_code == "en"]
    if exact_english:
        return exact_english[0]

    english_variants = [
        transcript for transcript in transcripts if transcript.language_code.startswith("en-")
    ]
    if english_variants:
        return english_variants[0]

    english_translatable = [
        transcript
        for transcript in transcripts
        if transcript.is_translatable
        and any(language.language_code == "en" for language in transcript.translation_languages)
    ]
    if english_translatable:
        return english_translatable[0].translate("en")

    available = ", ".join(
        f"{transcript.language_code} ({transcript.language})" for transcript in transcripts
    )
    raise RuntimeError(f"No English or English-translatable transcript found. Available: {available}")
