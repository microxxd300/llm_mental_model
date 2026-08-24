from rest_framework import serializers

# llama3.1:8b runs with a 4096-token context. ~4 chars per token means 10,000
# chars is roughly 2,500 input tokens, leaving room for the output.
MAX_TEXT_CHARS = 10_000

TONES = ["neutral", "formal", "casual", "confident", "friendly"]


class TextSerializer(serializers.Serializer):
    """The input every endpoint shares."""

    text = serializers.CharField(
        min_length=20,
        max_length=MAX_TEXT_CHARS,
        trim_whitespace=True,
    )


class SummarizeRequestSerializer(TextSerializer):
    pass


class RewriteRequestSerializer(TextSerializer):
    tone = serializers.ChoiceField(choices=TONES, default="neutral")


class TranslateRequestSerializer(TextSerializer):
    target_language = serializers.CharField(max_length=40, trim_whitespace=True)
