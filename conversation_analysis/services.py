import json
import logging

from django.conf import settings
from django.utils import timezone
from openai import OpenAI

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """You are analyzing a sales conversation between an agent and a potential customer.
Analyze the following conversation transcript and respond with ONLY a valid JSON object (no markdown, no extra text, no code fences) with these exact fields:

{
  "rating": <integer 1-5, where 1=very poor agent performance, 5=excellent>,
  "conversation_topic": "<main topic discussed in 5 words or fewer>",
  "short_description": "<2-3 sentence summary of the conversation>",
  "conversation_outcome": "<one sentence describing the result, e.g. 'Customer showed strong interest in the product and requested a follow-up meeting'>",
  "customer_sentiment": "<exactly one of: very_negative, negative, neutral, positive, very_positive>"
}

Rating criteria:
- 5: Agent was professional, addressed all concerns, built rapport, and moved toward a sale
- 4: Agent was mostly effective with minor areas for improvement
- 3: Average performance, some missed opportunities
- 2: Below average, multiple issues in communication or product knowledge
- 1: Poor handling, unprofessional, or failed to engage the customer

Transcript:
"""


def _get_client():
    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not configured in settings")
    return OpenAI(api_key=api_key)


def transcribe_audio(file_path):
    """Transcribe an audio file using OpenAI Whisper API."""
    client = _get_client()
    with open(file_path, 'rb') as audio:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio,
            response_format="text",
        )
    return response


def analyze_conversation(transcript):
    """Send transcript to ChatGPT and return structured analysis."""
    client = _get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a sales conversation analyst. Always respond with valid JSON only.",
            },
            {
                "role": "user",
                "content": ANALYSIS_PROMPT + transcript,
            },
        ],
        temperature=0.3,
        max_tokens=500,
    )
    raw_text = response.choices[0].message.content.strip()

    # Strip markdown code fences if present
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        raw_text = "\n".join(lines)

    return json.loads(raw_text)


def process_conversation(conversation):
    """
    Full pipeline: transcribe (if audio) then analyze.
    Updates the conversation instance in-place and saves.
    """
    needs_transcription = conversation.channel in ('in_person', 'phone')

    # Step 1: Transcribe audio if needed
    if needs_transcription and conversation.audio_file:
        if not conversation.raw_transcript:
            try:
                conversation.transcription_status = 'processing'
                conversation.save(update_fields=['transcription_status'])

                transcript = transcribe_audio(conversation.audio_file.path)
                conversation.raw_transcript = transcript
                conversation.transcription_status = 'completed'
                conversation.save(update_fields=['raw_transcript', 'transcription_status'])
            except Exception as e:
                logger.error(f"Transcription failed for conversation {conversation.id}: {e}")
                conversation.transcription_status = 'failed'
                conversation.save(update_fields=['transcription_status'])
                return
        else:
            conversation.transcription_status = 'skipped'
            conversation.save(update_fields=['transcription_status'])
    elif needs_transcription and not conversation.audio_file:
        if not conversation.raw_transcript:
            conversation.transcription_status = 'failed'
            conversation.analysis_status = 'failed'
            conversation.save(update_fields=['transcription_status', 'analysis_status'])
            return
    else:
        # Text channel — transcription not needed
        conversation.transcription_status = 'skipped'
        conversation.save(update_fields=['transcription_status'])

    # Step 2: Analyze transcript
    if not conversation.raw_transcript:
        conversation.analysis_status = 'failed'
        conversation.save(update_fields=['analysis_status'])
        return

    try:
        conversation.analysis_status = 'processing'
        conversation.save(update_fields=['analysis_status'])

        result = analyze_conversation(conversation.raw_transcript)
        conversation.ai_raw_response = result
        conversation.rating = result.get('rating')
        conversation.conversation_topic = result.get('conversation_topic', '')[:255]
        conversation.short_description = result.get('short_description', '')
        conversation.conversation_outcome = result.get('conversation_outcome', '')
        conversation.customer_sentiment = result.get('customer_sentiment', 'neutral')
        conversation.analysis_status = 'completed'
        conversation.analyzed_at = timezone.now()
        conversation.save(update_fields=[
            'ai_raw_response', 'rating', 'conversation_topic',
            'short_description', 'conversation_outcome', 'customer_sentiment',
            'analysis_status', 'analyzed_at',
        ])
    except Exception as e:
        logger.error(f"Analysis failed for conversation {conversation.id}: {e}")
        conversation.analysis_status = 'failed'
        conversation.save(update_fields=['analysis_status'])
