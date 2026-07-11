"""
test_gemini_key.py
-------------------
Quick standalone check: does this Gemini API key work at all, separate from
the full Streamlit app? Run with:

    python test_gemini_key.py YOUR_API_KEY

If this fails with the same RESOURCE_EXHAUSTED / quota error, the problem is
confirmed to be with the Google account/project, not the app.
"""
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_gemini_key.py YOUR_API_KEY")
        sys.exit(1)

    api_key = sys.argv[1]

    from google import genai
    client = genai.Client(api_key=api_key)

    print("Testing text generation (gemini-2.5-flash)...")
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents="Say hello in one word.")
        print("✅ Generation works:", response.text)
    except Exception as e:
        print("❌ Generation failed:", e)

    print("\nTesting embeddings (gemini-embedding-001)...")
    try:
        from google.genai import types
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=["hello world"],
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        print("✅ Embeddings work, vector length:", len(result.embeddings[0].values))
    except Exception as e:
        print("❌ Embeddings failed:", e)


if __name__ == "__main__":
    main()
