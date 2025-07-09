import json
import uuid
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from django.utils import timezone
from django.core.files.base import ContentFile
from .models import Exam, ExamSession, Subject
from .voice_processor import VoiceFlowManager
import logging

logger = logging.getLogger(__name__)


class ExamSessionView(View):
    """Main exam interface view"""
    
    def get(self, request):
        """Serve the main exam interface"""
        # Get active exams for teacher selection
        active_exams = Exam.objects.filter(is_active=True).select_related('subject').order_by('title')
        
        context = {
            'active_exams': active_exams,
            'subjects': Subject.objects.all()
        }
        
        return render(request, 'exam/exam_interface.html', context)
    
    def post(self, request):
        """Handle exam selection from teacher"""
        try:
            exam_id = request.POST.get('exam_id')
            if not exam_id:
                return JsonResponse({'error': 'No exam selected'}, status=400)
            
            exam = get_object_or_404(Exam, id=exam_id, is_active=True)
            
            # Create new exam session
            session = ExamSession.objects.create(
                exam=exam,
                session_id=str(uuid.uuid4()),
                current_state='student_name',
                time_remaining=exam.duration_minutes * 60  # Convert to seconds
            )
            
            # Store session ID in Django session
            request.session['exam_session_id'] = session.session_id
            
            return JsonResponse({
                'success': True,
                'session_id': session.session_id,
                'exam_title': exam.title,
                'subject': exam.subject.name,
                'total_questions': exam.get_total_questions(),
                'duration_minutes': exam.duration_minutes
            })
            
        except Exception as e:
            logger.error(f"Error creating exam session: {str(e)}")
            return JsonResponse({'error': 'Failed to create exam session'}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class VoiceProcessingView(View):
    """Handle voice processing requests"""
    
    def __init__(self):
        super().__init__()
        self.voice_flow_manager = VoiceFlowManager()
    
    def post(self, request):
        """Process uploaded audio and return response"""
        try:
            # Get session
            session_id = request.POST.get('session_id') or request.session.get('exam_session_id')
            if not session_id:
                return JsonResponse({'error': 'No active session'}, status=400)
            
            session = get_object_or_404(ExamSession, session_id=session_id)
            
            # Check if session is still valid (not expired)
            if session.time_remaining <= 0:
                session.current_state = 'exam_complete'
                session.save()
                return JsonResponse({
                    'error': 'Time expired',
                    'message': 'Your exam time has expired.',
                    'state': 'exam_complete'
                })
            
            # Get audio data
            audio_file = request.FILES.get('audio')
            if not audio_file:
                return JsonResponse({'error': 'No audio file provided'}, status=400)
            
            # Read audio data
            audio_data = audio_file.read()
            
            # Attach request session to the exam session for temporary data
            session._request_session = request.session
            
            # Process voice input
            response = self.voice_flow_manager.handle_voice_input(session, audio_data)
            
            # Update time remaining (basic implementation)
            session.time_remaining = max(0, session.time_remaining - 5)  # Rough estimate
            session.save()
            
            return JsonResponse(response)
            
        except ExamSession.DoesNotExist:
            return JsonResponse({'error': 'Invalid session'}, status=404)
        except Exception as e:
            logger.error(f"Voice processing error: {str(e)}")
            return JsonResponse({'error': 'Voice processing failed'}, status=500)


class SessionStateView(View):
    """Handle session state requests"""
    
    def get(self, request):
        """Return current session state as JSON"""
        try:
            session_id = request.GET.get('session_id') or request.session.get('exam_session_id')
            if not session_id:
                return JsonResponse({'error': 'No active session'}, status=400)
            
            session = get_object_or_404(ExamSession, session_id=session_id)
            
            current_question = session.current_question
            
            return JsonResponse({
                'session_id': session.session_id,
                'state': session.current_state,
                'student_name': session.student_name,
                'student_grade': session.student_grade,
                'current_question_index': session.current_question_index,
                'total_questions': session.exam.get_total_questions(),
                'progress_percentage': session.progress_percentage,
                'time_remaining': session.time_remaining,
                'time_remaining_formatted': session.time_remaining_formatted,
                'total_score': session.total_score,
                'max_score': session.exam.get_total_points(),
                'exam_title': session.exam.title,
                'subject': session.exam.subject.name,
                'current_question': {
                    'order': current_question.order,
                    'text': current_question.question_text,
                    'type': current_question.question_type,
                    'options': current_question.options,
                    'points': current_question.points
                } if current_question else None
            })
            
        except ExamSession.DoesNotExist:
            return JsonResponse({'error': 'Invalid session'}, status=404)
        except Exception as e:
            logger.error(f"Session state error: {str(e)}")
            return JsonResponse({'error': 'Failed to get session state'}, status=500)
    
    def post(self, request):
        """Update session state"""
        try:
            session_id = request.POST.get('session_id') or request.session.get('exam_session_id')
            if not session_id:
                return JsonResponse({'error': 'No active session'}, status=400)
            
            session = get_object_or_404(ExamSession, session_id=session_id)
            
            # Handle specific state updates
            action = request.POST.get('action')
            
            if action == 'emergency_stop':
                session.current_state = 'exam_complete'
                session.completed_at = timezone.now()
                session.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Exam stopped by supervisor',
                    'state': 'exam_complete'
                })
            
            elif action == 'update_time':
                time_remaining = int(request.POST.get('time_remaining', 0))
                session.time_remaining = max(0, time_remaining)
                session.save()
                
                return JsonResponse({
                    'success': True,
                    'time_remaining': session.time_remaining
                })
            
            return JsonResponse({'error': 'Invalid action'}, status=400)
            
        except ExamSession.DoesNotExist:
            return JsonResponse({'error': 'Invalid session'}, status=404)
        except Exception as e:
            logger.error(f"Session update error: {str(e)}")
            return JsonResponse({'error': 'Failed to update session'}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class TTSView(View):
    """Text-to-speech endpoint"""
    
    def __init__(self):
        super().__init__()
        self.voice_flow_manager = VoiceFlowManager()
    
    def post(self, request):
        """Convert text to speech and return audio"""
        try:
            text = request.POST.get('text')
            if not text:
                return JsonResponse({'error': 'No text provided'}, status=400)
            
            # Get language preference
            language_code = request.POST.get('language', 'en-US')
            
            # Generate TTS
            tts_result = self.voice_flow_manager.voice_processor.synthesize_speech(
                text, language_code
            )
            
            if tts_result['success']:
                response = HttpResponse(
                    tts_result['audio_content'],
                    content_type='audio/mpeg'
                )
                response['Content-Disposition'] = 'attachment; filename="speech.mp3"'
                return response
            else:
                return JsonResponse({'error': 'TTS generation failed'}, status=500)
                
        except Exception as e:
            logger.error(f"TTS error: {str(e)}")
            return JsonResponse({'error': 'TTS processing failed'}, status=500)


class ToneGeneratorView(View):
    """Generate audio tone for voice capture"""
    
    def __init__(self):
        super().__init__()
        self.voice_flow_manager = VoiceFlowManager()
    
    def get(self, request):
        """Generate and return audio tone"""
        try:
            frequency = int(request.GET.get('frequency', 800))
            duration = float(request.GET.get('duration', 0.5))
            
            tone_result = self.voice_flow_manager.voice_processor.generate_tone(
                frequency, duration
            )
            
            if tone_result['success']:
                response = HttpResponse(
                    tone_result['tone_data'],
                    content_type='audio/wav'
                )
                response['Content-Disposition'] = 'attachment; filename="tone.wav"'
                return response
            else:
                return JsonResponse({'error': 'Tone generation failed'}, status=500)
                
        except Exception as e:
            logger.error(f"Tone generation error: {str(e)}")
            return JsonResponse({'error': 'Tone generation failed'}, status=500)


class ExamResultsView(View):
    """View exam results and session details"""
    
    def get(self, request, session_id):
        """Display exam results"""
        try:
            session = get_object_or_404(ExamSession, session_id=session_id)
            
            # Get all responses for this session
            responses = session.responses.all().select_related('question').order_by('question__order')
            
            # Calculate detailed statistics
            total_questions = session.exam.get_total_questions()
            answered_questions = responses.count()
            correct_answers = responses.filter(is_correct=True).count()
            
            context = {
                'session': session,
                'responses': responses,
                'total_questions': total_questions,
                'answered_questions': answered_questions,
                'correct_answers': correct_answers,
                'accuracy_percentage': (correct_answers / answered_questions * 100) if answered_questions > 0 else 0,
                'completion_percentage': (answered_questions / total_questions * 100) if total_questions > 0 else 0
            }
            
            return render(request, 'exam/exam_results.html', context)
            
        except ExamSession.DoesNotExist:
            return render(request, 'exam/session_not_found.html', status=404)
        except Exception as e:
            logger.error(f"Results view error: {str(e)}")
            return render(request, 'exam/error.html', {'error': 'Failed to load results'}, status=500)


class SessionListView(View):
    """List all exam sessions for monitoring"""
    
    def get(self, request):
        """Display list of exam sessions"""
        try:
            # Get recent sessions
            sessions = ExamSession.objects.select_related('exam', 'exam__subject').order_by('-started_at')[:50]
            
            context = {
                'sessions': sessions,
                'active_sessions': sessions.filter(current_state__in=['student_name', 'student_grade', 'exam_briefing', 'question_reading', 'answer_capture', 'answer_confirmation']),
                'completed_sessions': sessions.filter(current_state='exam_complete')
            }
            
            return render(request, 'exam/session_list.html', context)
            
        except Exception as e:
            logger.error(f"Session list error: {str(e)}")
            return render(request, 'exam/error.html', {'error': 'Failed to load sessions'}, status=500)