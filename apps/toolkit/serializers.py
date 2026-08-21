from rest_framework import serializers

# llama3.1:8b runs with a 4096-token context. ~4 chars per token means 10,000
# chars is roughly 2,500 input tokens, leaving room for the summary.
MAX_TEXT_CHARS = 10_000


class SummarizeRequestSerializer(serializers.Serializer):
    text = serializers.CharField(
        min_length=20,
        max_length=MAX_TEXT_CHARS,
        trim_whitespace=True,
    )
