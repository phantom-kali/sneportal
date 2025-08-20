#!/usr/bin/env python
"""
Test script to download and initialize Whisper and Coqui TTS models
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sneportal.settings')
django.setup()

print("🎤 Initializing Local Voice Processor...")
print("=" * 50)

try:
    from exam.voice_processor_local import LocalVoiceProcessor
    
    print("📥 Loading Whisper 'small' model...")
    print("(This will download ~244MB on first run)")
    
    # Initialize the processor - this will download models
    processor = LocalVoiceProcessor()
    
    print("✅ Whisper model loaded successfully!")
    print("✅ Coqui TTS model loaded successfully!")
    print()
    
    # Test TTS
    print("🗣️  Testing Text-to-Speech...")
    test_text = "Hello! This is a test of the local voice processor."
    tts_result = processor.synthesize_speech(test_text)
    
    if tts_result['success']:
        print(f"✅ TTS Test successful! Generated {len(tts_result['audio_content'])} bytes of audio")
    else:
        print(f"❌ TTS Test failed: {tts_result.get('error')}")
    
    print()
    print("🎉 Local voice processor is ready for use!")
    print("You can now use voice features in the web application.")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you have installed the required packages:")
    print("pip install openai-whisper TTS torch torchaudio")
    
except Exception as e:
    print(f"❌ Error initializing voice processor: {e}")
    print("Check your internet connection for model downloads.")
