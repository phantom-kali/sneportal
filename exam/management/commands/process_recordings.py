from django.core.management.base import BaseCommand
from django.conf import settings
from exam.voice_processor import VoiceProcessor
import os
import json
from datetime import datetime

class Command(BaseCommand):
    help = 'Process audio recordings in the recordings directory and save transcriptions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Delete recordings after processing',
        )

    def handle(self, *args, **options):
        recordings_dir = os.path.join(settings.MEDIA_ROOT, 'recordings')
        output_dir = os.path.join(settings.MEDIA_ROOT, 'transcriptions')
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        processor = VoiceProcessor()
        
        for filename in os.listdir(recordings_dir):
            if filename.endswith('.webm'):
                self.stdout.write(f'Processing {filename}...')
                
                filepath = os.path.join(recordings_dir, filename)
                
                try:
                    # Read audio file
                    with open(filepath, 'rb') as audio_file:
                        audio_data = audio_file.read()
                    
                    # Try transcription with webm parameters
                    result = processor.transcribe_audio(
                        audio_data,
                        sample_rate_hertz=48000,  # Standard webm sample rate
                        encoding='WEBM_OPUS',
                        language_code='en-US',
                        channels=1
                    )
                    
                    # Save transcription result
                    output_filename = f"{os.path.splitext(filename)[0]}_transcript.json"
                    output_path = os.path.join(output_dir, output_filename)
                    
                    transcription_data = {
                        'filename': filename,
                        'processed_at': datetime.now().isoformat(),
                        'success': result.get('success', False),
                        'transcript': result.get('transcript', ''),
                        'error': result.get('error', None)
                    }
                    
                    with open(output_path, 'w') as f:
                        json.dump(transcription_data, f, indent=2)
                    
                    if result['success']:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Successfully transcribed {filename}'
                            )
                        )
                        
                        # Delete if requested and successful
                        if options['delete']:
                            os.remove(filepath)
                            self.stdout.write(f'Deleted {filename}')
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Failed to transcribe {filename}: {result.get("error")}'
                            )
                        )
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Error processing {filename}: {str(e)}'
                        )
                    )

        self.stdout.write(self.style.SUCCESS('Processing complete!'))