from django.urls import path
from django.contrib import admin
from . import views

app_name = 'exam'

urlpatterns = [
    # Main exam interface
    path('', views.ExamSessionView.as_view(), name='exam_session'),
    
    # Voice processing endpoints
    path('voice/process/', views.VoiceProcessingView.as_view(), name='voice_process'),
    path('voice/tts/', views.TTSView.as_view(), name='text_to_speech'),
    path('voice/tone/', views.ToneGeneratorView.as_view(), name='tone_generator'),
    
    # Session management
    path('session/state/', views.SessionStateView.as_view(), name='session_state'),
    path('session/list/', views.SessionListView.as_view(), name='session_list'),
    
    # Results and monitoring
    path('results/<str:session_id>/', views.ExamResultsView.as_view(), name='exam_results'),
    
    # Admin interface
    path('admin/', admin.site.urls),
]

