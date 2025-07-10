import json
import re
import wave
import numpy as np
import requests
import base64
from google.cloud import speech
from google.cloud import texttospeech
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class VoiceProcessor:
    """Core voice processing functionality using Google Cloud APIs"""
    
    def __init__(self):
        # Using API key directly instead of client library authentication
        self.api_key = settings.GOOGLE_API_KEY
        self.voice_settings = getattr(settings, 'VOICE_SETTINGS', {})
    
    def transcribe_audio(self, audio_data, language_code='en-US', sample_rate_hertz=16000, encoding='WEBM_OPUS', channels=1):
        """Convert audio to text using Google Speech-to-Text"""
        try:
            # Convert audio data to base64
            audio_content = base64.b64encode(audio_data).decode('utf-8')
            
            # Prepare request data with explicit audio config for webm
            data = {
                "config": {
                    "languageCode": language_code,
                    "enableAutomaticPunctuation": True,
                    "encoding": encoding,  # Changed to WEBM_OPUS
                    "sampleRateHertz": sample_rate_hertz,
                    "audioChannelCount": channels,
                    "model": "default"  # Use default model for better compatibility
                },
                "audio": {
                    "content": audio_content
                }
            }
            
            # Make request to Speech-to-Text API
            url = f"https://speech.googleapis.com/v1/speech:recognize?key={self.api_key}"
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            
            if 'results' in result and result['results']:
                transcript = result['results'][0]['alternatives'][0]['transcript']
                return {
                    'success': True,
                    'transcript': transcript
                }
            return {
                'success': False,
                'transcript': '',
                'error': 'No speech detected'
            }
                
        except requests.exceptions.RequestException as e:
            error_message = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_message = f"{error_message}: {error_detail}"
                except:
                    pass
            return {
                'success': False,
                'transcript': '',
                'error': error_message
            }
        except Exception as e:
            logger.error(f"Speech-to-Text error: {str(e)}")
            return {
                'success': False,
                'transcript': '',
                'error': str(e)
            }
    
    def synthesize_speech(self, text, language_code='en-US', voice_gender='NEUTRAL'):
        """Convert text to speech using Google Text-to-Speech"""
        try:
            # Get voice settings for language
            lang_key = 'en' if language_code.startswith('en') else 'sw'
            voice_config = self.voice_settings['LANGUAGES'].get(lang_key, {})
            
            # Prepare request data
            data = {
                "input": {"text": text},
                "voice": {
                    "languageCode": voice_config.get('code', language_code),
                    "name": voice_config.get('voice', 'en-US-Standard-C'),
                    "ssmlGender": voice_config.get('gender', voice_gender)
                },
                "audioConfig": {
                    "audioEncoding": "MP3"
                }
            }
            
            # Make request to Text-to-Speech API
            url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={self.api_key}"
            headers = {
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': self.api_key
            }
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            
            if 'audioContent' in result:
                audio_content = base64.b64decode(result['audioContent'])
                return {
                    'success': True,
                    'audio_content': audio_content,
                    'content_type': 'audio/mp3'
                }
            return {
                'success': False,
                'error': 'Failed to generate audio'
            }
            
        except Exception as e:
            logger.error(f"Text-to-Speech error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
            
    def generate_tone(self, frequency=800, duration=0.5, sample_rate=16000):
        """Generate audio tone to signal voice capture start"""
        try:
            import io
            import wave
            
            t = np.linspace(0, duration, int(sample_rate * duration))
            tone = np.sin(2 * np.pi * frequency * t)
            # Convert to 16-bit PCM
            tone = (tone * 32767).astype(np.int16)
            
            # Create WAV file in memory
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(tone.tobytes())
            
            return {
                'success': True,
                'tone_data': buffer.getvalue()
            }
            
        except Exception as e:
            logger.error(f"Tone generation error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


class VoiceCommandParser:
    """Parse voice commands and extract answers from natural speech"""
    
    def __init__(self):
        self.navigation_commands = {
            'go back': 'go_back',
            'previous': 'go_back',
            'back': 'go_back',
            'repeat': 'repeat_question',
            'repeat question': 'repeat_question',
            'say again': 'repeat_question',
            'time': 'time_remaining',
            'time remaining': 'time_remaining',
            'how much time': 'time_remaining',
            'next': 'next_question',
            'next question': 'next_question',
            'continue': 'next_question',
            'start': 'start_exam',
            'begin': 'start_exam',
            'ready': 'start_exam'
        }
        
        self.confirmation_commands = {
            'yes': True,
            'correct': True,
            'right': True,
            'that is correct': True,
            'that\'s right': True,
            'no': False,
            'incorrect': False,
            'wrong': False,
            'not correct': False,
            'that is wrong': False
        }
    
    def parse_command(self, transcribed_text, current_state):
        """Parse voice commands based on current state"""
        text_lower = transcribed_text.lower().strip()
        
        # Check for navigation commands
        for phrase, command in self.navigation_commands.items():
            if phrase in text_lower:
                return {
                    'type': 'navigation',
                    'command': command,
                    'original_text': transcribed_text
                }
        
        # Check for confirmation commands
        if current_state == 'answer_confirmation':
            for phrase, confirmation in self.confirmation_commands.items():
                if phrase in text_lower:
                    return {
                        'type': 'confirmation',
                        'confirmed': confirmation,
                        'original_text': transcribed_text
                    }
        
        # Default to content response
        return {
            'type': 'content',
            'content': transcribed_text,
            'original_text': transcribed_text
        }
    
    def extract_answer(self, text, question_type):
        """Extract answer from natural speech based on question type"""
        text_clean = text.strip()
        text_upper = text_clean.upper()
        text_lower = text_clean.lower()
        
        if question_type == 'multiple_choice':
            # Look for single letter answers
            single_letter_match = re.search(r'\b([ABCD])\b', text_upper)
            if single_letter_match:
                return {
                    'answer': single_letter_match.group(1),
                    'confidence': 'high',
                    'original_text': text
                }
            
            # Look for "option X" or "choice X"
            option_match = re.search(r'\b(?:option|choice)\s+([ABCD])\b', text_upper)
            if option_match:
                return {
                    'answer': option_match.group(1),
                    'confidence': 'medium',
                    'original_text': text
                }
            
            # Look for "the answer is X"
            answer_match = re.search(r'\b(?:the\s+)?answer\s+is\s+([ABCD])\b', text_upper)
            if answer_match:
                return {
                    'answer': answer_match.group(1),
                    'confidence': 'medium',
                    'original_text': text
                }
        
        elif question_type == 'true_false':
            if 'true' in text_lower:
                return {
                    'answer': 'true',
                    'confidence': 'high',
                    'original_text': text
                }
            elif 'false' in text_lower:
                return {
                    'answer': 'false',
                    'confidence': 'high',
                    'original_text': text
                }
        
        elif question_type == 'short_answer':
            # For short answers, return the cleaned text
            return {
                'answer': text_clean,
                'confidence': 'medium',
                'original_text': text
            }
        
        # If no clear answer found, return original text
        return {
            'answer': text_clean,
            'confidence': 'low',
            'original_text': text
        }
    
    def is_valid_answer(self, answer, question_type):
        """Validate if extracted answer is valid for question type"""
        if question_type == 'multiple_choice':
            return answer.upper() in ['A', 'B', 'C', 'D']
        elif question_type == 'true_false':
            return answer.lower() in ['true', 'false']
        elif question_type == 'short_answer':
            return len(answer.strip()) > 0
        
        return False


class VoiceFlowManager:
    """Manage the complete voice flow and state transitions"""
    
    def __init__(self):
        self.voice_processor = VoiceProcessor()
        self.command_parser = VoiceCommandParser()
    
    def handle_voice_input(self, session, audio_data, existing_transcript=None):
        """Main entry point for processing voice input"""
        try:
            # Use existing transcript if provided, otherwise transcribe
            if existing_transcript:
                transcript = existing_transcript
                transcription_success = True
            else:
                language_code = 'sw-KE' if session.exam.language == 'sw' else 'en-US'
                transcription_result = self.voice_processor.transcribe_audio(
                    audio_data, 
                    language_code,
                    sample_rate_hertz=48000,
                    encoding='WEBM_OPUS',
                    channels=1
                )
                transcription_success = transcription_result.get('success', False)
                transcript = transcription_result.get('transcript', '')
            
            # Validate transcript exists
            if not transcription_success or not transcript:
                return self._create_error_response(
                    "Sorry, I couldn't understand your response. Please try again."
                )
            
            # Process the transcript
            command = self.command_parser.parse_command(transcript, session.current_state)
                
            # Route to appropriate handler
            if session.current_state == 'student_name':
                return self._handle_name_input(session, transcript, command)
            elif session.current_state == 'student_grade':
                return self._handle_grade_input(session, transcript, command)
            elif session.current_state == 'exam_briefing':
                return self._handle_briefing_response(session, transcript, command)
            elif session.current_state == 'question_reading':
                return self._handle_question_command(session, transcript, command)
            elif session.current_state == 'answer_capture':
                return self._handle_answer_input(session, transcript, command)
            elif session.current_state == 'answer_confirmation':
                return self._handle_confirmation(session, transcript, command)
            
            return self._create_error_response("Invalid state")
            
        except Exception as e:
            logger.error(f"Voice flow error: {str(e)}")
            return self._create_error_response(
                "Sorry, there was an error processing your response. Please try again."
            )
    
    def _handle_name_input(self, session, transcript, command):
        """Handle student name input"""
        if command['type'] == 'navigation':
            return self._handle_navigation_command(session, command['command'])
        
        # Store name and confirm
        session.student_name = transcript
        session.current_state = 'student_grade'
        session.save()
        
        response_text = f"Thank you, {transcript}. Now please state your grade level."
        return self._create_voice_response(session, response_text)
    
    def _handle_grade_input(self, session, transcript, command):
        """Handle student grade input"""
        if command['type'] == 'navigation':
            return self._handle_navigation_command(session, command['command'])
        
        # Store grade and move to briefing
        session.student_grade = transcript
        session.current_state = 'exam_briefing'
        session.save()
        
        # Create briefing text
        briefing_text = self._create_exam_briefing(session)
        return self._create_voice_response(session, briefing_text)
    
    def _handle_briefing_response(self, session, transcript, command):
        """Handle exam briefing response"""
        if command['type'] == 'navigation' and command['command'] == 'start_exam':
            # Move to first question
            session.current_state = 'question_reading'
            session.save()
            
            question_text = self._format_question_for_voice(session.current_question)
            return self._create_voice_response(session, question_text)
        
        elif command['type'] == 'navigation' and command['command'] == 'repeat_question':
            # Repeat briefing
            briefing_text = self._create_exam_briefing(session)
            return self._create_voice_response(session, briefing_text)
        
        # Default response
        response_text = "Please say 'start' when you are ready to begin the exam, or say 'repeat' to hear the instructions again."
        return self._create_voice_response(session, response_text)
    
    def _handle_question_command(self, session, transcript, command):
        """Handle commands during question reading"""
        if command['type'] == 'navigation':
            return self._handle_navigation_command(session, command['command'])
        
        # Move to answer capture
        session.current_state = 'answer_capture'
        session.save()
        
        response_text = "Please provide your answer after the tone."
        return self._create_voice_response(session, response_text, include_tone=True)
    
    def _handle_answer_input(self, session, transcript, command):
        """Handle answer input from student"""
        if command['type'] == 'navigation':
            return self._handle_navigation_command(session, command['command'])
        
        # Extract answer from transcript
        current_question = session.current_question
        answer_result = self.command_parser.extract_answer(
            transcript, current_question.question_type
        )
        
        if self.command_parser.is_valid_answer(answer_result['answer'], current_question.question_type):
            # Store the answer temporarily and confirm
            session.current_state = 'answer_confirmation'
            session.save()
            
            # Store answer in session for confirmation
            # We'll use Django session storage for this temporary data
            from django.contrib.sessions.models import Session
            request_session = getattr(session, '_request_session', {})
            request_session['temp_answer'] = answer_result['answer']
            request_session['temp_transcript'] = transcript
            
            response_text = f"You answered {answer_result['answer']}. Is this correct? Say yes to confirm or no to try again."
            return self._create_voice_response(session, response_text)
        else:
            # Invalid answer, ask to try again
            response_text = f"I didn't understand your answer. For this {current_question.question_type} question, please provide a clear answer."
            return self._create_voice_response(session, response_text, include_tone=True)
    
    def _handle_confirmation(self, session, transcript, command):
        """Handle answer confirmation"""
        if command['type'] == 'confirmation':
            from django.contrib.sessions.models import Session
            request_session = getattr(session, '_request_session', {})
            
            if command['confirmed']:
                # Save the answer
                temp_answer = request_session.get('temp_answer', '')
                temp_transcript = request_session.get('temp_transcript', '')
                
                self._save_student_response(session, temp_answer, temp_transcript)
                
                # Move to next question or complete exam
                session.advance_question()
                
                if session.is_complete():
                    session.complete_exam()
                    final_text = self._create_exam_completion_text(session)
                    return self._create_voice_response(session, final_text)
                else:
                    session.current_state = 'question_reading'
                    session.save()
                    
                    question_text = self._format_question_for_voice(session.current_question)
                    return self._create_voice_response(session, question_text)
            else:
                # Go back to answer capture
                session.current_state = 'answer_capture'
                session.save()
                
                response_text = "Please provide your answer again after the tone."
                return self._create_voice_response(session, response_text, include_tone=True)
        
        # Default response for unclear confirmation
        response_text = "Please say 'yes' to confirm your answer or 'no' to try again."
        return self._create_voice_response(session, response_text)
    
    def _handle_navigation_command(self, session, command):
        """Handle navigation commands"""
        if command == 'go_back':
            if session.current_question_index > 0:
                session.go_back_question()
                session.current_state = 'question_reading'
                session.save()
                
                question_text = self._format_question_for_voice(session.current_question)
                return self._create_voice_response(session, question_text)
            else:
                response_text = "You are already at the first question."
                return self._create_voice_response(session, response_text)
        
        elif command == 'repeat_question':
            if session.current_question:
                question_text = self._format_question_for_voice(session.current_question)
                return self._create_voice_response(session, question_text)
            else:
                response_text = "No question to repeat."
                return self._create_voice_response(session, response_text)
        
        elif command == 'time_remaining':
            response_text = f"You have {session.time_remaining_formatted} remaining."
            return self._create_voice_response(session, response_text)
        
        elif command == 'next_question':
            if session.current_state == 'question_reading':
                session.current_state = 'answer_capture'
                session.save()
                response_text = "Please provide your answer after the tone."
                return self._create_voice_response(session, response_text, include_tone=True)
        
        # Default response
        response_text = "I didn't understand that command. Please try again."
        return self._create_voice_response(session, response_text)
    
    def _create_exam_briefing(self, session):
        """Create comprehensive exam briefing text"""
        exam = session.exam
        total_questions = exam.get_total_questions()
        
        briefing = f"""
        Hello {session.student_name}, Grade {session.student_grade}. 
        
        You are about to take the {exam.title} exam in {exam.subject.name}.
        
        This exam has {total_questions} questions and you have {exam.duration_minutes} minutes to complete it.
        
        {exam.instructions}
        
        Here are the voice commands you can use:
        - Say 'repeat' to hear a question again
        - Say 'go back' to return to the previous question
        - Say 'time remaining' to hear how much time you have left
        
        When you are ready to begin, say 'start'.
        """
        
        return briefing.strip()
    
    def _format_question_for_voice(self, question):
        """Format question for voice reading"""
        if not question:
            return "No more questions."
        
        return question.format_for_voice()
    
    def _create_exam_completion_text(self, session):
        """Create exam completion announcement"""
        return f"""
        Congratulations {session.student_name}! You have completed the {session.exam.title} exam.
        
        Your final score is {session.total_score} out of {session.exam.get_total_points()} points.
        
        Thank you for taking the exam. You may now leave your seat.
        """
    
    def _save_student_response(self, session, answer, transcript):
        """Save student response to database"""
        from .models import StudentResponse
        
        current_question = session.current_question
        
        # Create or update response
        response, created = StudentResponse.objects.get_or_create(
            exam_session=session,
            question=current_question,
            defaults={
                'transcribed_text': transcript,
                'final_answer': answer,
                'attempts': 1
            }
        )
        
        if not created:
            response.final_answer = answer
            response.transcribed_text = transcript
            response.attempts += 1
        
        # Check if answer is correct and calculate score
        response.check_answer()
        
        # Update session total score
        session.total_score = sum(
            r.points_earned for r in session.responses.all()
        )
        session.save()
        
        return response
    
    def _create_voice_response(self, session, text, include_tone=False):
        """Create voice response with TTS"""
        language_code = 'sw-KE' if session.exam.language == 'sw' else 'en-US'
        
        # Generate TTS
        tts_result = self.voice_processor.synthesize_speech(text, language_code)
        
        response = {
            'session_id': session.session_id,
            'state': session.current_state,
            'text': text,
            'audio_available': tts_result['success'],
            'include_tone': include_tone,
            'progress': session.progress_percentage,
            'time_remaining': session.time_remaining,
            'current_question': session.current_question_index + 1,
            'total_questions': session.exam.get_total_questions()
        }
        
        if tts_result['success']:
            # Encode audio data as base64 for JSON serialization
            response['audio_data'] = base64.b64encode(tts_result['audio_content']).decode('utf-8')
            response['audio_content_type'] = tts_result.get('content_type', 'audio/mp3')
        
        return response
    
    def _create_error_response(self, message):
        """Create error response"""
        return {
            'error': True,
            'message': message,
            'text': message,
            'audio_available': False
        }